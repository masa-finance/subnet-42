import os
from typing import List, Tuple
import asyncio
from fiber.chain import weights, interface
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from fiber.logging_utils import get_logger

from neurons import version_numerical

from interfaces.types import NodeData


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
    Apply custom kurtosis-like function with configurable parameters to weight the top performers more heavily.

    Args:
        x: Input array of values
        top_percentile: Percentile threshold for increased weighting (e.g. 90 for top 10%)
        reward_factor: Factor to increase weights for top performers (e.g. 0.4 for 40% boost)
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
    ):
        """
        Initialize the WeightsManager with a validator instance.

        :param validator: The validator instance to be used for weight calculations.
        """
        self.validator = validator

    def _get_delta_node_data(self) -> List[NodeData]:
        """
        Get telemetry data and calculate deltas between latest and oldest records.
        When TEE restarts are detected (negative deltas), split into chunks and sum them.

        :return: List of NodeData objects containing delta values.
        """
        delta_node_data = []
        hotkeys_to_score = (
            self.validator.telemetry_storage.get_all_hotkeys_with_telemetry()
        )
        # Get all hotkeys from metagraph to ensure we include those without telemetry
        all_hotkeys = []
        for node_idx, node in enumerate(self.validator.metagraph.nodes):
            node_data = self.validator.metagraph.nodes[node]
            hotkey = node_data.hotkey
            all_hotkeys.append((node_data.node_id, hotkey))

        # Process hotkeys with telemetry data
        processed_hotkeys = set()
        for hotkey in hotkeys_to_score:
            node_telemetry = self.validator.telemetry_storage.get_telemetry_by_hotkey(
                hotkey
            )
            logger.info(f"Showing {hotkey} telemetry: {len(node_telemetry)} records")
            logger.debug(node_telemetry)

            if len(node_telemetry) >= 2:
                # Sort by timestamp ascending (oldest first)
                sorted_telemetry = sorted(node_telemetry, key=lambda x: x.timestamp)

                # Find chunks separated by TEE restarts
                chunks = []
                current_chunk = [sorted_telemetry[0]]

                for i in range(1, len(sorted_telemetry)):
                    current = sorted_telemetry[i]
                    previous = sorted_telemetry[i - 1]

                    # Check if this record represents a reset (any key metric decreased)
                    is_reset = (
                        current.boot_time < previous.boot_time
                        or current.last_operation_time < previous.last_operation_time
                        or current.twitter_auth_errors < previous.twitter_auth_errors
                        or current.twitter_errors < previous.twitter_errors
                        or current.twitter_ratelimit_errors
                        < previous.twitter_ratelimit_errors
                        or current.twitter_returned_other
                        < previous.twitter_returned_other
                        or current.twitter_returned_profiles
                        < previous.twitter_returned_profiles
                        or current.twitter_returned_tweets
                        < previous.twitter_returned_tweets
                        or current.twitter_scrapes < previous.twitter_scrapes
                        or current.web_errors < previous.web_errors
                        or current.web_success < previous.web_success
                    )

                    if is_reset:
                        # This record starts a new chunk
                        logger.info(
                            f"Detected TEE restart for {hotkey} at record {i}. "
                            f"Starting new telemetry chunk."
                        )
                        chunks.append(current_chunk)
                        current_chunk = [current]
                    else:
                        # Add to current chunk
                        current_chunk.append(current)

                # Add the last chunk
                if current_chunk:
                    chunks.append(current_chunk)

                logger.info(
                    f"Split {hotkey} telemetry into {len(chunks)} chunks due to TEE restarts"
                )

                # Calculate deltas for each chunk and sum them
                total_boot_time_delta = 0
                total_last_operation_time_delta = 0
                total_twitter_auth_errors_delta = 0
                total_twitter_errors_delta = 0
                total_twitter_ratelimit_errors_delta = 0
                total_twitter_returned_other_delta = 0
                total_twitter_returned_profiles_delta = 0
                total_twitter_returned_tweets_delta = 0
                total_twitter_scrapes_delta = 0
                total_web_errors_delta = 0
                total_web_success_delta = 0

                for chunk in chunks:
                    if len(chunk) >= 2:
                        # Get first and last record in this chunk
                        first = chunk[0]
                        last = chunk[-1]

                        # Calculate deltas within this chunk (all should be non-negative)
                        total_boot_time_delta += max(
                            0, last.boot_time - first.boot_time
                        )
                        total_last_operation_time_delta += max(
                            0, last.last_operation_time - first.last_operation_time
                        )
                        total_twitter_auth_errors_delta += max(
                            0, last.twitter_auth_errors - first.twitter_auth_errors
                        )
                        total_twitter_errors_delta += max(
                            0, last.twitter_errors - first.twitter_errors
                        )
                        total_twitter_ratelimit_errors_delta += max(
                            0,
                            last.twitter_ratelimit_errors
                            - first.twitter_ratelimit_errors,
                        )
                        total_twitter_returned_other_delta += max(
                            0,
                            last.twitter_returned_other - first.twitter_returned_other,
                        )
                        total_twitter_returned_profiles_delta += max(
                            0,
                            last.twitter_returned_profiles
                            - first.twitter_returned_profiles,
                        )
                        total_twitter_returned_tweets_delta += max(
                            0,
                            last.twitter_returned_tweets
                            - first.twitter_returned_tweets,
                        )
                        total_twitter_scrapes_delta += max(
                            0, last.twitter_scrapes - first.twitter_scrapes
                        )
                        total_web_errors_delta += max(
                            0, last.web_errors - first.web_errors
                        )
                        total_web_success_delta += max(
                            0, last.web_success - first.web_success
                        )

                # Use the latest record's data for non-delta fields
                latest = sorted_telemetry[-1]

                # Create delta data with summed values
                delta_data = NodeData(
                    hotkey=hotkey,
                    uid=latest.uid,
                    worker_id=latest.worker_id,
                    timestamp=latest.timestamp,
                    boot_time=total_boot_time_delta,
                    last_operation_time=total_last_operation_time_delta,
                    current_time=latest.current_time,
                    twitter_auth_errors=total_twitter_auth_errors_delta,
                    twitter_errors=total_twitter_errors_delta,
                    twitter_ratelimit_errors=total_twitter_ratelimit_errors_delta,
                    twitter_returned_other=total_twitter_returned_other_delta,
                    twitter_returned_profiles=total_twitter_returned_profiles_delta,
                    twitter_returned_tweets=total_twitter_returned_tweets_delta,
                    twitter_scrapes=total_twitter_scrapes_delta,
                    web_errors=total_web_errors_delta,
                    web_success=total_web_success_delta,
                )

                delta_node_data.append(delta_data)
                processed_hotkeys.add(hotkey)
                logger.debug(
                    f"Calculated aggregate deltas for {hotkey} across {len(chunks)} chunks: {delta_data}"
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
                )
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
                )
                delta_node_data.append(delta_data)

        logger.info(f"Calculated deltas for {len(delta_node_data)} nodes")
        return delta_node_data

    async def calculate_weights(
        self, delta_node_data: List[NodeData], simulation: bool = False
    ) -> Tuple[List[int], List[float]]:
        """
        Calculate weights for nodes based on their web_success, twitter_returned_tweets,
        and twitter_returned_profiles using a kurtosis curve.

        :param delta_node_data: List of NodeData objects with delta values
        :return: A tuple containing a list of node IDs and their corresponding weights.
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
            )

        logger.info("Starting weight calculation...")
        miner_scores = {}

        if not delta_node_data:
            logger.warning("No node data provided for weight calculation")
            return [], []

        logger.debug(f"Calculating weights for {len(delta_node_data)} nodes")

        # Extract metrics
        logger.debug("Extracting node metrics")
        web_successes = np.array([float(node.web_success) for node in delta_node_data])
        tweets = np.array(
            [float(node.twitter_returned_tweets) for node in delta_node_data]
        )
        profiles = np.array(
            [float(node.twitter_returned_profiles) for node in delta_node_data]
        )

        # Normalize metrics using kurtosis curve
        logger.debug("Applying kurtosis curve to metrics")

        web_successes = apply_kurtosis_custom(web_successes)
        tweets = apply_kurtosis_custom(tweets)
        profiles = apply_kurtosis_custom(profiles)

        # Calculate combined score
        logger.debug("Calculating combined scores for each node")
        for idx, node in enumerate(delta_node_data):
            try:
                if simulation:
                    uid = node.uid
                else:
                    uid = self.validator.metagraph.nodes[node.hotkey].node_id

                if uid is not None:
                    # Combine scores with equal weight
                    score = float(
                        (web_successes[idx] + tweets[idx] + profiles[idx]) / 3
                    )
                    miner_scores[uid] = score

                    await self.validator.node_manager.send_score_report(
                        node.hotkey, score, node
                    )
                    logger.debug(f"Node {node.hotkey} (UID {uid}) score: {score:.4f}")
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
            data_to_score = self._get_delta_node_data()
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
