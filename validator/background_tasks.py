import os
import asyncio
from fiber.logging_utils import get_logger

from typing import TYPE_CHECKING

from validator.process_monitor import ProcessMonitor

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
        self.process_monitor = ProcessMonitor(max_records_per_process=256)

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
            execution_id = None
            try:
                # Start monitoring for this cycle
                execution_id = self.process_monitor.start_process("update_tee")

                # Track connected nodes before processing
                connected_nodes_count = len(self.validator.node_manager.connected_nodes)

                # Set update flag BEFORE any routing table operations
                self.validator.routing_table_updating = True

                try:
                    # Main tasks in proper order
                    await self.validator.node_manager.connect_new_nodes()

                    # Track nodes after connection attempt
                    nodes_after_connect = len(
                        self.validator.node_manager.connected_nodes
                    )
                    new_connections = nodes_after_connect - connected_nodes_count

                    # Update TEE list while flag is set
                    await self.validator.node_manager.update_tee_list()

                    # Clean old telemetry entries
                    self.validator.telemetry_storage.clean_old_entries(
                        TELEMETRY_EXPIRATION_HOURS
                    )

                finally:
                    # Clear update flag before NATS publishing (ensures atomic operation)
                    self.validator.routing_table_updating = False

                # Now safely publish to NATS with consistent data
                # await self.validator.NATSPublisher.send_connected_nodes()

                # Also publish priority miners sorted by score
                await self.validator.NATSPublisher.send_priority_miners()

                # Update metrics for successful cycle
                if execution_id:
                    self.process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=nodes_after_connect,
                        successful_nodes=new_connections,
                        failed_nodes=0,
                        additional_metrics={
                            "initial_connected_nodes": connected_nodes_count,
                            "final_connected_nodes": nodes_after_connect,
                            "new_connections": new_connections,
                        },
                    )

                # End monitoring for successful cycle
                if execution_id:
                    self.process_monitor.end_process(execution_id)
                    execution_id = None

                # Wait for next cycle
                await asyncio.sleep(safe_cadence)

            except Exception as e:
                # Ensure flag is cleared on error
                self.validator.routing_table_updating = False

                # Log the error
                logger.error(f"Error updating TEE 🚩: {str(e)}")
                logger.debug(f"Error in updating tee: {str(e)}")

                # Update metrics with error
                if execution_id:
                    self.process_monitor.update_metrics(
                        execution_id, errors=[str(e)], failed_nodes=1
                    )
                    # End monitoring for failed cycle
                    self.process_monitor.end_process(execution_id)
                    execution_id = None

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
            execution_id = None
            try:
                # Start monitoring for this cycle
                execution_id = self.process_monitor.start_process("telemetry_loop")

                # Track connected nodes before processing
                connected_nodes_count = len(self.validator.node_manager.connected_nodes)

                # Collect node telemetry data
                logger.info("Collecting node telemetry data")
                await self.scorer.get_node_data()

                # Update metrics for successful cycle
                if execution_id:
                    self.process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=connected_nodes_count,
                        successful_nodes=connected_nodes_count,  # Assume success unless error
                        failed_nodes=0,
                        additional_metrics={"connected_nodes": connected_nodes_count},
                    )

                # End monitoring for successful cycle
                if execution_id:
                    self.process_monitor.end_process(execution_id)
                    execution_id = None

                # Wait for next cycle
                await asyncio.sleep(safe_cadence)

            except Exception as e:
                # Log the error
                logger.error(f"Error collecting telemetry data: {str(e)}")
                logger.debug(f"Detailed telemetry error: {str(e)}")

                # Update metrics with error
                if execution_id:
                    connected_nodes_count = len(
                        self.validator.node_manager.connected_nodes
                    )
                    self.process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=connected_nodes_count,
                        successful_nodes=0,
                        failed_nodes=connected_nodes_count,
                        errors=[str(e)],
                    )
                    # End monitoring for failed cycle
                    self.process_monitor.end_process(execution_id)
                    execution_id = None

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

    async def monitor_cleanup_loop(self) -> None:
        """Periodic cleanup of monitoring data to prevent memory growth"""
        cleanup_interval = 3600  # 1 hour

        logger.info(f"Starting monitor cleanup loop (interval: {cleanup_interval}s)")

        while True:
            try:
                await asyncio.sleep(cleanup_interval)
                # Clean up old records (keep last 24 hours)
                self.process_monitor.cleanup_old_records(hours=24)
                logger.debug("Cleaned up old process monitoring records")
            except Exception as e:
                logger.error(f"Error in monitor cleanup: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
