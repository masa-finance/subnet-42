import os
import httpx
import uvicorn
import requests

from fiber.chain import chain_utils, post_ip_to_chain, interface
from fiber.chain.metagraph import Metagraph
from fiber.miner.server import factory_app

from fiber.networking.models import NodeWithFernet as Node
from fiber.logging_utils import get_logger

from typing import Optional
from fastapi import FastAPI
from miner.routes_manager import MinerAPI
from threading import Thread

logger = get_logger(__name__)


# Function to run the server
def run_server(app, port):
    uvicorn.run(app, host="127.0.0.1", port=port)


class AgentMiner:
    def __init__(self):
        """Initialize miner"""

        self.wallet_name = os.getenv("WALLET_NAME", "default")
        self.hotkey_name = os.getenv("HOTKEY_NAME", "default")
        self.port = int(os.getenv("MINER_PORT", 8082))
        self.external_ip = self.get_external_ip()

        self.keypair = chain_utils.load_hotkey_keypair(
            self.wallet_name, self.hotkey_name
        )

        self.httpx_client: Optional[httpx.AsyncClient] = None
        self.netuid = int(os.getenv("NETUID", "42"))
        self.subtensor_network = os.getenv("SUBTENSOR_NETWORK")
        self.subtensor_address = os.getenv("SUBTENSOR_ADDRESS")

        self.server: Optional[factory_app] = None
        self.app: Optional[FastAPI] = None

        self.substrate = interface.get_substrate(
            subtensor_network=self.subtensor_network,
            subtensor_address=self.subtensor_address,
        )
        self.metagraph = Metagraph(netuid=self.netuid, substrate=self.substrate)
        self.metagraph.sync_nodes()

        self.post_ip_to_chain()

        self.routes = MinerAPI(self)

    async def start(self) -> None:
        """Start the miner service"""

        try:
            self.httpx_client = httpx.AsyncClient()
            # self.routes.register_routes()

            config = uvicorn.Config(
                self.routes.app, host="0.0.0.0", port=self.port, lifespan="on"
            )
            server = uvicorn.Server(config)
            await server.serve()

        except Exception as e:
            logger.error(f"Failed to start miner: {str(e)}")
            raise

    def get_external_ip(self) -> str:
        env = os.getenv("ENV", "prod").lower()
        if env == "dev":
            # post this to chain to mark as local
            return "0.0.0.1"

        try:
            response = requests.get("https://api.ipify.org?format=json")
            response.raise_for_status()
            return response.json()["ip"]
        except requests.RequestException as e:
            logger.error(f"Failed to get external IP: {e}")
            return "0.0.0.0"

    def post_ip_to_chain(self) -> None:
        """Posts the miner's IP and port to the chain if they have changed."""
        logger.info("Starting post_ip_to_chain process")
        try:
            node = self.node()
            logger.debug(f"Retrieved node from metagraph: {node}")

            # Use override_external_ip if provided, else use self.external_ip
            external_ip = os.getenv("OVERRIDE_EXTERNAL_IP", self.external_ip)

            if node:
                if node.ip != external_ip or node.port != self.port:
                    logger.info(
                        f"IP/Port mismatch detected - Current chain values: "
                        f"IP={node.ip}, Port={node.port}"
                    )
                    logger.info(
                        f"Updating chain with new values: IP={external_ip}, "
                        f"Port={self.port}"
                    )

                    try:
                        logger.debug(
                            f"Loading coldkey pub for wallet: {self.wallet_name}"
                        )
                        coldkey_keypair_pub = chain_utils.load_coldkeypub_keypair(
                            wallet_name=self.wallet_name
                        )
                        logger.debug("Successfully loaded coldkey")

                        logger.debug("Posting IP/Port to chain...")
                        logger.info(
                            "Posting IP/Port to chain with params:\n"
                            f"  substrate: {self.substrate}\n"
                            f"  keypair: {self.keypair}\n"
                            f"  netuid: {self.netuid}\n"
                            f"  external_ip: {external_ip}\n"
                            f"  external_port: {self.port}\n"
                            f"  coldkey_ss58_address: {coldkey_keypair_pub.ss58_address}"
                        )
                        post_ip_to_chain.post_node_ip_to_chain(
                            substrate=self.substrate,
                            keypair=self.keypair,
                            netuid=self.netuid,
                            external_ip=external_ip,
                            external_port=self.port,
                            coldkey_ss58_address=coldkey_keypair_pub.ss58_address,
                        )
                        logger.info("✅ Successfully posted IP/Port to chain")

                    except Exception as e:
                        logger.error(
                            f"Failed to post IP/Port to chain: {str(e)}", exc_info=True
                        )
                else:
                    logger.info(
                        f"IP/Port already up to date on chain: IP={node.ip}, "
                        f"Port={node.port}"
                    )
            else:
                err_msg = (
                    f"Hotkey {self.keypair.ss58_address} not found in metagraph. "
                    f"Please ensure it is registered."
                )
                logger.error(err_msg)

        except Exception as e:
            logger.error(f"Error in post_ip_to_chain: {str(e)}", exc_info=True)

    def node(self) -> Optional[Node]:
        try:
            nodes = self.metagraph.nodes
            node = nodes[self.keypair.ss58_address]
            return node
        except Exception as e:
            logger.error(f"Failed to get node from metagraph: {e}")
            return None

    def information_handler(self) -> Optional[str]:
        """Send information back to the validator"""
        some_info = os.getenv("SOME_INFO", "no information provided")
        return some_info

    async def stop(self) -> None:
        """Cleanup and shutdown"""
        if self.server:
            await self.server.stop()
