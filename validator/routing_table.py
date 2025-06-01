import os
import aiohttp
import asyncio
import random

from db.routing_table_database import RoutingTableDatabase
import sqlite3
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


class RoutingTable:
    def __init__(self, db_path="miner_tee_addresses.db"):
        self.db = RoutingTableDatabase(db_path=db_path)

    def add_miner_address(self, hotkey, uid, address, worker_id=None):
        """Add a new miner address to the database."""
        try:
            logger.info(
                f"Adding miner to routing table: hotkey={hotkey}, uid={uid}, "
                f"address={address}, worker_id={worker_id}"
            )

            # Check if there's already an entry with the exact same fields
            existing_entries = self.db.get_miner_addresses_by_hotkey(hotkey)
            for existing_uid, existing_address, existing_worker_id in existing_entries:
                # Skip if identical entry already exists
                if (
                    existing_uid == uid
                    and existing_address == address
                    and existing_worker_id == worker_id
                ):
                    logger.debug(
                        "Skipping add: Entry with identical fields already exists"
                    )
                    # Update timestamp to current time for the existing entry
                    self.update_timestamp(hotkey, uid, address, worker_id)
                    return

                # If same hotkey and uid but different address or worker_id,
                # remove old record
                if existing_uid == uid and (
                    existing_address != address or existing_worker_id != worker_id
                ):
                    logger.debug(
                        "Removing old entry to update with new address or worker_id"
                    )
                    self.db.delete_address(hotkey, uid)
                    break

            # Add the new address
            self.db.add_address(hotkey, uid, address, worker_id)
            logger.debug("Successfully added miner address to routing table")
        except sqlite3.Error as e:
            error_msg = str(e)
            if "UNIQUE constraint failed: miner_addresses.address" in error_msg:
                logger.debug(f"Address {address} is already registered in the system")
            else:
                logger.error(f"Failed to add address: {e}")

    def update_timestamp(self, hotkey, uid, address, worker_id=None):
        """Update the timestamp for an existing miner address to current time."""
        try:
            success = self.db.update_timestamp(hotkey, uid, address, worker_id)
            if success:
                logger.debug(f"Updated timestamp for {hotkey} - {address}")
            else:
                logger.debug(
                    f"No matching entry found to update timestamp for "
                    f"{hotkey} - {address}"
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to update timestamp: {e}")

    def get_address_timestamp(self, address):
        """Get the timestamp of a specific address."""
        try:
            return self.db.get_address_timestamp(address)
        except sqlite3.Error as e:
            logger.error(f"Failed to get timestamp for address {address}: {e}")
            return None

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
        """Get all unique addresses, randomized for fair distribution."""
        try:
            with self.db.lock, sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                # Get addresses without ORDER BY to avoid index interference
                cursor.execute("SELECT address FROM miner_addresses")
                addresses = [row[0] for row in cursor.fetchall()]
                # Randomize in Python for true randomization
                random.shuffle(addresses)
                return addresses
        except sqlite3.Error as e:
            logger.error(f"Failed to get addresses: {e}")
            return []

    def get_all_addresses_atomic(self):
        """Get all addresses atomically with proper locking for NATS publishing."""
        with self.db.lock:
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    # Get addresses without ORDER BY to avoid UNIQUE index interference
                    cursor.execute("SELECT address FROM miner_addresses")
                    addresses = [row[0] for row in cursor.fetchall()]
                    # Randomize in Python for true randomization
                    random.shuffle(addresses)
                    return addresses
            except sqlite3.Error as e:
                logger.error(f"Failed to get addresses atomically: {e}")
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
                # Convert to list and randomize in Python
                address_list = [
                    (hotkey, address, worker_id)
                    for hotkey, address, worker_id in results
                ]
                random.shuffle(address_list)
                return address_list
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
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old entries: {e}")

    def clean_old_entries_conservative(self):
        """Clean very old entries (6+ hours) from both tables."""
        try:
            self.db.clean_old_entries_conservative()
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old entries conservatively: {e}")

    def remove_miner_address_by_address(self, address):
        """Remove a miner address by address only."""
        try:
            self.db.remove_miner_address_by_address(address)
        except sqlite3.Error as e:
            logger.error(f"Failed to remove address {address}: {e}")

    async def add_unregistered_tee(self, address, hotkey):
        """Add an unregistered TEE to the database."""
        try:
            # Validate input
            if not address or not hotkey:
                logger.error("Both address and hotkey are required fields")
                return False

            # Get the API URL from environment variables
            masa_tee_api = os.getenv("MASA_TEE_API", "")
            if not masa_tee_api:
                logger.error("MASA_TEE_API environment variable not set")
                return False

            # Format the API endpoint and payload
            base_url = masa_tee_api.rstrip("/")
            api_endpoint = f"{base_url}/register-tee-worker"
            payload = {"address": address}

            logger.info(f"Calling MASA TEE API to register TEE worker: {address}")

            # Make API call directly without nested function
            async with aiohttp.ClientSession() as session:
                async with session.post(api_endpoint, json=payload) as response:
                    if response.status == 200:
                        # Process response but don't need to store it
                        await response.json()
                        logger.info(
                            f"Successfully registered TEE worker with MASA API: "
                            f"{address}"
                        )
                        return True
                    else:
                        response_text = await response.text()
                        logger.error(
                            f"Failed to register TEE worker with MASA API: "
                            f"{response.status} - {response_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Failed to register TEE worker: {e}")
            return False

    def clean_old_unregistered_tees(self):
        """Clean unregistered TEEs older than one hour."""
        try:
            self.db.clean_old_unregistered_tees()
        except sqlite3.Error as e:
            logger.error(f"Failed to clean old unregistered TEEs: {e}")

    def get_all_unregistered_tees(self):
        """Get all unregistered TEEs from the database."""
        try:
            return self.db.get_all_unregistered_tees()
        except sqlite3.Error as e:
            logger.error(f"Failed to get all unregistered TEEs: {e}")
            return []

    def get_all_unregistered_tee_addresses(self):
        """Get all addresses from unregistered TEEs."""
        try:
            return self.db.get_all_unregistered_tee_addresses()
        except sqlite3.Error as e:
            logger.error(f"Failed to get unregistered TEE addresses: {e}")
            return []

    def remove_unregistered_tee(self, address):
        """Remove a specific unregistered TEE by address."""
        try:
            logger.info(f"Removing unregistered TEE: address={address}")
            result = self.db.remove_unregistered_tee(address)
            if result:
                logger.debug(f"Successfully removed unregistered TEE: {address}")
            else:
                logger.debug(f"No unregistered TEE found with address: {address}")
            return result
        except sqlite3.Error as e:
            logger.error(f"Failed to remove unregistered TEE: {e}")
            return False
