from typing import List, Tuple
import asyncio
from fiber.chain import weights, interface
import numpy as np
from fiber.logging_utils import get_logger

from neurons import version_numerical

from interfaces.types import NodeData
from validator.platform_config import PlatformManager, PlatformConfig


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)


def apply_kurtosis(x):
    if len(x) == 0 or np.all(x == 0):
        return np.zeros_like(x)

    # Center and scale the data
    x_centered = (x - np.mean(x)) / (np.std(x) + 1e-8)

    # Apply sigmoid with steeper curve for outliers
    k = 2.0  # Controls steepness of curve
    beta = 0.5  # Controls center point sensitivity

    # Custom kurtosis-like function that rewards high performers
    # but has diminishing returns
    y = 1 / (1 + np.exp(-k * (x_centered - beta)))
    y += 0.2 * np.tanh(x_centered)  # Add small boost for very high performers

    # Normalize to [0,1] range
    y = (y - np.min(y)) / (np.max(y) - np.min(y) + 1e-8)

    return y


def apply_kurtosis_custom(
    x,
    top_percentile=90,
    reward_factor=0.4,
    steepness=2.0,
    center_sensitivity=0.5,
    boost_factor=0.2,
):
    """
    Apply custom kurtosis-like function with configurable parameters to weight
    the top performers more heavily.

    Args:
        x: Input array of values
        top_percentile: Percentile threshold for increased weighting
                       (e.g. 90 for top 10%)
        reward_factor: Factor to increase weights for top performers
                      (e.g. 0.4 for 40% boost)
        steepness: Controls steepness of sigmoid curve (k parameter)
        center_sensitivity: Controls center point sensitivity (beta parameter)
        boost_factor: Factor for additional boost using tanh
    """
    if len(x) == 0 or np.all(x == 0):
        return np.zeros_like(x)

    # Center and scale the data
    x_centered = (x - np.mean(x)) / (np.std(x) + 1e-8)

    # Apply sigmoid with configurable steepness
    y = 1 / (1 + np.exp(-steepness * (x_centered - center_sensitivity)))

    # Add configurable boost for high performers
    y += boost_factor * np.tanh(x_centered)

    # Additional weighting for top percentile
    threshold = np.percentile(x, top_percentile)
    top_mask = x >= threshold
    y[top_mask] *= 1 + reward_factor

    # Normalize to [0,1] range
    y = (y - np.min(y)) / (np.max(y) - np.min(y) + 1e-8)

    return y


