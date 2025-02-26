import unittest
import asyncio
import os
from unittest.mock import MagicMock
from miner.nats_client import NatsClient
from nats.aio.client import Client as NATS


class TestNatsClient(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.nats_client = NatsClient()
        self.nc = NATS()

        self.nodes = None

    async def async_message_handler(self, msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print(f"Received a message on '{subject} {reply}': {data}")

        self.nodes = data
        # Process the message here

    def test_send_connected_nodes(self):
        async def run_test():
            # Mock the message handler to track calls
            self.nats_client.message_handler = MagicMock()

            # Connect to the NATS server
            nats_url = os.getenv("NATS_URL", "nats://127.0.0.1:4222")
            await self.nc.connect(nats_url)

            # Subscribe to the channel
            channel_name = os.getenv("TEE_NATS_CHANNEL_NAME", "miners")
            await self.nc.subscribe(channel_name, cb=self.async_message_handler)

            # Send a test message
            miners = ["0.0.0.0:8080", "0.0.0.0:8081"]
            await self.nats_client.send_connected_nodes(miners)

            # Allow some time for the message to be processed
            await asyncio.sleep(1)

            # Check if the message handler was called with the expected message
            # self.nats_client.message_handler.assert_called()

            await asyncio.sleep(2)

            # Verify the received message contains the expected miners
            received_data = eval(self.nodes)
            self.assertEqual(received_data["Miners"], miners)
            # Close the connection
            await self.nc.close()

        self.loop.run_until_complete(run_test())

    def tearDown(self):
        self.loop.close()


if __name__ == "__main__":
    unittest.main()
