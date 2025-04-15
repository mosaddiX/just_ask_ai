"""
Database utility for the Just Ask AI Telegram bot.
"""
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from src.config.settings import get_settings
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class DatabaseManager:
    """Database manager for the Just Ask AI Telegram bot."""

    def __init__(self):
        """Initialize database manager."""
        self.db_path = settings.DATABASE_PATH

        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.db = Database(self.db_path)

        # Create tables if they don't exist
        self._create_tables()

        logger.info(f"Initialized database at {self.db_path}")

    def _create_tables(self):
        """Create database tables if they don't exist."""
        # User preferences table
        if "user_preferences" not in self.db.table_names():
            self.db.create_table(
                "user_preferences",
                {
                    "user_id": int,
                    "preference_key": str,
                    "preference_value": str,
                    "updated_at": str,
                },
                pk=("user_id", "preference_key"),
            )
            logger.info("Created user_preferences table")

        # Reminders table
        if "reminders" not in self.db.table_names():
            self.db.create_table(
                "reminders",
                {
                    "id": int,
                    "user_id": int,
                    "text": str,
                    "scheduled_at": str,
                    "created_at": str,
                    "is_completed": int,  # 0 = False, 1 = True
                },
                pk="id",
            )
            # Create index on user_id for faster lookups
            self.db["reminders"].create_index(["user_id"])
            logger.info("Created reminders table")

        # Knowledge base table
        if "knowledge_base" not in self.db.table_names():
            self.db.create_table(
                "knowledge_base",
                {
                    "id": int,
                    "question": str,
                    "answer": str,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
            )
            # Create full-text search index
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_base_fts USING fts5(question, answer, content=knowledge_base)"
            )
            # Create triggers to keep FTS index updated
            self.db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS knowledge_base_ai AFTER INSERT ON knowledge_base
                BEGIN
                    INSERT INTO knowledge_base_fts(rowid, question, answer)
                    VALUES (new.id, new.question, new.answer);
                END;
                """
            )
            self.db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS knowledge_base_ad AFTER DELETE ON knowledge_base
                BEGIN
                    INSERT INTO knowledge_base_fts(knowledge_base_fts, rowid, question, answer)
                    VALUES ('delete', old.id, old.question, old.answer);
                END;
                """
            )
            self.db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS knowledge_base_au AFTER UPDATE ON knowledge_base
                BEGIN
                    INSERT INTO knowledge_base_fts(knowledge_base_fts, rowid, question, answer)
                    VALUES ('delete', old.id, old.question, old.answer);
                    INSERT INTO knowledge_base_fts(rowid, question, answer)
                    VALUES (new.id, new.question, new.answer);
                END;
                """
            )
            logger.info("Created knowledge_base table with FTS index")

    # User preferences methods

    def get_user_preference(self, user_id: int, preference_key: str) -> Optional[str]:
        """Get user preference.

        Args:
            user_id: User ID
            preference_key: Preference key

        Returns:
            Preference value or None if not found
        """
        try:
            result = self.db["user_preferences"].get(
                {"user_id": user_id, "preference_key": preference_key}
            )
            return result["preference_value"] if result else None
        except Exception as e:
            logger.error(f"Error getting user preference: {e}")
            return None

    def get_user_preferences(self, user_id: int) -> Dict[str, str]:
        """Get all preferences for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of preference key-value pairs
        """
        try:
            results = self.db["user_preferences"].rows_where(
                "user_id = ?", [user_id]
            )
            return {row["preference_key"]: row["preference_value"] for row in results}
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    def set_user_preference(self, user_id: int, preference_key: str, preference_value: str) -> bool:
        """Set user preference.

        Args:
            user_id: User ID
            preference_key: Preference key
            preference_value: Preference value

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db["user_preferences"].upsert(
                {
                    "user_id": user_id,
                    "preference_key": preference_key,
                    "preference_value": preference_value,
                    "updated_at": datetime.now().isoformat(),
                },
                pk=("user_id", "preference_key"),
            )
            return True
        except Exception as e:
            logger.error(f"Error setting user preference: {e}")
            return False

    def delete_user_preference(self, user_id: int, preference_key: str) -> bool:
        """Delete user preference.

        Args:
            user_id: User ID
            preference_key: Preference key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db["user_preferences"].delete_where(
                "user_id = ? AND preference_key = ?", [user_id, preference_key]
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting user preference: {e}")
            return False

    # Reminders methods

    def add_reminder(self, user_id: int, text: str, scheduled_at: str) -> Optional[int]:
        """Add a reminder.

        Args:
            user_id: User ID
            text: Reminder text
            scheduled_at: Scheduled time (ISO format)

        Returns:
            Reminder ID if successful, None otherwise
        """
        try:
            # Check if user has reached the maximum number of reminders
            count = self.db["reminders"].count_where(
                "user_id = ? AND is_completed = 0", [user_id]
            )
            if count >= settings.MAX_REMINDERS_PER_USER:
                logger.warning(
                    f"User {user_id} has reached the maximum number of reminders")
                return None

            # Add reminder
            reminder_id = self.db["reminders"].insert(
                {
                    "user_id": user_id,
                    "text": text,
                    "scheduled_at": scheduled_at,
                    "created_at": datetime.now().isoformat(),
                    "is_completed": 0,
                }
            ).last_pk
            return reminder_id
        except Exception as e:
            logger.error(f"Error adding reminder: {e}")
            return None

    def get_reminder(self, reminder_id: int) -> Optional[Dict]:
        """Get a reminder by ID.

        Args:
            reminder_id: Reminder ID

        Returns:
            Reminder data or None if not found
        """
        try:
            return self.db["reminders"].get(reminder_id)
        except Exception as e:
            logger.error(f"Error getting reminder: {e}")
            return None

    def get_user_reminders(self, user_id: int, include_completed: bool = False) -> List[Dict]:
        """Get all reminders for a user.

        Args:
            user_id: User ID
            include_completed: Whether to include completed reminders

        Returns:
            List of reminder data
        """
        try:
            if include_completed:
                return list(self.db["reminders"].rows_where(
                    "user_id = ?", [user_id]
                ))
            else:
                return list(self.db["reminders"].rows_where(
                    "user_id = ? AND is_completed = 0", [user_id]
                ))
        except Exception as e:
            logger.error(f"Error getting user reminders: {e}")
            return []

    def get_due_reminders(self) -> List[Dict]:
        """Get all due reminders.

        Returns:
            List of due reminder data
        """
        try:
            now = datetime.now().isoformat()
            return list(self.db["reminders"].rows_where(
                "scheduled_at <= ? AND is_completed = 0", [now]
            ))
        except Exception as e:
            logger.error(f"Error getting due reminders: {e}")
            return []

    def mark_reminder_completed(self, reminder_id: int) -> bool:
        """Mark a reminder as completed.

        Args:
            reminder_id: Reminder ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db["reminders"].update(
                reminder_id, {"is_completed": 1}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking reminder as completed: {e}")
            return False

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder.

        Args:
            reminder_id: Reminder ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db["reminders"].delete(reminder_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}")
            return False

    # Knowledge base methods

    def add_knowledge(self, question: str, answer: str) -> Optional[int]:
        """Add knowledge to the knowledge base.

        Args:
            question: Question
            answer: Answer

        Returns:
            Knowledge ID if successful, None otherwise
        """
        try:
            now = datetime.now().isoformat()
            knowledge_id = self.db["knowledge_base"].insert(
                {
                    "question": question,
                    "answer": answer,
                    "created_at": now,
                    "updated_at": now,
                }
            ).last_pk
            return knowledge_id
        except Exception as e:
            logger.error(f"Error adding knowledge: {e}")
            return None

    def search_knowledge(self, query: str, limit: int = 5) -> List[Dict]:
        """Search the knowledge base.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching knowledge items
        """
        try:
            # Use FTS to search
            results = self.db.execute(
                f"""
                SELECT kb.id, kb.question, kb.answer, kb.created_at, kb.updated_at
                FROM knowledge_base_fts fts
                JOIN knowledge_base kb ON fts.rowid = kb.id
                WHERE knowledge_base_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                [query, limit]
            ).fetchall()

            # Convert to list of dictionaries
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []


# Create a singleton instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get database manager instance.

    Returns:
        Database manager instance
    """
    return db_manager
