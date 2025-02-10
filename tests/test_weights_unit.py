import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from validator.metagraph import MetagraphManager
from neurons.validator import Validator


@pytest.fixture
def mock_validator():
    # Create a mock Validator instance
    mock_validator = MagicMock(spec=Validator)
    mock_validator.metagraph = MagicMock()
    mock_validator.substrate = MagicMock()
    mock_validator.node_manager = MagicMock()
    mock_validator.substrate.url = "wss://test.finney.opentensor.ai:443"
    return mock_validator


@pytest.fixture
def metagraph_manager(mock_validator):
    # Create a MetagraphManager instance with the mock validator
    return MetagraphManager(validator=mock_validator)


def test_sync_substrate(mock_validator, metagraph_manager):
    # Test sync_substrate method
    metagraph_manager.sync_substrate()
    mock_validator.substrate = mock_validator.substrate  # Ensure substrate is set


@pytest.mark.asyncio
async def test_sync_metagraph(mock_validator, metagraph_manager):
    # Mock the async method remove_disconnected_nodes
    mock_validator.node_manager.remove_disconnected_nodes = AsyncMock()

    # Test sync_metagraph method
    await metagraph_manager.sync_metagraph()
    mock_validator.metagraph.sync_nodes.assert_called_once()
    mock_validator.node_manager.remove_disconnected_nodes.assert_awaited_once()
