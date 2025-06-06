from fiber.logging_utils import get_logger
from interfaces.types import NodeData
from typing import TYPE_CHECKING, Dict, Any
from validator.telemetry import TEETelemetryClient
import time
import os
import aiohttp

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
        self.active_stat_name = None
        self.last_stat_name_refresh = 0
        self.stat_name_refresh_interval = 3600  # 1 hour in seconds
        self.active_worker_version = None
        self.last_worker_version_refresh = 0
        self.worker_version_refresh_interval = 600  # 10 minutes in seconds
        self.api_url = os.getenv("MASA_TEE_API", "https://tee-api.masa.ai").rstrip("/")
        logger.info("Initialized NodeDataScorer")
        # This can be replaced with a service client or API call in the future

    async def fetch_active_stat_name(self):
        """
        Fetch the active stat name from the API.

        :return: The active stat name
        """
        current_time = time.time()

        # Return cached stat name if refresh interval hasn't passed
        if (
            self.active_stat_name is not None
            and current_time - self.last_stat_name_refresh
            < self.stat_name_refresh_interval
        ):
            return self.active_stat_name

        logger.info("Fetching active stat name from API")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/worker-id") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.active_stat_name = data.get("worker_id")
                        self.last_stat_name_refresh = current_time
                        logger.info(f"Active stat name: {self.active_stat_name}")
                        return self.active_stat_name
                    else:
                        logger.error(
                            f"Failed to fetch active stat name: HTTP {response.status}"
                        )
        except Exception as e:
            logger.error(f"Error fetching active stat name: {str(e)}")

        # If fetch fails but we have a cached value, use that
        if self.active_stat_name is not None:
            logger.warning("Using cached active stat name")
            return self.active_stat_name

        # Default to None if no stat name is available
        return None

    async def fetch_active_worker_version(self):
        """
        Fetch the active worker version from the API.

        :return: The active worker version
        """
        current_time = time.time()

        # Return cached worker version if refresh interval hasn't passed
        if (
            self.active_worker_version is not None
            and current_time - self.last_worker_version_refresh
            < self.worker_version_refresh_interval
        ):
            return self.active_worker_version

        logger.info("Fetching active worker version from API")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/tee-version") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.active_worker_version = data.get("worker_version")
                        self.last_worker_version_refresh = current_time
                        logger.info(
                            f"Active worker version: " f"{self.active_worker_version}"
                        )
                        return self.active_worker_version
                    else:
                        logger.error(
                            f"Failed to fetch worker version: HTTP {response.status}"
                        )
        except Exception as e:
            logger.error(f"Error fetching worker version: {str(e)}")

        # If fetch fails but we have a cached value, use that
        if self.active_worker_version is not None:
            logger.warning("Using cached worker version")
            return self.active_worker_version

        # Default to None if no worker version is available
        return None

    def aggregate_telemetry_stats(
        self, telemetry_result: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Aggregate telemetry stats from multiple worker IDs.
        Only count stats with the active stat name and active worker version.

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
        worker_id = telemetry_result.get("worker_id", "unavailable")
        worker_version = telemetry_result.get("worker_version", None)

        # Skip if active_worker_version and worker_version doesn't match
        if (
            self.active_worker_version is not None
            and worker_version != self.active_worker_version
        ):
            logger.info(
                f"Worker ({worker_id}): Skipping due to version mismatch. "
                f"Got {worker_version}, expected {self.active_worker_version}"
            )
            return stats

        if self.active_worker_version is None or worker_version is None:
            logger.info(
                f"Worker ({worker_id}): Skipping due to missing version. "
                f"Worker verison is: {worker_version}"
                f"Expected verison is: {self.active_worker_version}"
            )
            return stats

        # Check if this is using the old format (stats directly in stats object)
        # or new format (stats inside worker IDs)
        if stats_dict and not any(isinstance(v, dict) for v in stats_dict.values()):
            # Old format - stats directly in the stats object (deprecated)
            logger.debug(
                f"Setting 0 telemetry for worker using older version {telemetry_result}"
            )
            logger.info(f"Worker ({worker_id}): is running old code")
            for stat_name in stats:
                stats[stat_name] = 0
        else:
            # New format - stats inside worker IDs
            # Only aggregate stats from the active stat worker
            logger.info(f"Worker ({worker_id}): Has source worker id")

            for source_worker_id, worker_stats in stats_dict.items():
                # Skip if active_stat_name is set and doesn't match this worker_id
                if (
                    self.active_stat_name is not None
                    and source_worker_id != self.active_stat_name
                ):
                    logger.info(
                        f"Worker ({worker_id}): Has wrong source {source_worker_id}"
                    )
                    continue

                # Aggregate stats from this worker
                logger.info(
                    f"Worker ({worker_id}): Has source worker id {source_worker_id} "
                    f"and it matches the indexer worker"
                )
                for stat_name in stats:
                    stats[stat_name] += worker_stats.get(stat_name, 0)

        return stats

    async def get_node_data(self):
        """
        Retrieve node data from all nodes in the network.

        :return: A list of NodeData objects containing node information
        """
        logger.info("Starting telemetry fetching process...")

        # Fetch the active stat name and worker version
        await self.fetch_active_stat_name()
        await self.fetch_active_worker_version()
        logger.info(
            f"Using active stat name: {self.active_stat_name or 'None (counting all)'}"
        )
        logger.info(
            f"Using active worker version: "
            f"{self.active_worker_version or 'None (counting all)'}"
        )

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
                        timestamp=int(time.time()),
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

        # Fix division by zero error
        if len(nodes) > 0:
            rate = f"  - Success rate: {successful_nodes/len(nodes)*100:.2f}%"
            logger.info(rate)
        else:
            logger.info("  - Success rate: N/A (no nodes to process)")

        logger.info(f"Completed telemetry fetching for {len(node_data)} nodes")

        self.telemetry = node_data

        return node_data