class WeightsManager:
    def __init__(
        self,
        validator: "Validator",
        tweets_weight: float = 0.6,
        error_quality_weight: float = 0.4,
        error_rate_threshold: float = 10.0,
    ):
        """
        Initialize the WeightsManager with a validator instance and
        configurable scoring weights.

        :param validator: The validator instance to be used for weight
                         calculations.
        :param tweets_weight: Weight for Twitter tweets returned component
                             (default: 0.6)
        :param error_quality_weight: Weight for error quality score component
                                    (default: 0.4)
        :param error_rate_threshold: Maximum errors per hour allowed before
                                   scoring 0 (default: 10.0)
        """
        self.validator = validator
        self.tweets_weight = tweets_weight
        self.error_quality_weight = error_quality_weight
        self.error_rate_threshold = error_rate_threshold

        # Initialize platform manager for multi-platform scoring
        self.platform_manager = PlatformManager()

        logger.info(
            f"Initialized WeightsManager with weights: "
            f"tweets={tweets_weight}, error_quality={error_quality_weight}, "
            f"error_rate_threshold={error_rate_threshold}"
        )
        logger.info(
            f"Platform manager initialized with {len(self.platform_manager.get_platform_names())} platforms"
        )

        # Ensure weights sum to 1.0
        total_weight = self.tweets_weight + self.error_quality_weight
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")

    def _convert_timestamp_to_int(self, timestamp) -> int:
        """
        Get telemetry data and calculate deltas using simple reset logic.
        If twitter_returned_tweets decreases, reset baseline to that point.
        Calculate delta from most recent reset point to latest value.

        :param timestamp: Timestamp value (string, int, or other)
        :return: Integer timestamp (unix seconds) or 0 if conversion fails
        """
        if isinstance(timestamp, int):
            return timestamp
        elif isinstance(timestamp, str):
            if timestamp == "" or timestamp is None:
                return 0
            try:
                # Try to parse as datetime string first
                from datetime import datetime

                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                return int(dt.timestamp())
            except ValueError:
                try:
                    # Try to parse as integer string
                    return int(timestamp)
                except ValueError:
                    logger.warning(
                        f"Failed to convert timestamp '{timestamp}' to int, using 0"
                    )
                    return 0
        else:
            logger.warning(f"Unexpected timestamp type {type(timestamp)}, using 0")
            return 0

    def calculate_platform_score(self, node: NodeData, platform_name: str) -> float:
        """
        Calculate the score for a single platform for a given node.

        :param node: NodeData object containing platform metrics
        :param platform_name: Name of the platform to score
        :return: Normalized platform score (0.0 to 1.0)
        """
        if not hasattr(node, "platform_metrics") or not node.platform_metrics:
            logger.debug(f"Node {node.hotkey} has no platform metrics")
            return 0.0

        platform_metrics = node.platform_metrics.get(platform_name, {})
        if not platform_metrics:
            logger.debug(
                f"Node {node.hotkey} has no metrics for platform {platform_name}"
            )
            return 0.0

        try:
            platform_config = self.platform_manager.get_platform(platform_name)
        except ValueError:
            logger.warning(f"Unknown platform: {platform_name}")
            return 0.0

        # Calculate success metrics
        success_score = 0.0
        for metric in platform_config.success_metrics:
            success_score += platform_metrics.get(metric, 0)

        # Calculate error rate
        error_count = 0
        for metric in platform_config.error_metrics:
            error_count += platform_metrics.get(metric, 0)

        # Calculate time span for error rate calculation
        time_span_seconds = getattr(node, "time_span_seconds", 0)
        if time_span_seconds > 0:
            hours = time_span_seconds / 3600
            error_rate = error_count / hours
        else:
            error_rate = float("inf") if error_count > 0 else 0.0

        # Apply error rate threshold
        if error_rate > self.error_rate_threshold:
            logger.debug(
                f"Node {node.hotkey} platform {platform_name} exceeds error threshold: "
                f"{error_rate:.2f} errors/hour"
            )
            return 0.0

        # Convert error rate to quality score
        error_quality = 1.0 / (1.0 + error_rate)

        # Combine success and error quality scores
        combined_score = (
            success_score * self.tweets_weight
            + error_quality * self.error_quality_weight
        )

        return float(combined_score)

    def _update_platform_metrics(self, delta_node_data: List[NodeData]) -> None:
        """
        Update platform_metrics for nodes based on their delta telemetry data.
        This ensures backward compatibility and proper multi-platform scoring.
        """
        for node in delta_node_data:
            if not hasattr(node, "platform_metrics") or not node.platform_metrics:
                node.platform_metrics = {}

            # Update Twitter platform metrics from legacy fields
            if (
                node.twitter_returned_tweets > 0
                or node.twitter_returned_profiles > 0
                or node.twitter_auth_errors > 0
                or node.twitter_errors > 0
                or node.twitter_ratelimit_errors > 0
            ):

                node.platform_metrics["twitter"] = {
                    "returned_tweets": node.twitter_returned_tweets,
                    "returned_profiles": node.twitter_returned_profiles,
                    "scrapes": node.twitter_scrapes,
                    "auth_errors": node.twitter_auth_errors,
                    "errors": node.twitter_errors,
                    "ratelimit_errors": node.twitter_ratelimit_errors,
                }

            # Update TikTok platform metrics from new fields
            tiktok_success = getattr(node, "tiktok_transcription_success", 0)
            tiktok_errors = getattr(node, "tiktok_transcription_errors", 0)

            if tiktok_success > 0 or tiktok_errors > 0:
                node.platform_metrics["tiktok"] = {
                    "transcription_success": tiktok_success,
                    "transcription_errors": tiktok_errors,
                }

    def _get_delta_node_data(self, telemetry_data: List[NodeData]) -> List[NodeData]:
        """
        Get telemetry data and calculate deltas between latest and oldest
        records. When TEE restarts are detected (negative deltas), split into
        chunks and sum them.

        :param telemetry_data: List of NodeData objects from get_all_telemetry()
        :return: List of NodeData objects containing delta values.
        """
        delta_node_data = []

        # Group telemetry data by hotkey
        telemetry_by_hotkey = {}
        for record in telemetry_data:
            if record.hotkey not in telemetry_by_hotkey:
                telemetry_by_hotkey[record.hotkey] = []
            telemetry_by_hotkey[record.hotkey].append(record)

        # Get all hotkeys from metagraph to ensure we include those without
        # telemetry
        all_hotkeys = []
        for node_idx, node in enumerate(self.validator.metagraph.nodes):
            node_data = self.validator.metagraph.nodes[node]
            hotkey = node_data.hotkey
            all_hotkeys.append((node_data.node_id, hotkey))

        print(f"all  hotkeys: {all_hotkeys}")
        # Process hotkeys with telemetry data
        processed_hotkeys = set()
        for hotkey, telemetry_list in telemetry_by_hotkey.items():
            if len(telemetry_list) >= 2:
                # Sort telemetry by timestamp (convert to int first)
                sorted_telemetry = sorted(
                    telemetry_list,
                    key=lambda x: self._convert_timestamp_to_int(x.timestamp),
                )

                # Find baseline: start from first record, reset on any decrease
                baseline_record = sorted_telemetry[0]
                latest_record = sorted_telemetry[-1]

                # Walk through records, reset baseline on any decrease in
                # twitter_returned_tweets
                for record in sorted_telemetry[1:]:
                    if (
                        record.twitter_returned_tweets
                        < baseline_record.twitter_returned_tweets
                    ):
                        baseline_record = record  # Reset baseline to this record
                        logger.debug(
                            f"Reset baseline for {hotkey} at timestamp "
                            f"{record.timestamp}"
                        )

                # Calculate simple delta from final baseline to latest
                delta_boot_time = 0  # Not used in simple mode
                delta_last_operation_time = 0  # Not used in simple mode
                delta_twitter_returned_other = 0  # Not used in simple mode

                # Calculate time span for this chunk
                # (timestamps are in seconds, convert to int first)
                first_timestamp = self._convert_timestamp_to_int(
                    baseline_record.timestamp
                )
                last_timestamp = self._convert_timestamp_to_int(latest_record.timestamp)
                total_time_span_seconds = last_timestamp - first_timestamp

                delta_twitter_auth_errors = max(
                    0,
                    latest_record.twitter_auth_errors
                    - baseline_record.twitter_auth_errors,
                )
                delta_twitter_errors = max(
                    0, latest_record.twitter_errors - baseline_record.twitter_errors
                )
                delta_twitter_ratelimit_errors = max(
                    0,
                    latest_record.twitter_ratelimit_errors
                    - baseline_record.twitter_ratelimit_errors,
                )

                delta_twitter_returned_profiles = max(
                    0,
                    latest_record.twitter_returned_profiles
                    - baseline_record.twitter_returned_profiles,
                )
                delta_twitter_returned_tweets = max(
                    0,
                    latest_record.twitter_returned_tweets
                    - baseline_record.twitter_returned_tweets,
                )

                delta_twitter_scrapes = max(
                    0, latest_record.twitter_scrapes - baseline_record.twitter_scrapes
                )
                delta_web_errors = max(
                    0, latest_record.web_errors - baseline_record.web_errors
                )
                delta_web_success = max(
                    0, latest_record.web_success - baseline_record.web_success
                )

                # Calculate TikTok deltas
                delta_tiktok_transcription_success = max(
                    0,
                    getattr(latest_record, "tiktok_transcription_success", 0)
                    - getattr(baseline_record, "tiktok_transcription_success", 0),
                )
                delta_tiktok_transcription_errors = max(
                    0,
                    getattr(latest_record, "tiktok_transcription_errors", 0)
                    - getattr(baseline_record, "tiktok_transcription_errors", 0),
                )

                # Use the latest record's data for non-delta fields
                latest = sorted_telemetry[-1]

                # Create delta data
                delta_data = NodeData(
                    hotkey=hotkey,
                    uid=latest.uid,
                    worker_id=latest.worker_id,
                    timestamp=self._convert_timestamp_to_int(latest.timestamp),
                    boot_time=delta_boot_time,
                    last_operation_time=delta_last_operation_time,
                    current_time=latest.current_time,
                    twitter_auth_errors=delta_twitter_auth_errors,
                    twitter_errors=delta_twitter_errors,
                    twitter_ratelimit_errors=delta_twitter_ratelimit_errors,
                    twitter_returned_other=delta_twitter_returned_other,
                    twitter_returned_profiles=delta_twitter_returned_profiles,
                    twitter_returned_tweets=delta_twitter_returned_tweets,
                    twitter_scrapes=delta_twitter_scrapes,
                    web_errors=delta_web_errors,
                    web_success=delta_web_success,
                    tiktok_transcription_success=delta_tiktok_transcription_success,
                    tiktok_transcription_errors=delta_tiktok_transcription_errors,
                )

                # Add custom attributes for error rate calculation
                delta_data.time_span_seconds = total_time_span_seconds
                delta_data.total_errors = (
                    delta_twitter_auth_errors
                    + delta_twitter_errors
                    + delta_twitter_ratelimit_errors
                )

                delta_node_data.append(delta_data)
                processed_hotkeys.add(hotkey)
                logger.debug(
                    f"Delta for {hotkey}: tweets={delta_twitter_returned_tweets}"
                )
            else:
                logger.debug(
                    f"Not enough telemetry data for {hotkey} to calculate deltas"
                )
                # Find UID for this hotkey
                uid = next((uid for uid, hk in all_hotkeys if hk == hotkey), 0)
                # Add empty telemetry for hotkeys with insufficient data
                delta_data = NodeData(
                    hotkey=hotkey,
                    uid=uid,
                    worker_id="",
                    timestamp=0,
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
                    tiktok_transcription_success=0,
                    tiktok_transcription_errors=0,
                )
                # Add custom attributes for error rate calculation
                delta_data.time_span_seconds = 0
                delta_data.total_errors = 0

                delta_node_data.append(delta_data)
                processed_hotkeys.add(hotkey)

        # Add empty telemetry for hotkeys without any telemetry data
        for uid, hotkey in all_hotkeys:
            if hotkey not in processed_hotkeys:
                logger.debug(f"Adding empty telemetry for {hotkey} (uid: {uid})")
                delta_data = NodeData(
                    hotkey=hotkey,
                    uid=uid,
                    worker_id="",
                    timestamp=0,
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
                    tiktok_transcription_success=0,
                    tiktok_transcription_errors=0,
                )
                # Add custom attributes for error rate calculation
                delta_data.time_span_seconds = 0
                delta_data.total_errors = 0

                delta_node_data.append(delta_data)

        logger.info(f"Calculated deltas for {len(delta_node_data)} nodes")
        return delta_node_data

    async def calculate_weights(
        self, delta_node_data: List[NodeData], simulation: bool = False
    ) -> Tuple[List[int], List[float]]:
        """
        Calculate weights for nodes based on their twitter_returned_tweets
        and error rate per hour using configurable weights and a kurtosis curve.

        :param delta_node_data: List of NodeData objects with delta values
        :param simulation: Whether this is a simulation run
        :return: A tuple containing a list of node IDs and their corresponding
                 weights.
        """
        # Log node data for debugging
        for node in delta_node_data:
            logger.debug(
                f"Node {node.hotkey} data:"
                f"\n\tWeb success: {node.web_success}"
                f"\n\tTwitter returned tweets: {node.twitter_returned_tweets}"
                f"\n\tTwitter returned profiles: "
                f"{node.twitter_returned_profiles}"
                f"\n\tTwitter errors: {node.twitter_errors}"
                f"\n\tTwitter auth errors: {node.twitter_auth_errors}"
                f"\n\tTwitter ratelimit errors: "
                f"{node.twitter_ratelimit_errors}"
                f"\n\tWeb errors: {node.web_errors}"
                f"\n\tBoot time: {node.boot_time}"
                f"\n\tLast operation time: {node.last_operation_time}"
                f"\n\tCurrent time: {node.current_time}"
                f"\n\tTotal errors: {getattr(node, 'total_errors', 0)}"
                f"\n\tTime span (hours): "
                f"{getattr(node, 'time_span_seconds', 0) / 3600:.2f}"
            )

        logger.info("Starting weight calculation...")
        miner_scores = {}

        if not delta_node_data:
            logger.warning("No node data provided for weight calculation")
            return [], []

        logger.debug(f"Calculating weights for {len(delta_node_data)} nodes")

        # Update platform metrics for multi-platform scoring
        logger.debug("Updating platform metrics for delta node data")
        self._update_platform_metrics(delta_node_data)

        # Calculate multi-platform scores
        logger.debug("Calculating multi-platform scores")
        combined_scores = []

        for node in delta_node_data:
            total_weighted_score = 0.0

            # Calculate score for each platform and apply emission weights
            for platform_name in self.platform_manager.get_platform_names():
                platform_config = self.platform_manager.get_platform(platform_name)
                platform_score = self.calculate_platform_score(node, platform_name)
                weighted_score = platform_score * platform_config.emission_weight
                total_weighted_score += weighted_score

                logger.debug(
                    f"Node {node.hotkey} platform {platform_name}: "
                    f"score={platform_score:.4f}, weighted={weighted_score:.4f}"
                )

            combined_scores.append(total_weighted_score)
            logger.debug(
                f"Node {node.hotkey} total weighted score: {total_weighted_score:.4f}"
            )

        # Apply kurtosis curve to final scores
        logger.debug("Applying kurtosis curve to combined scores")
        combined_scores = np.array(combined_scores)
        combined_scores = apply_kurtosis_custom(combined_scores)

        # Apply final scores
        logger.debug("Applying final scores to nodes")
        for idx, node in enumerate(delta_node_data):
            try:
                if simulation:
                    uid = node.uid
                else:
                    uid = self.validator.metagraph.nodes[node.hotkey].node_id

                if uid is not None:
                    # Use the multi-platform combined score
                    score = float(combined_scores[idx])

                    logger.debug(
                        f"Node {node.hotkey} (UID {uid}) final score: {score:.4f}"
                    )

                    miner_scores[uid] = score

                    await self.validator.node_manager.send_score_report(
                        node.hotkey, score, node
                    )
            except KeyError:
                logger.error(
                    f"Node with hotkey '{node.hotkey}' not found in metagraph."
                )
        # Convert string UIDs to integers for proper sorting, if needed
        uids = sorted(
            miner_scores.keys(),
            key=lambda x: int(x) if isinstance(x, str) and x.isdigit() else x,
        )
        weights = [float(miner_scores[uid]) for uid in uids]

        logger.info(f"Completed weight calculation for {len(uids)} nodes")
        logger.debug(f"UIDs: {uids}")
        logger.debug(f"weights: {weights}")

        return uids, weights

    async def get_priority_miners_by_score(
        self,
        delta_node_data: List[NodeData],
        simulation: bool = False,
        list_size: int = 256,
    ) -> List[str]:
        """
        Get weighted list of worker IPs based on score where better scoring
        miners appear more frequently in the list. This allows consumers to
        do random picks while maintaining probability bias towards better
        miners.

        :param delta_node_data: List of NodeData objects with delta values
        :param simulation: Whether this is a simulation run
        :param list_size: Size of the weighted list to generate (default: 100)
        :return: Weighted list of worker IP addresses where better miners
                appear more frequently
        """
        # Get the scores from calculate_weights
        uids, weights = await self.calculate_weights(delta_node_data, simulation)

        if not uids or not weights:
            logger.warning("No scores available for priority miners")
            return []

        # Create UID to score mapping
        uid_to_score = dict(zip(uids, weights))

        # Get all addresses with hotkeys from routing table
        addresses_with_hotkeys = (
            self.validator.routing_table.get_all_addresses_with_hotkeys()
        )

        # Create list of (address, score) tuples for addresses that have scores
        address_scores = []
        for hotkey, address, worker_id in addresses_with_hotkeys:
            try:
                # Get UID for this hotkey
                node_uid = self.validator.metagraph.nodes[hotkey].node_id
                if node_uid in uid_to_score:
                    score = uid_to_score[node_uid]
                    address_scores.append((address, score))
                    logger.debug(
                        f"Address {address} (hotkey {hotkey[:10]}...) "
                        f"score: {score:.4f}"
                    )
            except KeyError:
                logger.debug(f"Hotkey {hotkey} not found in metagraph, skipping")
                continue

        if not address_scores:
            logger.warning("No addresses with valid scores found")
            return []

        # Extract addresses and scores
        addresses = [item[0] for item in address_scores]
        scores = np.array([item[1] for item in address_scores])

        # Normalize scores to create probabilities
        # (handle negative or zero scores)
        min_score = np.min(scores)
        if min_score < 0:
            # Shift all scores to be positive
            scores = scores - min_score + 0.001  # small epsilon to avoid zeros

        # Add small epsilon to avoid division by zero
        scores = scores + 0.001

        # Create probability weights (higher scores get higher probability)
        probabilities = scores / np.sum(scores)

        # Generate weighted list by sampling with replacement
        try:
            weighted_addresses = np.random.choice(
                addresses, size=list_size, p=probabilities, replace=True
            ).tolist()
        except ValueError as e:
            logger.error(f"Error creating weighted list: {e}")
            # Fallback to sorted list if weighted sampling fails
            address_scores.sort(key=lambda x: x[1], reverse=True)
            weighted_addresses = [address for address, score in address_scores]
            logger.warning("Falling back to sorted list due to weighted sampling error")

        logger.info(
            f"Generated weighted priority miners list with "
            f"{len(weighted_addresses)} addresses"
        )

        # Log distribution statistics
        unique_addresses = list(set(weighted_addresses))
        logger.info(f"Unique addresses in weighted list: {len(unique_addresses)}")

        if unique_addresses:
            # Show top addresses and their frequency
            from collections import Counter

            address_counts = Counter(weighted_addresses)
            top_addresses = address_counts.most_common(3)
            logger.debug(f"Top 3 most frequent addresses: {top_addresses}")

        return weighted_addresses

    async def set_weights(self) -> None:
        """
        Set weights for nodes on the blockchain, ensuring the minimum interval between updates is respected.

        :param node_data: List of NodeData objects containing node information.
        """
        # Get process monitor from background tasks
        process_monitor = getattr(self.validator, "background_tasks", None)
        if process_monitor:
            process_monitor = getattr(process_monitor, "process_monitor", None)

        execution_id = None

        try:
            # Start monitoring for this weight setting
            if process_monitor:
                execution_id = process_monitor.start_process("set_weights")

            logger.info("Starting weight setting process")

            logger.debug("Refreshing substrate connection")
            self.validator.substrate = interface.get_substrate(
                subtensor_address=self.validator.substrate.url
            )

            logger.debug("Getting validator node ID")
            validator_node_id = self.validator.metagraph.nodes[
                self.validator.keypair.ss58_address
            ].node_id

            logger.debug(f"Validator node ID: {validator_node_id}")

            logger.debug("Checking blocks since last update")
            blocks_since_update = weights.blocks_since_last_update(
                self.validator.substrate, self.validator.netuid, validator_node_id
            )
            min_interval = weights.min_interval_to_set_weights(
                self.validator.substrate, self.validator.netuid
            )

            logger.info(f"Blocks since last update: {blocks_since_update}")
            logger.info(f"Minimum interval required: {min_interval}")

            if blocks_since_update is not None and blocks_since_update < min_interval:
                wait_blocks = min_interval - blocks_since_update
                wait_seconds = wait_blocks * 12
                logger.info(
                    f"Need to wait {wait_seconds} seconds before setting weights"
                )

                # Update metrics for waiting execution
                if execution_id and process_monitor:
                    process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=0,
                        successful_nodes=0,
                        failed_nodes=0,
                        additional_metrics={
                            "skipped": True,
                            "reason": "min_interval_not_met",
                            "wait_seconds": wait_seconds,
                            "blocks_since_update": blocks_since_update,
                            "min_interval": min_interval,
                        },
                    )
                    process_monitor.end_process(execution_id)

                await asyncio.sleep(wait_seconds)
                logger.info("Wait period complete")

            logger.debug("Calculating weights")

            telemetry = self.validator.telemetry_storage.get_all_telemetry()
            data_to_score = self._get_delta_node_data(telemetry)
            uids, scores = await self.calculate_weights(data_to_score)

            for attempt in range(3):
                logger.info(f"Setting weights attempt {attempt + 1}/3")
                try:
                    success = weights.set_node_weights(
                        substrate=self.validator.substrate,
                        keypair=self.validator.keypair,
                        node_ids=uids,
                        node_weights=scores,
                        netuid=self.validator.netuid,
                        validator_node_id=validator_node_id,
                        version_key=version_numerical,
                        wait_for_inclusion=False,
                        wait_for_finalization=False,
                    )

                    if success:
                        logger.debug(f"UIDS: {uids}")
                        logger.debug(f"Scores: {scores}")
                        logger.info("✅ Successfully set weights!")

                        # Update metrics for successful execution
                        if execution_id and process_monitor:
                            process_monitor.update_metrics(
                                execution_id,
                                nodes_processed=len(uids),
                                successful_nodes=len(uids),
                                failed_nodes=0,
                                additional_metrics={
                                    "uids": (
                                        uids.copy()
                                        if hasattr(uids, "copy")
                                        else list(uids)
                                    ),
                                    "scores": (
                                        scores.copy()
                                        if hasattr(scores, "copy")
                                        else list(scores)
                                    ),
                                    "attempts": attempt + 1,
                                    "validator_node_id": validator_node_id,
                                    "total_nodes_scored": len(data_to_score),
                                },
                            )
                            process_monitor.end_process(execution_id)
                            execution_id = None
                        return
                    else:
                        logger.error(
                            f"❌ Failed to set weights on attempt {attempt + 1}"
                        )
                        if attempt < 2:  # Don't sleep on last attempt
                            logger.debug("Waiting 10 seconds before next attempt")
                            await asyncio.sleep(10)

                except Exception as e:
                    logger.error(
                        f"Error on attempt {attempt + 1}: {str(e)}", exc_info=True
                    )
                    if attempt < 2:  # Don't sleep on last attempt
                        logger.debug("Waiting 10 seconds before next attempt")
                        await asyncio.sleep(10)

            logger.error("Failed to set weights after all attempts")

            # Update metrics for failed execution
            if execution_id and process_monitor:
                process_monitor.update_metrics(
                    execution_id,
                    nodes_processed=len(uids) if uids else 0,
                    successful_nodes=0,
                    failed_nodes=len(uids) if uids else 0,
                    errors=["Failed to set weights after all attempts"],
                    additional_metrics={
                        "uids": (
                            uids.copy()
                            if uids and hasattr(uids, "copy")
                            else list(uids) if uids else []
                        ),
                        "scores": (
                            scores.copy()
                            if scores and hasattr(scores, "copy")
                            else list(scores) if scores else []
                        ),
                        "attempts": 3,
                        "validator_node_id": validator_node_id,
                        "total_nodes_scored": (
                            len(data_to_score) if data_to_score else 0
                        ),
                    },
                )
                process_monitor.end_process(execution_id)

        except Exception as e:
            # Handle any unexpected errors
            if execution_id and process_monitor:
                process_monitor.update_metrics(
                    execution_id,
                    nodes_processed=0,
                    successful_nodes=0,
                    failed_nodes=0,
                    errors=[str(e)],
                    additional_metrics={"unexpected_error": str(e)},
                )
                process_monitor.end_process(execution_id)
            raise
