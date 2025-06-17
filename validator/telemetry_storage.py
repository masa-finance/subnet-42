from db.telemetry_database import TelemetryDatabase
from db.postgresql_telemetry_database import PostgreSQLTelemetryDatabase
import sqlite3
from fiber.logging_utils import get_logger
from interfaces.types import NodeData
import os

logger = get_logger(__name__)


class TelemetryStorage:
    def __init__(self, db_path="telemetry_data.db"):
        """Initialize dual storage: SQLite (primary) and PostgreSQL (persistent)."""
        # SQLite database (existing functionality)
        self.db = TelemetryDatabase(db_path=db_path)

        # PostgreSQL database (new persistent storage)
        self.postgres_db = None
        self.postgres_enabled = False

        # Try to initialize PostgreSQL connection
        self._init_postgresql()

    def _init_postgresql(self):
        """Initialize PostgreSQL connection if host is configured."""
        postgres_host = os.getenv("POSTGRES_HOST")

        # Only try to initialize PostgreSQL if host is explicitly set
        if not postgres_host:
            logger.info("POSTGRES_HOST not set, PostgreSQL telemetry storage disabled")
            self.postgres_enabled = False
            return

        try:
            # Check if all required PostgreSQL environment variables are set
            required_vars = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            if missing_vars:
                logger.warning(
                    f"Missing PostgreSQL environment variables: {missing_vars}"
                )
                logger.info("PostgreSQL telemetry storage disabled")
                self.postgres_enabled = False
                return

            self.postgres_db = PostgreSQLTelemetryDatabase()
            self.postgres_enabled = True
            logger.info("PostgreSQL telemetry storage enabled")
        except ConnectionError as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            logger.info(
                "PostgreSQL telemetry storage disabled - continuing with SQLite only"
            )
            self.postgres_enabled = False
        except Exception as e:
            logger.warning(f"Failed to initialize PostgreSQL telemetry storage: {e}")
            logger.info("Continuing with SQLite-only storage")
            self.postgres_enabled = False

    def add_telemetry(self, telemetry_data):
        """Add telemetry to both SQLite and PostgreSQL databases."""
        # Always add to SQLite (primary storage)
        try:
            self.db.add_telemetry(telemetry_data)
        except sqlite3.Error as e:
            logger.error(f"Failed to add telemetry to SQLite: {e}")

        # Try to add to PostgreSQL (persistent storage) if enabled
        if self.postgres_enabled and self.postgres_db:
            try:
                self.postgres_db.add_telemetry(telemetry_data)
            except Exception as e:
                logger.warning(f"Failed to add telemetry to PostgreSQL: {e}")
                # Don't disable PostgreSQL on individual failures
                # as connection might be temporarily unavailable

    def clean_old_entries(self, hours):
        """Clean old entries from both databases."""
        # Clean SQLite
        try:
            self.db.clean_old_entries(hours)
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old SQLite telemetry entries: {e}")

        # Clean PostgreSQL if enabled
        if self.postgres_enabled and self.postgres_db:
            try:
                self.postgres_db.clean_old_entries(hours)
            except Exception as e:
                logger.warning(f"Failed to clean old PostgreSQL telemetry entries: {e}")

    def get_telemetry_by_hotkey(self, hotkey):
        """
        Retrieve telemetry data for a specific hotkey using the
        TelemetryDatabase method. Returns a list of NodeData objects.
        """
        try:
            telemetry_data = self.db.get_telemetry_by_hotkey(hotkey)
            return [
                NodeData(
                    hotkey=row[0],
                    uid=row[1],
                    boot_time=row[3],
                    last_operation_time=row[4],
                    current_time=row[5],
                    twitter_auth_errors=row[6],
                    twitter_errors=row[7],
                    twitter_ratelimit_errors=row[8],
                    twitter_returned_other=row[9],
                    twitter_returned_profiles=row[10],
                    twitter_returned_tweets=row[11],
                    twitter_scrapes=row[12],
                    web_errors=row[13],
                    web_success=row[14],
                    timestamp=row[2],
                    worker_id=row[15],
                )
                for row in telemetry_data
            ]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve telemetry for hotkey {hotkey}: {e}")
            return []

    def get_telemetry_by_hotkey_postgresql(self, hotkey):
        """
        Retrieve telemetry data for a specific hotkey from PostgreSQL.
        Returns a list of NodeData objects.
        """
        if not self.postgres_enabled or not self.postgres_db:
            logger.warning("PostgreSQL not available for telemetry retrieval")
            return []

        try:
            telemetry_data = self.postgres_db.get_telemetry_by_hotkey(hotkey)
            return [
                NodeData(
                    hotkey=row["hotkey"],
                    uid=row["uid"],
                    boot_time=row["boot_time"],
                    last_operation_time=row["last_operation_time"],
                    current_time=row["current_time"],
                    twitter_auth_errors=row["twitter_auth_errors"],
                    twitter_errors=row["twitter_errors"],
                    twitter_ratelimit_errors=row["twitter_ratelimit_errors"],
                    twitter_returned_other=row["twitter_returned_other"],
                    twitter_returned_profiles=row["twitter_returned_profiles"],
                    twitter_returned_tweets=row["twitter_returned_tweets"],
                    twitter_scrapes=row["twitter_scrapes"],
                    web_errors=row["web_errors"],
                    web_success=row["web_success"],
                    timestamp=row["timestamp"],
                    worker_id=row["worker_id"],
                )
                for row in telemetry_data
            ]
        except Exception as e:
            logger.error(
                f"Failed to retrieve PostgreSQL telemetry for hotkey {hotkey}: {e}"
            )
            return []

    def get_all_hotkeys_with_telemetry(self):
        """
        Retrieve all unique hotkeys that have at least one telemetry entry
        using the TelemetryDatabase method.
        """
        try:
            hotkeys = self.db.get_all_hotkeys_with_telemetry()
            return hotkeys
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve hotkeys with telemetry: {e}")
            return []

    def delete_telemetry_by_hotkey(self, hotkey):
        """
        Delete all telemetry entries for a specific hotkey from both databases.
        """
        total_deleted = 0

        # Delete from SQLite
        try:
            rows_deleted = self.db.delete_telemetry_by_hotkey(hotkey)
            total_deleted += rows_deleted
            logger.info(
                f"Deleted {rows_deleted} SQLite telemetry entries for hotkey {hotkey}"
            )
        except sqlite3.Error as e:
            logger.error(f"Failed to delete SQLite telemetry for hotkey {hotkey}: {e}")

        # Delete from PostgreSQL if enabled
        if self.postgres_enabled and self.postgres_db:
            try:
                rows_deleted = self.postgres_db.delete_telemetry_by_hotkey(hotkey)
                total_deleted += rows_deleted
                logger.info(
                    f"Deleted {rows_deleted} PostgreSQL telemetry entries for hotkey {hotkey}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to delete PostgreSQL telemetry for hotkey {hotkey}: {e}"
                )

        return total_deleted

    def get_all_telemetry(self):
        """
        Retrieve all telemetry data from the SQLite database.
        Returns a list of NodeData objects.
        """
        try:
            telemetry_data = self.db.get_all_telemetry()
            return [
                NodeData(
                    hotkey=row[0],
                    uid=row[1],
                    boot_time=row[3],
                    last_operation_time=row[4],
                    current_time=row[5],
                    twitter_auth_errors=row[6],
                    twitter_errors=row[7],
                    twitter_ratelimit_errors=row[8],
                    twitter_returned_other=row[9],
                    twitter_returned_profiles=row[10],
                    twitter_returned_tweets=row[11],
                    twitter_scrapes=row[12],
                    web_errors=row[13],
                    web_success=row[14],
                    timestamp=row[2],
                    worker_id=row[15] if len(row) > 15 else None,
                )
                for row in telemetry_data
            ]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve all telemetry: {e}")
            return []

    def get_all_telemetry_postgresql(self, limit=1000):
        """
        Retrieve all telemetry data from PostgreSQL.
        Returns a list of NodeData objects.
        """
        if not self.postgres_enabled or not self.postgres_db:
            logger.warning("PostgreSQL not available for telemetry retrieval")
            return []

        try:
            telemetry_data = self.postgres_db.get_all_telemetry(limit)
            return [
                NodeData(
                    hotkey=row["hotkey"],
                    uid=row["uid"],
                    boot_time=row["boot_time"],
                    last_operation_time=row["last_operation_time"],
                    current_time=row["current_time"],
                    twitter_auth_errors=row["twitter_auth_errors"],
                    twitter_errors=row["twitter_errors"],
                    twitter_ratelimit_errors=row["twitter_ratelimit_errors"],
                    twitter_returned_other=row["twitter_returned_other"],
                    twitter_returned_profiles=row["twitter_returned_profiles"],
                    twitter_returned_tweets=row["twitter_returned_tweets"],
                    twitter_scrapes=row["twitter_scrapes"],
                    web_errors=row["web_errors"],
                    web_success=row["web_success"],
                    timestamp=row["timestamp"],
                    worker_id=row["worker_id"],
                )
                for row in telemetry_data
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve all PostgreSQL telemetry: {e}")
            return []

    def get_telemetry_stats_postgresql(self):
        """Get statistics from PostgreSQL telemetry data."""
        if not self.postgres_enabled or not self.postgres_db:
            logger.warning("PostgreSQL not available for telemetry stats")
            return {
                "total_entries": 0,
                "unique_hotkeys": 0,
                "oldest_entry": None,
                "newest_entry": None,
            }

        try:
            return self.postgres_db.get_telemetry_stats()
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL telemetry stats: {e}")
            return {
                "total_entries": 0,
                "unique_hotkeys": 0,
                "oldest_entry": None,
                "newest_entry": None,
            }

    def check_postgresql_status(self):
        """Check if PostgreSQL connection is working."""
        if not self.postgres_enabled or not self.postgres_db:
            return False

        try:
            return self.postgres_db.check_connection()
        except Exception:
            return False
