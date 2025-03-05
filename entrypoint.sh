#!/bin/bash
set -e

# Check for required environment variables
if [ -z "$COLDKEY_MNEMONIC" ]; then
    echo "Error: COLDKEY_MNEMONIC environment variable is required"
    exit 1
fi

# Initialize wallet using our Python script
python scripts/init_wallet.py

# Set secure permissions
chmod 600 /root/.bittensor/wallets/default/coldkey/default
chmod 600 /root/.bittensor/wallets/default/hotkeys/default

# Start the validator/miner
if [ "$ROLE" = "validator" ]; then
    exec python scripts/run_validator.py
else
    exec python -m neurons.miner
fi 