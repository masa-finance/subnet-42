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
        connected_nodes = self.validator.node_manager.connected_nodes

        if len(connected_nodes) == 0:
            logger.info("Skipping, no nodes connected")
            return

        logger.info("Connecting to nats...")

        miners_list = (
            [
                f"{'http://localhost' if node.ip == '1' else node.ip}:{node.port}"
                for node in connected_nodes.values()
            ]
            if connected_nodes
            else []
        )

        logger.info(f"Sending IP list: {miners_list}")

        await self.nc.send_connected_nodes(miners_list)
