from miner.nats_client import NatsClient
from typing import TYPE_CHECKING
from fiber.logging_utils import get_logger
import asyncio

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)


class MinersNATSPublisher:
    def __init__(self, validator: "Validator"):
        self.nc = NatsClient()
        self.validator = validator

    async def send_connected_nodes(self):
        # Get process monitor from background tasks
        process_monitor = getattr(self.validator, "background_tasks", None)
        if process_monitor:
            process_monitor = getattr(process_monitor, "process_monitor", None)

        execution_id = None

        try:
            # Start monitoring for this NATS publish
            if process_monitor:
                execution_id = process_monitor.start_process("send_connected_nodes")

            # Check if routing table is currently being updated
            if getattr(self.validator, "routing_table_updating", False):
                logger.debug("Skipping NATS publish during routing table update")

                # Update metrics for skipped execution
                if execution_id and process_monitor:
                    process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=0,
                        successful_nodes=0,
                        failed_nodes=0,
                        additional_metrics={
                            "skipped": True,
                            "reason": "routing_table_updating",
                            "addresses": [],
                        },
                    )
                    process_monitor.end_process(execution_id)
                return

            # Get connected nodes from the validator using atomic method
            routing_table = self.validator.routing_table
            addresses = routing_table.get_all_addresses_atomic()

            if len(addresses) == 0:
                logger.debug("Skipping, no addresses found")

                # Update metrics for empty execution
                if execution_id and process_monitor:
                    process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=0,
                        successful_nodes=0,
                        failed_nodes=0,
                        additional_metrics={
                            "skipped": True,
                            "reason": "no_addresses",
                            "addresses": [],
                        },
                    )
                    process_monitor.end_process(execution_id)
                return

            logger.info(f"About to send {len(addresses)} IPs to NATS")
            logger.info(f"Sending IP list: {addresses}")

            # Retry logic for NATS publishing
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    await self.nc.send_connected_nodes(addresses)
                    logger.info("Successfully published to NATS")

                    # Update metrics for successful execution
                    if execution_id and process_monitor:
                        process_monitor.update_metrics(
                            execution_id,
                            nodes_processed=len(addresses),
                            successful_nodes=len(addresses),
                            failed_nodes=0,
                            additional_metrics={
                                "addresses": addresses.copy(),
                                "attempts": attempt + 1,
                                "max_retries": max_retries,
                            },
                        )
                        process_monitor.end_process(execution_id)
                        execution_id = None
                    return
                except Exception as e:
                    logger.warning(
                        f"NATS publish attempt {attempt + 1}/"
                        f"{max_retries} failed: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Failed to publish to NATS after "
                            f"{max_retries} attempts"
                        )

                        # Update metrics for failed execution
                        if execution_id and process_monitor:
                            process_monitor.update_metrics(
                                execution_id,
                                nodes_processed=len(addresses),
                                successful_nodes=0,
                                failed_nodes=len(addresses),
                                errors=[str(e)],
                                additional_metrics={
                                    "addresses": addresses.copy(),
                                    "attempts": max_retries,
                                    "max_retries": max_retries,
                                    "final_error": str(e),
                                },
                            )
                            process_monitor.end_process(execution_id)
                            execution_id = None
                        raise

        except Exception as e:
            # Handle any unexpected errors
            if execution_id and process_monitor:
                addresses = getattr(
                    self.validator.routing_table, "get_all_addresses_atomic", lambda: []
                )()
                process_monitor.update_metrics(
                    execution_id,
                    nodes_processed=len(addresses) if addresses else 0,
                    successful_nodes=0,
                    failed_nodes=len(addresses) if addresses else 0,
                    errors=[str(e)],
                    additional_metrics={
                        "addresses": (addresses.copy() if addresses else []),
                        "unexpected_error": str(e),
                    },
                )
                process_monitor.end_process(execution_id)
            raise

    async def send_priority_miners(self):
        """
        Send priority miners (sorted by score) to NATS for external consumption.
        """
        # Get process monitor from background tasks
        process_monitor = getattr(self.validator, "background_tasks", None)
        if process_monitor:
            process_monitor = getattr(process_monitor, "process_monitor", None)

        execution_id = None

        try:
            # Start monitoring for this NATS publish
            if process_monitor:
                execution_id = process_monitor.start_process("send_priority_miners")

            # Check if routing table is currently being updated
            if getattr(self.validator, "routing_table_updating", False):
                logger.debug(
                    "Skipping priority miners NATS publish during routing table update"
                )

                # Update metrics for skipped execution
                if execution_id and process_monitor:
                    process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=0,
                        successful_nodes=0,
                        failed_nodes=0,
                        additional_metrics={
                            "skipped": True,
                            "reason": "routing_table_updating",
                            "priority_miners": [],
                        },
                    )
                    process_monitor.end_process(execution_id)
                return

            # Get telemetry data and calculate priority miners
            logger.info("Calculating priority miners based on scoring")
            telemetry = self.validator.telemetry_storage.get_all_telemetry()
            delta_node_data = self.validator.weights_manager._get_delta_node_data(
                telemetry
            )

            # Get priority miners sorted by score
            priority_miners = (
                await self.validator.weights_manager.get_priority_miners_by_score(
                    delta_node_data
                )
            )

            if len(priority_miners) == 0:
                logger.debug("Skipping, no priority miners found")

                # Update metrics for empty execution
                if execution_id and process_monitor:
                    process_monitor.update_metrics(
                        execution_id,
                        nodes_processed=0,
                        successful_nodes=0,
                        failed_nodes=0,
                        additional_metrics={
                            "skipped": True,
                            "reason": "no_priority_miners",
                            "priority_miners": [],
                        },
                    )
                    process_monitor.end_process(execution_id)
                return

            logger.info(f"About to send {len(priority_miners)} priority miners to NATS")
            logger.info(f"Top 5 priority miners: {priority_miners[:5]}")

            # Retry logic for NATS publishing
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    await self.nc.send_priority_miners(priority_miners)
                    logger.info("Successfully published priority miners to NATS")

                    # Update metrics for successful execution
                    if execution_id and process_monitor:
                        process_monitor.update_metrics(
                            execution_id,
                            nodes_processed=len(priority_miners),
                            successful_nodes=len(priority_miners),
                            failed_nodes=0,
                            additional_metrics={
                                "priority_miners": priority_miners.copy(),
                                "attempts": attempt + 1,
                                "max_retries": max_retries,
                            },
                        )
                        process_monitor.end_process(execution_id)
                        execution_id = None
                    return
                except Exception as e:
                    logger.warning(
                        f"Priority miners NATS publish attempt {attempt + 1}/"
                        f"{max_retries} failed: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Failed to publish priority miners to NATS after "
                            f"{max_retries} attempts"
                        )

                        # Update metrics for failed execution
                        if execution_id and process_monitor:
                            process_monitor.update_metrics(
                                execution_id,
                                nodes_processed=len(priority_miners),
                                successful_nodes=0,
                                failed_nodes=len(priority_miners),
                                errors=[str(e)],
                                additional_metrics={
                                    "priority_miners": priority_miners.copy(),
                                    "attempts": max_retries,
                                    "max_retries": max_retries,
                                    "final_error": str(e),
                                },
                            )
                            process_monitor.end_process(execution_id)
                            execution_id = None
                        raise

        except Exception as e:
            # Handle any unexpected errors
            if execution_id and process_monitor:
                priority_miners = []
                try:
                    # Try to get telemetry for error reporting
                    telemetry = self.validator.telemetry_storage.get_all_telemetry()
                    delta_node_data = (
                        self.validator.weights_manager._get_delta_node_data(telemetry)
                    )
                    priority_miners = await self.validator.weights_manager.get_priority_miners_by_score(
                        delta_node_data
                    )
                except:
                    pass  # If we can't get priority miners, just use empty list

                process_monitor.update_metrics(
                    execution_id,
                    nodes_processed=len(priority_miners) if priority_miners else 0,
                    successful_nodes=0,
                    failed_nodes=len(priority_miners) if priority_miners else 0,
                    errors=[str(e)],
                    additional_metrics={
                        "priority_miners": (
                            priority_miners.copy() if priority_miners else []
                        ),
                        "unexpected_error": str(e),
                    },
                )
                process_monitor.end_process(execution_id)
            raise
