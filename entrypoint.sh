#!/bin/bash
set -e

# Check for required environment variables
if [ -z "$COLDKEY_MNEMONIC" ]; then
    echo "Error: COLDKEY_MNEMONIC environment variable is required"
    exit 1
fi

# Initialize wallet using our Python script
python scripts/init_wallet.py

# Start the validator/miner
if [ "$ROLE" = "validator" ]; then
    exec python scripts/run_validator.py
else
    exec python -m neurons.miner
fi 