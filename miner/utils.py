from fastapi import Request
import os
import httpx
from fiber.encrypted.miner.endpoints.handshake import (
    get_public_key,
    exchange_symmetric_key,
)
from typing import TYPE_CHECKING
from fiber.logging_utils import get_logger
from fiber.chain.chain_utils import query_substrate

if TYPE_CHECKING:
    from neurons.miner import AgentMiner

# Remove logging configuration to centralize it in the main entry point

logger = get_logger(__name__)


def get_validators_permits(miner: "AgentMiner"):
    vpermits = miner.substrate.query(
        "SubtensorModule", "ValidatorPermit", [miner.netuid]
    )
    logger.info(f"*********** Validator Permits: {vpermits}")

    for uid, permit in enumerate(vpermits):
        logger.info(f"UID {uid}: Permit = {bool(permit)}")

    return vpermits


def get_validators_weight(miner: "AgentMiner", uid):
    substrate, weights = query_substrate(
        miner.substrate, "SubtensorModule", "Weights", [miner.netuid, uid]
    )
    weights_values = [0 for i in range(256)]
    for node_id, weight_value in weights:
        weights_values[node_id] = weight_value

    return weights_values


def get_last_updated(miner: "AgentMiner"):

    substrate, current_block = query_substrate(
        miner.substrate, "System", "Number", [], return_value=True
    )

    substrate, last_updated_value = query_substrate(
        miner.substrate,
        "SubtensorModule",
        "LastUpdate",
        [miner.netuid],
        return_value=False,
    )

    last_updated = []

    for uid, value in enumerate(last_updated_value):
        updated: int = current_block - value
        last_updated.append(updated)

    return last_updated


def get_all_validators_weights(miner: "AgentMiner"):
    # Get all validator permits
    vpermits = get_validators_permits(miner)

    # Get last updated by uid
    last_updated = get_last_updated(miner)

    # Get weights for each validator and check for non-zero values
    for uid, permit in enumerate(vpermits):
        if bool(permit):  # Only check weights for validators with permits
            weights = get_validators_weight(miner, uid)

            # Check if any weights are greater than 0
            non_zero_weights = [(i, w) for i, w in enumerate(weights) if w > 0]

            if non_zero_weights:
                logger.info(
                    f"Validator {uid} has non-zero weights ( {last_updated[uid]} blocks ago ):"
                )
                logger.info(f"VALIDATOR {uid} WEIGHTS: {weights}")
            else:
                logger.info(
                    f"Validator {uid} has all zero weights ( {last_updated[uid]} blocks ago )"
                )

    return vpermits


def healthcheck(miner: "AgentMiner"):

    logger.info("Performing miner healthcheck")
    logger.info(f"SS58 Address: {miner.keypair.ss58_address}")
    # logger.info(f'UID: {miner.metagraph.nodes[miner.keypair.ss58_address].node_id}')
    # logger.info(f'IP: {miner.metagraph.nodes[miner.keypair.ss58_address].ip}')
    # logger.info(f'Port: {miner.metagraph.nodes[miner.keypair.ss58_address].port}')
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
