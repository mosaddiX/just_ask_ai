"""
Reminder handlers for the Just Ask AI Telegram bot.
"""
import re
from datetime import datetime, timedelta

import pytz
from telegram import Update, ChatAction, ParseMode
from telegram.ext import CallbackContext

from src.utils.database_new import get_db_manager
from src.utils.logger import get_logger
from src.utils.telegram_utils import create_response_template, create_bold_text

logger = get_logger(__name__)
db_manager = get_db_manager()


def remind_command(update: Update, context: CallbackContext) -> None:
    """Handle the /remind command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used remind command")

    # Get command arguments
    text = " ".join(context.args)

    if not text:
        update.message.reply_text(
            "Please provide a reminder text and time.\n"
            "Examples:\n"
            "• /remind Call John in 30 minutes\n"
            "• /remind Buy milk tomorrow at 10am\n"
            "• /remind Meeting with team on Friday at 2pm"
        )
        return

    # Parse reminder text and time
    reminder_text, scheduled_time = parse_reminder(text)

    if not scheduled_time:
        update.message.reply_text(
            "I couldn't understand when you want to be reminded. Please specify a time.\n"
            "Examples:\n"
            "• in 30 minutes\n"
            "• tomorrow at 10am\n"
            "• on Friday at 2pm"
        )
        return

    # Add reminder to database
    reminder_id = db_manager.add_reminder(
        user_id=user_id,
        text=reminder_text,
        scheduled_at=scheduled_time.isoformat()
    )

    if reminder_id is None:
        update.message.reply_text(
            "❌ Failed to set reminder. You may have reached the maximum number of reminders."
        )
        return

    # Format response
    formatted_time = scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p")

    # Create response with Markdown formatting
    response_template = create_response_template(
        title="✅ Reminder Set",
        body=f"I'll remind you: {create_bold_text(reminder_text)}\n\nOn: {formatted_time}\nReminder ID: {reminder_id}"
    )

    update.message.reply_text(
        text=response_template['text'],
        parse_mode=response_template['parse_mode']
    )

    # Schedule the reminder
    schedule_reminder(context, reminder_id, user_id,
                      reminder_text, scheduled_time)


def reminders_command(update: Update, context: CallbackContext) -> None:
    """Handle the /reminders command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested reminders list")

    # Get user reminders
    reminders = db_manager.get_user_reminders(user_id)

    if not reminders:
        update.message.reply_text(
            "You don't have any active reminders. Use /remind to set a reminder."
        )
        return

    # Format reminders
    reminders_list = []

    for reminder in reminders:
        scheduled_time = datetime.fromisoformat(reminder["scheduled_at"])
        formatted_time = scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p")

        reminders_list.append(
            f"• ID {reminder['id']}: {create_bold_text(reminder['text'])} on {formatted_time}")

    reminders_text = "\n".join(reminders_list)

    # Create response with Markdown formatting
    response_template = create_response_template(
        title="Your Active Reminders",
        body=reminders_text,
        footer="Use /cancelreminder <id> to cancel a reminder."
    )

    update.message.reply_text(
        text=response_template['text'],
        parse_mode=response_template['parse_mode']
    )


