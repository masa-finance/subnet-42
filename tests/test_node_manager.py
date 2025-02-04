import unittest
from unittest.mock import AsyncMock, MagicMock
from validator.node_manager import NodeManager
from fiber.networking.models import NodeWithFernet as Node


class TestNodeManager(unittest.TestCase):
    def setUp(self):
        # Mock the Validator and Node
        self.mock_validator = MagicMock()
        self.mock_node = MagicMock(spec=Node)
        self.node_manager = NodeManager(validator=self.mock_validator)

    async def test_connect_with_miner_success(self):
        # Mock the handshake function to return a valid key and UUID
        self.mock_validator.http_client_manager.client = AsyncMock()
        self.mock_validator.keypair = MagicMock()
        self.mock_node.hotkey = "test_hotkey"

        # Mock the perform_handshake function
        with unittest.mock.patch(
            "fiber.encrypted.validator.handshake.perform_handshake",
            return_value=("symmetric_key_str", "symmetric_key_uuid"),
        ):
            result = await self.node_manager.connect_with_miner(
                miner_address="test_address",
                miner_hotkey="test_hotkey",
                node=self.mock_node,
            )
            self.assertTrue(result)
            self.assertIn("test_hotkey", self.node_manager.connected_nodes)

    async def test_connect_with_miner_failure(self):
        # Mock the handshake function to return None
        self.mock_validator.http_client_manager.client = AsyncMock()
        self.mock_validator.keypair = MagicMock()
        self.mock_node.hotkey = "test_hotkey"

        # Mock the perform_handshake function
        with unittest.mock.patch(
            "fiber.encrypted.validator.handshake.perform_handshake",
            return_value=(None, None),
        ):
            result = await self.node_manager.connect_with_miner(
                miner_address="test_address",
                miner_hotkey="test_hotkey",
                node=self.mock_node,
            )
            self.assertFalse(result)
            self.assertNotIn("test_hotkey", self.node_manager.connected_nodes)


if __name__ == "__main__":
    unittest.main()
