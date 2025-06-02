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
        # Check if routing table is currently being updated
        if getattr(self.validator, "routing_table_updating", False):
            logger.debug("Skipping NATS publish during routing table update")
            return

        # Get connected nodes from the validator using atomic method
        routing_table = self.validator.routing_table
        addresses = routing_table.get_all_addresses_atomic()

        if len(addresses) == 0:
            logger.debug("Skipping, no addresses found")
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
                return
            except Exception as e:
                logger.warning(
                    f"NATS publish attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to publish to NATS after {max_retries} attempts"
                    )
                    raise