def cancel_reminder_command(update: Update, context: CallbackContext) -> None:
    """Handle the /cancelreminder command.

    Args:
        update: Update object
        context: Context object
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} used cancelreminder command")

    # Get command arguments
    args = context.args

    if not args:
        update.message.reply_text(
            "Please provide a reminder ID to cancel.\n"
            "Example: /cancelreminder 123\n\n"
            "Use /reminders to see your active reminders."
        )
        return

    # Get reminder ID
    try:
        reminder_id = int(args[0])
    except ValueError:
        update.message.reply_text(
            "Invalid reminder ID. Please provide a valid number."
        )
        return

    # Get reminder
    reminder = db_manager.get_reminder(reminder_id)

    if not reminder:
        update.message.reply_text(
            f"Reminder with ID {reminder_id} not found."
        )
        return

    # Check if reminder belongs to user
    if reminder["user_id"] != user_id:
        update.message.reply_text(
            "You don't have permission to cancel this reminder."
        )
        return

    # Delete reminder
    success = db_manager.delete_reminder(reminder_id)

    if success:
        # Remove scheduled job if it exists
        job_name = f"reminder_{reminder_id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()

        # Create response with Markdown formatting
        response_template = create_response_template(
            title="✅ Reminder Cancelled",
            body=f"Reminder with ID {reminder_id} has been cancelled."
        )

        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode']
        )
    else:
        # Create error response with Markdown formatting
        response_template = create_response_template(
            title="❌ Failed to Cancel Reminder",
            body="Please try again later."
        )

        update.message.reply_text(
            text=response_template['text'],
            parse_mode=response_template['parse_mode']
        )


def parse_reminder(text: str) -> tuple:
    """Parse reminder text and time.

    Args:
        text: Reminder text with time information

    Returns:
        Tuple of (reminder_text, scheduled_time)
    """
    # Common time patterns
    patterns = [
        # in X minutes/hours
        r'(.*?)\s+in\s+(\d+)\s+(minute|minutes|min|mins|hour|hours|hr|hrs)(?:\s+.*)?$',
        # tomorrow at X
        r'(.*?)\s+tomorrow\s+at\s+(\d+(?::\d+)?)\s*(am|pm)?(?:\s+.*)?$',
        # on day at X
        r'(.*?)\s+on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+(\d+(?::\d+)?)\s*(am|pm)?(?:\s+.*)?$',
        # at X today
        r'(.*?)\s+at\s+(\d+(?::\d+)?)\s*(am|pm)?(?:\s+today)?(?:\s+.*)?$',
    ]

    now = datetime.now()
    scheduled_time = None
    reminder_text = text

    for pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()

            if 'minute' in groups or 'minutes' in groups or 'min' in groups or 'mins' in groups:
                # in X minutes
                reminder_text = groups[0].strip()
                minutes = int(groups[1])
                scheduled_time = now + timedelta(minutes=minutes)

            elif 'hour' in groups or 'hours' in groups or 'hr' in groups or 'hrs' in groups:
                # in X hours
                reminder_text = groups[0].strip()
                hours = int(groups[1])
                scheduled_time = now + timedelta(hours=hours)

            elif 'tomorrow' in pattern:
                # tomorrow at X
                reminder_text = groups[0].strip()
                time_str = groups[1]
                am_pm = groups[2]

                # Parse time
                scheduled_time = parse_time(
                    time_str, am_pm, now + timedelta(days=1))

            elif 'monday' in pattern or 'tuesday' in pattern or 'wednesday' in pattern or 'thursday' in pattern or 'friday' in pattern or 'saturday' in pattern or 'sunday' in pattern:
                # on day at X
                reminder_text = groups[0].strip()
                day_name = groups[1].lower()
                time_str = groups[2]
                am_pm = groups[3]

                # Get day of week
                days = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                    'friday': 4, 'saturday': 5, 'sunday': 6
                }
                target_day = days[day_name]
                current_day = now.weekday()

                # Calculate days to add
                days_to_add = (target_day - current_day) % 7
                if days_to_add == 0:
                    days_to_add = 7  # Next week if today

                target_date = now + timedelta(days=days_to_add)
                scheduled_time = parse_time(time_str, am_pm, target_date)

            elif 'at' in pattern:
                # at X today
                reminder_text = groups[0].strip()
                time_str = groups[1]
                am_pm = groups[2]

                # Parse time
                scheduled_time = parse_time(time_str, am_pm, now)

                # If the time is in the past, schedule for tomorrow
                if scheduled_time < now:
                    scheduled_time = parse_time(
                        time_str, am_pm, now + timedelta(days=1))

            break

    return reminder_text, scheduled_time


def parse_time(time_str: str, am_pm: str, date: datetime) -> datetime:
    """Parse time string.

    Args:
        time_str: Time string (e.g., "10:30")
        am_pm: AM/PM indicator
        date: Base date

    Returns:
        Datetime object
    """
    # Parse hour and minute
    if ':' in time_str:
        hour, minute = map(int, time_str.split(':'))
    else:
        hour = int(time_str)
        minute = 0

    # Adjust for AM/PM
    if am_pm and am_pm.lower() == 'pm' and hour < 12:
        hour += 12
    elif am_pm and am_pm.lower() == 'am' and hour == 12:
        hour = 0

    # Create datetime
    return date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def schedule_reminder(context: CallbackContext, reminder_id: int, user_id: int, text: str, scheduled_time: datetime) -> None:
    """Schedule a reminder.

    Args:
        context: Context object
        reminder_id: Reminder ID
        user_id: User ID
        text: Reminder text
        scheduled_time: Scheduled time
    """
    # Calculate seconds until reminder
    now = datetime.now()
    seconds = (scheduled_time - now).total_seconds()

    if seconds <= 0:
        logger.warning(
            f"Reminder {reminder_id} is in the past, scheduling for 1 minute from now")
        seconds = 60  # Schedule for 1 minute from now

    # Schedule job
    context.job_queue.run_once(
        send_reminder,
        seconds,
        context=(reminder_id, user_id, text),
        name=f"reminder_{reminder_id}"
    )

    logger.info(
        f"Scheduled reminder {reminder_id} for {scheduled_time.isoformat()}")


def send_reminder(context: CallbackContext) -> None:
    """Send a reminder.

    Args:
        context: Context object
    """
    job = context.job
    reminder_id, user_id, text = job.context

    # Mark reminder as completed
    db_manager.mark_reminder_completed(reminder_id)

    # Create response with Markdown formatting
    response_template = create_response_template(
        title="⏰ Reminder",
        body=create_bold_text(text)
    )

    # Send reminder message
    context.bot.send_message(
        chat_id=user_id,
        text=response_template['text'],
        parse_mode=response_template['parse_mode']
    )

    logger.info(f"Sent reminder {reminder_id} to user {user_id}")


def check_due_reminders(context: CallbackContext) -> None:
    """Check for due reminders and send them.

    Args:
        context: Context object
    """
    try:
        # Get due reminders
        due_reminders = db_manager.get_due_reminders()

        for reminder in due_reminders:
            # Mark as completed
            db_manager.mark_reminder_completed(reminder["id"])

            # Send reminder
            try:
                # Create response with Markdown formatting
                response_template = create_response_template(
                    title="⏰ Reminder",
                    body=create_bold_text(reminder['text'])
                )

                context.bot.send_message(
                    chat_id=reminder["user_id"],
                    text=response_template['text'],
                    parse_mode=response_template['parse_mode']
                )
                logger.info(
                    f"Sent due reminder {reminder['id']} to user {reminder['user_id']}")
            except Exception as e:
                logger.error(f"Error sending reminder {reminder['id']}: {e}")
    except Exception as e:
        logger.error(f"Error checking due reminders: {e}")


def setup_reminder_checker(job_queue) -> None:
    """Set up periodic reminder checker.

    Args:
        job_queue: Job queue
    """
    # Check for due reminders every minute
    job_queue.run_repeating(
        check_due_reminders,
        interval=60,
        first=0,
        name="reminder_checker"
    )

    logger.info("Set up reminder checker job")
