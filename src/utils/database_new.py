"""
Thread-safe database utility for the Just Ask AI Telegram bot.
"""
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.settings import get_settings
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class DatabaseManager:
    """Thread-safe database manager for the Just Ask AI Telegram bot."""

    # Thread-local storage for database connections
    _local = threading.local()

    def __init__(self):
        """Initialize database manager."""
        self.db_path = settings.DATABASE_PATH

        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_db()

        logger.info(f"Initialized database at {self.db_path}")

    def _get_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            # Configure connection
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, preference_key)
                )
            """)

            # Reminders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_completed INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Create index on user_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_user_id
                ON reminders (user_id)
            """)

            # Knowledge base table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create full-text search index
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_base_fts
                USING fts5(question, answer, content=knowledge_base)
            """)

            # Create triggers to keep FTS index updated
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_base_ai AFTER INSERT ON knowledge_base
                BEGIN
                    INSERT INTO knowledge_base_fts(rowid, question, answer)
                    VALUES (new.id, new.question, new.answer);
                END;
            """)

            # User feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    reason TEXT,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # Create index on user_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id
                ON user_feedback (user_id)
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_base_ad AFTER DELETE ON knowledge_base
                BEGIN
                    INSERT INTO knowledge_base_fts(knowledge_base_fts, rowid, question, answer)
                    VALUES ('delete', old.id, old.question, old.answer);
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_base_au AFTER UPDATE ON knowledge_base
                BEGIN
                    INSERT INTO knowledge_base_fts(knowledge_base_fts, rowid, question, answer)
                    VALUES ('delete', old.id, old.question, old.answer);
                    INSERT INTO knowledge_base_fts(rowid, question, answer)
                    VALUES (new.id, new.question, new.answer);
                END;
            """)

            conn.commit()
            logger.info("Database schema initialized")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error initializing database: {e}")
        finally:
            conn.close()

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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT preference_value FROM user_preferences WHERE user_id = ? AND preference_key = ?",
                (user_id, preference_key)
            )

            result = cursor.fetchone()
            return result[0] if result else None

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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT preference_key, preference_value FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )

            return {row[0]: row[1] for row in cursor.fetchall()}

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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, preference_key, preference_value,
                 datetime.now().isoformat())
            )

            conn.commit()
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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM user_preferences WHERE user_id = ? AND preference_key = ?",
                (user_id, preference_key)
            )

            conn.commit()
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
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if user has reached the maximum number of reminders
            cursor.execute(
                "SELECT COUNT(*) FROM reminders WHERE user_id = ? AND is_completed = 0",
                (user_id,)
            )

            count = cursor.fetchone()[0]
            if count >= settings.MAX_REMINDERS_PER_USER:
                logger.warning(
                    f"User {user_id} has reached the maximum number of reminders")
                return None

            # Add reminder
            cursor.execute(
                """
                INSERT INTO reminders (user_id, text, scheduled_at, created_at, is_completed)
                VALUES (?, ?, ?, ?, 0)
                """,
                (user_id, text, scheduled_at, datetime.now().isoformat())
            )

            conn.commit()
            return cursor.lastrowid

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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_id,)
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

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
            conn = self._get_connection()
            cursor = conn.cursor()

            if include_completed:
                cursor.execute(
                    "SELECT * FROM reminders WHERE user_id = ? ORDER BY scheduled_at",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM reminders WHERE user_id = ? AND is_completed = 0 ORDER BY scheduled_at",
                    (user_id,)
                )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting user reminders: {e}")
            return []

    def get_due_reminders(self) -> List[Dict]:
        """Get all due reminders.

        Returns:
            List of due reminder data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            cursor.execute(
                "SELECT * FROM reminders WHERE scheduled_at <= ? AND is_completed = 0",
                (now,)
            )

            return [dict(row) for row in cursor.fetchall()]

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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE reminders SET is_completed = 1 WHERE id = ?",
                (reminder_id,)
            )

            conn.commit()
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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder_id,)
            )

            conn.commit()
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
            conn = self._get_connection()
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO knowledge_base (question, answer, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (question, answer, now, now)
            )

            conn.commit()
            return cursor.lastrowid

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
            conn = self._get_connection()
            cursor = conn.cursor()

            # Use FTS to search
            cursor.execute(
                """
                SELECT kb.id, kb.question, kb.answer, kb.created_at, kb.updated_at
                FROM knowledge_base_fts fts
                JOIN knowledge_base kb ON fts.rowid = kb.id
                WHERE knowledge_base_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit)
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    # Feedback methods

    def store_feedback(self, user_id: int, message_id: str, rating: int, reason: Optional[str] = None, details: Optional[str] = None) -> Optional[int]:
        """Store user feedback.

        Args:
            user_id: User ID
            message_id: Message ID
            rating: Rating (1-5)
            reason: Reason for rating (optional)
            details: Additional details (optional)

        Returns:
            Feedback ID if successful, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO user_feedback (user_id, message_id, rating, reason, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, message_id, rating, reason,
                 details, datetime.now().isoformat())
            )

            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
            return None

    def get_user_feedback(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get feedback from a user.

        Args:
            user_id: User ID
            limit: Maximum number of results

        Returns:
            List of feedback items
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM user_feedback
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting user feedback: {e}")
            return []

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics.

        Returns:
            Dictionary with feedback statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get average rating
            cursor.execute("SELECT AVG(rating) FROM user_feedback")
            avg_rating = cursor.fetchone()[0]

            # Get rating distribution
            cursor.execute(
                """
                SELECT rating, COUNT(*) as count
                FROM user_feedback
                GROUP BY rating
                ORDER BY rating
                """
            )
            rating_distribution = {row[0]: row[1] for row in cursor.fetchall()}

            # Get total feedback count
            cursor.execute("SELECT COUNT(*) FROM user_feedback")
            total_count = cursor.fetchone()[0]

            return {
                "average_rating": avg_rating,
                "rating_distribution": rating_distribution,
                "total_count": total_count
            }

        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {
                "average_rating": 0,
                "rating_distribution": {},
                "total_count": 0
            }


# Create a singleton instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get database manager instance.

    Returns:
        Database manager instance
    """
    return db_manager
