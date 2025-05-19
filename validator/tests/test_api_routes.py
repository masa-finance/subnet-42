import unittest
from unittest.mock import Mock, patch, AsyncMock
import os
from validator.api_routes import ValidatorAPI
from fastapi import HTTPException


class TestApiRoutes(unittest.TestCase):

    def setUp(self):
        # Create mock validator
        self.mock_validator = Mock()
        self.api = ValidatorAPI(self.mock_validator)

        # Set up environment variable
        self.original_env = os.environ.get("MASA_TEE_API", None)
        os.environ["MASA_TEE_API"] = "https://api.masa.test"

    def tearDown(self):
        # Restore original environment variable
        if self.original_env is not None:
            os.environ["MASA_TEE_API"] = self.original_env
        else:
            del os.environ["MASA_TEE_API"]

    @patch("aiohttp.ClientSession.post")
    async def test_add_unregistered_tee_success(self, mock_post):
        """Test successful registration of a TEE worker."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "message": "Worker registered successfully",
                "address": "test_address",
            }
        )
        mock_post.return_value.__aenter__.return_value = mock_response

        # Call the method
        result = await self.api.add_unregistered_tee(
            address="test_address", hotkey="test_hotkey"
        )

        # Verify the result
        self.assertTrue(result["success"])
        self.assertIn("Successfully registered TEE worker", result["message"])

        # Verify the API was called with the correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.masa.test/register-tee-worker")

        # Verify the payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["address"], "test_address")
        self.assertEqual(payload["hotkey"], "test_hotkey")

    @patch("aiohttp.ClientSession.post")
    async def test_add_unregistered_tee_api_error(self, mock_post):
        """Test handling of API errors when registering a TEE worker."""
        # Setup mock response with error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_post.return_value.__aenter__.return_value = mock_response

        # Call the method
        result = await self.api.add_unregistered_tee(
            address="test_address", hotkey="test_hotkey"
        )

        # Verify the result
        self.assertFalse(result["success"])
        self.assertIn("API call failed with status 500", result["error"])

    @patch("aiohttp.ClientSession.post")
    async def test_add_unregistered_tee_connection_error(self, mock_post):
        """Test handling of connection errors when registering a TEE worker."""
        # Setup mock to raise a connection error
        mock_post.side_effect = AsyncMock(side_effect=Exception("Connection refused"))

        # Call the method
        result = await self.api.add_unregistered_tee(
            address="test_address", hotkey="test_hotkey"
        )

        # Verify the result
        self.assertFalse(result["success"])
        self.assertIn("Connection refused", result["error"])

    async def test_add_unregistered_tee_missing_api_url(self):
        """Test handling of missing API URL."""
        # Remove the environment variable
        del os.environ["MASA_TEE_API"]

        # Call the method
        result = await self.api.add_unregistered_tee(
            address="test_address", hotkey="test_hotkey"
        )

        # Verify the result
        self.assertFalse(result["success"])
        self.assertIn("MASA_TEE_API environment variable not set", result["error"])

    async def test_add_unregistered_tee_missing_params(self):
        """Test validation of required parameters."""
        # Call with missing parameters
        with self.assertRaises(HTTPException) as context:
            await self.api.add_unregistered_tee(address="", hotkey="test_hotkey")

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("required fields", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
