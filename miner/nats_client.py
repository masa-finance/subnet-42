import asyncio
import os
import json
from nats.aio.client import Client as NATS
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


class NatsClient:
    def __init__(self):
        self.nc = NATS()
        logger.info("Initializing NATS client")

    async def send_connected_nodes(self, miners):

        # Connect to the NATS server
        nats_url = os.getenv("NATS_URL", None)
        logger.info(f"Connecting to NATS server at {nats_url}")

        if nats_url:
            await self.nc.connect(nats_url)

            try:
                nats_message = json.dumps({"Miners": miners})
                channel_name = os.getenv("TEE_NATS_CHANNEL_NAME", "miners")

                logger.info(
                    f"Publishing message to channel '{channel_name}' with {len(miners)} miners"
                )
                logger.info(f"Message content: {nats_message}")

                await self.nc.publish(channel_name, nats_message.encode())
                logger.info("Successfully published message")

            except Exception as e:
                logger.info(f"Error publishing message to NATS: {str(e)}")
                raise
            finally:
                # Ensure the NATS connection is closed
                logger.info("Closing NATS connection")
                await self.nc.close()


# Example usage
async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Assuming you have an instance of AgentValidator
    nats_client = NatsClient()
    await nats_client.send_connected_nodes(["0.0.0.0:8080"])


if __name__ == "__main__":
    asyncio.run(main())
