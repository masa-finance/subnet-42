import sqlite3
from threading import Lock


class RoutingTableDatabase:
    def __init__(self, db_path="./miner_tee_addresses.db"):
        self.db_path = db_path
        self.lock = Lock()
        self._create_table()
        self._create_worker_registry_table()

    def _create_table(self):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS miner_addresses (
                    hotkey TEXT,
                    uid TEXT,
                    address TEXT UNIQUE,
                    worker_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()

    def _create_worker_registry_table(self):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_registry (
                    worker_id TEXT PRIMARY KEY,
                    hotkey TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()

    def add_address(self, hotkey, uid, address, worker_id=None):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO miner_addresses (hotkey, uid, address, worker_id) 
                VALUES (?, ?, ?, ?)
                """,
                (hotkey, uid, address, worker_id),
            )
            conn.commit()

    def update_address(self, hotkey, uid, new_address, worker_id=None):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if worker_id is not None:
                cursor.execute(
                    """
                    UPDATE miner_addresses SET address = ?, worker_id = ? 
                    WHERE hotkey = ? AND uid = ?
                    """,
                    (new_address, worker_id, hotkey, uid),
                )
            else:
                cursor.execute(
                    """
                    UPDATE miner_addresses SET address = ? 
                    WHERE hotkey = ? AND uid = ?
                    """,
                    (new_address, hotkey, uid),
                )
            conn.commit()

    def delete_address(self, hotkey, uid):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM miner_addresses 
                WHERE hotkey = ? AND uid = ?
                """,
                (hotkey, uid),
            )
            conn.commit()

    def clean_old_entries(self):
        """
        Remove all entries where the timestamp is more than one hour older.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM miner_addresses 
                WHERE timestamp < datetime('now', '-1 hour')
                """
            )
            conn.commit()

    def register_worker(self, worker_id, hotkey):
        """
        Register a worker_id with a hotkey in the worker registry.
        If the worker_id already exists, it will update the hotkey.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO worker_registry (worker_id, hotkey) 
                VALUES (?, ?)
                """,
                (worker_id, hotkey),
            )
            conn.commit()

    def unregister_worker(self, worker_id):
        """
        Remove a worker_id from the worker registry.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM worker_registry 
                WHERE worker_id = ?
                """,
                (worker_id,),
            )
            conn.commit()

    def unregister_workers_by_hotkey(self, hotkey):
        """
        Remove all worker_ids associated with a hotkey from the registry.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM worker_registry 
                WHERE hotkey = ?
                """,
                (hotkey,),
            )
            conn.commit()

    def get_worker_hotkey(self, worker_id):
        """
        Get the hotkey associated with a worker_id from the registry.
        Returns None if the worker_id is not registered.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT hotkey FROM worker_registry 
                WHERE worker_id = ?
                """,
                (worker_id,),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def get_workers_by_hotkey(self, hotkey):
        """
        Get all worker_ids associated with a hotkey from the registry.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT worker_id FROM worker_registry 
                WHERE hotkey = ?
                """,
                (hotkey,),
            )
            results = cursor.fetchall()
            return [row[0] for row in results]

    def get_all_worker_registrations(self):
        """
        Get all worker_id and hotkey pairs from the registry.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT worker_id, hotkey FROM worker_registry
                """
            )
            results = cursor.fetchall()
            return [(row[0], row[1]) for row in results]

    def clean_old_worker_registrations(self, hours=24):
        """
        Remove worker registrations older than the specified number of hours.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM worker_registry 
                WHERE timestamp < datetime('now', ?)
                """,
                (f"-{hours} hours",),
            )
            conn.commit()
