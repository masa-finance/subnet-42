import sqlite3
from threading import Lock


class TelemetryDatabase:
    def __init__(self, db_path="./telemetry_data.db"):
        self.db_path = db_path
        self.lock = Lock()
        self._create_table()
        self._ensure_worker_id_column()

    def _create_table(self):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    hotkey TEXT,
                    uid TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    boot_time INT,
                    last_operation_time INT,
                    current_time INT,
                    twitter_auth_errors INT,
                    twitter_errors INT,
                    twitter_ratelimit_errors INT,
                    twitter_returned_other INT,
                    twitter_returned_profiles INT,
                    twitter_returned_tweets INT,
                    twitter_scrapes INT,
                    web_errors INT,
                    web_success INT,
                    worker_id TEXT
                )
            """
            )
            conn.commit()

    def _ensure_worker_id_column(self):
        """
        Ensure the worker_id column exists in the telemetry table.
        This handles database migrations for existing databases.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Check if worker_id column exists
            cursor.execute("PRAGMA table_info(telemetry)")
            columns = [col[1] for col in cursor.fetchall()]

            if "worker_id" not in columns:
                # Add the worker_id column if it doesn't exist
                cursor.execute(
                    """
                    ALTER TABLE telemetry
                    ADD COLUMN worker_id TEXT
                    """
                )
                conn.commit()

    def add_telemetry(self, telemetry_data):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO telemetry (hotkey, uid, boot_time, last_operation_time, current_time, 
                twitter_auth_errors, twitter_errors, twitter_ratelimit_errors, twitter_returned_other, 
                twitter_returned_profiles, twitter_returned_tweets, twitter_scrapes, web_errors, web_success,
                worker_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telemetry_data.hotkey,
                    telemetry_data.uid,
                    telemetry_data.boot_time,
                    telemetry_data.last_operation_time,
                    telemetry_data.current_time,
                    telemetry_data.twitter_auth_errors,
                    telemetry_data.twitter_errors,
                    telemetry_data.twitter_ratelimit_errors,
                    telemetry_data.twitter_returned_other,
                    telemetry_data.twitter_returned_profiles,
                    telemetry_data.twitter_returned_tweets,
                    telemetry_data.twitter_scrapes,
                    telemetry_data.web_errors,
                    telemetry_data.web_success,
                    telemetry_data.worker_id,
                ),
            )
            conn.commit()

    def clean_old_entries(self, hours):
        """
        Remove all telemetry entries older than the specified number of hours.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM telemetry 
                WHERE timestamp < datetime('now', ?)
                """,
                (f"-{hours} hours",),
            )
            conn.commit()

    def get_telemetry_by_hotkey(self, hotkey):
        """Retrieve telemetry data for a specific hotkey."""
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM telemetry WHERE hotkey = ?
                """,
                (hotkey,),
            )
            telemetry_data = cursor.fetchall()
            return telemetry_data

    def get_all_hotkeys_with_telemetry(self):
        """Retrieve all unique hotkeys that have at least one telemetry entry."""
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT hotkey FROM telemetry
                """
            )
            hotkeys = [row[0] for row in cursor.fetchall()]
            return hotkeys

    def delete_telemetry_by_hotkey(self, hotkey):
        """Delete all telemetry entries for a specific hotkey."""
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM telemetry WHERE hotkey = ?
                """,
                (hotkey,),
            )
            conn.commit()
            return cursor.rowcount  # Return the number of rows deleted

    def get_all_telemetry(self):
        """Retrieve all telemetry data from the database."""
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM telemetry
                """
            )
            telemetry_data = cursor.fetchall()
            return telemetry_data
