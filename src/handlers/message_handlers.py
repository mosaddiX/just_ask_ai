"""
Message handlers for the Just Ask AI Telegram bot.
"""
from typing import Dict, List

import uuid

from telegram import Update, ChatAction, ParseMode
from telegram.ext import CallbackContext

from src.handlers.feedback_handlers import add_feedback_buttons
from src.services.gemini_service import GeminiService
from src.utils.database_new import get_db_manager
from src.utils.datetime_utils import is_datetime_question, get_datetime_response
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_response_template

logger = get_logger(__name__)
gemini_service = GeminiService()
db_manager = get_db_manager()


def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle user messages.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    user_message = update.message.text

    logger.info(
        f"Received message from user {user_id}: {user_message[:50]}...")

    # Initialize conversation history if it doesn't exist
    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    # Get conversation history
    conversation_history: List[Dict[str, str]
                               ] = context.user_data["conversation_history"]

    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # Send typing action
    update.message.chat.send_action(action=ChatAction.TYPING)

    # Check if there's a pending preference input
    if "waiting_for_preference" in context.user_data:
        # Get the preference key
        preference_key = context.user_data["waiting_for_preference"]
        preference_value = user_message

        # Import preference handlers to avoid circular imports
        from src.handlers.preference_handlers import get_preference_emoji, create_bold_text

        # Set the preference
        success = db_manager.set_user_preference(
            user_id, preference_key, preference_value)

        if success:
            # Get emoji for the preference
            emoji = get_preference_emoji(preference_key)

            # Create response with current preferences
            preferences = db_manager.get_user_preferences(user_id)
            preferences_text = "\n\nYour current preferences:\n"
            for key, value in preferences.items():
                pref_emoji = get_preference_emoji(key)
                preferences_text += f"\n• {pref_emoji} {create_bold_text(key.capitalize())}: {value}"

            # Create buttons for other preferences
            valid_keys = ["language", "tone",
                          "length", "expertise", "interests"]
            buttons = []
            for key in valid_keys:
                if key != preference_key:  # Don't show the one we just set
                    key_emoji = get_preference_emoji(key)
                    buttons.append(
                        {'text': f"Set {key_emoji} {key.capitalize()}", 'callback_data': f"pref:set:{key}"})

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
                body=f"Your {emoji} {create_bold_text(preference_key.capitalize())} preference has been set to '{preference_value}'.{preferences_text}",
                footer="These preferences will be used to personalize my responses.",
                buttons=button_rows
            )

            # Send response with buttons
            update.message.reply_text(
                text=response['text'],
                parse_mode=response['parse_mode'],
                reply_markup=response['reply_markup']
            )
        else:
            # Show error message
            update.message.reply_text(
                "❌ Failed to set preference. Please try again later."
            )

        # Clear the pending preference input
        del context.user_data["waiting_for_preference"]
        return

    # Check if there's a pending translation request
    elif "translation_target" in context.user_data:
        # Get the target language
        target_language = context.user_data["translation_target"]

        # Translate the text
        translated_text = gemini_service.translate_text(
            text=user_message,
            target_language=target_language
        )

        # Generate a unique message ID for feedback
        message_id = f"tr_{user_id}_{target_language[:2]}"

        # Create feedback buttons
        buttons = add_feedback_buttons(message_id)

        # Create response template
        response_template = create_response_template(
            title=f"🌐 Translation to {target_language}",
            body=translated_text,
            buttons=buttons
        )

        # Send translation with feedback buttons
        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode'],
            reply_markup=response_template['reply_markup']
        )

        # Clear the pending translation request
        del context.user_data["translation_target"]
        return

    # Check if there's a pending summary request
    elif "summary_style" in context.user_data:
        # Get the summary style
        style = context.user_data["summary_style"]

        # Summarize the text with the selected style
        if style == "short":
            summary = gemini_service.summarize_text(
                text=user_message, length="short")
        elif style == "medium":
            summary = gemini_service.summarize_text(text=user_message)
        elif style == "detailed":
            summary = gemini_service.summarize_text(
                text=user_message, length="detailed")
        elif style == "key":
            summary = gemini_service.summarize_text(
                text=user_message, format="bullet_points")
        else:
            summary = gemini_service.summarize_text(text=user_message)

        # Generate a unique message ID for feedback
        message_id = f"sum_{user_id}_{style}"

        # Create feedback buttons
        buttons = add_feedback_buttons(message_id)

        # Create response template
        response_template = create_response_template(
            title=f"📝 {style.capitalize()} Summary",
            body=summary,
            buttons=buttons
        )

        # Send summary with feedback buttons
        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode'],
            reply_markup=response_template['reply_markup']
        )

        # Clear the pending summary request
        del context.user_data["summary_style"]
        return

    # Check if there's a pending generation request
    elif "generation_type" in context.user_data:
        # Get the content type
        content_type = context.user_data["generation_type"]

        # Store the prompt for potential regeneration
        context.user_data["last_generation_prompt"] = user_message

        # Generate content
        generated_content = gemini_service.generate_creative_content(
            prompt=user_message,
            content_type=content_type
        )

        # Generate a unique message ID for feedback
        message_id = f"gen_{user_id}_{content_type}"

        # Create feedback buttons
        buttons = add_feedback_buttons(message_id)

        # Add regenerate button
        regenerate_button = {'text': "🔄 Regenerate",
                             'callback_data': f"regen:{content_type}:{user_message[:10]}"}
        buttons[0].append(regenerate_button)

        # Create response template
        response_template = create_response_template(
            title=f"✨ Generated {content_type.capitalize()}",
            body=generated_content,
            buttons=buttons
        )

        # Send generated content with feedback buttons
        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode'],
            reply_markup=response_template['reply_markup']
        )

        # Clear the pending generation request
        del context.user_data["generation_type"]
        return

    # Handle regular messages
    # Check if it's a date/time question first
    if is_datetime_question(user_message):
        logger.info(f"Detected date/time question: {user_message}")
        response = get_datetime_response(user_message)
    else:
        # Detect question type for non-date/time questions
        question_type = gemini_service.detect_question_type(user_message)
        logger.info(f"Detected question type: {question_type}")

        # Generate response based on question type
        if question_type == "FACTUAL":
            # Use information retrieval for factual questions
            response = gemini_service.answer_question(user_message)
        else:
            # Use regular conversation for other types
            response = gemini_service.generate_text(
                prompt=user_message,
                conversation_history=conversation_history,
                user_id=user_id
            )

    # Get user preferences
    user_preferences = db_manager.get_user_preferences(user_id)

    # Personalize response if preferences exist
    if user_preferences:
        response = gemini_service.personalize_response(
            response, user_preferences)

    # Add assistant response to history
    conversation_history.append({
        "role": "assistant",
        "content": response
    })

    # Update conversation history
    context.user_data["conversation_history"] = conversation_history

    # Generate a unique message ID for feedback
    message_id = str(uuid.uuid4())

    # Create feedback buttons
    buttons = add_feedback_buttons(message_id)

    # Create response with feedback buttons
    response_template = create_response_template(
        body=response,
        buttons=buttons
    )

    # Send response with Markdown formatting and feedback buttons
    update.message.reply_text(
        text=response_template['text'],
        parse_mode=response_template['parse_mode'],
        reply_markup=response_template['reply_markup']
    )
