from miner.nats_client import NatsClient
from typing import TYPE_CHECKING
from fiber.logging_utils import get_logger

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)


class MinersNATSPublisher:
    def __init__(self, validator: "Validator"):
        self.nc = NatsClient()
        self.validator = validator

        # Track initialization state
        self.initial_empty_sent = False
        self.threshold_reached = False
        self.min_threshold = 100

    async def send_connected_nodes(self):
        # Check if routing table is currently being updated
        if getattr(self.validator, "routing_table_updating", False):
            logger.debug("Skipping NATS publish during routing table update")
            return

        # Get connected nodes from the validator
        routing_table = self.validator.routing_table
        addresses = routing_table.get_all_addresses()

        # Send initial empty list on startup
        if not self.initial_empty_sent:
            logger.info("Sending initial empty list to NATS on startup")
            await self.nc.send_connected_nodes([])
            self.initial_empty_sent = True
            return

        # If we haven't reached the threshold yet, check if we have enough items
        if not self.threshold_reached:
            if len(addresses) < self.min_threshold:
                logger.debug(
                    f"Waiting for threshold: {len(addresses)}/"
                    f"{self.min_threshold} addresses. Not sending to NATS."
                )
                return
            else:
                # We've reached the threshold for the first time
                self.threshold_reached = True
                logger.info(
                    f"Threshold reached! Now have {len(addresses)} addresses. "
                    f"Starting normal NATS publishing."
                )

        # Normal publishing logic (after threshold is reached)
        if len(addresses) == 0:
            logger.debug("Skipping, no addresses found")
            return

        logger.info(f"About to send {len(addresses)} IPs to NATS")
        logger.info(f"Sending IP list: {addresses}")
        await self.nc.send_connected_nodes(addresses)
