"""
Google Gemini API service for the Just Ask AI Telegram bot.
"""
import re
from typing import Dict, List, Optional, Union

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from src.config.settings import get_settings
from src.services.scraper_search_service import get_scraper_search_service
from src.utils.database_new import get_db_manager
from src.utils.datetime_utils import get_datetime_context_string
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class GeminiService:
    """Google Gemini API service."""

    def __init__(self):
        """Initialize Gemini service."""
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.max_history = settings.MAX_CONVERSATION_HISTORY

        # Get services
        self.search_service = get_scraper_search_service()
        self.db_manager = get_db_manager()

        # Configure the Gemini API
        genai.configure(api_key=self.api_key)

        # Get the model
        self.model = genai.GenerativeModel(self.model_name)

        # Default generation config
        self.default_config = GenerationConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )

        logger.info(
            f"Initialized Gemini service with model: {self.model_name}")

    def generate_text(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        generation_config: Optional[GenerationConfig] = None,
        user_id: Optional[int] = None
    ) -> str:
        """Generate text using the Gemini API.

        Args:
            prompt: User prompt
            conversation_history: Conversation history
            generation_config: Generation configuration
            user_id: User ID for applying preferences

        Returns:
            Generated text
        """
        try:
            # Use default config if not provided
            if generation_config is None:
                generation_config = self.default_config

            # Apply user preferences if user_id is provided
            if user_id is not None:
                prompt = self.apply_user_preferences(prompt, user_id)

            # Create chat session
            chat = self.model.start_chat(history=[])

            # Add conversation history if provided
            if conversation_history:
                # Limit history to max_history
                if len(conversation_history) > self.max_history:
                    conversation_history = conversation_history[-self.max_history:]

                # Add history to chat
                for message in conversation_history:
                    role = message.get("role", "user")
                    content = message.get("content", "")

                    if role == "user":
                        chat.send_message(content)
                    elif role == "assistant":
                        # We need to manually add assistant messages to history
                        chat.history.append({
                            "role": "model",
                            "parts": [content]
                        })

            # Generate response
            response = chat.send_message(
                prompt,
                generation_config=generation_config
            )

            return response.text

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}"

    def apply_user_preferences(self, prompt: str, user_id: int) -> str:
        """Apply user preferences to the prompt.

        Args:
            prompt: Original prompt
            user_id: User ID

        Returns:
            Modified prompt with user preferences
        """
        try:
            # Get user preferences from database
            preferences = self.db_manager.get_user_preferences(user_id)

            if not preferences:
                return prompt

            # Build preference instructions
            preference_instructions = "User preferences:\n"

            # Apply language preference
            if "language" in preferences:
                preference_instructions += f"- Respond in {preferences['language']} language when appropriate\n"

            # Apply tone preference
            if "tone" in preferences:
                preference_instructions += f"- Use a {preferences['tone'].lower()} tone in your response\n"

            # Apply length preference
            if "length" in preferences:
                length = preferences['length'].lower()
                if "very short" in length:
                    preference_instructions += "- Keep your response very brief and concise\n"
                elif "short" in length:
                    preference_instructions += "- Keep your response brief\n"
                elif "medium" in length:
                    preference_instructions += "- Provide a moderately detailed response\n"
                elif "detailed" in length:
                    preference_instructions += "- Provide a detailed response\n"
                elif "comprehensive" in length:
                    preference_instructions += "- Provide a comprehensive and thorough response\n"

            # Apply expertise preference
            if "expertise" in preferences:
                expertise = preferences['expertise'].lower()
                if "beginner" in expertise:
                    preference_instructions += "- Explain concepts in simple terms for beginners\n"
                elif "intermediate" in expertise:
                    preference_instructions += "- Use intermediate-level explanations\n"
                elif "advanced" in expertise:
                    preference_instructions += "- Use advanced terminology and concepts\n"
                elif "expert" in expertise:
                    preference_instructions += "- Use expert-level terminology and detailed technical explanations\n"
                elif "technical" in expertise:
                    preference_instructions += "- Include technical details in your response\n"

            # Apply interests preference
            if "interests" in preferences:
                interests = preferences['interests']
                preference_instructions += f"- When relevant, include information related to the user's interests: {interests}\n"

            # Combine preference instructions with the original prompt
            enhanced_prompt = f"{preference_instructions}\n\nUser query: {prompt}\n\nPlease respond to the query according to the user preferences above. If a preference doesn't apply to this specific query, you can ignore it."

            return enhanced_prompt
        except Exception as e:
            logger.error(f"Error applying user preferences: {e}")
            return prompt

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text to the target language.

        Args:
            text: Text to translate
            target_language: Target language

        Returns:
            Translated text
        """
        prompt = f"Translate the following text to {target_language}:\n\n{text}"

        return self.generate_text(
            prompt=prompt,
            generation_config=GenerationConfig(
                temperature=0.2,  # Lower temperature for more deterministic output
                max_output_tokens=4096,
            )
        )

    def summarize_text(self, text: str, length: str = "medium", format: str = "paragraph") -> str:
        """Summarize text.

        Args:
            text: Text to summarize
            length: Summary length (short, medium, detailed)
            format: Summary format (paragraph, bullet_points, key_points)

        Returns:
            Summarized text
        """
        # Determine the appropriate prompt based on length and format
        if format == "bullet_points":
            prompt = f"""Summarize the following text in bullet points, extracting the key information. Make it {length} length.

