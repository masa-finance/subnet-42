from db.routing_table_database import RoutingTableDatabase
import sqlite3
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


class RoutingTable:
    def __init__(self, db_path="miner_tee_addresses"):
        self.db = RoutingTableDatabase(db_path=db_path)

    def add_miner_address(self, hotkey, uid, address, worker_id=None):
        """Add a new miner address to the database."""
        try:
            self.db.add_address(hotkey, uid, address, worker_id)
        except sqlite3.Error as e:
            logger.error(f"Failed to add address: {e}")

    def remove_miner_address(self, hotkey, uid):
        """Remove a specific miner address from the database."""
        try:
            self.db.delete_address(hotkey, uid)
        except sqlite3.Error as e:
            logger.error(f"Failed to remove address: {e}")

    def clear_miner(self, hotkey):
        """Remove all addresses and worker registrations for a miner."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM miner_addresses WHERE hotkey = ?
                """,
                    (hotkey,),
                )
                conn.commit()

            # Also remove all worker registrations for this hotkey
            self.unregister_workers_by_hotkey(hotkey)
        except sqlite3.Error as e:
            logger.error(f"Failed to clear miner: {e}")

    def get_miner_addresses(self, hotkey):
        """Retrieve all addresses associated with a given miner hotkey."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT address, worker_id FROM miner_addresses WHERE hotkey = ?
                """,
                    (hotkey,),
                )
                results = cursor.fetchall()
                return [(address, worker_id) for address, worker_id in results]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve addresses: {e}")
            return []

    def get_all_addresses(self):
        """Retrieve a list of all addresses in the database."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT address FROM miner_addresses
                """
                )
                addresses = cursor.fetchall()
                return [address[0] for address in addresses]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve all addresses: {e}")
            return []

    def get_all_addresses_with_hotkeys(self):
        """Retrieve a list of all addresses and their associated hotkeys from the database."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT hotkey, address, worker_id FROM miner_addresses
                """
                )
                results = cursor.fetchall()
                return [
                    (hotkey, address, worker_id)
                    for hotkey, address, worker_id in results
                ]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve addresses with hotkeys: {e}")
            return []

    def register_worker(self, worker_id, hotkey):
        """Register a worker_id with a hotkey."""
        try:
            self.db.register_worker(worker_id, hotkey)
        except sqlite3.Error as e:
            logger.error(f"Failed to register worker: {e}")

    def unregister_worker(self, worker_id):
        """Remove a worker_id from the registry."""
        try:
            self.db.unregister_worker(worker_id)
        except sqlite3.Error as e:
            logger.error(f"Failed to unregister worker: {e}")

    def unregister_workers_by_hotkey(self, hotkey):
        """Remove all worker_ids associated with a hotkey."""
        try:
            self.db.unregister_workers_by_hotkey(hotkey)
        except sqlite3.Error as e:
            logger.error(f"Failed to unregister workers for hotkey {hotkey}: {e}")

    def get_worker_hotkey(self, worker_id):
        """Get the hotkey associated with a worker_id."""
        try:
            return self.db.get_worker_hotkey(worker_id)
        except sqlite3.Error as e:
            logger.error(f"Failed to get hotkey for worker {worker_id}: {e}")
            return None

    def get_workers_by_hotkey(self, hotkey):
        """Get all worker_ids associated with a hotkey."""
        try:
            return self.db.get_workers_by_hotkey(hotkey)
        except sqlite3.Error as e:
            logger.error(f"Failed to get workers for hotkey {hotkey}: {e}")
            return []

    def get_all_worker_registrations(self):
        """Get all worker_id and hotkey pairs from the registry."""
        try:
            return self.db.get_all_worker_registrations()
        except sqlite3.Error as e:
            logger.error(f"Failed to get all worker registrations: {e}")
            return []

    def clean_old_worker_registrations(self, hours=24):
        """Clean worker registrations older than the specified hours."""
        try:
            self.db.clean_old_worker_registrations(hours)
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old worker registrations: {e}")

    def clean_old_entries(self):
        """Clean all old entries from both tables."""
        try:
            self.db.clean_old_entries()
            self.db.clean_old_worker_registrations()
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old entries: {e}")
