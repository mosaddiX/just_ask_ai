"""
Feedback handlers for the Just Ask AI Telegram bot.
"""
import json
from typing import Dict, Any, Optional

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from src.utils.database_new import get_db_manager
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_response_template

logger = get_logger(__name__)
db_manager = get_db_manager()


def feedback_command(update: Update, context: CallbackContext) -> None:
    """Handle the /feedback command.

    Args:
        update: Update object
        context: CallbackContext object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used feedback command")

    # Create feedback options with compact callback data
    buttons = [
        [
            {'text': "Very satisfied", 'callback_data': "fb:5:general"},
            {'text': "Satisfied", 'callback_data': "fb:4:general"}
        ],
        [
            {'text': "Neutral", 'callback_data': "fb:3:general"}
        ],
        [
            {'text': "Dissatisfied", 'callback_data': "fb:2:general"},
            {'text': "Very dissatisfied", 'callback_data': "fb:1:general"}
        ]
    ]

    response = create_response_template(
        title="How would you rate your experience with Just Ask AI?",
        body="Your feedback helps us improve the bot.",
        buttons=buttons
    )

    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def add_feedback_buttons(message_id: str) -> Dict[str, Any]:
    """Create feedback buttons for a message.

    Args:
        message_id: The message ID to associate with the feedback

    Returns:
        Inline keyboard markup with feedback buttons
    """
    # Use shorter message_id (first 8 chars) to avoid callback_data size limit
    short_id = message_id[:8] if len(message_id) > 8 else message_id

    buttons = [
        [
            {'text': "👍", 'callback_data': f"fb:5:{short_id}"},
            {'text': "👎", 'callback_data': f"fb:1:{short_id}"}
        ]
    ]

    return buttons