Format your summary with:
- Clear, concise bullet points
- Each bullet point should be a complete thought
- Use sub-bullets for supporting details if needed
- Maintain a consistent structure throughout
- Ensure the most important points are included

Text to summarize:
{text}

Your bullet-point summary:"""
        elif format == "key_points":
            prompt = f"""Extract the key points from the following text. Provide a {length} summary in a numbered list format.

Format your summary with:
1. Clear, numbered points in order of importance
2. Each point should capture a main idea
3. Use concise language while preserving meaning
4. Ensure the summary covers all essential information
5. Make each point easy to understand on its own

Text to summarize:
{text}

Your numbered key points:"""
        else:  # paragraph format
            prompt = f"""Summarize the following text in paragraph form. Provide a {length} length summary.

Format your summary with:
- Clear, well-structured paragraphs
- Logical flow from one idea to the next
- Concise language that preserves the main points
- A cohesive narrative that captures the essence of the original
- Proper transitions between ideas

Text to summarize:
{text}

Your paragraph summary:"""

        return self.generate_text(
            prompt=prompt,
            generation_config=GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
            )
        )

    def generate_creative_content(self, prompt: str, content_type: str) -> str:
        """Generate creative content.

        Args:
            prompt: User prompt
            content_type: Type of content (poem, story, joke, code)

        Returns:
            Generated content
        """
        # Create specific prompts based on content type
        if content_type == "poem":
            enhanced_prompt = f"""Create a beautiful, original poem about {prompt}.

Format your poem with:
- Thoughtful structure and line breaks
- Appropriate stanza divisions
- Consistent style throughout
- Evocative imagery and language
- A meaningful theme or message

Your poem:"""
        elif content_type == "story":
            enhanced_prompt = f"""Create an engaging short story about {prompt}.

Format your story with:
- A clear beginning, middle, and end
- Well-developed characters
- Descriptive settings and scenes
- Proper paragraph breaks
- Dialogue formatted with quotation marks when appropriate
- An interesting plot with some tension or conflict

Your story:"""
        elif content_type == "joke":
            enhanced_prompt = f"""Create a funny, original joke about {prompt}.

Format your joke with:
- A clear setup and punchline
- Appropriate timing and structure
- Clean, family-friendly humor
- Creative wordplay or unexpected twists

Your joke:"""
        elif content_type == "code":
            enhanced_prompt = f"""Write clean, well-documented code related to {prompt}.

Format your code with:
- Clear comments explaining the purpose and functionality
- Proper indentation and formatting
- Descriptive variable and function names
- Efficient and readable implementation
- Example usage if appropriate

Your code:"""
        else:
            enhanced_prompt = f"""Create a {content_type} about {prompt}. Be creative and original.

Make sure your content is:
- Well-structured and formatted
- Easy to read and understand
- Creative and engaging
- Appropriate for all audiences

Your {content_type}:"""

        return self.generate_text(
            prompt=enhanced_prompt,
            generation_config=GenerationConfig(
                temperature=0.9,  # Higher temperature for more creative output
                max_output_tokens=4096,
            )
        )

    def answer_question(self, question: str, use_search: bool = True) -> str:
        """Answer a factual question.

        Args:
            question: Question to answer
            use_search: Whether to use web search for additional information

        Returns:
            Answer to the question
        """
        # First, check the knowledge base
        knowledge_results = self.db_manager.search_knowledge(question)

        # If we have relevant knowledge, use it
        knowledge_context = ""
        if knowledge_results:
            knowledge_context = "Knowledge Base Information:\n\n"
            for item in knowledge_results:
                knowledge_context += f"Q: {item['question']}\nA: {item['answer']}\n\n"

        # If enabled, perform web search
        search_context = ""
        if use_search:
            search_results = self.search_service.search(question)
            if search_results:
                search_context = self.search_service.format_results_for_prompt(
                    search_results)

        # Combine contexts
        context = ""
        if knowledge_context:
            context += knowledge_context + "\n"
        if search_context:
            context += search_context + "\n"

        # Create prompt with context
        if context:
            prompt = f"""I need you to answer the following question using the provided information. If the information doesn't contain the answer, use your own knowledge but make it clear.

