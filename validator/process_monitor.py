import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessMetrics:
    """Metrics for a single process execution"""

    start_time: str
    end_time: str
    duration_seconds: float
    nodes_processed: int
    successful_nodes: int
    failed_nodes: int
    errors: List[str]
    additional_metrics: Dict[str, Any]


class ProcessMonitor:
    """Monitor process performance and store historical data in memory"""

    def __init__(self, max_records_per_process: int = 100):
        """
        Initialize the process monitor

        Args:
            max_records_per_process: Maximum number of records to keep per process
        """
        self.max_records = max_records_per_process
        self.process_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_records)
        )
        self.current_executions: Dict[str, Dict[str, Any]] = {}

    def start_process(self, process_name: str) -> str:
        """
        Start tracking a process execution

        Args:
            process_name: Name of the process being tracked

        Returns:
            execution_id: Unique identifier for this execution
        """
        execution_id = f"{process_name}_{int(time.time() * 1000)}"
        start_time = datetime.now()

        self.current_executions[execution_id] = {
            "process_name": process_name,
            "start_time": start_time,
            "nodes_processed": 0,
            "successful_nodes": 0,
            "failed_nodes": 0,
            "errors": [],
            "additional_metrics": {},
        }

        logger.debug(f"Started tracking process: {process_name} ({execution_id})")
        return execution_id

    def update_metrics(self, execution_id: str, **kwargs):
        """
        Update metrics for a running process

        Args:
            execution_id: The execution ID returned by start_process
            **kwargs: Metrics to update (nodes_processed, successful_nodes, etc.)
        """
        if execution_id in self.current_executions:
            for key, value in kwargs.items():
                if key == "errors" and isinstance(value, list):
                    self.current_executions[execution_id]["errors"].extend(value)
                elif key == "additional_metrics" and isinstance(value, dict):
                    self.current_executions[execution_id]["additional_metrics"].update(
                        value
                    )
                else:
                    self.current_executions[execution_id][key] = value

    def end_process(self, execution_id: str) -> Optional[ProcessMetrics]:
        """
        End tracking a process execution and store the metrics

        Args:
            execution_id: The execution ID returned by start_process

        Returns:
            ProcessMetrics: The final metrics for this execution
        """
        if execution_id not in self.current_executions:
            logger.warning(f"Execution ID {execution_id} not found")
            return None

        execution = self.current_executions.pop(execution_id)
        end_time = datetime.now()
        duration = (end_time - execution["start_time"]).total_seconds()

        metrics = ProcessMetrics(
            start_time=execution["start_time"].isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            nodes_processed=execution["nodes_processed"],
            successful_nodes=execution["successful_nodes"],
            failed_nodes=execution["failed_nodes"],
            errors=execution["errors"],
            additional_metrics=execution["additional_metrics"],
        )

        # Store in history
        process_name = execution["process_name"]
        self.process_history[process_name].append(metrics)

        logger.debug(
            f"Completed tracking process: {process_name} "
            f"(duration: {duration:.2f}s, nodes: {metrics.nodes_processed})"
        )

        return metrics

    def get_process_statistics(self, process_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific process

        Args:
            process_name: Name of the process

        Returns:
            Dictionary with process statistics
        """
        if process_name not in self.process_history:
            return {
                "process_name": process_name,
                "total_executions": 0,
                "statistics": {},
            }

        history = list(self.process_history[process_name])
        if not history:
            return {
                "process_name": process_name,
                "total_executions": 0,
                "statistics": {},
            }

        durations = [m.duration_seconds for m in history]
        nodes_processed = [m.nodes_processed for m in history]
        successful_nodes = [m.successful_nodes for m in history]

        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        avg_nodes = (
            sum(nodes_processed) / len(nodes_processed) if nodes_processed else 0
        )
        total_nodes = sum(nodes_processed)
        total_successful = sum(successful_nodes)

        # Recent performance (last 10 executions)
        recent_history = history[-10:]
        recent_durations = [m.duration_seconds for m in recent_history]
        recent_avg_duration = (
            sum(recent_durations) / len(recent_durations) if recent_durations else 0
        )

        return {
            "process_name": process_name,
            "total_executions": len(history),
            "statistics": {
                "duration": {
                    "average_seconds": round(avg_duration, 2),
                    "min_seconds": round(min_duration, 2),
                    "max_seconds": round(max_duration, 2),
                    "recent_average_seconds": round(recent_avg_duration, 2),
                },
                "nodes": {
                    "average_per_execution": round(avg_nodes, 2),
                    "total_processed": total_nodes,
                    "total_successful": total_successful,
                    "success_rate": (
                        round(total_successful / total_nodes * 100, 2)
                        if total_nodes > 0
                        else 0
                    ),
                },
            },
            "recent_executions": [asdict(m) for m in recent_history],
            "last_execution": asdict(history[-1]) if history else None,
        }

    def get_all_processes_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all monitored processes

        Returns:
            Dictionary with all process statistics
        """
        return {
            "monitoring_status": {
                "active_executions": len(self.current_executions),
                "monitored_processes": list(self.process_history.keys()),
                "max_records_per_process": self.max_records,
                "timestamp": datetime.now().isoformat(),
            },
            "processes": {
                process_name: self.get_process_statistics(process_name)
                for process_name in self.process_history.keys()
            },
        }

    def cleanup_old_records(self, hours: int = 24):
        """
        Clean up records older than specified hours

        Args:
            hours: Number of hours to retain records
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for process_name, history in self.process_history.items():
            original_length = len(history)
            # Filter out old records
            filtered_history = deque(
                [
                    m
                    for m in history
                    if datetime.fromisoformat(m.start_time) > cutoff_time
                ],
                maxlen=self.max_records,
            )
            self.process_history[process_name] = filtered_history

            removed_count = original_length - len(filtered_history)
            if removed_count > 0:
                logger.debug(
                    f"Cleaned up {removed_count} old records for {process_name}"
                )
