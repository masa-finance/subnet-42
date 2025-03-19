from fiber.logging_utils import get_logger

from fiber.chain import interface
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurons.validator import Validator

logger = get_logger(__name__)


class MetagraphManager:
    def __init__(self, validator: "Validator"):
        """
        Initialize the MetagraphManager with a validator instance.

        :param validator: The validator instance to manage the metagraph.
        """
        self.validator = validator

    def sync_substrate(self) -> None:
        """
        Sync the substrate with the latest chain state.
        """
        self.validator.substrate = interface.get_substrate(
            subtensor_address=self.validator.substrate.url
        )

    async def sync_metagraph(self) -> None:
        """
        Synchronize local metagraph state with the chain.
        """
        try:
            self.sync_substrate()
            self.validator.metagraph.sync_nodes()

            await self.validator.node_manager.remove_disconnected_nodes()

            logger.info("Metagraph synced successfully")
        except Exception as e:
            logger.error(f"Failed to sync metagraph: {str(e)}")