Context Information:
{context}

Question: {question}

Answer the question in a well-formatted way with the following guidelines:
1. Use proper paragraphs with line breaks between them
2. If appropriate, use bullet points or numbered lists for clarity
3. For important terms or concepts, use emphasis (but don't overuse it)
4. If providing steps or instructions, number them clearly
5. Make sure the response is easy to read on a mobile device
6. Don't use excessive technical jargon unless the question specifically requires it
7. Format any code snippets, mathematical formulas, or technical information in a clear, readable way
8. If including statistics or data, present them in an organized manner

Your response:"""
        else:
            # No external information found, rely on model's knowledge
            prompt = f"""Answer this question factually and concisely: {question}

If you don't know the answer, please state that clearly rather than making up information. Include relevant details that would be helpful to the user.

Format your response in a well-structured way with the following guidelines:
1. Use proper paragraphs with line breaks between them
2. If appropriate, use bullet points or numbered lists for clarity
3. For important terms or concepts, use emphasis (but don't overuse it)
4. If providing steps or instructions, number them clearly
5. Make sure the response is easy to read on a mobile device
6. Don't use excessive technical jargon unless the question specifically requires it
7. Format any code snippets, mathematical formulas, or technical information in a clear, readable way
8. If including statistics or data, present them in an organized manner

Your response:"""

        return self.generate_text(
            prompt=prompt,
            generation_config=GenerationConfig(
                temperature=0.3,  # Lower temperature for more factual output
                max_output_tokens=2048,
            )
        )

    def detect_question_type(self, text: str) -> str:
        """Detect the type of question.

        Args:
            text: User message

        Returns:
            Question type (factual, opinion, creative, personal, etc.)
        """
        prompt = f"""Analyze the following message and determine what type of question or request it is.
        Respond with ONLY ONE of these categories:
        - FACTUAL: Asking for factual information or answers to knowledge-based questions
        - OPINION: Asking for opinions, advice, or subjective views
        - CREATIVE: Asking for creative content or ideas
        - PERSONAL: Asking about the AI itself or personal questions
        - TRANSLATION: Asking for translation
        - SUMMARIZATION: Asking for summarization
        - CONVERSATION: General conversation or chat
        - OTHER: None of the above

        Message: "{text}"

        Category:"""

        response = self.generate_text(
            prompt=prompt,
            generation_config=GenerationConfig(
                temperature=0.1,
                max_output_tokens=10,
            )
        )

        # Extract just the category
        response = response.strip().upper()
        if "FACTUAL" in response:
            return "FACTUAL"
        elif "OPINION" in response:
            return "OPINION"
        elif "CREATIVE" in response:
            return "CREATIVE"
        elif "PERSONAL" in response:
            return "PERSONAL"
        elif "TRANSLATION" in response:
            return "TRANSLATION"
        elif "SUMMARIZATION" in response:
            return "SUMMARIZATION"
        elif "CONVERSATION" in response:
            return "CONVERSATION"
        else:
            return "OTHER"

    def personalize_response(self, response: str, user_preferences: Dict[str, str]) -> str:
        """Personalize a response based on user preferences.

        Args:
            response: Original response
            user_preferences: User preferences

        Returns:
            Personalized response
        """
        if not user_preferences:
            return response

        # Create a prompt for personalization
        preferences_text = "\n".join(
            [f"{k}: {v}" for k, v in user_preferences.items()])

        prompt = f"""I have a response that needs to be personalized based on user preferences.

Original response: "{response}"

User preferences:
{preferences_text}

Please rewrite the response to match the user's preferences. Keep the same information but adjust the tone, style, and content to better match their preferences. Don't explicitly mention the preferences.

Make sure your response is well-formatted with:
1. Clear paragraph breaks where appropriate
2. Proper use of bullet points or numbered lists if needed
3. Good spacing and organization
4. Emphasis on important points
5. A conversational and engaging style

Your personalized response:"""

        personalized_response = self.generate_text(
            prompt=prompt,
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        return personalized_response


# Create a singleton instance
gemini_service = GeminiService()


def get_gemini_service() -> GeminiService:
    """Get Gemini service instance.

    Returns:
        Gemini service instance
    """
    return gemini_service
