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
        # Ensure we have a safe cadence value (at least 30 seconds)
        safe_cadence = max(30, int(cadence_seconds or 60))

        if safe_cadence != cadence_seconds:
            logger.warning(
                f"Adjusted sync cadence from {cadence_seconds} to {safe_cadence} seconds"
            )

        # Calculate a safe retry delay (at least 30 seconds)
        retry_delay = max(30, safe_cadence // 2)  # Integer division to avoid float

        logger.info(
            f"Starting sync loop (cadence: {safe_cadence}s, retry: {retry_delay}s)"
        )

        while True:
            try:
                # Main tasks
                logger.info("Running sync loop")
                await self.validator.metagraph_manager.sync_metagraph()

                # Wait for next cycle
                await asyncio.sleep(safe_cadence)
            except Exception as e:
                # Log the error
                logger.error(f"Error in sync metagraph: {str(e)}")

                # Wait before retrying (using pre-calculated safe delay)
                await asyncio.sleep(retry_delay)

    async def update_tee(self, cadence_seconds) -> None:
        """Background task to update tee"""
        # Ensure we have a safe cadence value (at least 30 seconds)
        safe_cadence = max(30, int(cadence_seconds or 120))

        if safe_cadence != cadence_seconds:
            logger.warning(
                f"Adjusted TEE update cadence from {cadence_seconds} to {safe_cadence} seconds"
            )

        # Calculate a safe retry delay (at least 30 seconds)
        retry_delay = max(30, safe_cadence // 2)  # Integer division to avoid float

        logger.info(
            f"Starting TEE update loop (cadence: {safe_cadence}s, retry: {retry_delay}s)"
        )

        while True:
            try:
                # Main tasks
                await self.validator.node_manager.connect_new_nodes()
                await self.validator.NATSPublisher.send_connected_nodes()
                await self.validator.NATSPublisher.send_unregistered_tees()
                self.validator.telemetry_storage.clean_old_entries(
                    TELEMETRY_EXPIRATION_HOURS
                )
                # Node data collection moved to its own loop

                # Wait for next cycle
                await asyncio.sleep(safe_cadence)
            except Exception as e:
                # Log the error
                logger.error(f"Error updating TEE 🚩: {str(e)}")
                logger.debug(f"Error in updating tee: {str(e)}")

                # Wait before retrying (using pre-calculated safe delay)
                await asyncio.sleep(retry_delay)

    async def telemetry_loop(self, cadence_seconds) -> None:
        """Background task to collect node telemetry data independently"""
        # Ensure we have a safe cadence value (at least 30 seconds)
        safe_cadence = max(30, int(cadence_seconds or 180))  # Default: 3 minutes

        if safe_cadence != cadence_seconds:
            logger.warning(
                f"Adjusted telemetry cadence from {cadence_seconds} to {safe_cadence} seconds"
            )

        # Calculate a safe retry delay (at least 30 seconds)
        retry_delay = max(30, safe_cadence // 2)  # Integer division to avoid float

        logger.info(
            f"Starting telemetry loop (cadence: {safe_cadence}s, retry: {retry_delay}s)"
        )

        while True:
            try:
                # Collect node telemetry data
                logger.info("Collecting node telemetry data")
                await self.scorer.get_node_data()

                # Wait for next cycle
                await asyncio.sleep(safe_cadence)
            except Exception as e:
                # Log the error
                logger.error(f"Error collecting telemetry data: {str(e)}")
                logger.debug(f"Detailed telemetry error: {str(e)}")

                # Wait before retrying (using pre-calculated safe delay)
                await asyncio.sleep(retry_delay)

    async def set_weights_loop(self, cadence_seconds) -> None:
        """Background task to set weights using the weights manager"""
        # Ensure we have a safe cadence value (at least 30 seconds)
        safe_cadence = max(30, int(cadence_seconds or 60))

        if safe_cadence != cadence_seconds:
            logger.warning(
                f"Adjusted weights cadence from {cadence_seconds} to {safe_cadence} seconds"
            )

        # Calculate a safe retry delay (at least 30 seconds)
        retry_delay = max(30, safe_cadence // 2)  # Integer division to avoid float

        logger.info(
            f"Starting weights loop (cadence: {safe_cadence}s, retry: {retry_delay}s)"
        )

        while True:
            try:
                # Main tasks
                await self.validator.weights_manager.set_weights()

                # Wait for next cycle
                await asyncio.sleep(safe_cadence)
            except Exception as e:
                # Log the error
                logger.error(f"Error in setting weights: {str(e)}")

                # Wait before retrying (using pre-calculated safe delay)
                await asyncio.sleep(retry_delay)
