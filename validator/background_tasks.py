import os
import asyncio
from fiber.logging_utils import get_logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)

TELEMETRY_EXPIRATION_HOURS = int(os.getenv("TELEMETRY_EXPIRATION_HOURS", "8"))


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
        # Ensure cadence_seconds is never zero to prevent division by zero
        if cadence_seconds <= 0:
            cadence_seconds = 60  # Default to 1 minute if invalid
            logger.warning(f"Invalid sync cadence, using default: 60 seconds")

        while True:
            try:
                logger.info("Running sync loop")
                await self.validator.metagraph_manager.sync_metagraph()

                await asyncio.sleep(cadence_seconds)
            except Exception as e:
                logger.error(f"Error in sync metagraph: {str(e)}")
                # Use a minimum retry delay to avoid division by zero
                retry_delay = max(30, cadence_seconds / 2)  # At least 30 seconds
                await asyncio.sleep(retry_delay)  # Wait before retrying

    async def update_tee(self, cadence_seconds) -> None:
        """Background task to update tee"""
        # Ensure cadence_seconds is never zero to prevent division by zero
        if cadence_seconds <= 0:
            cadence_seconds = 120  # Default to 2 minutes if invalid
            logger.warning(
                f"Invalid TEE update cadence ({cadence_seconds}), using default: 120 seconds"
            )

        while True:
            try:
                await self.validator.NATSPublisher.send_connected_nodes()
                await self.validator.NATSPublisher.send_unregistered_tees()
                self.validator.telemetry_storage.clean_old_entries(
                    TELEMETRY_EXPIRATION_HOURS
                )
                await self.scorer.get_node_data()
                await asyncio.sleep(cadence_seconds)
            except Exception as e:
                logger.error(f"Error updating TEE 🚩: {str(e)}")
                logger.debug(f"Error in updating tee: {str(e)}")
                # Use a minimum retry delay to avoid division by zero
                retry_delay = max(30, cadence_seconds / 2)  # At least 30 seconds
                await asyncio.sleep(retry_delay)  # Wait before retrying

    async def set_weights_loop(self, cadence_seconds) -> None:
        """Background task to set weights using the weights manager"""
        # Ensure cadence_seconds is never zero to prevent division by zero
        if cadence_seconds <= 0:
            cadence_seconds = 60  # Default to 1 minute if invalid
            logger.warning(f"Invalid weights cadence, using default: 60 seconds")

        while True:
            try:
                # TODO: Calculate scores and set weights
                await self.validator.weights_manager.set_weights()
                await asyncio.sleep(cadence_seconds)
            except Exception as e:
                logger.error(f"Error in setting weights: {str(e)}")
                # Use a minimum retry delay to avoid division by zero
                retry_delay = max(30, cadence_seconds / 2)  # At least 30 seconds
                await asyncio.sleep(retry_delay)  # Wait before retrying
