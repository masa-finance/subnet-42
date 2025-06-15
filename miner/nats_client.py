import os
import json
from nats.aio.client import Client as NATS
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


class NatsClient:
    def __init__(self):
        self.nc = NATS()
        logger.info("Initializing NATS client")

    async def error_callback(self, ex):
        logger.debug("Nats connecting error")

    async def send_connected_nodes(self, miners):

        # Connect to the NATS server
        nats_url = os.getenv("NATS_URL", None)
        logger.debug(f"Connecting to NATS server at {nats_url}")

        if nats_url:
            try:
                await self.nc.connect(
                    nats_url,
                    error_cb=self.error_callback,
                )
            except Exception as e:
                logger.info(f"An error ocurred when connecting to nats 🚩 {str(e)}")
                logger.debug(
                    f"Failed to connect to NATS server ( {nats_url} ) : {str(e)}"
                )
                return

            try:
                nats_message = json.dumps({"Miners": miners})
                channel_name = os.getenv("TEE_NATS_CHANNEL_NAME", "miners")

                logger.info(
                    f"Publishing message to channel '{channel_name}' with "
                    f"{len(miners)} miners"
                )
                logger.debug(f"Message content: {nats_message}")

                await self.nc.publish(channel_name, nats_message.encode())
                logger.info("Successfully published message ✅")

            except Exception as e:
                logger.info(f"Error publishing message to NATS ({nats_url})")
                logger.debug(f"Error publishing message to NATS: {str(e)}")

            finally:
                # Ensure the NATS connection is closed
                logger.debug("Closing NATS connection")
                await self.nc.close()

    async def send_priority_miners(self, priority_miners):
        """Send priority miners list to NATS"""
        # Connect to the NATS server
        nats_url = os.getenv("NATS_URL", None)
        logger.debug(f"Connecting to NATS server at {nats_url}")

        if not nats_url:
            raise ValueError("NATS_URL environment variable is not set")

        try:
            await self.nc.connect(
                nats_url,
                error_cb=self.error_callback,
            )
            logger.debug(f"Successfully connected to NATS server at {nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS server ({nats_url}): {str(e)}")
            raise ConnectionError(f"NATS connection failed: {str(e)}")

        try:
            nats_message = json.dumps({"PriorityMiners": priority_miners})
            channel_name = os.getenv("TEE_NATS_PRIORITY_CHANNEL", "miners")

            logger.info(
                f"Publishing priority miners to channel '{channel_name}' "
                f"with {len(priority_miners)} miners"
            )
            logger.debug(f"Priority miners message content: {nats_message}")

            await self.nc.publish(channel_name, nats_message.encode())
            logger.info("Successfully published priority miners message ✅")

        except Exception as e:
            logger.error(
                f"Error publishing priority miners message to NATS "
                f"({nats_url}): {str(e)}"
            )
            raise RuntimeError(f"NATS publish failed: {str(e)}")

        finally:
            # Ensure the NATS connection is closed
            logger.debug("Closing NATS connection for priority miners")
            try:
                await self.nc.close()
            except Exception as e:
                logger.warning(f"Error closing NATS connection: {str(e)}")
                # Don't raise here as the main operation completed
