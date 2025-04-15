"""
Configuration settings for the Just Ask AI Telegram bot.
"""
import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = Field(
        default=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        description="Telegram Bot API token obtained from BotFather"
    )

    # Google Gemini API Configuration
    GEMINI_API_KEY: str = Field(
        default=os.getenv("GEMINI_API_KEY", ""),
        description="Google Gemini API key"
    )
    GEMINI_MODEL: str = Field(
        default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        description="Google Gemini model to use"
    )

    # Search API Configuration
    SERPAPI_KEY: str = Field(
        default=os.getenv("SERPAPI_KEY", ""),
        description="SerpAPI key for web search"
    )

    # Database Configuration
    DATABASE_PATH: str = Field(
        default=os.getenv("DATABASE_PATH", "data/justaskai.db"),
        description="Path to the SQLite database file"
    )

    # Bot Configuration
    MAX_CONVERSATION_HISTORY: int = Field(
        default=int(os.getenv("MAX_CONVERSATION_HISTORY", "10")),
        description="Maximum number of messages to keep in conversation history"
    )
    DEFAULT_LANGUAGE: str = Field(
        default=os.getenv("DEFAULT_LANGUAGE", "en"),
        description="Default language for the bot"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level"
    )

    # Task Automation Configuration
    MAX_REMINDERS_PER_USER: int = Field(
        default=int(os.getenv("MAX_REMINDERS_PER_USER", "5")),
        description="Maximum number of reminders per user"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings.

    Returns:
        Settings: Application settings
    """
    return settings
