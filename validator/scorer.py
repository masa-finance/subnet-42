import os
import logging
from interfaces.types import NodeData
from typing import TYPE_CHECKING
from validator.telemetry import TEETelemetryClient

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = logging.getLogger(__name__)


class NodeDataScorer:
    def __init__(self, validator: "Validator"):
        """
        Initialize the NodeDataScorer with a validator instance and a stub for node data.

        :param validator: The validator instance to be used for scoring node data.
        """
        self.validator = validator
        self.telemetry = []
        logger.info("Initialized NodeDataScorer")
        # This can be replaced with a service client or API call in the future

    async def get_node_data(self):
        """
        Retrieve node data. Currently returns a stub list of NodeData objects.
        In the future, this method should fetch data from an external service.

        :return: A list of NodeData objects containing node information.
        """
        logger.info("Starting node data retrieval")
        self.validator.metagraph.sync_nodes()
        connected_nodes = self.validator.node_manager.connected_nodes
        logger.info(f"Found {len(connected_nodes)} connected nodes")

        node_data = []
        for hotkey, node in connected_nodes.items():
            logger.debug(f"Processing node {hotkey} at IP {node.ip}")
            try:
                logger.debug(f"Creating telemetry client for node {hotkey}")
                overwrite_localhost = os.getenv("OVERWRITE_LOCAL_TEE", None)

                # Determine the server address
                server_address = (
                    overwrite_localhost
                    if node.ip == "1" and overwrite_localhost is not None
                    else f"{node.ip}:{node.port}"
                )
                telemetry_client = TEETelemetryClient(server_address)

                logger.debug(f"Executing telemetry sequence for node {hotkey}")
                telemetry_result = await telemetry_client.execute_telemetry_sequence()

                if telemetry_result:
                    logger.info(
                        f"Node {hotkey} telemetry successful: {telemetry_result}"
                    )
                    node_data.append(
                        NodeData(
                            hotkey=hotkey,
                            boot_time=telemetry_result.get("boot_time", 0),
                            last_operation_time=telemetry_result.get(
                                "last_operation_time", 0
                            ),
                            current_time=telemetry_result.get("current_time", 0),
                            twitter_auth_errors=telemetry_result.get("stats", {}).get(
                                "twitter_auth_errors", 0
                            ),
                            twitter_errors=telemetry_result.get("stats", {}).get(
                                "twitter_errors", 0
                            ),
                            twitter_ratelimit_errors=telemetry_result.get(
                                "stats", {}
                            ).get("twitter_ratelimit_errors", 0),
                            twitter_returned_other=telemetry_result.get(
                                "stats", {}
                            ).get("twitter_returned_other", 0),
                            twitter_returned_profiles=telemetry_result.get(
                                "stats", {}
                            ).get("twitter_returned_profiles", 0),
                            twitter_returned_tweets=telemetry_result.get(
                                "stats", {}
                            ).get("twitter_returned_tweets", 0),
                            twitter_scrapes=telemetry_result.get("stats", {}).get(
                                "twitter_scrapes", 0
                            ),
                            web_errors=telemetry_result.get("stats", {}).get(
                                "web_errors", 0
                            ),
                            web_success=telemetry_result.get("stats", {}).get(
                                "web_success", 0
                            ),
                        )
                    )
                else:
                    logger.warning(f"Node {hotkey} telemetry returned no results")
                    node_data.append(
                        NodeData(
                            hotkey=hotkey,
                            boot_time=0,
                            last_operation_time=0,
                            current_time=0,
                            twitter_auth_errors=0,
                            twitter_errors=0,
                            twitter_ratelimit_errors=0,
                            twitter_returned_other=0,
                            twitter_returned_profiles=0,
                            twitter_returned_tweets=0,
                            twitter_scrapes=0,
                            web_errors=0,
                            web_success=0,
                        )
                    )
            except Exception as e:
                logger.error(
                    f"Failed to get telemetry for node {hotkey}: {str(e)}",
                    exc_info=True,
                )
                node_data.append(NodeData(hotkey=hotkey, posts=0))

        logger.info(f"Completed node data retrieval for {len(node_data)} nodes")

        self.telemetry = node_data

        return node_data
