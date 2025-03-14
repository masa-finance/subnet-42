from fastapi import Request
import os
import httpx
from fiber.encrypted.miner.endpoints.handshake import (
    get_public_key,
    exchange_symmetric_key,
)
from typing import TYPE_CHECKING
import logging


if TYPE_CHECKING:
    from neurons.miner import AgentMiner


logger = logging.getLogger(__name__)


def healthcheck(miner: "AgentMiner"):

    logger.info("Performing miner healthcheck")
    logger.info(f"SS58 Address: {miner.keypair.ss58_address}")
    # logger.info(f"UID: {miner.metagraph.nodes[miner.keypair.ss58_address].node_id}")
    # logger.info(f"IP: {miner.metagraph.nodes[miner.keypair.ss58_address].ip}")
    # logger.info(f"Port: {miner.metagraph.nodes[miner.keypair.ss58_address].port}")
    logger.info(f"Netuid: {miner.netuid}")
    logger.info(f"Subtensor Network: {miner.subtensor_network}")
    logger.info(f"Subtensor Address: {miner.subtensor_address}")
    try:
        info = {
            "ss58_address": str(miner.keypair.ss58_address),
            "uid": str(miner.metagraph.nodes[miner.keypair.ss58_address].node_id),
            "ip": str(miner.metagraph.nodes[miner.keypair.ss58_address].ip),
            "port": str(miner.metagraph.nodes[miner.keypair.ss58_address].port),
            "netuid": str(miner.netuid),
            "subtensor_network": str(miner.subtensor_network),
            "subtensor_address": str(miner.subtensor_address),
        }
        return info
    except Exception as e:
        logger.error(f"Failed to get miner info: {str(e)}")
        return None


# Encryption methods
get_public_key = get_public_key
exchange_symmetric_key = exchange_symmetric_key
