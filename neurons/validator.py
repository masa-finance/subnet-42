from dotenv import load_dotenv

import os
import asyncio
import uvicorn
from typing import Optional, Any, List

from fiber.chain import chain_utils, interface
from fiber.chain.metagraph import Metagraph
from fiber.miner.server import factory_app
from fiber.networking.models import NodeWithFernet as Node
from fiber.logging_utils import get_logger

from fastapi import FastAPI

from validator.config import Config
from validator.http_client import HttpClientManager
from validator.background_tasks import BackgroundTasks
from validator.api_routes import register_routes
from validator.network_operations import (
    make_non_streamed_get,
    make_non_streamed_post,
)
from validator.metagraph import MetagraphManager
from validator.node_manager import NodeManager
from validator.nats import MinersNATSPublisher
from validator.weights import WeightsManager
from validator.scorer import NodeDataScorer

logger = get_logger(__name__)

BLOCKS_PER_WEIGHT_SETTING = 100
BLOCK_TIME_SECONDS = 12
TIME_PER_WEIGHT_SETTING = BLOCKS_PER_WEIGHT_SETTING * BLOCK_TIME_SECONDS
WEIGHTS_LOOP_CADENCE_SECONDS = (
    TIME_PER_WEIGHT_SETTING / 2
)  # half of a weight setting period

SYNC_LOOP_CADENCE_SECONDS = 10


class Validator:
    def __init__(self):
        """Initialize validator"""
        load_dotenv()

        self.config = Config()
        self.http_client_manager = HttpClientManager()

        self.keypair = chain_utils.load_hotkey_keypair(
            self.config.VALIDATOR_WALLET_NAME, self.config.VALIDATOR_HOTKEY_NAME
        )

        self.netuid = int(os.getenv("NETUID", "42"))

        self.subtensor_network = os.getenv("SUBTENSOR_NETWORK", "finney")
        self.subtensor_address = os.getenv(
            "SUBTENSOR_ADDRESS", "wss://entrypoint-finney.opentensor.ai:443"
        )

        self.server: Optional[factory_app] = None
        self.app: Optional[FastAPI] = None

        self.substrate = interface.get_substrate(
            subtensor_network=self.config.SUBTENSOR_NETWORK,
            subtensor_address=self.config.SUBTENSOR_ADDRESS,
        )

        self.metagraph = Metagraph(netuid=self.config.NETUID, substrate=self.substrate)
        self.metagraph.sync_nodes()

        self.node_manager = NodeManager(validator=self)
        self.scorer = NodeDataScorer(validator=self)
        self.weights_manager = WeightsManager(validator=self)
        self.background_tasks = BackgroundTasks(validator=self)
        self.metagraph_manager = MetagraphManager(validator=self)
        self.NATSPublisher = MinersNATSPublisher(
            validator=self
        )  # Not used yet (Depends on Nats on TEE side)

    async def start(self) -> None:
        """Start the validator service"""
        try:
            await self.http_client_manager.start()
            self.app = factory_app(debug=False)
            register_routes(self.app, self.healthcheck)

            # Start background tasks

            asyncio.create_task(
                self.background_tasks.sync_loop(SYNC_LOOP_CADENCE_SECONDS)
            )
            asyncio.create_task(
                self.background_tasks.set_weights_loop(WEIGHTS_LOOP_CADENCE_SECONDS)
            )

            # asyncio.create_task(self.background_tasks.update_tee(10)) not doing this yet

            config = uvicorn.Config(
                self.app, host="0.0.0.0", port=self.config.VALIDATOR_PORT, lifespan="on"
            )
            server = uvicorn.Server(config)
            await server.serve()

        except Exception as e:
            logger.error(f"Failed to start validator: {str(e)}")
            raise

    def node(self) -> Optional[Node]:
        try:
            nodes = self.metagraph.nodes
            node = nodes[self.keypair.ss58_address]
            return node
        except Exception as e:
            logger.error(f"Failed to get node from metagraph: {e}")
            return None

    async def make_non_streamed_get(self, node: Node, endpoint: str) -> Optional[Any]:
        return await make_non_streamed_get(
            httpx_client=self.http_client_manager.client,
            node=node,
            endpoint=endpoint,
            connected_nodes=self.node_manager.connected_nodes,
            validator_ss58_address=self.keypair.ss58_address,
        )

    async def make_non_streamed_post(
        self, node: Node, endpoint: str, payload: Any
    ) -> Optional[Any]:
        return await make_non_streamed_post(
            httpx_client=self.http_client_manager.client,
            node=node,
            endpoint=endpoint,
            payload=payload,
            connected_nodes=self.node_manager.connected_nodes,
            validator_ss58_address=self.keypair.ss58_address,
            keypair=self.keypair,
        )

    async def stop(self) -> None:
        """Cleanup validator resources and shutdown gracefully.

        Closes:
        - HTTP client connections
        - Server instances
        """
        await self.http_client_manager.stop()
        if self.server:
            await self.server.stop()

    def healthcheck(self):
        try:
            info = {
                "ss58_address": str(self.keypair.ss58_address),
                "uid": str(self.metagraph.nodes[self.keypair.ss58_address].node_id),
                "ip": str(self.metagraph.nodes[self.keypair.ss58_address].ip),
                "port": str(self.metagraph.nodes[self.keypair.ss58_address].port),
                "netuid": str(self.config.NETUID),
                "subtensor_network": str(self.config.SUBTENSOR_NETWORK),
                "subtensor_address": str(self.config.SUBTENSOR_ADDRESS),
            }
            return info
        except Exception as e:
            logger.error(f"Failed to get validator info: {str(e)}")
            return None
