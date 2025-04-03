import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from validator.weights import WeightsManager
from interfaces.types import NodeData


@pytest.fixture
def mock_validator():
    # Create a mock Validator instance
    mock_validator = MagicMock()
    mock_validator.metagraph = MagicMock()
    mock_validator.substrate = MagicMock()
    mock_validator.keypair = MagicMock()
    return mock_validator


@pytest.fixture
def weights_manager(mock_validator):
    # Create a WeightsManager instance with the mock validator
    return WeightsManager(validator=mock_validator)


def test_calculate_weights(weights_manager):
    # Test calculate_weights method
    node_data = [
        NodeData(
            hotkey="node1",
            worker_id="worker1",
            uid=1,
            boot_time=0,
            last_operation_time=0,
            current_time=0,
            twitter_auth_errors=0,
            twitter_errors=0,
            twitter_ratelimit_errors=0,
            twitter_returned_other=0,
            twitter_returned_profiles=0,
            twitter_returned_tweets=0,
            twitter_scrapes=0,
            web_errors=0,
            web_success=10,
            timestamp=0,
        ),
        NodeData(
            hotkey="node2",
            worker_id="worker2",
            uid=2,
            boot_time=0,
            last_operation_time=0,
            current_time=0,
            twitter_auth_errors=0,
            twitter_errors=0,
            twitter_ratelimit_errors=0,
            twitter_returned_other=0,
            twitter_returned_profiles=0,
            twitter_returned_tweets=20,
            twitter_scrapes=0,
            web_errors=0,
            web_success=20,
            timestamp=0,
        ),
    ]
    uids, weights = weights_manager.calculate_weights(node_data)
    assert len(uids) == len(weights) == 2
    assert weights[0] < weights[1]  # Assuming node2 has more activity


@pytest.mark.asyncio
async def test_set_weights(weights_manager, mock_validator):
    # Mock the async method and dependencies
    mock_validator.substrate.query = MagicMock(return_value=MagicMock(value=1))
    mock_validator.metagraph.nodes = {
        "node1": MagicMock(node_id=1),
        "node2": MagicMock(node_id=2),
    }
    with patch(
        "validator.weights.weights.set_node_weights", return_value=True
    ) as mock_set_node_weights:
        await weights_manager.set_weights([])
        mock_set_node_weights.assert_called_once()
