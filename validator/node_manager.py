from typing import Dict, Optional
from fiber.networking.models import NodeWithFernet as Node
from fiber.encrypted.validator import handshake, client as vali_client
from cryptography.fernet import Fernet
import os
from typing import TYPE_CHECKING
import sqlite3
from fiber.logging_utils import get_logger

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)


class NodeManager:
    def __init__(self, validator: "Validator"):
        """
        Initialize the NodeManager with a validator instance.

        :param validator: The validator instance to manage nodes.
        """
        self.validator = validator
        self.connected_nodes: Dict[str, Node] = {}

    async def connect_with_miner(
        self, miner_address: str, miner_hotkey: str, node: Node
    ) -> bool:
        """
        Perform a handshake with a miner and establish a secure connection.

        :param httpx_client: The HTTP client to use for the connection.
        :param miner_address: The address of the miner to connect to.
        :param miner_hotkey: The hotkey of the miner.
        :return: True if the connection was successful, False otherwise.
        """
        try:
            symmetric_key_str, symmetric_key_uuid = await handshake.perform_handshake(
                self.validator.http_client_manager.client,
                miner_address,
                self.validator.keypair,
                miner_hotkey,
            )

            if not symmetric_key_str or not symmetric_key_uuid:
                logger.error(
                    f"Failed to establish secure connection with miner {miner_hotkey}"
                )
                return False

            logger.debug(
                f"************* Handshake node data address: {miner_address}, "
                f"symmetric_key_str: {symmetric_key_str}, "
                f"symmetric_key_uuid: {symmetric_key_uuid}, "
            )

            self.connected_nodes[miner_hotkey] = Node(
                hotkey=miner_hotkey,
                coldkey="",  # Not needed for validator's node tracking
                node_id=node.node_id,
                incentive=node.incentive,
                netuid=node.netuid,
                stake=node.stake,
                trust=node.trust,
                vtrust=node.vtrust,
                last_updated=node.last_updated,
                ip=node.ip,
                ip_type=node.ip_type,
                port=node.port,
                protocol=node.protocol,
                fernet=Fernet(symmetric_key_str),
                symmetric_key_uuid=symmetric_key_uuid,
            )
            logger.debug(f"Handshake successful with miner {miner_hotkey}")
            return True

        except Exception as e:
            logger.debug(
                f"Failed to connect to miner {miner_address} - {miner_hotkey}: {str(e)}"
            )
            return False

    async def get_tee_address(self, node: Node) -> Optional[str]:
        endpoint = "/tee"
        try:
            return await self.validator.make_non_streamed_get(node, endpoint)
        except Exception as e:
            logger.error(f"Failed to get tee address: {node.hotkey} {str(e)}")

    async def connect_new_nodes(self) -> None:
        """
        Verify node registration and attempt to connect to new nodes.

        :param httpx_client: The HTTP client to use for connections.
        """
        logger.info("Attempting nodes connection")
        try:
            nodes = dict(self.validator.metagraph.nodes)
            nodes_list = list(nodes.values())
            # Filter to specific miners if in dev environment
            if os.getenv("ENV", "prod").lower() == "dev":
                whitelist = os.getenv("MINER_WHITELIST", "").split(",")
                nodes_list = [node for node in nodes_list if node.hotkey in whitelist]

            # Filter out already connected nodes
            available_nodes = [
                node
                for node in nodes_list
                if node.hotkey not in self.connected_nodes
                and (node.ip != "0.0.0.0" or node.ip != "0.0.0.1")
            ]

            logger.info(f"Found {len(available_nodes)} miners")
            for node in available_nodes:
                server_address = vali_client.construct_server_address(
                    node=node,
                    replace_with_docker_localhost=True,
                    replace_with_localhost=True,
                )
                success = await self.connect_with_miner(
                    miner_address=server_address, miner_hotkey=node.hotkey, node=node
                )

                if success:
                    logger.debug(
                        f"Connected to miner: {node.hotkey}, IP: {node.ip}, Port: {node.port}"
                    )
                else:
                    logger.debug(
                        f"Failed to connect to miner {node.hotkey} with address {server_address}"
                    )

        except Exception as e:
            logger.error("Error in registration check: %s", str(e))

    async def remove_disconnected_nodes(self):
        keys_to_delete = []
        for hotkey, _ in self.connected_nodes.items():
            if hotkey not in self.validator.metagraph.nodes:
                logger.info(
                    f"Hotkey: {hotkey} has been deregistered from the metagraph"
                )
                keys_to_delete.append(hotkey)

        for hotkey in keys_to_delete:
            del self.connected_nodes[hotkey]

        self.validator.connected_tee_list = []
        await self.update_tee_list()

    async def update_tee_list(self):
        logger.info("Starting TEE list update")
        routing_table = self.validator.routing_table

        # cleaning old addresses
        routing_table.clean_old_entries()

        for hotkey, _ in self.connected_nodes.items():
            logger.debug(f"Processing hotkey: {hotkey}")
            if hotkey in self.validator.metagraph.nodes:
                node = self.validator.metagraph.nodes[hotkey]
                logger.debug(f"Found node in metagraph for hotkey: {hotkey}")

                try:
                    tee_addresses = await self.get_tee_address(node)
                    logger.debug(
                        f"Retrieved TEE addresses for hotkey {hotkey}: {tee_addresses}"
                    )

                    # Cleaning DB from addresses under this hotkey
                    routing_table.clear_miner(hotkey=node.hotkey)
                    logger.debug(f"Cleared existing addresses for hotkey {hotkey}")

                    if tee_addresses:
                        for tee_address in tee_addresses.split(","):
                            tee_address = tee_address.strip()
                            # Skip if localhost
                            if "localhost" in tee_address or "127.0.0.1" in tee_address:
                                logger.debug(
                                    f"Skipping localhost TEE address {tee_address} - {hotkey}"
                                )
                                continue

                            # Skip if not https
                            if not tee_address.startswith("https://"):
                                logger.debug(
                                    f"Skipping non-HTTPS TEE address {tee_address} - {hotkey}"
                                )
                                continue

                            try:
                                routing_table.add_miner_address(
                                    hotkey, node.node_id, tee_address
                                )
                                logger.debug(
                                    f"Added TEE address {tee_address} for "
                                    f"hotkey {hotkey}"
                                )
                            except sqlite3.IntegrityError:
                                logger.debug(
                                    f"TEE address {tee_address} already exists in "
                                    f"routing table for hotkey {hotkey}"
                                )
                    else:
                        logger.debug(f"No TEE addresses returned for hotkey {hotkey}")
                except Exception as e:
                    logger.error(
                        f"Error processing TEE addresses for hotkey {hotkey}: {e}"
                    )
            else:
                logger.debug(f"Hotkey {hotkey} not found in metagraph")
        logger.info("Completed TEE list update ✅")
