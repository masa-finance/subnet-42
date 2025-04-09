import os
from fiber.logging_utils import get_logger
from interfaces.types import NodeData
from typing import TYPE_CHECKING
from validator.telemetry import TEETelemetryClient

if TYPE_CHECKING:
    from neurons.validator import Validator

# Remove logging configuration to centralize it in the main entry point

logger = get_logger(__name__)


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
        logger.info("Starting telemetry fetching process...")
        logger.info("Syncing metagraph to get latest node information")
        self.validator.metagraph.sync_nodes()

        nodes = self.validator.routing_table.get_all_addresses_with_hotkeys()
        logger.info(f"Found {len(nodes)} nodes in the routing table")
        logger.debug(f"Found {len(nodes)} nodes")

        node_data = []
        successful_nodes = 0
        failed_nodes = 0

        logger.info("Beginning telemetry collection for each node")
        for index, (hotkey, ip, worker_id) in enumerate(nodes):
            logger.info(f"Processing node {index+1}/{len(nodes)}: {hotkey[:10]}...")
            logger.debug(f"Processing node {hotkey} at IP {ip}")
            try:
                logger.info(f"Connecting to node {hotkey[:10]}... at {ip}")
                logger.debug(f"Creating telemetry client for node {hotkey}")

                # Determine the server address
                server_address = ip
                telemetry_client = TEETelemetryClient(server_address)

                logger.info(f"Executing telemetry sequence for node {hotkey[:10]}...")
                logger.debug(f"Executing telemetry sequence for node {hotkey}")
                telemetry_result = await telemetry_client.execute_telemetry_sequence(
                    routing_table=self.validator.routing_table
                )

                if telemetry_result:
                    successful_nodes += 1
                    logger.info(f"Node {hotkey[:10]}... telemetry successful")
                    logger.debug(
                        f"Node {hotkey} telemetry successful: {telemetry_result}"
                    )
                    uid = self.validator.metagraph.nodes[hotkey].node_id
                    logger.info(f"Node {hotkey[:10]}... has UID: {uid}")

                    logger.info(f"Node {hotkey[:10]}... worker ID: {worker_id}")

                    telemetry_data = NodeData(
                        hotkey=hotkey,
                        uid=uid,
                        worker_id=worker_id,
                        timestamp="",
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
                        twitter_ratelimit_errors=telemetry_result.get("stats", {}).get(
                            "twitter_ratelimit_errors", 0
                        ),
                        twitter_returned_other=telemetry_result.get("stats", {}).get(
                            "twitter_returned_other", 0
                        ),
                        twitter_returned_profiles=telemetry_result.get("stats", {}).get(
                            "twitter_returned_profiles", 0
                        ),
                        twitter_returned_tweets=telemetry_result.get("stats", {}).get(
                            "twitter_returned_tweets", 0
                        ),
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
                    logger.info(f"Storing telemetry for node {hotkey[:10]}...")
                    logger.info(
                        f"Twitter stats for {hotkey[:10]}: "
                        f"scrapes={telemetry_data.twitter_scrapes}, "
                        f"profiles={telemetry_data.twitter_returned_profiles}, "
                        f"tweets={telemetry_data.twitter_returned_tweets}"
                    )
                    logger.info(
                        f"Web stats for {hotkey[:10]}: "
                        f"success={telemetry_data.web_success}, "
                        f"errors={telemetry_data.web_errors}"
                    )
                    logger.debug(f"telemetry for {hotkey}: {telemetry_data}")

                    self.validator.telemetry_storage.add_telemetry(telemetry_data)
                    logger.info(f"Successfully stored telemetry for {hotkey[:10]}...")
                    node_data.append(telemetry_data)
                else:
                    failed_nodes += 1
                    logger.info(f"Node {hotkey[:10]}... returned no telemetry data")

            # Should add empty telemetry if a node isnt replying?

            except Exception as e:
                failed_nodes += 1
                logger.info(f"Failed to get telemetry for node {hotkey[:10]}...")
                logger.error(
                    f"Failed to get telemetry for node {hotkey}: {str(e)}",
                    exc_info=True,
                )

        logger.info(f"Telemetry collection summary:")
        logger.info(f"  - Total nodes processed: {len(nodes)}")
        logger.info(f"  - Successful telemetry collections: {successful_nodes}")
        logger.info(f"  - Failed telemetry collections: {failed_nodes}")
        logger.info(f"  - Success rate: {successful_nodes/len(nodes)*100:.2f}%")
        logger.info(f"Completed telemetry fetching for {len(node_data)} nodes")

        self.telemetry = node_data

        return node_data
