# Changelog

All notable changes to the Just Ask AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-04-17

### Added
- User Experience Enhancements:
  - Implemented HTML and Markdown formatting for all responses
  - Added inline keyboard buttons for interactive responses
  - Created feedback system with rating buttons
  - Added quick reply options for common queries
  - Improved message styling and readability
  - New command: /feedback
  - Added menu button showing all available commands
  - Category-based command organization in menu
  - Improved translation with language selection buttons
  - Enhanced summarization with style options (short, medium, detailed, key points)
  - Content generation with topic selection and regeneration
  - Confirmation dialogs for destructive actions
  - Persistent context for multi-step interactions
  - Visual indicators and better formatting
  - Enhanced preference management with interactive UI
  - Preset preference options for easy selection
  - Preference categories with detailed descriptions
  - Automatic preference application to all responses
  - Personalized responses based on user preferences

### Fixed
- Fixed SQLite threading issues by implementing a thread-safe database manager
- Replaced SerpAPI with a web scraper for search functionality to avoid API limits
- Added date/time awareness to the bot for answering questions about current date, time, day, month, etc.
- Fixed formatting issues with Gemini responses in Telegram
- Fixed regenerate button functionality
- Improved search result formatting

## [0.2.0] - 2025-04-16
### Added
- Information Retrieval features:
  - Question answering system with web search integration
  - Factual information lookup
  - Knowledge base for storing and retrieving information
  - New commands: /search, /ask, /learn
- Personalization features:
  - User preference storage in SQLite database
  - Personalized responses based on user preferences
  - User profile management
  - New commands: /preferences, /setpreference, /deletepreference
- Task Automation features:
  - Reminder functionality with natural language parsing
  - Scheduling system for future notifications
  - Notification system for reminders
  - New commands: /remind, /reminders, /cancelreminder

## [0.1.0] - 2025-04-16
### Added
- Initial project setup
- Created project documentation structure with roadmap and changelog
- Set up development environment and project architecture
- Implemented configuration management system with environment variables
- Set up logging system for better debugging
- Implemented error handling framework
- Registered Telegram bot with BotFather
- Implemented basic Telegram bot integration with polling mechanism
- Created command handler system for processing user commands
- Implemented basic conversation flow with context retention
- Added core commands: start, help, translate, summarize, generate, reset
- Set up Gemini API authentication and client for the gemini-2.0-flash model
- Implemented prompt engineering system for better responses
- Added context management for multi-turn conversations
- Implemented core features:
  - Conversational AI with context retention
  - Language translation with support for multiple language pairs
  - Text summarization with different summary lengths
  - Content generation for poems, stories, jokes, and code snippets

### Fixed
- Updated Pydantic configuration to work with Pydantic v2
- Fixed compatibility issues with python-telegram-bot by downgrading to v13.15
