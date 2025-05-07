import unittest
from unittest.mock import Mock
from validator.scorer import NodeDataScorer


class TestNodeDataScorer(unittest.TestCase):

    def setUp(self):
        # Create a mock validator
        self.mock_validator = Mock()
        self.scorer = NodeDataScorer(self.mock_validator)

    def test_aggregate_telemetry_stats_empty(self):
        """Test aggregation with empty stats."""
        telemetry_result = {"stats": {}}
        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # All stats should be 0
        for value in result.values():
            self.assertEqual(value, 0)

    def test_aggregate_telemetry_stats_single_worker(self):
        """Test aggregation with a single worker."""
        telemetry_result = {
            "stats": {
                "worker1": {
                    "twitter_auth_errors": 5,
                    "twitter_errors": 10,
                    "twitter_ratelimit_errors": 2,
                    "twitter_returned_other": 3,
                    "twitter_returned_profiles": 20,
                    "twitter_returned_tweets": 100,
                    "twitter_scrapes": 120,
                    "web_errors": 7,
                    "web_success": 93,
                }
            }
        }

        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        self.assertEqual(result["twitter_auth_errors"], 5)
        self.assertEqual(result["twitter_errors"], 10)
        self.assertEqual(result["twitter_ratelimit_errors"], 2)
        self.assertEqual(result["twitter_returned_other"], 3)
        self.assertEqual(result["twitter_returned_profiles"], 20)
        self.assertEqual(result["twitter_returned_tweets"], 100)
        self.assertEqual(result["twitter_scrapes"], 120)
        self.assertEqual(result["web_errors"], 7)
        self.assertEqual(result["web_success"], 93)

    def test_aggregate_telemetry_stats_multiple_workers(self):
        """Test aggregation with multiple workers."""
        telemetry_result = {
            "stats": {
                "worker1": {
                    "twitter_auth_errors": 5,
                    "twitter_errors": 10,
                    "twitter_scrapes": 120,
                    "web_errors": 7,
                    "web_success": 93,
                },
                "worker2": {
                    "twitter_ratelimit_errors": 8,
                    "twitter_returned_other": 12,
                    "twitter_returned_profiles": 50,
                    "twitter_returned_tweets": 200,
                    "twitter_scrapes": 250,
                },
            }
        }

        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        self.assertEqual(result["twitter_auth_errors"], 5)
        self.assertEqual(result["twitter_errors"], 10)
        self.assertEqual(result["twitter_ratelimit_errors"], 8)
        self.assertEqual(result["twitter_returned_other"], 12)
        self.assertEqual(result["twitter_returned_profiles"], 50)
        self.assertEqual(result["twitter_returned_tweets"], 200)
        self.assertEqual(result["twitter_scrapes"], 370)  # 120 + 250
        self.assertEqual(result["web_errors"], 7)
        self.assertEqual(result["web_success"], 93)

    def test_aggregate_telemetry_stats_missing_stats(self):
        """Test aggregation with missing stats in the telemetry result."""
        telemetry_result = {"other_field": "value"}
        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # All stats should be 0
        for value in result.values():
            self.assertEqual(value, 0)

    def test_aggregate_telemetry_stats_partial_fields(self):
        """Test aggregation with partial fields in worker stats."""
        telemetry_result = {
            "stats": {
                "worker1": {
                    "twitter_auth_errors": 5,
                    # Missing other fields
                },
                "worker2": {
                    # Only has web stats
                    "web_errors": 3,
                    "web_success": 97,
                },
            }
        }

        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        self.assertEqual(result["twitter_auth_errors"], 5)
        self.assertEqual(result["twitter_errors"], 0)  # Default value
        self.assertEqual(result["twitter_ratelimit_errors"], 0)  # Default value
        self.assertEqual(result["web_errors"], 3)
        self.assertEqual(result["web_success"], 97)

    def test_aggregate_telemetry_stats_old_format(self):
        """Test aggregation with the old format (stats not inside worker IDs)."""
        # In the old format, stats were directly in the stats object,
        # not nested inside worker IDs
        telemetry_result = {
            "stats": {
                "twitter_auth_errors": 5,
                "twitter_errors": 10,
                "twitter_ratelimit_errors": 2,
                "twitter_returned_other": 3,
                "twitter_returned_profiles": 20,
                "twitter_returned_tweets": 100,
                "twitter_scrapes": 120,
                "web_errors": 7,
                "web_success": 93,
            }
        }

        result = self.scorer.aggregate_telemetry_stats(telemetry_result)

        # Values should now match since we've updated the implementation
        # to handle the old format
        self.assertEqual(result["twitter_auth_errors"], 5)
        self.assertEqual(result["twitter_errors"], 10)
        self.assertEqual(result["twitter_ratelimit_errors"], 2)
        self.assertEqual(result["twitter_returned_other"], 3)
        self.assertEqual(result["twitter_returned_profiles"], 20)
        self.assertEqual(result["twitter_returned_tweets"], 100)
        self.assertEqual(result["twitter_scrapes"], 120)
        self.assertEqual(result["web_errors"], 7)
        self.assertEqual(result["web_success"], 93)


if __name__ == "__main__":
    unittest.main()
