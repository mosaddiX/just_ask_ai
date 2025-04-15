# Just Ask AI

A powerful Telegram bot powered by Google's Gemini API (gemini-2.0-flash model) that provides text-based AI assistance.

## Features

- **Conversational AI**: Natural, multi-turn conversations with context retention
- **Language Translation**: Translate text between 100+ languages
- **Text Summarization**: Get concise summaries of long texts in various formats
- **Content Generation**: Create poems, stories, jokes, and code snippets
- **Information Retrieval**: Get answers to factual questions with web search integration
- **Personalization**: Tailored responses based on user preferences
- **Task Automation**: Set reminders and schedule notifications
- **Interactive UI**: Inline buttons, menu system, and feedback mechanisms
- **Date/Time Awareness**: Answers questions about current date, time, day, etc.
- **Well-Formatted Responses**: Clean, readable responses with proper formatting

## Getting Started

### Prerequisites

- Python 3.8+
- Telegram Bot Token (from BotFather)
- Google AI Studio API Key (for Gemini API)

### Installation

```bash
# Clone the repository
git clone https://github.com/mosaddiX/just_ask_ai.git
cd just_ask_ai

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Usage

```bash
# Start the bot
python bot.py
```

## Documentation

For detailed documentation, see the [docs](./docs) directory:

- [Project Roadmap](./docs/ROADMAP.md)
- [Changelog](./docs/CHANGELOG.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google's Gemini API for providing the AI capabilities
- Telegram Bot API for the messaging platform
