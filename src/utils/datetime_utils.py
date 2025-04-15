"""
Date and time utilities for the Just Ask AI Telegram bot.
"""
from datetime import datetime
import pytz


def get_current_datetime_info() -> dict:
    """Get current date and time information.

    Returns:
        Dictionary with current date and time information
    """
    now = datetime.now()
    utc_now = datetime.now(pytz.UTC)

    # Format date in different formats
    date_standard = now.strftime("%Y-%m-%d")
    date_readable = now.strftime("%A, %B %d, %Y")
    time_standard = now.strftime("%H:%M:%S")
    time_12h = now.strftime("%I:%M %p")

    # Get day of week, month, year
    day_of_week = now.strftime("%A")
    month = now.strftime("%B")
    year = now.strftime("%Y")

    # Get UTC time
    utc_date = utc_now.strftime("%Y-%m-%d")
    utc_time = utc_now.strftime("%H:%M:%S")

    return {
        "current_date": date_standard,
        "current_date_readable": date_readable,
        "current_time": time_standard,
        "current_time_12h": time_12h,
        "day_of_week": day_of_week,
        "month": month,
        "year": year,
        "utc_date": utc_date,
        "utc_time": utc_time,
        "timestamp": int(now.timestamp()),
        "utc_timestamp": int(utc_now.timestamp()),
    }


def get_datetime_context_string() -> str:
    """Get a formatted string with current date and time information.

    Returns:
        Formatted string with current date and time information
    """
    info = get_current_datetime_info()

    return (
        f"Current Date and Time Information:\n"
        f"- Current date: {info['current_date_readable']} ({info['current_date']})\n"
        f"- Current time: {info['current_time_12h']} ({info['current_time']})\n"
        f"- Day of week: {info['day_of_week']}\n"
        f"- Month: {info['month']}\n"
        f"- Year: {info['year']}\n"
        f"- UTC date and time: {info['utc_date']} {info['utc_time']}\n"
    )


def is_datetime_question(text: str) -> bool:
    """Check if a question is related to date or time.

    Args:
        text: Question text

    Returns:
        True if the question is related to date or time, False otherwise
    """
    # List of keywords related to date and time
    datetime_keywords = [
        "current date", "today's date", "what day is it", "what is the date",
        "current time", "what time is it", "current day", "what day is today",
        "today is what day", "current month", "what month is it", "what is the month",
        "current year", "what year is it", "what is the year", "date today",
        "time now", "current datetime", "today date", "now date", "present date",
        "present time", "current moment", "right now", "what day of the week",
        "day of the week", "date and time", "time and date", "today", "now"
    ]

    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()

    # Check if any of the keywords are in the text
    for keyword in datetime_keywords:
        if keyword in text_lower:
            return True

    return False


def get_datetime_response(question: str) -> str:
    """Get a response for a date or time related question.

    Args:
        question: Question text

    Returns:
        Response text
    """
    info = get_current_datetime_info()
    question_lower = question.lower()

    # Check what kind of datetime information is being requested
    if any(keyword in question_lower for keyword in ["time", "hour", "minute", "second"]):
        return f"The current time is {info['current_time_12h']} ({info['current_time']} in 24-hour format)."

    elif any(keyword in question_lower for keyword in ["date", "day", "today"]):
        return f"Today's date is {info['current_date_readable']} ({info['current_date']} in ISO format)."

    elif "day of the week" in question_lower or "weekday" in question_lower:
        return f"Today is {info['day_of_week']}."

    elif "month" in question_lower:
        return f"The current month is {info['month']}."

    elif "year" in question_lower:
        return f"The current year is {info['year']}."

    else:
        # General date and time information
        return (
            f"Current date: {info['current_date_readable']} ({info['current_date']})\n"
            f"Current time: {info['current_time_12h']} ({info['current_time']})\n"
            f"Day of week: {info['day_of_week']}\n"
            f"Month: {info['month']}\n"
            f"Year: {info['year']}"
        )
