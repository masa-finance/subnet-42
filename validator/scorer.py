from interfaces.types import NodeData
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurons.validator import Validator


class NodeDataScorer:
    def __init__(self, validator: "Validator"):
        self.validator = validator
        # This can be replaced with a service client or API call in the future
        self.node_data_stub = [
            NodeData(hotkey="node1", posts=10, uptime=100, latency=50),
            NodeData(hotkey="node2", posts=20, uptime=200, latency=30),
        ]

    def get_node_data(self):
        # In the future, replace this with a call to fetch data from an external service
        return self.node_data_stub


# Example usage
if __name__ == "__main__":
    scorer = NodeDataScorer()
    node_data = scorer.get_node_data()
    for node in node_data:
        print(
            f"Node {node.hotkey}: Posts={node.posts}, Uptime={node.uptime}, Latency={node.latency}"
        )
