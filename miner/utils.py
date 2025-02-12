from fastapi import Request
import os
import httpx
from fiber.encrypted.miner.endpoints.handshake import (
    get_public_key,
    exchange_symmetric_key,
)
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from neurons.miner import AgentMiner


async def proxy_to_tee(request: Request):
    """Proxy incoming requests to the TEE address."""
    tee_address = os.getenv("TEE_ADDRESS")
    if not tee_address:
        return {"error": "TEE address not configured."}

    print("ABOUT TO PROXY: ", tee_address)
    print(request)

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{tee_address}{request.url.path.replace('/proxy', '')}",
            headers=request.headers,
            content=await request.body(),
        )

        print("***************** RESPONSE")
        print(response)

        # Extract content and return it in a JSON-serializable format
        return {
            "status_code": response.status_code,
            "content": response.json(),
            "headers": dict(response.headers),
        }


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
