"""
Command handlers for the Just Ask AI Telegram bot.
"""
import json

from telegram import Update, ChatAction, ParseMode
from telegram.ext import CallbackContext

from src.services.gemini_service import get_gemini_service
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_response_template, create_bold_text, create_italic_text

logger = get_logger(__name__)
gemini_service = get_gemini_service()


def start_command(update: Update, context: CallbackContext) -> None:
    """Handle the /start command.

    Args:
        update: Update object
        context: Context object
    """
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")

    # Create welcome message with Markdown formatting
    title = f"👋 Hello, {user.first_name}!"
    body = (
        f"I'm {create_bold_text('Just Ask AI')}, powered by Google's Gemini API.\n\n"
        f"{create_bold_text('I can help you with:')}\n"
        "• Answering questions and having conversations\n"
        "• Translating text between languages\n"
        "• Summarizing long texts\n"
        "• Generating creative content\n"
        "• Searching the web for information\n"
        "• Setting reminders and notifications\n"
        "• Personalizing responses to your preferences"
    )

    footer = "Select a category below or just ask me something!"

    # Create quick action buttons
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

    # Create response template
    response = create_response_template(
        title=title,
        body=body,
        footer=footer,
        buttons=buttons
    )

    # Send welcome message with buttons
    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command.

    Args:
        update: Update object
        context: Context object
    """
    logger.info(f"User {update.effective_user.id} requested help")

    # Create help message with Markdown formatting
    title = "🤖 Just Ask AI - Available Commands"

    # Create buttons for command categories
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
            {'text': "📱 Show All Commands", 'callback_data': "help:all"}
        ]
    ]

    # Create response template
    response = create_response_template(
        title=title,
        body="Select a category to see available commands or 'Show All Commands' to view everything at once.",
        footer="You can also just send me a message and I'll do my best to respond!",
        buttons=buttons
    )

    # Send help message with buttons
    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def translate_command(update: Update, context: CallbackContext) -> None:
    """Handle the /translate command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used translate command")

    # Get command arguments
    text = " ".join(context.args)

    if not text:
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
            ]
        ]

        # Create response template
        response = create_response_template(
            title="🌎 Translation",
            body="Please provide text to translate and the target language.\n\nExample: /translate Hello to Spanish\n\nOr select a language below and then send the text you want to translate.",
            buttons=buttons
        )

        # Send message with buttons
        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
        return

    # Check if the text contains "to" to specify the target language
    if " to " in text.lower():
        text_parts = text.lower().split(" to ", 1)
        text_to_translate = text_parts[0].strip()
        target_language = text_parts[1].strip()

        # Send typing action
        update.message.chat.send_action(action=ChatAction.TYPING)

        # Translate text
        translated_text = gemini_service.translate_text(
            text=text_to_translate,
            target_language=target_language
        )

        # Generate a unique message ID for feedback
        message_id = f"tr_{user_id}_{target_language[:2]}"

        # Create feedback buttons
        from src.handlers.feedback_handlers import add_feedback_buttons
        buttons = add_feedback_buttons(message_id)

        # Create response template
        response = create_response_template(
            title=f"🌐 Translation to {target_language}",
            body=translated_text,
            buttons=buttons,
            is_gemini_response=True  # This will format the Gemini response for HTML
        )

        # Send translation with feedback buttons
        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
    else:
        update.message.reply_text(
            "Please specify the target language using 'to'.\n"
            "Example: /translate Hello to Spanish"
        )


