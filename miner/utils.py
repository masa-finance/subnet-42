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


async def proxy_to_tee(request: Request):
    """Proxy incoming requests to the TEE address."""
    tee_address = os.getenv("MINER_TEE_ADDRESS")

    logger.info(f"Preparing to send a request to TEE address: {tee_address}")
    if not tee_address:
        logger.error("TEE address not configured.")
        return {"error": "TEE address not configured."}

    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Request Method: {request.method}")
            logger.debug(f"Request URL: {tee_address}{request.url.path}")
            logger.debug(f"Request Headers: {request.headers}")
            logger.debug(f"Request Body: {await request.body()}")

            response = await client.request(
                method=request.method,
                url=f"{tee_address}{request.url.path.replace('', '')}",
                headers=request.headers,
                content=await request.body(),
            )

            logger.info(f"Received response with status code: {response.status_code}")
            logger.debug(f"Response Headers: {response.headers}")
            logger.debug(f"Response Content: {response.text}")

            # Ensure the response is JSON-serializable
            try:
                return response.json()
            except ValueError:
                logger.debug(f"Non json response: {response.text}")
                return response.text
    except httpx.ConnectError as e:
        logger.error(f"Connection failed: {str(e)}")
        return {"error": f"Connection failed: {str(e)}"}
    except Exception:
        logger.exception("An unexpected error occurred.")
        return {"error": "An unexpected error occurred."}


def healthcheck(miner: "AgentMiner"):
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
        miner.logger.error(f"Failed to get miner info: {str(e)}")
        return None


# Encryption methods
get_public_key = get_public_key
exchange_symmetric_key = exchange_symmetric_key
