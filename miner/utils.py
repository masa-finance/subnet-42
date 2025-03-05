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

            body = await request.body()
            logger.debug(f"Request Method: {request.method}")
            logger.debug(f"Request URL: {tee_address}{request.url.path}")
            logger.debug(f"Request Headers: {request.headers}")
            logger.debug(f"Request Body: {body}")

            # Clean up encrypted fields in the body if present
            try:
                body_str = body.decode("utf-8")
                import json

                body_dict = json.loads(body_str)

                # Clean encrypted fields if present
                for key in ["encrypted_job", "encrypted_request", "encrypted_result"]:
                    if key in body_dict:
                        value = body_dict[key]
                        if isinstance(value, str):
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            value = value.replace("\\", "")
                            body_dict[key] = value

                # Convert back to bytes
                body = json.dumps(body_dict).encode("utf-8")

            except Exception as e:
                logger.debug(f"Failed to clean encrypted fields: {str(e)}")
                # Continue with original body if cleaning fails
                pass

            # Log post-processed body after cleaning encrypted fields
            logger.debug(f"Post-processed Request Body: {body}")

            # Create new headers dict from original headers, excluding Content-Length
            headers = {
                k: v
                for k, v in request.headers.items()
                if k.lower() != "content-length"
            }

            response = await client.request(
                method=request.method,
                url=f"{tee_address}{request.url.path.replace('', '')}",
                headers=headers,
                content=body,
            )

            logger.info(f"Received response with status code: {response.status_code}")
            logger.debug(f"Response Headers: {response.headers}")
            logger.debug(f"Response Content: {response.text}")

            # Ensure the response is JSON-serializable
            try:
                response_json = response.json()
                # Clean up any backslashes or extra quotes in specific fields
                for key in ["encrypted_job", "encrypted_request"]:
                    if key in response_json:
                        value = response_json[key]
                        if isinstance(value, str):
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            value = value.replace("\\", "")
                            response_json[key] = value

                logger.debug(
                    f"RESPONSE TO {tee_address}{request.url.path}: {response_json}"
                )
                return response_json
            except ValueError:
                logger.debug(f"Non json response: {response.text}")
                content = response.content

                signature = content.decode("utf-8")
                if signature.startswith('"') and signature.endswith('"'):
                    signature = signature[1:-1]
                signature = signature.replace("\\", "")

                return signature
    except httpx.ConnectError as e:
        logger.error(f"Connection failed: {str(e)}")
        return {"error": f"Connection failed: {str(e)}"}
    except Exception:
        logger.exception("An unexpected error occurred.")
        return {"error": "An unexpected error occurred."}


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
