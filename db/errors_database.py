import sqlite3
from threading import Lock


class ErrorsDatabase:
    def __init__(self, db_path="./errors.db"):
        self.db_path = db_path
        self.lock = Lock()
        self._create_table()

    def _create_table(self):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hotkey TEXT,
                    tee_address TEXT,
                    miner_address TEXT,
                    message TEXT
                )
            """
            )
            conn.commit()

    def add_error(self, hotkey, tee_address, miner_address, message):
        """
        Add a new error entry to the database.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO errors (hotkey, tee_address, miner_address, message) 
                VALUES (?, ?, ?, ?)
                """,
                (hotkey, tee_address, miner_address, message),
            )
            conn.commit()

    def get_errors_by_hotkey(self, hotkey, limit=100):
        """
        Retrieve errors for a specific hotkey.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, tee_address, miner_address, message 
                FROM errors 
                WHERE hotkey = ? 
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (hotkey, limit),
            )
            results = cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "tee_address": row[1],
                    "miner_address": row[2],
                    "message": row[3],
                }
                for row in results
            ]

    def get_all_errors(self, limit=100):
        """
        Retrieve all errors, ordered by timestamp descending.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, hotkey, tee_address, miner_address, message 
                FROM errors 
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            results = cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "hotkey": row[1],
                    "tee_address": row[2],
                    "miner_address": row[3],
                    "message": row[4],
                }
                for row in results
            ]

    def clean_old_errors(self, hours=24):
        """
        Remove error entries older than the specified number of hours.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM errors 
                WHERE timestamp < datetime('now', ?)
                """,
                (f"-{hours} hours",),
            )
            conn.commit()
            return cursor.rowcount

    def get_error_count(self, hours=24):
        """
        Get the count of errors in the last specified number of hours.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM errors 
                WHERE timestamp > datetime('now', ?)
                """,
                (f"-{hours} hours",),
            )
            result = cursor.fetchone()
            return result[0] if result else 0
