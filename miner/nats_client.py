import asyncio
import os
import json
import logging
from nats.aio.client import Client as NATS


class NatsClient:
    def __init__(self):
        self.nc = NATS()
        logging.info("Initializing NATS client")

    async def send_connected_nodes(self, miners):
        # Connect to the NATS server
        logging.info("Connecting to NATS server at nats://127.0.0.1:4222")
        await self.nc.connect("nats://127.0.0.1:4222")

        try:
            nats_message = json.dumps({"Miners": miners})
            channel_name = os.getenv("TEE_NATS_CHANNEL_NAME", "miners")

            logging.info(
                f"Publishing message to channel '{channel_name}' with {len(miners)} miners"
            )
            logging.debug(f"Message content: {nats_message}")

            await self.nc.publish(channel_name, nats_message.encode())
            logging.info("Successfully published message")

        except Exception as e:
            logging.error(f"Error publishing message to NATS: {str(e)}")
            raise
        finally:
            # Ensure the NATS connection is closed
            logging.info("Closing NATS connection")
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
