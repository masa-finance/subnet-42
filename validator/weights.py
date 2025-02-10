from typing import List, Tuple, Any
import asyncio
from fiber.chain import weights, interface
from fiber.logging_utils import get_logger

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
        self.validator = validator

    def calculate_weights(
        self, node_data: List[NodeData]
    ) -> Tuple[List[int], List[float]]:
        miner_scores = {}
        if node_data:
            min_posts = min(node.posts for node in node_data)
            max_posts = max(node.posts for node in node_data)
            post_range = max_posts - min_posts if max_posts != min_posts else 1

            for node in node_data:
                uid = self.validator.metagraph.nodes[node.hotkey].node_id
                if uid is not None:
                    miner_scores[uid] = (node.posts - min_posts) / post_range

        uids = sorted(miner_scores.keys())
        weights = [miner_scores[uid] for uid in uids]
        return uids, weights

    async def set_weights(self, node_data: List[NodeData]) -> None:
        self.validator.substrate = interface.get_substrate(
            subtensor_address=self.validator.substrate.url
        )
        validator_node_id = self.validator.substrate.query(
            "SubtensorModule",
            "Uids",
            [self.validator.netuid, self.validator.keypair.ss58_address],
        ).value

        blocks_since_update = weights._blocks_since_last_update(
            self.validator.substrate, self.validator.netuid, validator_node_id
        )
        min_interval = weights._min_interval_to_set_weights(
            self.validator.substrate, self.validator.netuid
        )

        logger.info(f"Blocks since last update: {blocks_since_update}")
        logger.info(f"Minimum interval required: {min_interval}")

        if blocks_since_update is not None and blocks_since_update < min_interval:
            wait_blocks = min_interval - blocks_since_update
            wait_seconds = wait_blocks * 12
            logger.info(f"Waiting {wait_seconds} seconds...")
            await asyncio.sleep(wait_seconds)

        uids, scores = self.calculate_weights(node_data)

        logger.info(f"Uids: {uids} Scores: {scores}")

        for attempt in range(3):
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
                    await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                await asyncio.sleep(10)

        logger.error("Failed to set weights after all attempts")
