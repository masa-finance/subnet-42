import unittest
from unittest.mock import Mock, patch, AsyncMock
from validator.scorer import NodeDataScorer


class TestNodeDataScorer(unittest.TestCase):

    def setUp(self):
        # Create mock validator
        self.mock_validator = Mock()
        self.scorer = NodeDataScorer(self.mock_validator)

        # Reset active_stat_name and time
        self.scorer.active_stat_name = None
        self.scorer.last_stat_name_refresh = 0

    @patch("aiohttp.ClientSession.get")
    @patch("time.time")
    async def test_fetch_active_stat_name(self, mock_time, mock_get):
        """Test fetching the active stat name from the API."""
        # Setup mocks
        mock_time.return_value = 1000  # Mock current time

        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"active_stat_name": "worker_123"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call the method
        result = await self.scorer.fetch_active_stat_name()

        # Verify the result
        self.assertEqual(result, "worker_123")
        self.assertEqual(self.scorer.active_stat_name, "worker_123")
        self.assertEqual(self.scorer.last_stat_name_refresh, 1000)

        # Verify the API was called
        mock_get.assert_called_once_with(self.scorer.api_url)

    @patch("aiohttp.ClientSession.get")
    @patch("time.time")
    async def test_fetch_active_stat_name_caching(self, mock_time, mock_get):
        """Test that the stat name is cached properly."""
        # Setup initial state
        self.scorer.active_stat_name = "cached_worker"
        self.scorer.last_stat_name_refresh = 1000

        # Set current time to be within refresh interval
        refresh_delta = self.scorer.stat_name_refresh_interval - 10
        mock_time.return_value = 1000 + refresh_delta

        # Call the method
        result = await self.scorer.fetch_active_stat_name()

        # Verify the cached value was returned without calling the API
        self.assertEqual(result, "cached_worker")
        mock_get.assert_not_called()

    @patch("aiohttp.ClientSession.get")
    @patch("time.time")
    async def test_fetch_active_stat_name_refresh(self, mock_time, mock_get):
        """Test that the stat name is refreshed after the interval."""
        # Setup initial state
        self.scorer.active_stat_name = "old_worker"
        self.scorer.last_stat_name_refresh = 1000

        # Set current time to be after refresh interval
        refresh_delta = self.scorer.stat_name_refresh_interval + 10
        mock_time.return_value = 1000 + refresh_delta

        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"active_stat_name": "new_worker"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call the method
        result = await self.scorer.fetch_active_stat_name()

        # Verify the new value was returned
        self.assertEqual(result, "new_worker")
        self.assertEqual(self.scorer.active_stat_name, "new_worker")
        mock_get.assert_called_once()

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_active_stat_name_api_error(self, mock_get):
        """Test handling of API errors when fetching the stat name."""
        # Setup mock response with error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call the method
        result = await self.scorer.fetch_active_stat_name()

        # Verify the result is None on error
        self.assertIsNone(result)

        # Test with cached value
        self.scorer.active_stat_name = "fallback_worker"
        result = await self.scorer.fetch_active_stat_name()

        # Verify fallback to cached value
        self.assertEqual(result, "fallback_worker")

    def test_aggregate_telemetry_stats_old_format(self):
        """Test aggregation with old format telemetry data."""
        telemetry_result = {
            "stats": {
                "twitter_auth_errors": 5,
                "twitter_errors": 10,
                "twitter_scrapes": 120,
                "web_success": 93,
            }
        }

        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # Should still aggregate old format stats
        self.assertEqual(result["twitter_auth_errors"], 5)
        self.assertEqual(result["twitter_errors"], 10)
        self.assertEqual(result["twitter_scrapes"], 120)
        self.assertEqual(result["web_success"], 93)

    def test_aggregate_telemetry_stats_new_format_no_active_stat(self):
        """Test with new format telemetry and no active stat name."""
        # Setup multiple workers
        telemetry_result = {
            "stats": {
                "worker_1": {
                    "twitter_auth_errors": 5,
                    "twitter_errors": 10,
                    "twitter_scrapes": 120,
                },
                "worker_2": {
                    "twitter_scrapes": 80,
                    "web_success": 93,
                },
            }
        }

        # No active stat name set, should aggregate all workers
        self.scorer.active_stat_name = None
        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # Should aggregate stats from all workers
        self.assertEqual(result["twitter_auth_errors"], 5)
        self.assertEqual(result["twitter_errors"], 10)
        self.assertEqual(result["twitter_scrapes"], 200)  # 120 + 80
        self.assertEqual(result["web_success"], 93)

    def test_aggregate_telemetry_stats_new_format_with_active_stat(self):
        """Test with new format telemetry and active stat name."""
        # Setup multiple workers
        telemetry_result = {
            "stats": {
                "worker_1": {
                    "twitter_auth_errors": 5,
                    "twitter_errors": 10,
                    "twitter_scrapes": 120,
                },
                "worker_2": {
                    "twitter_scrapes": 80,
                    "web_success": 93,
                },
            }
        }

        # Set active stat name to worker_2
        self.scorer.active_stat_name = "worker_2"
        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # Should only aggregate stats from worker_2
        self.assertEqual(result["twitter_auth_errors"], 0)  # Not in worker_2
        self.assertEqual(result["twitter_errors"], 0)  # Not in worker_2
        self.assertEqual(result["twitter_scrapes"], 80)  # Only from worker_2
        self.assertEqual(result["web_success"], 93)  # Only from worker_2

    def test_aggregate_telemetry_stats_new_format_missing_active_stat(self):
        """Test when the active stat name doesn't exist in the data."""
        # Setup workers
        telemetry_result = {
            "stats": {
                "worker_1": {
                    "twitter_scrapes": 120,
                },
                "worker_2": {
                    "web_success": 93,
                },
            }
        }

        # Set active stat name to non-existent worker
        self.scorer.active_stat_name = "worker_3"
        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # Should have zeros for all stats since active worker doesn't exist
        self.assertEqual(result["twitter_scrapes"], 0)
        self.assertEqual(result["web_success"], 0)


if __name__ == "__main__":
    unittest.main()
