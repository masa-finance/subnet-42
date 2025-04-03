import pytest
from neurons.validator import Validator
from validator.weights import WeightsManager
from interfaces.types import NodeData


@pytest.mark.asyncio
async def test_weights_e2e():
    # Initialize a real Validator instance
    validator = Validator()
    weights_manager = WeightsManager(validator=validator)

    # Simulate node data
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

    # Calculate weights
    uids, weights = weights_manager.calculate_weights(node_data)
    assert len(uids) == len(weights) > 0, "Weights should be calculated for nodes"

    # Set weights
    await weights_manager.set_weights(node_data)

    # Here you would verify the weights were set correctly, possibly by querying the substrate
