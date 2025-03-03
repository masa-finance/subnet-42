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

    def get_node_data(self):
        """
        Retrieve node data. Currently returns a stub list of NodeData objects.
        In the future, this method should fetch data from an external service.

        :return: A list of NodeData objects containing node information.
        """
        self.validator.metagraph.sync_nodes()
        return self.validator.metagraph.nodes
