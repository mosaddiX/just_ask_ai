"""
Preference handlers for the Just Ask AI Telegram bot.
"""
from telegram import Update, ChatAction, ParseMode
from telegram.ext import CallbackContext

from src.utils.database_new import get_db_manager
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_response_template, create_bold_text

logger = get_logger(__name__)
db_manager = get_db_manager()


def get_preference_emoji(preference_key: str) -> str:
    """Get emoji for preference key.

    Args:
        preference_key: Preference key

    Returns:
        Emoji for the preference key
    """
    emoji_map = {
        "language": "🌐",  # Globe
        "tone": "🔊",      # Speaker
        "length": "📏",    # Straight ruler
        "expertise": "📚",  # Books
        "interests": "🎯"   # Bullseye
    }

    return emoji_map.get(preference_key.lower(), "⚙️")  # Default: gear


def preferences_command(update: Update, context: CallbackContext) -> None:
    """Handle the /preferences command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested preferences")

    # Get user preferences
    preferences = db_manager.get_user_preferences(user_id)

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

    # Add delete buttons if preferences exist
    delete_buttons = []
    for key in preferences.keys():
        emoji = get_preference_emoji(key)
        delete_buttons.append(
            {'text': f"🗑️ Delete {emoji} {key.capitalize()}", 'callback_data': f"pref:delete:{key}"})

    # Organize delete buttons into rows of 2
    delete_rows = []
    for i in range(0, len(delete_buttons), 2):
        row = delete_buttons[i:i+2]
        delete_rows.append(row)

    # Add delete rows to buttons if they exist
    if delete_rows:
        buttons.extend(delete_rows)

    # Create body text
    if preferences:
        body = "Your current preferences:\n\n"
        for key, value in preferences.items():
            emoji = get_preference_emoji(key)
            body += f"• {emoji} {create_bold_text(key.capitalize())}: {value}\n"

        body += "\nSelect a preference to change it or delete it."
    else:
        body = "You don't have any preferences set yet. Select a preference category below to set it."

    # Create response template
    response = create_response_template(
        title="⚙️ Preference Settings",
        body=body,
        footer="Preferences help me personalize my responses to better match your needs.",
        buttons=buttons
    )

    # Send message with buttons
    update.message.reply_text(
        text=response['text'],
        parse_mode=response['parse_mode'],
        reply_markup=response['reply_markup']
    )


def set_preference_command(update: Update, context: CallbackContext) -> None:
    """Handle the /setpreference command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used setpreference command")

    # Get command arguments
    args = context.args

    if len(args) < 2:
        # Show interactive preference selection
        preference_categories = [
            {"key": "language", "name": "Language",
                "description": "Your preferred language for responses"},
            {"key": "tone", "name": "Tone",
                "description": "How formal or casual you want responses to be"},
            {"key": "length", "name": "Length",
                "description": "How detailed you want responses to be"},
            {"key": "expertise", "name": "Expertise",
                "description": "The level of technical detail in responses"},
            {"key": "interests", "name": "Interests",
                "description": "Topics you're interested in"}
        ]

        # Create buttons for preference categories
        buttons = []
        for category in preference_categories:
            emoji = get_preference_emoji(category["key"])
            buttons.append([{'text': f"{emoji} {category['name']}",
                           'callback_data': f"pref:set:{category['key']}"}])

        # Add back button
        buttons.append(
            [{'text': "⬅️ Back to Main Menu", 'callback_data': "menu:main"}])

        # Create response template
        response = create_response_template(
            title="⚙️ Set Preference",
            body="Please select a preference category to set:\n\n" +
                 "\n".join(
                     [f"{get_preference_emoji(cat['key'])} {create_bold_text(cat['name'])}: {cat['description']}" for cat in preference_categories]),
            footer="Your preferences help me personalize my responses to better match your needs.",
            buttons=buttons
        )

        # Send message with buttons
        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
        return

    # Get preference key and value
    preference_key = args[0].lower()
    preference_value = " ".join(args[1:])

    # Validate preference key
    valid_keys = ["language", "tone", "length", "expertise", "interests"]
    if preference_key not in valid_keys:
        # Show error with valid options
        buttons = []
        for key in valid_keys:
            emoji = get_preference_emoji(key)
            buttons.append(
                [{'text': f"{emoji} {key.capitalize()}", 'callback_data': f"pref:set:{key}"}])

        response = create_response_template(
            title="❌ Invalid Preference",
            body=f"'{preference_key}' is not a valid preference key. Please choose from the options below:",
            buttons=buttons
        )

        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
        return

    # Set preference
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

        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
    else:
        update.message.reply_text(
            "❌ Failed to set preference. Please try again later."
        )


