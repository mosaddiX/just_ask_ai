"""
Information retrieval handlers for the Just Ask AI Telegram bot.
"""
import uuid

from telegram import Update, ChatAction, ParseMode
from telegram.ext import CallbackContext

from src.handlers.feedback_handlers import add_feedback_buttons
from src.services.gemini_service import GeminiService
from src.services.scraper_search_service import get_scraper_search_service
from src.utils.database_new import get_db_manager
from src.utils.datetime_utils import is_datetime_question, get_datetime_response
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_response_template, create_bold_text, create_link, create_inline_keyboard

logger = get_logger(__name__)
gemini_service = GeminiService()
search_service = get_scraper_search_service()
db_manager = get_db_manager()


def search_command(update: Update, context: CallbackContext) -> None:
    """Handle the /search command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used search command")

    # Get command arguments
    query = " ".join(context.args)

    if not query:
        update.message.reply_text(
            "Please provide a search query.\n"
            "Example: /search latest news about AI"
        )
        return

    # Send typing action
    update.message.chat.send_action(action=ChatAction.TYPING)

    # Check if it's a date/time question first
    if is_datetime_question(query):
        logger.info(f"Detected date/time question in search: {query}")
        response = get_datetime_response(query)

        update.message.reply_text(response)
        return

    # Perform search for non-date/time questions
    results = search_service.search(query)

    if not results:
        # If web search fails, use Gemini to answer the question
        update.message.chat.send_action(action=ChatAction.TYPING)
        answer = gemini_service.answer_question(query, use_search=False)

        # Generate a unique message ID for feedback
        message_id = str(uuid.uuid4())

        # Create feedback buttons
        buttons = add_feedback_buttons(message_id)

        # Create response template with HTML formatting for Gemini response
        response_template = create_response_template(
            title=f"🔍 Search for \"{query}\"",
            body=f"I couldn't find any search results, but here's what I know:\n\n{answer}",
            buttons=buttons,
            is_gemini_response=True  # This will format the Gemini response for HTML
        )

        # Send response with HTML formatting and feedback buttons
        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode'],
            reply_markup=response_template['reply_markup'],
            disable_web_page_preview=True
        )
        return

    # Generate a unique message ID for feedback
    message_id = str(uuid.uuid4())

    # Format results with Markdown
    title = f"🔍 Search results for \"{query}\""
    body = ""

    for i, result in enumerate(results, 1):
        body += f"{i}. {create_bold_text(result['title'])}\n"
        # Format snippet with proper indentation and line breaks
        snippet = result['snippet'].strip()
        # Ensure snippet is not too long
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        body += f"   {snippet}\n"
        body += f"   {create_link('🔗 Source', result['link'])}\n\n"

    # Create feedback buttons
    buttons = add_feedback_buttons(message_id)

    # Create response with feedback buttons
    response_template = create_response_template(
        title=title,
        body=body,
        buttons=buttons
    )

    # Send response with Markdown formatting and feedback buttons
    update.message.reply_text(
        text=response_template['text'],
        parse_mode=response_template['parse_mode'],
        reply_markup=response_template['reply_markup'],
        disable_web_page_preview=True
    )


def ask_command(update: Update, context: CallbackContext) -> None:
    """Handle the /ask command for factual questions.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used ask command")

    # Get command arguments
    question = " ".join(context.args)

    if not question:
        update.message.reply_text(
            "Please provide a question to answer.\n"
            "Example: /ask What is the capital of France?"
        )
        return

    # Send typing action
    update.message.chat.send_action(action=ChatAction.TYPING)

    # Generate a unique message ID for feedback
    message_id = str(uuid.uuid4())

    # Check if it's a date/time question first
    if is_datetime_question(question):
        logger.info(f"Detected date/time question in ask: {question}")
        answer = get_datetime_response(question)
    else:
        # Answer non-date/time question
        answer = gemini_service.answer_question(question)

    # Create feedback buttons
    buttons = add_feedback_buttons(message_id)

    # Create response with feedback buttons
    response_template = create_response_template(
        title=f"Q: {question}",
        body=answer,
        buttons=buttons,
        is_gemini_response=True  # This will format the Gemini response for HTML
    )

    # Send response with Markdown formatting and feedback buttons
    update.message.reply_text(
        text=response_template['text'],
        parse_mode=response_template['parse_mode'],
        reply_markup=response_template['reply_markup']
    )


def learn_command(update: Update, context: CallbackContext) -> None:
    """Handle the /learn command to add to knowledge base.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used learn command")

    # Get command arguments
    text = " ".join(context.args)

    if not text:
        update.message.reply_text(
            "Please provide a question and answer to add to the knowledge base.\n"
            "Format: /learn Question | Answer\n"
            "Example: /learn What is Just Ask AI? | Just Ask AI is a Telegram bot powered by Google's Gemini API."
        )
        return

    # Split into question and answer
    parts = text.split("|", 1)

    if len(parts) < 2:
        update.message.reply_text(
            "Please separate the question and answer with a | character.\n"
            "Example: /learn What is Just Ask AI? | Just Ask AI is a Telegram bot powered by Google's Gemini API."
        )
        return

    question = parts[0].strip()
    answer = parts[1].strip()

    # Add to knowledge base
    knowledge_id = db_manager.add_knowledge(question, answer)

    if knowledge_id:
        # Create response with Markdown formatting
        response_template = create_response_template(
            title="✅ Added to knowledge base",
            body=f"Q: {create_bold_text(question)}\n\nA: {answer}"
        )

        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode']
        )
    else:
        # Create error response with Markdown formatting
        response_template = create_response_template(
            title="❌ Failed to add to knowledge base",
            body="Please try again later."
        )

        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode']
        )
