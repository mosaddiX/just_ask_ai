"""
Just Ask AI - Telegram bot powered by Google's Gemini API.
"""
import os
from pathlib import Path
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
)

from src.config.settings import get_settings
from src.handlers.callback_handlers import handle_callback_query
from src.handlers.command_handlers import (
    start_command,
    help_command,
    translate_command,
    summarize_command,
    generate_command,
    reset_command,
)
from src.handlers.feedback_handlers import feedback_command
from src.handlers.info_handlers import (
    search_command,
    ask_command,
    learn_command,
)
from src.handlers.message_handlers import handle_message
from src.handlers.preference_handlers import (
    preferences_command,
    set_preference_command,
    delete_preference_command,
)
from src.handlers.reminder_handlers import (
    remind_command,
    reminders_command,
    cancel_reminder_command,
    setup_reminder_checker,
)
from src.utils.logger import get_logger

# Get settings and logger
settings = get_settings()
logger = get_logger(__name__)


def set_bot_commands(updater):
    """Set bot commands to be displayed in the menu.

    Args:
        updater: Telegram updater object
    """
    bot = updater.bot
    commands = [
        # Core Commands
        ("start", "Start the bot"),
        ("help", "Show help information"),
        ("translate", "Translate text"),
        ("summarize", "Summarize text"),
        ("generate", "Generate creative content"),
        ("reset", "Reset conversation history"),

        # Information Retrieval
        ("search", "Search the web"),
        ("ask", "Ask a question"),
        ("learn", "Add to knowledge base"),

        # Personalization
        ("preferences", "View your preferences"),
        ("setpreference", "Set a preference"),
        ("deletepreference", "Delete a preference"),

        # Task Automation
        ("remind", "Set a reminder"),
        ("reminders", "View your reminders"),
        ("cancelreminder", "Cancel a reminder"),

        # User Experience
        ("feedback", "Provide feedback")
    ]

    # Set commands for the bot
    bot.set_my_commands(commands)
    logger.info("Bot commands menu set up successfully")


def main() -> None:
    """Start the bot."""
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Check if token is available
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error(
            "Telegram bot token not found. Please set TELEGRAM_BOT_TOKEN in .env file.")
        return

    # Check if Gemini API key is available
    if not settings.GEMINI_API_KEY:
        logger.error(
            "Gemini API key not found. Please set GEMINI_API_KEY in .env file.")
        return

    # Create the Updater and pass it your bot's token
    updater = Updater(settings.TELEGRAM_BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add command handlers - Core
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("translate", translate_command))
    dispatcher.add_handler(CommandHandler("summarize", summarize_command))
    dispatcher.add_handler(CommandHandler("generate", generate_command))
    dispatcher.add_handler(CommandHandler("reset", reset_command))

    # Add command handlers - Information Retrieval
    dispatcher.add_handler(CommandHandler("search", search_command))
    dispatcher.add_handler(CommandHandler("ask", ask_command))
    dispatcher.add_handler(CommandHandler("learn", learn_command))

    # Add command handlers - Personalization
    dispatcher.add_handler(CommandHandler("preferences", preferences_command))
    dispatcher.add_handler(CommandHandler(
        "setpreference", set_preference_command))
    dispatcher.add_handler(CommandHandler(
        "deletepreference", delete_preference_command))

    # Add command handlers - Task Automation
    dispatcher.add_handler(CommandHandler("remind", remind_command))
    dispatcher.add_handler(CommandHandler("reminders", reminders_command))
    dispatcher.add_handler(CommandHandler(
        "cancelreminder", cancel_reminder_command))

    # Add command handlers - User Experience
    dispatcher.add_handler(CommandHandler("feedback", feedback_command))

    # Set up reminder checker
    setup_reminder_checker(dispatcher.job_queue)

    # Add message handler
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, handle_message))

    # Add callback query handler
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Set up bot commands menu
    set_bot_commands(updater)

    # Start the Bot
    logger.info("Starting bot...")
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

    logger.info("Bot stopped")


if __name__ == "__main__":
    main()
