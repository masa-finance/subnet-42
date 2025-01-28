import asyncio
from fiber.logging_utils import get_logger
from typing import TYPE_CHECKING

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
