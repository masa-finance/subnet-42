from typing import Dict, Optional
from fiber.networking.models import NodeWithFernet as Node
from fiber.encrypted.validator import handshake, client as vali_client
from cryptography.fernet import Fernet
import os
from typing import TYPE_CHECKING
import sqlite3
from fiber.logging_utils import get_logger
from interfaces.types import NodeData
from validator.telemetry import TEETelemetryClient

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
                    logger.info(
                        f"Connected to miner: {node.hotkey}, IP: {node.ip}, Port: {node.port}"
                    )
                else:
                    logger.info(
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

    async def send_custom_message(self, node_hotkey: str, message: str) -> None:
        """
        Send a custom message to a specific miner.

        Args:
            node_hotkey (str): The miner's hotkey
            message (str): The message to send
        """
        try:
            if node_hotkey not in self.connected_nodes:
                logger.warning(f"No connected node found for hotkey {node_hotkey}")
                return

            node = self.connected_nodes[node_hotkey]
            uid = str(
                self.validator.metagraph.nodes[
                    self.validator.keypair.ss58_address
                ].node_id
            )
            payload = {
                "message": message,
                "sender": f"Validator {uid} ({self.validator.keypair.ss58_address})",
            }

            response = await self.validator.http_client_manager.client.post(
                f"http://{node.ip}:{node.port}/custom-message", json=payload
            )

            if response.status_code == 200:
                logger.debug(f"Successfully sent custom message to miner {node_hotkey}")
            else:
                logger.warning(
                    f"Failed to send custom message to miner {node_hotkey}. "
                    f"Status code: {response.status_code}"
                )

        except Exception as e:
            logger.error(
                f"Error sending custom message to miner {node_hotkey}: {str(e)}"
            )

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
                                telemetry_client = TEETelemetryClient(tee_address)

                                logger.info(
                                    f"Executing telemetry sequence for node {hotkey} at {tee_address}"
                                )

                                telemetry_result = (
                                    await telemetry_client.execute_telemetry_sequence()
                                )

                                worker_id = telemetry_result.get("worker_id", "N/A")

                                worker_hotkey = routing_table.get_worker_hotkey(
                                    worker_id=worker_id
                                )

                                is_worker_already_owned = (
                                    worker_hotkey is not None
                                    and worker_hotkey is not hotkey
                                )

                                # This checks that a worker address is only owned by the first node that requests it
                                # For removing this restriction shoot a message on discord
                                if is_worker_already_owned:
                                    logger.warning(
                                        f"Worker ID {worker_id} is already registered to another hotkey. "
                                        f"Skipping registration for {hotkey}."
                                    )
                                    continue

                                routing_table.register_worker(
                                    hotkey=hotkey, worker_id=worker_id
                                )
                                routing_table.add_miner_address(
                                    hotkey, node.node_id, tee_address, worker_id
                                )

                                logger.debug(
                                    f"Added TEE address {tee_address} for "
                                    f"hotkey {hotkey}"
                                )

                                if not worker_hotkey:
                                    # Send notification to miner about successful registration
                                    await self.send_custom_message(
                                        hotkey,
                                        f"Your TEE address {tee_address} has been successfully registered with worker_id {worker_id} for hotkey {hotkey}",
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

    async def send_score_report(
        self, node_hotkey: str, score: float, telemetry: NodeData
    ) -> None:
        """
        Send a score report to a specific miner.

        Args:
            hotkey (str): The miner's hotkey
            score (float): The calculated score for the miner
            telemetry (dict): The telemetry data for the miner
        """
        try:
            if node_hotkey not in self.connected_nodes:
                logger.warning(f"No connected node found for hotkey {node_hotkey}")
                return

            node = self.connected_nodes[node_hotkey]
            validator_node_id = self.validator.metagraph.nodes[
                self.validator.keypair.ss58_address
            ].node_id

            payload = {
                "telemetry": {
                    "web_success": telemetry.web_success,
                    "twitter_returned_tweets": telemetry.twitter_returned_tweets,
                    "twitter_returned_profiles": telemetry.twitter_returned_profiles,
                    "twitter_errors": telemetry.twitter_errors,
                    "twitter_auth_errors": telemetry.twitter_auth_errors,
                    "twitter_ratelimit_errors": telemetry.twitter_ratelimit_errors,
                    "web_errors": telemetry.web_errors,
                    "boot_time": telemetry.boot_time,
                    "last_operation_time": telemetry.last_operation_time,
                    "current_time": telemetry.current_time,
                },
                "score": score,
                "hotkey": self.validator.keypair.ss58_address,
                "uid": validator_node_id,
            }

            response = await self.validator.http_client_manager.client.post(
                f"http://{node.ip}:{node.port}/score-report", json=payload
            )

            if response.status_code == 200:
                logger.debug(f"Successfully sent score report to miner {node_hotkey}")
            else:
                logger.warning(
                    f"Failed to send score report to miner {node_hotkey}. "
                    f"Status code: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error sending score report to miner {node_hotkey}: {str(e)}")
