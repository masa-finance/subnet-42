import asyncio
from fiber.logging_utils import get_logger
from typing import TYPE_CHECKING
from validator.scorer import NodeDataScorer

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)


class BackgroundTasks:
    def __init__(self, validator: "Validator"):
        """
        Initialize the BackgroundTasks with necessary components.

        :param validator: The validator instance for agent registration tasks.
        """
        self.validator = validator
        self.scorer = validator.scorer  # Initialize the scorer from the validator

    async def sync_loop(self, cadence_seconds) -> None:
        """Background task to sync metagraph"""
        while True:
            try:
                await self.validator.node_manager.connect_new_nodes()
                await self.validator.metagraph_manager.sync_metagraph()

                await asyncio.sleep(cadence_seconds)
            except Exception as e:
                logger.error(f"Error in sync metagraph: {str(e)}")
                await asyncio.sleep(cadence_seconds / 2)  # Wait before retrying

    async def update_tee(self, cadence_seconds) -> None:
        """Background task to update tee"""
        while True:
            try:
                await self.validator.NATSPublisher.send_connected_nodes()
                await asyncio.sleep(cadence_seconds)
            except Exception as e:
                logger.error(f"Error in sync metagraph: {str(e)}")
                await asyncio.sleep(cadence_seconds / 2)  # Wait before retrying

    async def set_weights_loop(self, cadence_seconds) -> None:
        """Background task to set weights using the weights manager"""
        while True:
            try:
                # TODO: Calculate scores and set weights
                node_data = await self.scorer.get_node_data()
                await self.validator.weights_manager.set_weights(node_data)
                await asyncio.sleep(cadence_seconds)
            except Exception as e:
                logger.error(f"Error in setting weights: {str(e)}")
                await asyncio.sleep(cadence_seconds / 2)  # Wait before retrying
