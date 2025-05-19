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

    async def send_connected_nodes(self):
        # Get connected nodes from the validator
        routing_table = self.validator.routing_table
        addresses = routing_table.get_all_addresses()

        if len(addresses) == 0:
            logger.debug("Skipping, no addresses found")
            return

        logger.info(f"About to send {len(addresses)} IPs to NATS")

        logger.info(f"Sending IP list: {addresses}")

        await self.nc.send_connected_nodes(addresses)
