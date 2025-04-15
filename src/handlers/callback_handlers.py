"""
Callback query handlers for the Just Ask AI Telegram bot.
"""
import json
from typing import Dict, Any, Optional

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from src.utils.database_new import get_db_manager
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_inline_keyboard, create_response_template

logger = get_logger(__name__)
db_manager = get_db_manager()


def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handle callback queries from inline keyboards.

    Args:
        update: Update object
        context: CallbackContext object
    """
    query = update.callback_query

    # Get the callback data
    callback_data = query.data
    user_id = update.effective_user.id

    # Log the callback query with detailed information
    logger.info(
        f"Received callback query: '{callback_data}' (type: {type(callback_data)}, length: {len(callback_data)}) from user {user_id}")

    try:
        # Fix for typos in 'pref:view' callback data
        if callback_data.startswith('pref:') and callback_data != 'pref:view':
            # Check if it's a typo of 'pref:view'
            if len(callback_data) >= 8 and callback_data[5:8] in ['viw', 'vew', 'vie', 'viev']:
                logger.warning(
                    f"Fixing typo in callback data: {callback_data} -> pref:view")
                callback_data = 'pref:view'
            # Also check for other common typos
            elif len(callback_data) >= 7 and callback_data[5:7] in ['vi', 've']:
                logger.warning(
                    f"Fixing possible typo in callback data: {callback_data} -> pref:view")
                callback_data = 'pref:view'

        # Check if it's a compact format
        if ':' in callback_data:
            parts = callback_data.split(':')
            prefix = parts[0]

            # Handle different compact formats
            if prefix == 'fb' and len(parts) >= 3:
                # Feedback format: fb:rating:message_id
                rating = int(parts[1])
                message_id = parts[2]

                # Create a data dict for compatibility with existing handler
                data = {
                    'rating': rating,
                    'message_id': message_id
                }

                # Handle feedback
                handle_feedback_callback(update, context, data)
                return

            elif prefix == 'df' and len(parts) >= 3:
                # Detailed feedback format: df:reason:message_id
                reason_code = parts[1]
                message_id = parts[2]

                # Map reason codes to full reasons
                reason_map = {
                    'nh': 'not_helpful',
                    'ic': 'incorrect',
                    'ia': 'inappropriate'
                }

                reason = reason_map.get(reason_code, 'other')

                # Store detailed feedback
                db_manager.store_feedback(
                    user_id=user_id,
                    message_id=message_id,
                    rating=1,  # Negative feedback
                    reason=reason
                )

                # Acknowledge the feedback
                query.answer("Thanks for your detailed feedback!")

                # Remove the buttons
                query.edit_message_reply_markup(reply_markup=None)
                return

            elif prefix == 'cn' and len(parts) >= 2:
                # Cancel format: cn:message_id
                # Just remove the buttons
                query.answer("Cancelled")
                query.edit_message_reply_markup(reply_markup=None)
                return

            elif prefix == 'menu' and len(parts) >= 2:
                # Menu navigation: menu:section
                section = parts[1]
                handle_menu_callback(update, context, section)
                return

            elif prefix == 'help' and len(parts) >= 2:
                # Help section: help:section
                section = parts[1]
                handle_help_callback(update, context, section)
                return

            elif prefix == 'tr' and len(parts) >= 2:
                # Translation language: tr:language_code
                language_code = parts[1]
                handle_translation_callback(update, context, language_code)
                return

            elif prefix == 'sum' and len(parts) >= 2:
                # Summary style: sum:style
                style = parts[1]
                handle_summary_callback(update, context, style)
                return

            elif prefix == 'gen' and len(parts) >= 2:
                # Generate content: gen:content_type
                content_type = parts[1]
                handle_generation_callback(update, context, content_type)
                return

            elif prefix == 'regen' and len(parts) >= 3:
                # Regenerate content: regen:content_type:prompt
                content_type = parts[1]
                prompt_prefix = parts[2]
                handle_regeneration_callback(
                    update, context, content_type, prompt_prefix)
                return

            elif prefix == 'reset' and len(parts) >= 2:
                # Reset confirmation: reset:action
                action = parts[1]
                handle_reset_callback(update, context, action)
                return

            elif prefix == 'pref':
                if len(parts) >= 3:
                    # Preference actions: pref:action:key
                    action = parts[1]
                    key = parts[2]
                    handle_preference_callback(update, context, action, key)
                    return
                elif len(parts) == 2 and parts[1] == 'view':
                    # Special case for pref:view (no key needed)
                    handle_preference_callback(update, context, 'view', '')
                    return

            elif prefix == 'prefval' and len(parts) >= 3:
                # Preference value selection: prefval:key:value
                key = parts[1]
                value = parts[2]
                handle_preference_value_callback(update, context, key, value)
                return

            elif prefix == 'prefcustom' and len(parts) >= 2:
                # Custom preference value: prefcustom:key
                key = parts[1]
                handle_custom_preference_callback(update, context, key)
                return

            elif prefix == 'prefconfirm' and len(parts) >= 3:
                # Preference confirmation: prefconfirm:action:key
                action = parts[1]
                key = parts[2]
                handle_preference_confirmation_callback(
                    update, context, action, key)
                return

        # Try to parse as JSON for other actions
        try:
            data = json.loads(callback_data)
            action = data.get('action')

            # Handle different actions
            if action == 'quick_reply':
                handle_quick_reply_callback(update, context, data)
            elif action == 'more_info':
                handle_more_info_callback(update, context, data)
            elif action == 'cancel':
                handle_cancel_callback(update, context, data)
            else:
                # Unknown action
                query.answer(f"Unknown action: {action}")
                logger.warning(f"Unknown callback action: {action}")
        except json.JSONDecodeError:
            # Not a valid JSON and not a compact format
            logger.warning(f"Invalid callback data format: {callback_data}")
            query.answer("This button is no longer supported.")

    except Exception as e:
        # Handle any other errors
        logger.error(f"Error handling callback query: {e}")
        query.answer("An error occurred while processing your request.")


def handle_feedback_callback(update: Update, context: CallbackContext, data: Dict[str, Any]) -> None:
    """Handle feedback callback queries.

    Args:
        update: Update object
        context: CallbackContext object
        data: Callback data
    """
    query = update.callback_query

    # Get the feedback rating and message_id
    rating = data.get('rating')
    message_id = data.get('message_id')

    if not rating or not message_id:
        query.answer("Invalid feedback data.")
        return

    # Store the feedback in the database
    user_id = update.effective_user.id
    db_manager.store_feedback(user_id, message_id, rating)

    # Acknowledge the feedback
    if rating > 3:
        query.answer("Thanks for the positive feedback!")
    else:
        # For negative feedback, ask for more details
        query.answer(
            "Thanks for your feedback. Would you like to tell us more?")

        # Create buttons for detailed feedback with compact format
        # Use shorter message_id (first 8 chars) to avoid callback_data size limit
        short_id = message_id[:8] if len(message_id) > 8 else message_id

        buttons = [
            [
                {'text': "It wasn't helpful", 'callback_data': f"df:nh:{short_id}"},
                {'text': "It was incorrect", 'callback_data': f"df:ic:{short_id}"}
            ],
            [
                {'text': "It was inappropriate",
                    'callback_data': f"df:ia:{short_id}"},
                {'text': "No thanks", 'callback_data': f"cn:{short_id}"}
            ]
        ]

        # Edit the message to remove the rating buttons and add detailed feedback buttons
        response = create_response_template(
            title="We'd like to improve",
            body="Could you tell us what was wrong with the response?",
            buttons=buttons
        )

        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )


def handle_quick_reply_callback(update: Update, context: CallbackContext, data: Dict[str, Any]) -> None:
    """Handle quick reply callback queries.

    Args:
        update: Update object
        context: CallbackContext object
        data: Callback data
    """
    query = update.callback_query

    # Get the query text
    query_text = data.get('query')

    if not query_text:
        query.answer("Invalid quick reply data.")
        return

    # Acknowledge the button press
    query.answer(f"Sending: {query_text}")

    # Send the query text as a new message
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"/{query_text}"
    )


def handle_more_info_callback(update: Update, context: CallbackContext, data: Dict[str, Any]) -> None:
    """Handle more info callback queries.

    Args:
        update: Update object
        context: CallbackContext object
        data: Callback data
    """
    query = update.callback_query

    # Get the info type
    info_type = data.get('type')

    if not info_type:
        query.answer("Invalid info type.")
        return

    # Acknowledge the button press
    query.answer(f"Showing more information about {info_type}")

    # Handle different info types
    if info_type == 'commands':
        # Show more information about commands
        response = create_response_template(
            title="Available Commands",
            body=(
                "Here are all the available commands:\n\n"
                "/start - Start the bot\n"
                "/help - Show help information\n"
                "/translate - Translate text\n"
                "/summarize - Summarize text\n"
                "/generate - Generate creative content\n"
                "/search - Search the web\n"
                "/ask - Ask a question\n"
                "/learn - Add to knowledge base\n"
                "/preferences - View your preferences\n"
                "/setpreference - Set a preference\n"
                "/deletepreference - Delete a preference\n"
                "/remind - Set a reminder\n"
                "/reminders - View your reminders\n"
                "/cancelreminder - Cancel a reminder\n"
                "/reset - Reset conversation history\n"
                "/feedback - Provide feedback"
            )
        )

        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    elif info_type == 'features':
        # Show more information about features
        response = create_response_template(
            title="Bot Features",
            body=(
                "Just Ask AI can help you with:\n\n"
                "• Answering questions\n"
                "• Translating text\n"
                "• Summarizing content\n"
                "• Generating creative text\n"
                "• Setting reminders\n"
                "• Searching the web\n"
                "• Storing personal preferences\n"
                "• Learning new information"
            )
        )

        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )


def handle_cancel_callback(update: Update, context: CallbackContext, data: Dict[str, Any]) -> None:
    """Handle cancel callback queries.

    Args:
        update: Update object
        context: CallbackContext object
        data: Callback data
    """
    query = update.callback_query

    # Acknowledge the button press
    query.answer("Cancelled")

    # Remove the inline keyboard
    query.edit_message_reply_markup(reply_markup=None)


def handle_menu_callback(update: Update, context: CallbackContext, section: str) -> None:
    """Handle menu navigation callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        section: Menu section to navigate to
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Acknowledge the button press
    query.answer(f"Navigating to {section}")

    if section == "search":
        # Create response for search section
        response = create_response_template(
            title="🔍 Search",
            body="You can search the web for information using the /search command.\n\nExample: /search latest news about AI",
            footer="What would you like to search for?"
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    elif section == "ask":
        # Create response for ask section
        response = create_response_template(
            title="💬 Ask a Question",
            body="You can ask me factual questions using the /ask command.\n\nExample: /ask What is the capital of France?",
            footer="What would you like to know?"
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    elif section == "translate":
        # Create buttons for common languages
        buttons = [
            [
                {'text': "English", 'callback_data': "tr:en"},
                {'text': "Spanish", 'callback_data': "tr:es"},
                {'text': "French", 'callback_data': "tr:fr"}
            ],
            [
                {'text': "German", 'callback_data': "tr:de"},
                {'text': "Italian", 'callback_data': "tr:it"},
                {'text': "Japanese", 'callback_data': "tr:ja"}
            ],
            [
                {'text': "Chinese", 'callback_data': "tr:zh"},
                {'text': "Russian", 'callback_data': "tr:ru"},
                {'text': "Arabic", 'callback_data': "tr:ar"}
            ],
            [
                {'text': "⬅️ Back to Menu", 'callback_data': "menu:main"}
            ]
        ]

        # Create response for translate section
        response = create_response_template(
            title="🌎 Translation",
            body="You can translate text using the /translate command.\n\nExample: /translate Hello to Spanish\n\nOr select a language below and then send the text you want to translate.",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

    elif section == "summarize":
        # Create buttons for summary options
        buttons = [
            [
                {'text': "Short Summary", 'callback_data': "sum:short"},
                {'text': "Medium Summary", 'callback_data': "sum:medium"}
            ],
            [
                {'text': "Detailed Summary", 'callback_data': "sum:detailed"},
                {'text': "Key Points Only", 'callback_data': "sum:key"}
            ],
            [
                {'text': "⬅️ Back to Menu", 'callback_data': "menu:main"}
            ]
        ]

        # Create response for summarize section
        response = create_response_template(
            title="📋 Text Summarization",
            body="You can summarize text using the /summarize command.\n\nExample: /summarize followed by the text you want to summarize\n\nOr select a summary style below and then send the text you want to summarize.",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

    elif section == "reminders":
        # Create response for reminders section
        response = create_response_template(
            title="⏰ Reminders",
            body="You can set reminders using the /remind command.\n\nExamples:\n• /remind Call John in 30 minutes\n• /remind Buy milk tomorrow at 10am\n• /remind Meeting with team on Friday at 2pm\n\nUse /reminders to view your active reminders and /cancelreminder to cancel a reminder.",
            footer="What would you like to be reminded about?"
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    elif section == "preferences":
        # Create response for preferences section
        response = create_response_template(
            title="⚙️ Preferences",
            body="You can view and manage your preferences using these commands:\n\n• /preferences - View your current preferences\n• /setpreference - Set a preference (e.g., /setpreference language Spanish)\n• /deletepreference - Delete a preference (e.g., /deletepreference language)",
            footer="Your preferences help me personalize my responses to you."
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    elif section == "generate":
        # Create buttons for content types
        buttons = [
            [
                {'text': "🌿 Poem", 'callback_data': "gen:poem"},
                {'text': "📖 Story", 'callback_data': "gen:story"}
            ],
            [
                {'text': "😄 Joke", 'callback_data': "gen:joke"},
                {'text': "💻 Code", 'callback_data': "gen:code"}
            ],
            [
                {'text': "⬅️ Back to Menu", 'callback_data': "menu:main"}
            ]
        ]

        # Create response for generate section
        response = create_response_template(
            title="✨ Content Generation",
            body="You can generate creative content using the /generate command.\n\nExample: /generate poem about nature\n\nOr select a content type below and then send your topic.",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

    elif section == "help":
        # Create buttons for help categories
        buttons = [
            [
                {'text': "🔎 Core Commands", 'callback_data': "help:core"},
                {'text': "📄 Info Retrieval", 'callback_data': "help:info"}
            ],
            [
                {'text': "💻 Personalization", 'callback_data': "help:personal"},
                {'text': "⏰ Task Automation", 'callback_data': "help:tasks"}
            ],
            [
                {'text': "📱 Show All Commands", 'callback_data': "help:all"},
                {'text': "⬅️ Back to Menu", 'callback_data': "menu:main"}
            ]
        ]

        # Create response for help section
        response = create_response_template(
            title="🤖 Just Ask AI - Available Commands",
            body="Select a category to see available commands or 'Show All Commands' to view everything at once.",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

    elif section == "main":
        # Create main menu buttons
        buttons = [
            [
                {'text': "🔍 Search", 'callback_data': "menu:search"},
                {'text': "💬 Ask", 'callback_data': "menu:ask"}
            ],
            [
                {'text': "🔄 Translate", 'callback_data': "menu:translate"},
                {'text': "📋 Summarize", 'callback_data': "menu:summarize"}
            ],
            [
                {'text': "⏰ Reminders", 'callback_data': "menu:reminders"},
                {'text': "⚙️ Preferences", 'callback_data': "menu:preferences"}
            ],
            [
                {'text': "✨ Generate Content", 'callback_data': "menu:generate"}
            ],
            [
                {'text': "📖 Help & Commands", 'callback_data': "menu:help"}
            ]
        ]

        # Get user's first name
        first_name = update.effective_user.first_name

        # Create response for main menu
        response = create_response_template(
            title=f"👋 Hello, {first_name}!",
            body=f"I'm Just Ask AI, powered by Google's Gemini API.\n\nI can help you with a variety of tasks. Select an option below to learn more or just ask me something!",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

    else:
        # Unknown section
        query.answer("Unknown section")


def handle_help_callback(update: Update, context: CallbackContext, section: str) -> None:
    """Handle help section callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        section: Help section to display
    """
    query = update.callback_query

    # Acknowledge the button press
    query.answer(f"Showing {section} commands")

    # Back button for all sections
    back_button = [
        {'text': "⬅️ Back to Help Menu", 'callback_data': "help:back"}]

    if section == "core":
        # Create response for core commands
        response = create_response_template(
            title="🔎 Core Commands",
            body="/start - Start the bot\n/help - Show this help message\n/translate - Translate text (usage: /translate Hello to Spanish)\n/summarize - Summarize text (usage: /summarize followed by the text)\n/generate - Generate creative content (usage: /generate poem about nature)\n/reset - Reset conversation history",
            buttons=[back_button]
        )

    elif section == "info":
        # Create response for info retrieval commands
        response = create_response_template(
            title="📄 Information Retrieval",
            body="/search - Search the web (usage: /search latest news about AI)\n/ask - Ask a factual question (usage: /ask What is the capital of France?)\n/learn - Add to knowledge base (usage: /learn Question | Answer)",
            buttons=[back_button]
        )

    elif section == "personal":
        # Create response for personalization commands
        response = create_response_template(
            title="💻 Personalization",
            body="/preferences - View your preferences\n/setpreference - Set a preference (usage: /setpreference language Spanish)\n/deletepreference - Delete a preference (usage: /deletepreference language)",
            buttons=[back_button]
        )

    elif section == "tasks":
        # Create response for task automation commands
        response = create_response_template(
            title="⏰ Task Automation",
            body="/remind - Set a reminder (usage: /remind Call John in 30 minutes)\n/reminders - View your active reminders\n/cancelreminder - Cancel a reminder (usage: /cancelreminder 123)",
            buttons=[back_button]
        )

    elif section == "all":
        # Create response for all commands
        response = create_response_template(
            title="🤖 All Available Commands",
            body="Core Commands:\n/start - Start the bot\n/help - Show this help message\n/translate - Translate text\n/summarize - Summarize text\n/generate - Generate creative content\n/reset - Reset conversation history\n\nInformation Retrieval:\n/search - Search the web\n/ask - Ask a factual question\n/learn - Add to knowledge base\n\nPersonalization:\n/preferences - View your preferences\n/setpreference - Set a preference\n/deletepreference - Delete a preference\n\nTask Automation:\n/remind - Set a reminder\n/reminders - View your active reminders\n/cancelreminder - Cancel a reminder\n\nFeedback:\n/feedback - Provide feedback about the bot",
            buttons=[back_button]
        )

    elif section == "back":
        # Go back to help menu
        return handle_menu_callback(update, context, "help")

    else:
        # Unknown section
        query.answer("Unknown help section")
        return

    # Edit message with new content
    query.edit_message_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def handle_translation_callback(update: Update, context: CallbackContext, language_code: str) -> None:
    """Handle translation language selection callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        language_code: Language code selected
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Map language codes to full names
    language_map = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'ja': 'Japanese',
        'zh': 'Chinese',
        'ru': 'Russian',
        'ar': 'Arabic'
    }

    language_name = language_map.get(language_code, language_code)

    # Acknowledge the button press
    query.answer(f"Selected {language_name}")

    # Store the selected language in user_data for later use
    context.user_data["translation_target"] = language_name

    # Create response asking for text to translate
    response = create_response_template(
        title=f"🌎 Translation to {language_name}",
        body="Please send the text you want to translate.",
        footer=f"Your text will be translated to {language_name}."
    )

    # Edit message with new content
    query.edit_message_text(
        text=response['text'],
        parse_mode=response['parse_mode']
    )


def handle_summary_callback(update: Update, context: CallbackContext, style: str) -> None:
    """Handle summary style selection callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        style: Summary style selected
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Acknowledge the button press
    query.answer(f"Selected {style} summary style")

    # Store the selected style in user_data for later use
    context.user_data["summary_style"] = style

    # Create response asking for text to summarize
    response = create_response_template(
        title=f"📋 {style.capitalize()} Summary",
        body="Please send the text you want to summarize.",
        footer=f"Your text will be summarized in {style} style."
    )

    # Edit message with new content
    query.edit_message_text(
        text=response['text'],
        parse_mode=response['parse_mode']
    )


def handle_generation_callback(update: Update, context: CallbackContext, content_type: str) -> None:
    """Handle content type selection callbacks for generation.

    Args:
        update: Update object
        context: CallbackContext object
        content_type: Content type selected
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Acknowledge the button press
    query.answer(f"Selected {content_type} generation")

    # Store the selected content type in user_data for later use
    context.user_data["generation_type"] = content_type

    # Create response asking for topic
    response = create_response_template(
        title=f"✨ Generate {content_type.capitalize()}",
        body=f"Please send the topic for your {content_type}.",
        footer=f"I'll generate a {content_type} based on your topic."
    )

    # Edit message with new content
    query.edit_message_text(
        text=response['text'],
        parse_mode=response['parse_mode']
    )


def handle_regeneration_callback(update: Update, context: CallbackContext, content_type: str, prompt_prefix: str) -> None:
    """Handle regeneration callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        content_type: Content type to regenerate
        prompt_prefix: Prefix of the original prompt
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Acknowledge the button press
    query.answer(f"Regenerating {content_type}...")

    # Import here to avoid circular imports
    from src.services.gemini_service import get_gemini_service
    gemini_service = get_gemini_service()

    # Try to find the full prompt from user_data or use the prefix
    prompt = context.user_data.get("last_generation_prompt", prompt_prefix)

    # Send typing action
    context.bot.send_chat_action(chat_id=user_id, action="typing")

    # Generate new content
    generated_content = gemini_service.generate_creative_content(
        prompt=prompt,
        content_type=content_type
    )

    # Generate a unique message ID for feedback
    message_id = f"regen_{user_id}_{content_type}"

    # Create feedback buttons
    from src.handlers.feedback_handlers import add_feedback_buttons
    buttons = add_feedback_buttons(message_id)

    # Add regenerate button
    regenerate_button = {'text': "🔄 Regenerate",
                         'callback_data': f"regen:{content_type}:{prompt_prefix}"}
    buttons[0].append(regenerate_button)

    # Create response template
    response = create_response_template(
        title=f"✨ Regenerated {content_type}",
        body=generated_content,
        buttons=buttons,
        is_gemini_response=True  # This will format the Gemini response for HTML
    )

    # Send as a new message instead of editing
    context.bot.send_message(
        chat_id=user_id,
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def handle_reset_callback(update: Update, context: CallbackContext, action: str) -> None:
    """Handle reset confirmation callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        action: Confirmation action (confirm or cancel)
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Check if reset is pending
    if not context.user_data.get("reset_pending", False):
        query.answer("No reset pending")
        return

    if action == "confirm":
        # Clear conversation history
        if "conversation_history" in context.user_data:
            context.user_data["conversation_history"] = []

        # Acknowledge the confirmation
        query.answer("Conversation history has been reset")

        # Update the message
        response = create_response_template(
            title="🔄 Conversation Reset",
            body="Your conversation history has been reset. Let's start fresh!"
        )

        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    elif action == "cancel":
        # Acknowledge the cancellation
        query.answer("Reset cancelled")

        # Update the message
        response = create_response_template(
            title="Reset Cancelled",
            body="Your conversation history has been preserved."
        )

        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )

    # Clear the pending flag
    context.user_data["reset_pending"] = False


def handle_preference_callback(update: Update, context: CallbackContext, action: str, key: str) -> None:
    """Handle preference-related callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        action: Action to perform (set, delete, view)
        key: Preference key
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Import preference handlers to avoid circular imports
    from src.handlers.preference_handlers import get_preference_emoji, create_bold_text

    # Acknowledge the button press
    query.answer(f"Selected {action} {key}")

    if action == "view":
        # Get user preferences
        preferences = db_manager.get_user_preferences(user_id)

        if not preferences:
            # No preferences to show
            response = create_response_template(
                title="ℹ️ No Preferences",
                body="You don't have any preferences set yet. Select a preference category below to set it.",
                footer="Preferences help me personalize my responses to better match your needs."
            )

            # Edit message with new content
            query.edit_message_text(
                text=response['text'],
                parse_mode=response['parse_mode']
            )
            return

        # Create buttons for preference categories
        buttons = [
            [
                {'text': "🌐 Language", 'callback_data': "pref:set:language"},
                {'text': "🔊 Tone", 'callback_data': "pref:set:tone"}
            ],
            [
                {'text': "📏 Length", 'callback_data': "pref:set:length"},
                {'text': "📚 Expertise", 'callback_data': "pref:set:expertise"}
            ],
            [
                {'text': "🎯 Interests", 'callback_data': "pref:set:interests"}
            ]
        ]

        # Add delete buttons
        delete_buttons = []
        for pref_key in preferences.keys():
            emoji = get_preference_emoji(pref_key)
            delete_buttons.append(
                {'text': f"🗑️ Delete {emoji} {pref_key.capitalize()}", 'callback_data': f"pref:delete:{pref_key}"})

        # Organize delete buttons into rows of 2
        delete_rows = []
        for i in range(0, len(delete_buttons), 2):
            row = delete_buttons[i:i+2]
            delete_rows.append(row)

        # Add delete rows to buttons
        if delete_rows:
            buttons.extend(delete_rows)

        # Create body text
        body = "Your current preferences:\n\n"
        for pref_key, value in preferences.items():
            emoji = get_preference_emoji(pref_key)
            body += f"• {emoji} {create_bold_text(pref_key.capitalize())}: {value}\n"

        body += "\nSelect a preference to change it or delete it."

        # Create response template
        response = create_response_template(
            title="⚙️ Preference Settings",
            body=body,
            footer="Preferences help me personalize my responses to better match your needs.",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

    elif action == "set":
        # Show options for the selected preference
        preference_options = get_preference_options(key)

        # Create buttons for preference options
        buttons = []
        for option in preference_options:
            buttons.append(
                [{'text': option, 'callback_data': f"prefval:{key}:{option}"}])

        # Add custom option button
        buttons.append(
            [{'text': "✏️ Custom Value", 'callback_data': f"prefcustom:{key}"}])

        # Add back button
        buttons.append(
            [{'text': "⬅️ Back to Preferences", 'callback_data': "pref:view"}])

        # Create response template
        response = create_response_template(
            title=f"{get_preference_emoji(key)} Set {key.capitalize()} Preference",
            body=f"Select a value for your {key} preference or choose 'Custom Value' to enter your own.",
            footer=get_preference_description(key),
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )

        # Store that we're waiting for a custom value if the user selects that option
        context.user_data["waiting_for_preference"] = key

    elif action == "delete":
        # Show confirmation for deletion
        current_value = db_manager.get_user_preference(user_id, key)

        if current_value is None:
            # Preference doesn't exist anymore
            query.answer("This preference no longer exists.")

            # Go back to view preferences
            handle_preference_callback(update, context, "view", "")
            return

        # Create confirmation buttons
        buttons = [
            [
                {'text': "Yes, delete it", 'callback_data': f"prefconfirm:delete:{key}"},
                {'text': "No, keep it", 'callback_data': "pref:view"}
            ]
        ]

        # Create response template
        emoji = get_preference_emoji(key)
        response = create_response_template(
            title=f"🗑️ Delete {key.capitalize()} Preference",
            body=f"Are you sure you want to delete your {emoji} {create_bold_text(key.capitalize())} preference?\n\nCurrent value: {current_value}",
            footer="This action cannot be undone.",
            buttons=buttons
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )


def get_preference_options(preference_key: str) -> list:
    """Get predefined options for a preference key.

    Args:
        preference_key: Preference key

    Returns:
        List of predefined options
    """
    options_map = {
        "language": ["English", "Spanish", "French", "German", "Chinese", "Japanese", "Russian", "Arabic"],
        "tone": ["Formal", "Professional", "Casual", "Friendly", "Technical", "Simple"],
        "length": ["Very Short", "Short", "Medium", "Detailed", "Comprehensive"],
        "expertise": ["Beginner", "Intermediate", "Advanced", "Expert", "Technical"],
        "interests": ["Technology", "Science", "Arts", "Business", "Sports", "Health", "Education"]
    }

    return options_map.get(preference_key.lower(), [])


def get_preference_description(preference_key: str) -> str:
    """Get description for a preference key.

    Args:
        preference_key: Preference key

    Returns:
        Description of the preference
    """
    description_map = {
        "language": "This sets your preferred language for responses. I'll try to respond in this language when appropriate.",
        "tone": "This sets how formal or casual you want my responses to be.",
        "length": "This sets how detailed you want my responses to be. Choose 'Short' for brief answers or 'Comprehensive' for detailed explanations.",
        "expertise": "This sets the technical level of my responses. Choose 'Beginner' for simpler explanations or 'Expert' for more technical details.",
        "interests": "This helps me personalize content based on topics you care about. You can list multiple interests separated by commas."
    }

    return description_map.get(preference_key.lower(), "This preference helps personalize my responses to better match your needs.")


def handle_preference_value_callback(update: Update, context: CallbackContext, key: str, value: str) -> None:
    """Handle preference value selection callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        key: Preference key
        value: Selected preference value
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Import preference handlers to avoid circular imports
    from src.handlers.preference_handlers import get_preference_emoji, create_bold_text

    # Acknowledge the button press
    query.answer(f"Setting {key} to {value}")

    # Set the preference
    success = db_manager.set_user_preference(user_id, key, value)

    if success:
        # Get emoji for the preference
        emoji = get_preference_emoji(key)

        # Create response with current preferences
        preferences = db_manager.get_user_preferences(user_id)
        preferences_text = "\n\nYour current preferences:\n"
        for pref_key, pref_value in preferences.items():
            pref_emoji = get_preference_emoji(pref_key)
            preferences_text += f"\n• {pref_emoji} {create_bold_text(pref_key.capitalize())}: {pref_value}"

        # Create buttons for other preferences
        valid_keys = ["language", "tone", "length", "expertise", "interests"]
        buttons = []
        for pref_key in valid_keys:
            if pref_key != key:  # Don't show the one we just set
                key_emoji = get_preference_emoji(pref_key)
                buttons.append({'text': f"Set {key_emoji} {pref_key.capitalize()}",
                               'callback_data': f"pref:set:{pref_key}"})

        # Organize buttons into rows of 2
        button_rows = []
        for i in range(0, len(buttons), 2):
            row = buttons[i:i+2]
            button_rows.append(row)

        # Add view all preferences button
        button_rows.append(
            [{'text': "📑 View All Preferences", 'callback_data': "pref:view"}])

        response = create_response_template(
            title=f"✅ Preference Updated",
            body=f"Your {emoji} {create_bold_text(key.capitalize())} preference has been set to '{value}'.{preferences_text}",
            footer="These preferences will be used to personalize my responses.",
            buttons=button_rows
        )

        # Edit message with new content
        query.edit_message_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
    else:
        # Show error message
        query.answer("Failed to set preference. Please try again.")

        # Go back to preference selection
        handle_preference_callback(update, context, "set", key)


def handle_custom_preference_callback(update: Update, context: CallbackContext, key: str) -> None:
    """Handle custom preference value callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        key: Preference key
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Import preference handlers to avoid circular imports
    from src.handlers.preference_handlers import get_preference_emoji

    # Acknowledge the button press
    query.answer("Please enter your custom value")

    # Store that we're waiting for a custom value
    context.user_data["waiting_for_preference"] = key

    # Create response asking for custom value
    emoji = get_preference_emoji(key)
    response = create_response_template(
        title=f"{emoji} Custom {key.capitalize()} Value",
        body=f"Please send a message with your custom value for the {key} preference.",
        footer=get_preference_description(key)
    )

    # Edit message with new content
    query.edit_message_text(
        text=response['text'],
        parse_mode=response['parse_mode']
    )


def handle_preference_confirmation_callback(update: Update, context: CallbackContext, action: str, key: str) -> None:
    """Handle preference confirmation callbacks.

    Args:
        update: Update object
        context: CallbackContext object
        action: Action to confirm (delete)
        key: Preference key
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Import preference handlers to avoid circular imports
    from src.handlers.preference_handlers import get_preference_emoji, create_bold_text

    if action == "delete":
        # Delete the preference
        success = db_manager.delete_user_preference(user_id, key)

        if success:
            # Acknowledge the deletion
            query.answer(f"{key.capitalize()} preference deleted")

            # Get emoji for the preference
            emoji = get_preference_emoji(key)

            # Get remaining preferences
            remaining_preferences = db_manager.get_user_preferences(user_id)

            # Create buttons for remaining preferences or setting new ones
            buttons = []

            if remaining_preferences:
                # Show remaining preferences that can be deleted
                for pref_key in remaining_preferences.keys():
                    key_emoji = get_preference_emoji(pref_key)
                    buttons.append(
                        [{'text': f"🗑️ Delete {key_emoji} {pref_key.capitalize()}", 'callback_data': f"pref:delete:{pref_key}"}])

                # Add view all preferences button
                buttons.append(
                    [{'text': "📑 View All Preferences", 'callback_data': "pref:view"}])

                # Create response with remaining preferences
                preferences_text = "\n\nYour remaining preferences:\n"
                for pref_key, value in remaining_preferences.items():
                    pref_emoji = get_preference_emoji(pref_key)
                    preferences_text += f"\n• {pref_emoji} {create_bold_text(pref_key.capitalize())}: {value}"
            else:
                # No remaining preferences, show options to set new ones
                valid_keys = ["language", "tone",
                              "length", "expertise", "interests"]
                for pref_key in valid_keys:
                    key_emoji = get_preference_emoji(pref_key)
                    buttons.append(
                        [{'text': f"Set {key_emoji} {pref_key.capitalize()}", 'callback_data': f"pref:set:{pref_key}"}])

                preferences_text = "\n\nYou have no remaining preferences. Select an option above to set a new preference."

            response = create_response_template(
                title=f"✅ Preference Deleted",
                body=f"Your {emoji} {create_bold_text(key.capitalize())} preference has been deleted.{preferences_text}",
                buttons=buttons
            )

            # Edit message with new content
            query.edit_message_text(
                text=response['text'],
                parse_mode=response['parse_mode'],
                reply_markup=response['reply_markup']
            )
        else:
            # Show error message
            query.answer("Failed to delete preference. Please try again.")

            # Go back to preference view
            handle_preference_callback(update, context, "view", "")
