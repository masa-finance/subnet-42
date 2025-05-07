from fiber.logging_utils import get_logger
from interfaces.types import NodeData
from typing import TYPE_CHECKING, Dict, Any
from validator.telemetry import TEETelemetryClient

if TYPE_CHECKING:
    from neurons.validator import Validator

# Remove logging configuration to centralize it in the main entry point

logger = get_logger(__name__)


class NodeDataScorer:
    def __init__(self, validator: "Validator"):
        """
        Initialize the NodeDataScorer with a validator instance.

        :param validator: The validator instance to be used for scoring node data
        """
        self.validator = validator
        self.telemetry = []
        logger.info("Initialized NodeDataScorer")
        # This can be replaced with a service client or API call in the future

    def aggregate_telemetry_stats(
        self, telemetry_result: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Aggregate telemetry stats from multiple worker IDs.

        :param telemetry_result: The telemetry result with stats by worker ID
        :return: A dictionary with aggregated stats
        """
        # Initialize aggregated stats
        stats = {
            "twitter_auth_errors": 0,
            "twitter_errors": 0,
            "twitter_ratelimit_errors": 0,
            "twitter_returned_other": 0,
            "twitter_returned_profiles": 0,
            "twitter_returned_tweets": 0,
            "twitter_scrapes": 0,
            "web_errors": 0,
            "web_success": 0,
        }

        # Get the stats dictionary
        stats_dict = telemetry_result.get("stats", {})

        # Check if this is using the old format (stats directly in stats object)
        # or new format (stats inside worker IDs)
        if stats_dict and not any(isinstance(v, dict) for v in stats_dict.values()):
            # Old format - stats directly in the stats object
            for stat_name in stats:
                stats[stat_name] += stats_dict.get(stat_name, 0)
        else:
            # New format - stats inside worker IDs
            # Aggregate stats from all worker IDs
            for worker_stats in stats_dict.values():
                stats["twitter_auth_errors"] += worker_stats.get(
                    "twitter_auth_errors", 0
                )
                stats["twitter_errors"] += worker_stats.get("twitter_errors", 0)
                stats["twitter_ratelimit_errors"] += worker_stats.get(
                    "twitter_ratelimit_errors", 0
                )
                stats["twitter_returned_other"] += worker_stats.get(
                    "twitter_returned_other", 0
                )
                stats["twitter_returned_profiles"] += worker_stats.get(
                    "twitter_returned_profiles", 0
                )
                stats["twitter_returned_tweets"] += worker_stats.get(
                    "twitter_returned_tweets", 0
                )
                stats["twitter_scrapes"] += worker_stats.get("twitter_scrapes", 0)
                stats["web_errors"] += worker_stats.get("web_errors", 0)
                stats["web_success"] += worker_stats.get("web_success", 0)

        return stats

    async def get_node_data(self):
        """
        Retrieve node data from all nodes in the network.

        :return: A list of NodeData objects containing node information
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

                    # Aggregate stats across all worker IDs
                    aggregated_stats = self.aggregate_telemetry_stats(telemetry_result)

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
                        twitter_auth_errors=aggregated_stats["twitter_auth_errors"],
                        twitter_errors=aggregated_stats["twitter_errors"],
                        twitter_ratelimit_errors=aggregated_stats[
                            "twitter_ratelimit_errors"
                        ],
                        twitter_returned_other=aggregated_stats[
                            "twitter_returned_other"
                        ],
                        twitter_returned_profiles=aggregated_stats[
                            "twitter_returned_profiles"
                        ],
                        twitter_returned_tweets=aggregated_stats[
                            "twitter_returned_tweets"
                        ],
                        twitter_scrapes=aggregated_stats["twitter_scrapes"],
                        web_errors=aggregated_stats["web_errors"],
                        web_success=aggregated_stats["web_success"],
                    )
                    logger.info(f"Storing telemetry for node {hotkey[:10]}...")
                    twitter_stats = (
                        f"Twitter stats for {hotkey[:10]}: "
                        f"scrapes={telemetry_data.twitter_scrapes}, "
                        f"profiles={telemetry_data.twitter_returned_profiles}, "
                        f"tweets={telemetry_data.twitter_returned_tweets}"
                    )
                    logger.info(twitter_stats)

                    web_stats = (
                        f"Web stats for {hotkey[:10]}: "
                        f"success={telemetry_data.web_success}, "
                        f"errors={telemetry_data.web_errors}"
                    )
                    logger.info(web_stats)

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

        logger.info("Telemetry collection summary:")
        logger.info(f"  - Total nodes processed: {len(nodes)}")
        logger.info(f"  - Successful telemetry collections: {successful_nodes}")
        logger.info(f"  - Failed telemetry collections: {failed_nodes}")
        rate = f"  - Success rate: {successful_nodes/len(nodes)*100:.2f}%"
        logger.info(rate)
        logger.info(f"Completed telemetry fetching for {len(node_data)} nodes")

        self.telemetry = node_data

        return node_data