def summarize_command(update: Update, context: CallbackContext) -> None:
    """Handle the /summarize command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used summarize command")

    # Get command arguments
    text = " ".join(context.args)

    if not text:
        # Check if the command is a reply to a message
        if update.message.reply_to_message and update.message.reply_to_message.text:
            text = update.message.reply_to_message.text
        else:
            # Create buttons for summary length options
            buttons = [
                [
                    {'text': "Short Summary", 'callback_data': "sum:short"},
                    {'text': "Medium Summary", 'callback_data': "sum:medium"}
                ],
                [
                    {'text': "Detailed Summary", 'callback_data': "sum:detailed"},
                    {'text': "Key Points Only", 'callback_data': "sum:key"}
                ]
            ]

            # Create response template
            response = create_response_template(
                title="📋 Text Summarization",
                body="Please provide text to summarize or reply to a message with /summarize.\n\nYou can also select a summary style below and then send the text you want to summarize.",
                buttons=buttons
            )

            # Send message with buttons
            update.message.reply_text(
                text=response['text'],
                parse_mode=response['parse_mode'],
                reply_markup=response['reply_markup']
            )
            return

    # Send typing action
    update.message.chat.send_action(action=ChatAction.TYPING)

    # Summarize text
    summary = gemini_service.summarize_text(text=text)

    # Generate a unique message ID for feedback
    message_id = f"sum_{user_id}_{len(text) % 100}"

    # Create feedback buttons
    from src.handlers.feedback_handlers import add_feedback_buttons
    buttons = add_feedback_buttons(message_id)

    # Create response template
    response = create_response_template(
        title="📝 Summary",
        body=summary,
        buttons=buttons,
        is_gemini_response=True  # This will format the Gemini response for HTML
    )

    # Send summary with feedback buttons
    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def generate_command(update: Update, context: CallbackContext) -> None:
    """Handle the /generate command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used generate command")

    # Get command arguments
    args = context.args

    if not args or len(args) < 2:
        # Create buttons for content types
        buttons = [
            [
                {'text': "🌿 Poem", 'callback_data': "gen:poem"},
                {'text': "📖 Story", 'callback_data': "gen:story"}
            ],
            [
                {'text': "😄 Joke", 'callback_data': "gen:joke"},
                {'text': "💻 Code", 'callback_data': "gen:code"}
            ]
        ]

        # Create response template
        response = create_response_template(
            title="✨ Content Generation",
            body="Please specify what to generate.\n\nExample: /generate poem about nature\n\nOr select a content type below and then send your topic.",
            buttons=buttons
        )

        # Send message with buttons
        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
        return

    content_type = args[0].lower()
    prompt = " ".join(args[1:])

    valid_types = ["poem", "story", "joke", "code"]

    if content_type not in valid_types:
        update.message.reply_text(
            f"Invalid content type. Please choose from: {', '.join(valid_types)}"
        )
        return

    # Send typing action
    update.message.chat.send_action(action=ChatAction.TYPING)

    # Generate content
    generated_content = gemini_service.generate_creative_content(
        prompt=prompt,
        content_type=content_type
    )

    # Generate a unique message ID for feedback
    message_id = f"gen_{user_id}_{content_type}"

    # Create feedback buttons
    from src.handlers.feedback_handlers import add_feedback_buttons
    buttons = add_feedback_buttons(message_id)

    # Add regenerate button
    regenerate_button = {'text': "🔄 Regenerate",
                         'callback_data': f"regen:{content_type}:{prompt[:10]}"}
    buttons[0].append(regenerate_button)

    # Create response template
    response = create_response_template(
        title=f"✨ Generated {content_type}",
        body=generated_content,
        buttons=buttons,
        is_gemini_response=True  # This will format the Gemini response for HTML
    )

    # Send generated content with feedback buttons
    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def reset_command(update: Update, context: CallbackContext) -> None:
    """Handle the /reset command to reset conversation history.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} reset conversation history")

    # Create confirmation buttons
    buttons = [
        [
            {'text': "Yes, reset history", 'callback_data': "reset:confirm"},
            {'text': "No, keep history", 'callback_data': "reset:cancel"}
        ]
    ]

    # Create response template
    response = create_response_template(
        title="🔄 Reset Conversation",
        body="Are you sure you want to reset our conversation history? This will clear all previous messages and context.",
        buttons=buttons
    )

    # Send confirmation message with buttons
    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )

    # Store the reset intent in user_data for the callback handler
    context.user_data["reset_pending"] = True
