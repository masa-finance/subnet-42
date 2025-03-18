from typing import List, Tuple
import asyncio
from fiber.chain import weights, interface
from fiber.logging_utils import get_logger
from sklearn.preprocessing import MinMaxScaler
import numpy as np

from neurons import version_numerical

from interfaces.types import NodeData

logger = get_logger(__name__)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurons.validator import Validator


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

    def calculate_weights(
        self, node_data: List[NodeData]
    ) -> Tuple[List[int], List[float]]:
        """
        Calculate weights for nodes based on their web_success, twitter_returned_tweets, and twitter_returned_profiles.

        :param node_data: List of NodeData objects containing node information.
        :return: A tuple containing a list of node IDs and their corresponding weights.
        """

        # Log node data for debugging
        for node in node_data:
            logger.info(
                f"Node {node.hotkey} data:"
                f"\n\tWeb success: {node.web_success}"
                f"\n\tTwitter returned tweets: {node.twitter_returned_tweets}"
                f"\n\tTwitter returned profiles: {node.twitter_returned_profiles}"
                f"\n\tTwitter errors: {node.twitter_errors}"
                f"\n\tTwitter auth errors: {node.twitter_auth_errors}"
                f"\n\tTwitter ratelimit errors: {node.twitter_ratelimit_errors}"
                f"\n\tWeb errors: {node.web_errors}"
                f"\n\tBoot time: {node.boot_time}"
                f"\n\tLast operation time: {node.last_operation_time}"
                f"\n\tCurrent time: {node.current_time}"
            )
        logger.info("Starting weight calculation")
        miner_scores = {}

        if not node_data:
            logger.warning("No node data provided for weight calculation")
            return [], []

        logger.debug(f"Calculating weights for {len(node_data)} nodes")

        # Extract metrics
        logger.debug("Extracting node metrics")
        web_successes = np.array([node.web_success for node in node_data]).reshape(
            -1, 1
        )
        tweets = np.array([node.twitter_returned_tweets for node in node_data]).reshape(
            -1, 1
        )
        profiles = np.array(
            [node.twitter_returned_profiles for node in node_data]
        ).reshape(-1, 1)

        # Normalize metrics
        logger.debug("Normalizing metrics using MinMaxScaler")
        scaler = MinMaxScaler(feature_range=(0, 1))
        web_successes = scaler.fit_transform(web_successes).flatten()
        tweets = scaler.fit_transform(tweets).flatten()
        profiles = scaler.fit_transform(profiles).flatten()

        # Calculate combined score
        logger.debug("Calculating combined scores for each node")
        for idx, node in enumerate(node_data):
            try:
                uid = self.validator.metagraph.nodes[node.hotkey].node_id
                if uid is not None:
                    # Combine scores with equal weight
                    score = (web_successes[idx] + tweets[idx] + profiles[idx]) / 3
                    miner_scores[uid] = score
                    logger.debug(f"Node {node.hotkey} (UID {uid}) score: {score:.4f}")
            except KeyError:
                logger.error(
                    f"Node with hotkey '{node.hotkey}' not found in metagraph."
                )

        uids = sorted(miner_scores.keys())
        weights = [miner_scores[uid] for uid in uids]

        logger.info(f"Completed weight calculation for {len(uids)} nodes")
        logger.debug(f"UIDs: {uids}")
        logger.debug(f"Weights: {[f'{w:.4f}' for w in weights]}")

        return uids, weights

    async def set_weights(self, node_data: List[NodeData]) -> None:
        """
        Set weights for nodes on the blockchain, ensuring the minimum interval between updates is respected.

        :param node_data: List of NodeData objects containing node information.
        """
        logger.info("Starting weight setting process")

        logger.debug("Refreshing substrate connection")
        self.validator.substrate = interface.get_substrate(
            subtensor_address=self.validator.substrate.url
        )

        logger.debug("Getting validator node ID")
        # validator_node_id = self.validator.substrate.query(
        #     "SubtensorModule",
        #     "Uids",
        #     [self.validator.netuid, self.validator.keypair.ss58_address],
        # ).value
        validator_node_id = 95
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
            logger.info(f"Need to wait {wait_seconds} seconds before setting weights")
            await asyncio.sleep(wait_seconds)
            logger.info("Wait period complete")

        logger.debug("Calculating weights")
        uids, scores = self.calculate_weights(node_data)
        logger.info(f"Calculated weights - UIDs: {uids}")
        logger.info(f"Calculated scores: {scores}")

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
                    logger.info("✅ Successfully set weights!")
                    return
                else:
                    logger.error(f"❌ Failed to set weights on attempt {attempt + 1}")
                    if attempt < 2:  # Don't sleep on last attempt
                        logger.debug("Waiting 10 seconds before next attempt")
                        await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}", exc_info=True)
                if attempt < 2:  # Don't sleep on last attempt
                    logger.debug("Waiting 10 seconds before next attempt")
                    await asyncio.sleep(10)

        logger.error("Failed to set weights after all attempts")
