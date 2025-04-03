from db.errors_database import ErrorsDatabase
import sqlite3
from fiber.logging_utils import get_logger
import os

logger = get_logger(__name__)


class ErrorsStorage:
    def __init__(self, db_path="errors.db"):
        self.db = ErrorsDatabase(db_path=db_path)
        # Get retention period from environment or use default of 5 days
        self.retention_days = int(os.getenv("ERROR_LOGS_RETENTION_DAYS", "5"))
        logger.info(f"Error logs retention period set to {self.retention_days} days")

    def add_error(self, hotkey, tee_address, miner_address, message):
        """Add a new error entry to the database."""
        try:
            logger.debug(f"Recording error for hotkey={hotkey}: {message}")
            self.db.add_error(hotkey, tee_address, miner_address, message)
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to add error: {e}")
            return False

    def get_errors_by_hotkey(self, hotkey, limit=100):
        """Get errors for a specific hotkey."""
        try:
            return self.db.get_errors_by_hotkey(hotkey, limit)
        except sqlite3.Error as e:
            logger.error(f"Failed to get errors for hotkey {hotkey}: {e}")
            return []

    def get_all_errors(self, limit=100):
        """Get all errors."""
        try:
            return self.db.get_all_errors(limit)
        except sqlite3.Error as e:
            logger.error(f"Failed to get all errors: {e}")
            return []

    def clean_old_errors(self, hours=24):
        """Clean errors older than the specified hours."""
        try:
            count = self.db.clean_old_errors(hours)
            logger.info(f"Cleaned {count} errors older than {hours} hours")
            return count
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old errors: {e}")
            return 0

    def clean_errors_based_on_retention(self):
        """
        Clean errors based on the configured retention period.
        Uses ERROR_LOGS_RETENTION_DAYS environment variable (default: 5 days).
        """
        retention_hours = self.retention_days * 24
        try:
            count = self.db.clean_old_errors(retention_hours)
            logger.info(
                f"Retention cleanup: removed {count} errors older than {self.retention_days} days"
            )
            return count
        except sqlite3.Error as e:
            logger.error(f"Failed to clean errors based on retention period: {e}")
            return 0

    def get_error_count(self, hours=24):
        """Get count of errors in the last specified hours."""
        try:
            return self.db.get_error_count(hours)
        except sqlite3.Error as e:
            logger.error(f"Failed to get error count: {e}")
            return 0