def delete_preference_command(update: Update, context: CallbackContext) -> None:
    """Handle the /deletepreference command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used deletepreference command")

    # Get command arguments
    args = context.args

    # Get user preferences
    preferences = db_manager.get_user_preferences(user_id)

    if not preferences:
        # No preferences to delete
        response = create_response_template(
            title="ℹ️ No Preferences",
            body="You don't have any preferences set yet. Use /setpreference to set preferences.",
            footer="Example: /setpreference language Spanish"
        )

        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode']
        )
        return

    if not args:
        # Show interactive preference deletion
        buttons = []
        for key, value in preferences.items():
            emoji = get_preference_emoji(key)
            buttons.append(
                [{'text': f"🗑️ Delete {emoji} {key.capitalize()}", 'callback_data': f"pref:delete:{key}"}])

        # Add view all preferences button
        buttons.append(
            [{'text': "📑 View All Preferences", 'callback_data': "pref:view"}])

        # Create response template
        response = create_response_template(
            title="🗑️ Delete Preference",
            body="Select a preference to delete:\n\n" +
                 "\n".join(
                     [f"• {get_preference_emoji(key)} {create_bold_text(key.capitalize())}: {value}" for key, value in preferences.items()]),
            footer="Deleting a preference will remove it from your profile.",
            buttons=buttons
        )

        # Send message with buttons
        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
        return

    # Get preference key
    preference_key = args[0].lower()

    # Check if preference exists
    current_value = db_manager.get_user_preference(user_id, preference_key)
    if current_value is None:
        # Show error with valid options
        buttons = []
        for key in preferences.keys():
            emoji = get_preference_emoji(key)
            buttons.append(
                [{'text': f"🗑️ Delete {emoji} {key.capitalize()}", 'callback_data': f"pref:delete:{key}"}])

        response = create_response_template(
            title="❌ Invalid Preference",
            body=f"You don't have a preference set for '{preference_key}'.\n\nYour current preferences are:\n\n" +
            "\n".join(
                [f"• {get_preference_emoji(key)} {create_bold_text(key.capitalize())}: {value}" for key, value in preferences.items()]),
            buttons=buttons
        )

        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
        return

    # Delete preference
    success = db_manager.delete_user_preference(user_id, preference_key)

    if success:
        # Get emoji for the preference
        emoji = get_preference_emoji(preference_key)

        # Get remaining preferences
        remaining_preferences = db_manager.get_user_preferences(user_id)

        # Create buttons for remaining preferences or setting new ones
        buttons = []

        if remaining_preferences:
            # Show remaining preferences that can be deleted
            for key in remaining_preferences.keys():
                key_emoji = get_preference_emoji(key)
                buttons.append(
                    [{'text': f"🗑️ Delete {key_emoji} {key.capitalize()}", 'callback_data': f"pref:delete:{key}"}])

            # Add view all preferences button
            buttons.append(
                [{'text': "📑 View All Preferences", 'callback_data': "pref:view"}])

            # Create response with remaining preferences
            preferences_text = "\n\nYour remaining preferences:\n"
            for key, value in remaining_preferences.items():
                pref_emoji = get_preference_emoji(key)
                preferences_text += f"\n• {pref_emoji} {create_bold_text(key.capitalize())}: {value}"
        else:
            # No remaining preferences, show options to set new ones
            valid_keys = ["language", "tone",
                          "length", "expertise", "interests"]
            for key in valid_keys:
                key_emoji = get_preference_emoji(key)
                buttons.append(
                    [{'text': f"Set {key_emoji} {key.capitalize()}", 'callback_data': f"pref:set:{key}"}])

            preferences_text = "\n\nYou have no remaining preferences. Select an option above to set a new preference."

        response = create_response_template(
            title=f"✅ Preference Deleted",
            body=f"Your {emoji} {create_bold_text(preference_key.capitalize())} preference has been deleted.{preferences_text}",
            buttons=buttons
        )

        update.message.reply_text(
            text=response['text'],
            parse_mode=response['parse_mode'],
            reply_markup=response['reply_markup']
        )
    else:
        update.message.reply_text(
            "❌ Failed to delete preference. Please try again later."
        )
