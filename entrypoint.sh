#!/bin/bash
set -ex

# Trap all exits
trap 'echo "Script exiting with code $?"' EXIT

# If we have a mounted wallet, skip all initialization
if [ -d "/root/.bittensor/wallets" ] && [ "$(ls -A /root/.bittensor/wallets)" ]; then
    echo "Found mounted wallet, skipping initialization"
else
    # Only do initialization if no mounted wallet
    if [ -z "$COLDKEY_MNEMONIC" ]; then
        echo "Error: COLDKEY_MNEMONIC environment variable is required"
        exit 1
    fi

    if ! python scripts/init_wallet.py; then
        echo "Error: Wallet initialization failed"
        exit 1
    fi
fi

# Debug role
echo "ROLE is set to: '$ROLE'"

# Start the validator/miner
if [ "$ROLE" = "validator" ]; then
    echo "Starting validator..."
    exec python scripts/run_validator.py
else
    echo "Starting miner..."
    exec python scripts/run_miner.py
fi 