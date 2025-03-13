from db.routing_table_database import RoutingTableDatabase
import sqlite3


class RoutingTable:
    def __init__(self, db_path="miner_tee_addresses"):
        self.db = RoutingTableDatabase(db_path=db_path)

    def add_miner_address(self, hotkey, uid, address):
        """Add a new miner address to the database."""
        try:
            self.db.add_address(hotkey, uid, address)
        except sqlite3.Error as e:
            print(f"Failed to add address: {e}")

    def remove_miner_address(self, hotkey, uid):
        """Remove a specific miner address from the database."""
        try:
            self.db.delete_address(hotkey, uid)
        except sqlite3.Error as e:
            print(f"Failed to remove address: {e}")

    def clear_miner(self, hotkey):
        """Remove all addresses associated with a miner."""
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
        except sqlite3.Error as e:
            print(f"Failed to clear miner: {e}")

    def get_miner_addresses(self, hotkey):
        """Retrieve all addresses associated with a given miner hotkey."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT address FROM miner_addresses WHERE hotkey = ?
                """,
                    (hotkey,),
                )
                addresses = cursor.fetchall()
                return [address[0] for address in addresses]
        except sqlite3.Error as e:
            print(f"Failed to retrieve addresses: {e}")
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
            print(f"Failed to retrieve all addresses: {e}")
            return []

    def get_all_addresses_with_hotkeys(self):
        """Retrieve a list of all addresses and their associated hotkeys from the database."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT hotkey, address FROM miner_addresses
                """
                )
                results = cursor.fetchall()
                return [(hotkey, address) for hotkey, address in results]
        except sqlite3.Error as e:
            print(f"Failed to retrieve addresses with hotkeys: {e}")
            return []
