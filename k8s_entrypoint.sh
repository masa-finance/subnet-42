#!/bin/bash
set -e

# Create necessary directories
mkdir -p /root/.bittensor/wallets/default/hotkeys

# Check for required environment variables
if [ -z "$BITTENSOR_HOTKEY" ]; then
    echo "Error: BITTENSOR_HOTKEY environment variable is required"
    exit 1
fi

# Write the hotkey file
echo "$BITTENSOR_HOTKEY" > /root/.bittensor/wallets/default/hotkeys/default

# Set permissions
chmod 600 /root/.bittensor/wallets/default/hotkeys/default

# Start the validator
exec python scripts/run_validator.py 