import unittest
from unittest.mock import Mock
from validator.weights import WeightsManager
from interfaces.types import NodeData


class TestGetDeltaNodeData(unittest.TestCase):

    def setUp(self):
        # Create mock validator
        self.mock_validator = Mock()

        # Mock telemetry storage
        self.mock_telemetry_storage = Mock()
        self.mock_validator.telemetry_storage = self.mock_telemetry_storage

        # Mock metagraph
        self.mock_metagraph = Mock()
        self.mock_validator.metagraph = self.mock_metagraph

        # Create WeightsManager with mock validator
        self.weights_manager = WeightsManager(self.mock_validator)

        # Create sample hotkeys
        self.hotkeys = ["hotkey1", "hotkey2", "hotkey3"]

        # Setup metagraph nodes mock
        self.metagraph_nodes = {}
        for idx, hotkey in enumerate(self.hotkeys):
            node_mock = Mock()
            node_mock.hotkey = hotkey
            node_mock.node_id = idx + 1
            self.metagraph_nodes[hotkey] = node_mock

        self.mock_metagraph.nodes = self.metagraph_nodes

        # Mock telemetry_storage.get_all_hotkeys_with_telemetry()
        self.mock_telemetry_storage.get_all_hotkeys_with_telemetry.return_value = (
            self.hotkeys[:2]
        )  # Only first two have telemetry

    def create_telemetry_data(
        self,
        hotkey,
        timestamps,
        boots,
        operations,
        twitter_scrapes,
        twitter_tweets,
        twitter_profiles,
        web_success,
        worker_id="worker_123",
    ):
        """Helper method to create telemetry data for testing."""
        data = []
        for i, timestamp in enumerate(timestamps):
            node_data = NodeData(
                hotkey=hotkey,
                uid=self.metagraph_nodes[hotkey].node_id,
                worker_id=worker_id,
                timestamp=timestamp,
                boot_time=boots[i],
                last_operation_time=operations[i],
                current_time=timestamp,
                twitter_auth_errors=i,
                twitter_errors=i,
                twitter_ratelimit_errors=i,
                twitter_returned_other=i,
                twitter_returned_profiles=twitter_profiles[i],
                twitter_returned_tweets=twitter_tweets[i],
                twitter_scrapes=twitter_scrapes[i],
                web_errors=i,
                web_success=web_success[i],
            )
            data.append(node_data)
        return data

    def test_no_telemetry_data(self):
        """Test when no telemetry data is available for any node."""
        # Mock empty telemetry data
        self.mock_telemetry_storage.get_all_hotkeys_with_telemetry.return_value = []

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Verify results - should get empty values for all nodes in metagraph
        self.assertEqual(len(result), len(self.hotkeys))
        for node_data in result:
            self.assertEqual(node_data.twitter_scrapes, 0)
            self.assertEqual(node_data.web_success, 0)
            self.assertEqual(node_data.twitter_returned_tweets, 0)

    def test_insufficient_telemetry_data(self):
        """Test when there's only one telemetry record (not enough to calculate deltas)."""
        # Mock only one telemetry record for hotkey1
        hotkey1_data = self.create_telemetry_data(
            "hotkey1",
            [1000],  # Only one timestamp
            [100],  # Boot time
            [200],  # Operation time
            [50],  # Twitter scrapes
            [30],  # Twitter tweets
            [20],  # Twitter profiles
            [40],  # Web success
        )

        self.mock_telemetry_storage.get_telemetry_by_hotkey.side_effect = (
            lambda hotkey: (hotkey1_data if hotkey == "hotkey1" else [])
        )

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Find hotkey1 result
        hotkey1_result = next(data for data in result if data.hotkey == "hotkey1")

        # Verify results - should have zeros for all metrics since only one record
        self.assertEqual(hotkey1_result.twitter_scrapes, 0)
        self.assertEqual(hotkey1_result.web_success, 0)
        self.assertEqual(hotkey1_result.twitter_returned_tweets, 0)

    def test_normal_delta_calculation(self):
        """Test normal delta calculation without any resets."""
        # Create telemetry data with normal progression (no resets)
        hotkey1_data = self.create_telemetry_data(
            "hotkey1",
            [1000, 2000, 3000],  # Timestamps
            [100, 100, 100],  # Same boot time (no restart)
            [200, 300, 400],  # Incrementing operation time
            [50, 70, 100],  # Incrementing Twitter scrapes
            [30, 45, 60],  # Incrementing Twitter tweets
            [20, 25, 35],  # Incrementing Twitter profiles
            [40, 60, 80],  # Incrementing Web success
        )

        self.mock_telemetry_storage.get_telemetry_by_hotkey.side_effect = (
            lambda hotkey: (hotkey1_data if hotkey == "hotkey1" else [])
        )

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Find hotkey1 result
        hotkey1_result = next(data for data in result if data.hotkey == "hotkey1")

        # Verify results - should be deltas between last and first record
        self.assertEqual(hotkey1_result.boot_time, 0)  # Not used in simple mode
        self.assertEqual(
            hotkey1_result.last_operation_time, 0
        )  # Not used in simple mode
        self.assertEqual(hotkey1_result.twitter_scrapes, 50)  # 100 - 50
        self.assertEqual(hotkey1_result.twitter_returned_tweets, 30)  # 60 - 30
        self.assertEqual(hotkey1_result.twitter_returned_profiles, 15)  # 35 - 20
        self.assertEqual(hotkey1_result.web_success, 40)  # 80 - 40

    def test_one_reset(self):
        """Test handling of one reset when twitter_returned_tweets decreases."""
        # Create telemetry data with one reset (twitter_returned_tweets decreases)
        hotkey1_data = self.create_telemetry_data(
            "hotkey1",
            [1000, 2000, 3000, 4000],  # Timestamps
            [100, 100, 200, 200],  # Boot time changes at index 2 (restart)
            [200, 300, 100, 200],  # Operation time resets at restart
            [50, 70, 10, 30],  # Twitter scrapes reset at restart
            [30, 45, 5, 15],  # Twitter tweets reset at restart (45 -> 5)
            [20, 25, 5, 10],  # Twitter profiles reset at restart
            [40, 60, 10, 30],  # Web success reset at restart
        )

        self.mock_telemetry_storage.get_telemetry_by_hotkey.side_effect = (
            lambda hotkey: (hotkey1_data if hotkey == "hotkey1" else [])
        )

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Find hotkey1 result
        hotkey1_result = next(data for data in result if data.hotkey == "hotkey1")

        # Verify results - baseline resets at index 2 (timestamp 3000) when tweets go from 45 to 5
        # Delta calculated from baseline (index 2) to latest (index 3):
        # tweets: 15 - 5 = 10, profiles: 10 - 5 = 5, scrapes: 30 - 10 = 20, web: 30 - 10 = 20
        self.assertEqual(hotkey1_result.boot_time, 0)  # Not used in simple mode
        self.assertEqual(
            hotkey1_result.last_operation_time, 0
        )  # Not used in simple mode
        self.assertEqual(hotkey1_result.twitter_scrapes, 20)  # 30 - 10
        self.assertEqual(hotkey1_result.twitter_returned_tweets, 10)  # 15 - 5
        self.assertEqual(hotkey1_result.twitter_returned_profiles, 5)  # 10 - 5
        self.assertEqual(hotkey1_result.web_success, 20)  # 30 - 10

    def test_multiple_resets(self):
        """Test handling of multiple resets when twitter_returned_tweets decreases multiple times."""
        # Create telemetry data with multiple resets
        hotkey1_data = self.create_telemetry_data(
            "hotkey1",
            [1000, 2000, 3000, 4000, 5000, 6000],  # Timestamps
            [100, 100, 200, 200, 300, 300],  # Boot time changes twice
            [200, 300, 100, 200, 100, 200],  # Operation time resets at each restart
            [50, 70, 10, 30, 5, 25],  # Twitter scrapes resets
            [30, 45, 5, 15, 2, 12],  # Twitter tweets resets (45->5, then 15->2)
            [20, 25, 5, 10, 2, 7],  # Twitter profiles resets
            [40, 60, 10, 30, 5, 25],  # Web success resets
        )

        self.mock_telemetry_storage.get_telemetry_by_hotkey.side_effect = (
            lambda hotkey: (hotkey1_data if hotkey == "hotkey1" else [])
        )

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Find hotkey1 result
        hotkey1_result = next(data for data in result if data.hotkey == "hotkey1")

        # Verify results - baseline resets twice:
        # 1st reset at index 2 (timestamp 3000) when tweets go from 45 to 5
        # 2nd reset at index 4 (timestamp 5000) when tweets go from 15 to 2
        # Final baseline is index 4, delta calculated from there to latest (index 5):
        # tweets: 12 - 2 = 10, profiles: 7 - 2 = 5, scrapes: 25 - 5 = 20, web: 25 - 5 = 20
        self.assertEqual(hotkey1_result.boot_time, 0)  # Not used in simple mode
        self.assertEqual(
            hotkey1_result.last_operation_time, 0
        )  # Not used in simple mode
        self.assertEqual(hotkey1_result.twitter_scrapes, 20)  # 25 - 5
        self.assertEqual(hotkey1_result.twitter_returned_tweets, 10)  # 12 - 2
        self.assertEqual(hotkey1_result.twitter_returned_profiles, 5)  # 7 - 2
        self.assertEqual(hotkey1_result.web_success, 20)  # 25 - 5

    def test_multiple_hotkeys(self):
        """Test handling multiple hotkeys with different telemetry patterns."""
        # Create telemetry for hotkey1 (normal progression)
        hotkey1_data = self.create_telemetry_data(
            "hotkey1",
            [1000, 2000, 3000],  # Timestamps
            [100, 100, 100],  # Same boot time (no restart)
            [200, 300, 400],  # Incrementing operation time
            [50, 70, 100],  # Incrementing Twitter scrapes
            [30, 45, 60],  # Incrementing Twitter tweets
            [20, 25, 35],  # Incrementing Twitter profiles
            [40, 60, 80],  # Incrementing Web success
        )

        # Create telemetry for hotkey2 (with restart)
        hotkey2_data = self.create_telemetry_data(
            "hotkey2",
            [1000, 2000, 3000, 4000],  # Timestamps
            [100, 100, 200, 200],  # Boot time changes at index 2 (restart)
            [200, 300, 100, 200],  # Operation time resets at restart
            [50, 70, 10, 30],  # Twitter scrapes reset at restart
            [30, 45, 5, 15],  # Twitter tweets reset at restart
            [20, 25, 5, 10],  # Twitter profiles reset at restart
            [40, 60, 10, 30],  # Web success reset at restart
            "worker_456",  # Different worker ID
        )

        self.mock_telemetry_storage.get_telemetry_by_hotkey.side_effect = (
            lambda hotkey: (
                hotkey1_data
                if hotkey == "hotkey1"
                else hotkey2_data if hotkey == "hotkey2" else []
            )
        )

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Find results for each hotkey
        hotkey1_result = next(data for data in result if data.hotkey == "hotkey1")
        hotkey2_result = next(data for data in result if data.hotkey == "hotkey2")

        # Verify hotkey1 results (no reset)
        self.assertEqual(hotkey1_result.boot_time, 0)
        self.assertEqual(
            hotkey1_result.last_operation_time, 0
        )  # Not used in simple mode
        self.assertEqual(hotkey1_result.twitter_scrapes, 50)
        self.assertEqual(hotkey1_result.web_success, 40)

        # Verify hotkey2 results (with reset at index 2 when tweets go from 45 to 5)
        # Delta from baseline (index 2) to latest (index 3): tweets=10, scrapes=20, web=20
        self.assertEqual(hotkey2_result.boot_time, 0)
        self.assertEqual(
            hotkey2_result.last_operation_time, 0
        )  # Not used in simple mode
        self.assertEqual(hotkey2_result.twitter_scrapes, 20)  # 30 - 10
        self.assertEqual(hotkey2_result.web_success, 20)  # 30 - 10
        self.assertEqual(hotkey2_result.worker_id, "worker_456")

        # Verify hotkey3 is also in results (but with zero data)
        hotkey3_result = next(data for data in result if data.hotkey == "hotkey3")
        self.assertEqual(hotkey3_result.twitter_scrapes, 0)
        self.assertEqual(hotkey3_result.web_success, 0)

    def test_no_reset_with_steady_increase(self):
        """Test handling when twitter_returned_tweets only increases (no reset)."""
        # Create telemetry data where twitter_returned_tweets only increases
        hotkey1_data = self.create_telemetry_data(
            "hotkey1",
            [1000, 2000, 3000, 4000],  # Timestamps
            [100, 100, 100, 100],  # Same boot time (no restart)
            [200, 300, 400, 500],  # Incrementing operation time
            [50, 70, 60, 90],  # Twitter scrapes dips at index 2
            [30, 45, 60, 75],  # Twitter tweets steady increase (no reset)
            [20, 25, 35, 45],  # Twitter profiles steady increase
            [40, 60, 80, 100],  # Web success steady increase
        )

        self.mock_telemetry_storage.get_telemetry_by_hotkey.side_effect = (
            lambda hotkey: (hotkey1_data if hotkey == "hotkey1" else [])
        )

        # Call the method
        result = self.weights_manager._get_delta_node_data()

        # Find hotkey1 result
        hotkey1_result = next(data for data in result if data.hotkey == "hotkey1")

        # Since twitter_returned_tweets never decreases, no reset occurs
        # Delta calculated from first record to last record:
        # tweets: 75 - 30 = 45, profiles: 45 - 20 = 25, scrapes: 90 - 50 = 40, web: 100 - 40 = 60
        self.assertEqual(hotkey1_result.boot_time, 0)  # Not used in simple mode
        self.assertEqual(
            hotkey1_result.last_operation_time, 0
        )  # Not used in simple mode
        self.assertEqual(hotkey1_result.twitter_scrapes, 40)  # 90 - 50
        self.assertEqual(hotkey1_result.twitter_returned_tweets, 45)  # 75 - 30
        self.assertEqual(hotkey1_result.twitter_returned_profiles, 25)  # 45 - 20
        self.assertEqual(hotkey1_result.web_success, 60)  # 100 - 40


if __name__ == "__main__":
    unittest.main()
