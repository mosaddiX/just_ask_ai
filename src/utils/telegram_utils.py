"""
Telegram utility functions for the Just Ask AI Telegram bot.
"""
import re
from typing import List, Dict, Any, Optional, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode


def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
    """Create an inline keyboard markup from a list of button definitions.

    Args:
        buttons: List of button rows, where each row is a list of button definitions.
                Each button definition is a dict with 'text' and one of:
                - 'callback_data': For callback buttons
                - 'url': For URL buttons
                - 'switch_inline_query': For inline query buttons
                - 'switch_inline_query_current_chat': For inline query in current chat

    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = []

    for row in buttons:
        keyboard_row = []
        for button in row:
            if 'url' in button:
                keyboard_row.append(InlineKeyboardButton(
                    text=button['text'],
                    url=button['url']
                ))
            elif 'callback_data' in button:
                keyboard_row.append(InlineKeyboardButton(
                    text=button['text'],
                    callback_data=button['callback_data']
                ))
            elif 'switch_inline_query' in button:
                keyboard_row.append(InlineKeyboardButton(
                    text=button['text'],
                    switch_inline_query=button['switch_inline_query']
                ))
            elif 'switch_inline_query_current_chat' in button:
                keyboard_row.append(InlineKeyboardButton(
                    text=button['text'],
                    switch_inline_query_current_chat=button['switch_inline_query_current_chat']
                ))
        keyboard.append(keyboard_row)

    return InlineKeyboardMarkup(keyboard)


def format_message(text: str, parse_mode: str = ParseMode.MARKDOWN) -> str:
    """Format a message with the specified parse mode.

    Args:
        text: The text to format
        parse_mode: The parse mode to use (MARKDOWN or HTML)

    Returns:
        Formatted text
    """
    # Escape special characters if using Markdown
    if parse_mode == ParseMode.MARKDOWN:
        # Characters that need escaping in Markdown: _ * [ ] ( ) ~ ` > # + - = | { } . !
        special_chars = [
            '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            # Don't escape if it's already part of a Markdown formatting sequence
            if f"\\{char}" not in text:
                text = text.replace(char, f"\\{char}")

    return text


def create_bold_text(text: str) -> str:
    """Create bold text for Markdown.

    Args:
        text: The text to make bold

    Returns:
        Bold text
    """
    return f"*{text}*"


def create_italic_text(text: str) -> str:
    """Create italic text for Markdown.

    Args:
        text: The text to make italic

    Returns:
        Italic text
    """
    return f"_{text}_"


def create_code_text(text: str) -> str:
    """Create code text for Markdown.

    Args:
        text: The text to format as code

    Returns:
        Code text
    """
    return f"`{text}`"


def create_code_block(text: str, language: str = "") -> str:
    """Create a code block for Markdown.

    Args:
        text: The text to format as a code block
        language: The programming language for syntax highlighting

    Returns:
        Code block
    """
    return f"```{language}\n{text}\n```"


def create_link(text: str, url: str) -> str:
    """Create a link for Markdown.

    Args:
        text: The link text
        url: The URL

    Returns:
        Link text
    """
    return f"[{text}]({url})"


def create_list_item(text: str, ordered: bool = False, index: int = 1) -> str:
    """Create a list item for Markdown.

    Args:
        text: The list item text
        ordered: Whether the list is ordered
        index: The index for ordered lists

    Returns:
        List item text
    """
    if ordered:
        return f"{index}. {text}"
    else:
        return f"• {text}"


def create_section_header(text: str, level: int = 1) -> str:
    """Create a section header for Markdown.

    Args:
        text: The header text
        level: The header level (1-3)

    Returns:
        Header text
    """
    if level == 1:
        return f"*{text}*\n"
    elif level == 2:
        return f"*{text}*\n"
    else:
        return f"_{text}_\n"


def format_gemini_response(text: str) -> str:
    """Format a response from Gemini API for Telegram.

    Args:
        text: The text from Gemini API

    Returns:
        Formatted text for Telegram HTML
    """
    # Replace Markdown-style formatting with HTML

    # Replace bold: **text** or *text* -> <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*|\*(.*?)\*', r'<b>\1\2</b>', text)

    # Replace italic: _text_ -> <i>text</i>
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

    # Replace code: `text` -> <code>text</code>
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)

    # Replace bullet points: * item -> • item
    text = re.sub(r'^\* (.+)$', r'• \1', text, flags=re.MULTILINE)

    # Clean up any remaining asterisks that might cause formatting issues
    text = text.replace('*', '•')

    # Ensure proper spacing for bullet points and numbered lists
    text = re.sub(
        r'(^|\n)(\d+\.|•) ([^\n]+)(\n)(?!(\d+\.|•))', r'\1\2 \3\4\4', text)

    # Replace multiple newlines with just two
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def create_response_template(
    title: Optional[str] = None,
    body: Optional[str] = None,
    footer: Optional[str] = None,
    buttons: Optional[List[List[Dict[str, str]]]] = None,
    use_html: bool = False,
    is_gemini_response: bool = False
) -> Dict[str, Any]:
    """Create a response template with optional title, body, footer, and buttons.

    Args:
        title: The title text
        body: The body text
        footer: The footer text
        buttons: List of button definitions
        use_html: Whether to use HTML formatting instead of Markdown
        is_gemini_response: Whether the body is a response from Gemini API

    Returns:
        Response template dict with 'text' and optional 'reply_markup'
    """
    text_parts = []

    if title:
        # Format title with emoji if not already present
        if not any(emoji in title for emoji in ['🔍', '📝', '🌐', '✨', '⚙️', '📊', '⏰', '💬', '📖']):
            title = f"✨ {title}"

        if use_html:
            text_parts.append(f"<b>{title}</b>")
        else:
            text_parts.append(create_bold_text(title))

    if body:
        if title:
            text_parts.append("\n\n")

        # Format the body text for better readability
        # Replace multiple newlines with just two
        body = re.sub(r'\n{3,}', '\n\n', body)

        # Ensure proper spacing after bullet points and numbered lists
        body = re.sub(
            r'(^|\n)(\d+\.|•|\*) ([^\n]+)(\n)(?!(\d+\.|•|\*))', r'\1\2 \3\4\4', body)

        if use_html or is_gemini_response:
            # If it's a Gemini response or HTML is requested, format it for HTML
            formatted_body = format_gemini_response(
                body) if is_gemini_response else body
            text_parts.append(formatted_body)
        else:
            # For Markdown, we need to escape special characters
            special_chars = [
                '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

            # Process the body to escape special characters
            processed_body = ""
            i = 0
            while i < len(body):
                # Check if this is the start of a Markdown formatting sequence
                if body[i] in ['*', '_', '`', '['] and i + 1 < len(body):
                    # For bold/italic/code/links, don't escape the formatting characters
                    if body[i] == '*' and i + 1 < len(body) and body[i+1] != ' ':
                        processed_body += body[i]
                    elif body[i] == '_' and i + 1 < len(body) and body[i+1] != ' ':
                        processed_body += body[i]
                    elif body[i] == '`' and i + 1 < len(body) and body[i+1] != ' ':
                        processed_body += body[i]
                    # Check for link format
                    elif body[i] == '[' and '](' in body[i:i+20]:
                        processed_body += body[i]
                    else:
                        # Escape the character
                        processed_body += f"\\{body[i]}"
                elif body[i] in special_chars:
                    # Escape other special characters
                    processed_body += f"\\{body[i]}"
                else:
                    # Regular character, no escaping needed
                    processed_body += body[i]
                i += 1

            # Add the formatted and escaped body
            text_parts.append(processed_body)

    if footer:
        if title or body:
            text_parts.append("\n\n")

        if use_html:
            text_parts.append(f"<i>{footer}</i>")
        else:
            text_parts.append(create_italic_text(footer))

    response = {
        'text': ''.join(text_parts),
        'parse_mode': ParseMode.HTML if (use_html or is_gemini_response) else ParseMode.MARKDOWN
    }

    if buttons:
        response['reply_markup'] = create_inline_keyboard(buttons)

    return response
