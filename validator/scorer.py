from interfaces.types import NodeData
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurons.validator import Validator


class NodeDataScorer:
    def __init__(self, validator: "Validator"):
        """
        Initialize the NodeDataScorer with a validator instance and a stub for node data.

        :param validator: The validator instance to be used for scoring node data.
        """
        self.validator = validator
        # This can be replaced with a service client or API call in the future
        self.node_data_stub = [
            NodeData(
                hotkey=self.validator.metagraph.nodes[0].hotkey,
                posts=10,
                uptime=100,
                latency=0.6,
            ),
            NodeData(
                hotkey=self.validator.metagraph.nodes[1].hotkey,
                posts=500,
                uptime=200,
                latency=0.5,
            ),
        ]

    def get_node_data(self):
        """
        Retrieve node data. Currently returns a stub list of NodeData objects.
        In the future, this method should fetch data from an external service.

        :return: A list of NodeData objects containing node information.
        """
        return self.node_data_stub


# # Example usage
# if __name__ == "__main__":
#     scorer = NodeDataScorer()
#     node_data = scorer.get_node_data()
#     for node in node_data:
#         print(
#             f"Node {node.hotkey}: Posts={node.posts}, Uptime={node.uptime}, Latency={node.latency}"
#         )
