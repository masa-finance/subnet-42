#!/bin/bash
set -e
# Trap all exits
trap 'echo "Script exiting with code $?"' EXIT

# Turn off command echoing before handling sensitive data
set +x

# If we have a mounted wallet, skip all initialization
if [ -d "/root/.bittensor/wallets" ] && [ "$(ls -A /root/.bittensor/wallets)" ]; then
    echo "Found mounted wallet, skipping initialization"
else
    # Only do initialization if no mounted wallet
    if [ -z "${COLDKEY_MNEMONIC+x}" ]; then    # Check if variable exists without exposing value
        echo "Error: COLDKEY_MNEMONIC environment variable is required"
        exit 1
    fi

    if ! python scripts/init_wallet.py; then
        echo "Error: Wallet initialization failed"
        exit 1
    fi
fi

# Re-enable command echoing for the rest of the script
set -x

# Debug role
echo "ROLE is set to: '$ROLE'"

# Verify wallet and hotkey exist in the correct location
if [ ! -d "/root/.bittensor/wallets/default" ]; then
    echo "Error: Wallet directory not found at /root/.bittensor/wallets/default"
    exit 1
fi

if [ ! -f "/root/.bittensor/wallets/default/hotkeys/default" ]; then
    echo "Error: Hotkey not found at /root/.bittensor/wallets/default/hotkeys/default"
    exit 1
fi

# Start the validator/miner
if [ "$ROLE" = "validator" ]; then
    echo "Starting validator..."
    exec python scripts/run_validator.py
else
    echo "Starting miner..."
    exec python scripts/run_miner.py
fi 