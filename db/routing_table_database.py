import sqlite3
from threading import Lock


class RoutingTableDatabase:
    def __init__(self, db_path="./miner_tee_addresses.db"):
        self.db_path = db_path
        self.lock = Lock()
        self._create_table()

    def _create_table(self):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS miner_addresses (
                    hotkey TEXT,
                    uid TEXT,
                    address TEXT UNIQUE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()

    def add_address(self, hotkey, uid, address):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO miner_addresses (hotkey, uid, address) 
                VALUES (?, ?, ?)
                """,
                (hotkey, uid, address),
            )
            conn.commit()

    def update_address(self, hotkey, uid, new_address):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
