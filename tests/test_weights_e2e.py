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
        NodeData(hotkey="node1", posts=10, uptime=100, latency=50),
        NodeData(hotkey="node2", posts=20, uptime=200, latency=30),
    ]

    # Calculate weights
    uids, weights = weights_manager.calculate_weights(node_data)
    assert len(uids) == len(weights) > 0, "Weights should be calculated for nodes"

    # Set weights
    await weights_manager.set_weights(node_data)
    
    # Here you would verify the weights were set correctly, possibly by querying the substrate
