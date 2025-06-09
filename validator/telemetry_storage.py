from db.telemetry_database import TelemetryDatabase
import sqlite3
from fiber.logging_utils import get_logger
from interfaces.types import NodeData

logger = get_logger(__name__)


class TelemetryStorage:
    def __init__(self, db_path="telemetry_data.db"):
        self.db = TelemetryDatabase(db_path=db_path)

    def add_telemetry(self, telemetry_data):
        """Add a new telemetry entry to the database."""
        try:
            self.db.add_telemetry(telemetry_data)
        except sqlite3.Error as e:
            logger.error(f"Failed to add telemetry: {e}")

    def clean_old_entries(self, hours):
        """
        Clean all telemetry entries older than the specified number
        of hours.
        """
        try:
            self.db.clean_old_entries(hours)
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old telemetry entries: {e}")

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
        Delete all telemetry entries for a specific hotkey using the
        TelemetryDatabase method.
        """
        try:
            rows_deleted = self.db.delete_telemetry_by_hotkey(hotkey)
            logger.info(f"Deleted {rows_deleted} telemetry entries for hotkey {hotkey}")
            return rows_deleted
        except sqlite3.Error as e:
            logger.error(f"Failed to delete telemetry for hotkey {hotkey}: {e}")
            return 0

    def get_all_telemetry(self):
        """
        Retrieve all telemetry data from the database.
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
