import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from validator.process_monitor import ProcessMonitor
from validator.nats import MinersNATSPublisher
from validator.weights import WeightsManager


class TestProcessMonitoring:
    """Test the process monitoring functionality for NATS and weights"""

    def test_process_monitor_basic_functionality(self):
        """Test that the process monitor works correctly"""
        monitor = ProcessMonitor()

        # Start a process
        execution_id = monitor.start_process("test_process")
        assert execution_id is not None
        assert "test_process" in execution_id

        # Update metrics
        monitor.update_metrics(
            execution_id,
            nodes_processed=5,
            successful_nodes=4,
            failed_nodes=1,
            additional_metrics={"test_data": "test_value"},
        )

        # End process
        result = monitor.end_process(execution_id)
        assert result is not None
        assert result.nodes_processed == 5
        assert result.successful_nodes == 4
        assert result.failed_nodes == 1
        assert result.additional_metrics["test_data"] == "test_value"

        # Check statistics
        stats = monitor.get_process_statistics("test_process")
        assert stats["total_executions"] == 1
        assert len(stats["recent_executions"]) == 1

    @pytest.mark.asyncio
    async def test_nats_monitoring_integration(self):
        """Test NATS publishing with monitoring"""
        # Mock validator
        mock_validator = Mock()
        mock_validator.routing_table_updating = False
        mock_validator.routing_table.get_all_addresses_atomic.return_value = [
            "192.168.1.1",
            "192.168.1.2",
            "192.168.1.3",
        ]

        # Mock background tasks with process monitor
        mock_background_tasks = Mock()
        mock_process_monitor = ProcessMonitor()
        mock_background_tasks.process_monitor = mock_process_monitor
        mock_validator.background_tasks = mock_background_tasks

        # Create NATS publisher
        nats_publisher = MinersNATSPublisher(mock_validator)

        # Mock the NATS client
        with patch.object(
            nats_publisher.nc, "send_connected_nodes", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = None

            # Execute the method
            await nats_publisher.send_connected_nodes()

            # Verify NATS was called
            mock_send.assert_called_once_with(
                ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
            )

            # Check monitoring data
            stats = mock_process_monitor.get_process_statistics("send_connected_nodes")
            assert stats["total_executions"] == 1
            assert len(stats["recent_executions"]) == 1

            # Check the recorded data
            execution = stats["recent_executions"][0]
            assert execution["nodes_processed"] == 3
            assert execution["successful_nodes"] == 3
            assert execution["failed_nodes"] == 0
            assert "addresses" in execution["additional_metrics"]
            assert len(execution["additional_metrics"]["addresses"]) == 3

    @pytest.mark.asyncio
    async def test_nats_monitoring_empty_addresses(self):
        """Test NATS monitoring when no addresses are available"""
        # Mock validator with empty addresses
        mock_validator = Mock()
        mock_validator.routing_table_updating = False
        mock_validator.routing_table.get_all_addresses_atomic.return_value = []

        # Mock background tasks with process monitor
        mock_background_tasks = Mock()
        mock_process_monitor = ProcessMonitor()
        mock_background_tasks.process_monitor = mock_process_monitor
        mock_validator.background_tasks = mock_background_tasks

        # Create NATS publisher
        nats_publisher = MinersNATSPublisher(mock_validator)

        # Execute the method
        await nats_publisher.send_connected_nodes()

        # Check monitoring data
        stats = mock_process_monitor.get_process_statistics("send_connected_nodes")
        assert stats["total_executions"] == 1

        # Check the recorded data shows it was skipped
        execution = stats["recent_executions"][0]
        assert execution["nodes_processed"] == 0
        assert execution["additional_metrics"]["skipped"] is True
        assert execution["additional_metrics"]["reason"] == "no_addresses"

    def test_weights_monitoring_structure(self):
        """Test that weights monitoring structure is correct"""
        # Mock validator for weights manager
        mock_validator = Mock()
        mock_validator.substrate = Mock()
        mock_validator.metagraph = Mock()
        mock_validator.keypair = Mock()
        mock_validator.netuid = 42
        mock_validator.telemetry_storage = Mock()

        # Mock background tasks with process monitor
        mock_background_tasks = Mock()
        mock_process_monitor = ProcessMonitor()
        mock_background_tasks.process_monitor = mock_process_monitor
        mock_validator.background_tasks = mock_background_tasks

        # Create weights manager
        weights_manager = WeightsManager(mock_validator)

        # Verify the structure is set up correctly
        assert hasattr(mock_validator, "background_tasks")
        assert hasattr(mock_validator.background_tasks, "process_monitor")
        assert isinstance(
            mock_validator.background_tasks.process_monitor, ProcessMonitor
        )


if __name__ == "__main__":
    pytest.main([__file__])
