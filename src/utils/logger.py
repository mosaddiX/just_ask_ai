"""
Logging utility for the Just Ask AI Telegram bot.
"""
import sys
from pathlib import Path

from loguru import logger

from src.config.settings import get_settings

settings = get_settings()

# Configure logger
LOG_LEVEL = settings.LOG_LEVEL
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Add console logger
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level=LOG_LEVEL,
    colorize=True,
)

# Add file logger
logger.add(
    "logs/bot.log",
    format=LOG_FORMAT,
    level=LOG_LEVEL,
    rotation="10 MB",
    compression="zip",
    retention="1 month",
)


def get_logger(name: str = "justaskai"):
    """Get logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)
