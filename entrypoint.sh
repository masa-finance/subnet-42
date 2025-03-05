#!/bin/bash
set -e

# Check for required environment variables
if [ -z "$COLDKEY_MNEMONIC" ]; then
    echo "Error: COLDKEY_MNEMONIC environment variable is required"
    exit 1
fi

# Create necessary directories
mkdir -p /root/.bittensor/wallets/default/coldkey
mkdir -p /root/.bittensor/wallets/default/hotkeys

# Python script to handle key generation
python3 -c "
from fiber.wallet import Wallet
from fiber.keys import KeyType
import os

# Initialize wallet
wallet = Wallet(path='/root/.bittensor/wallets/', name='default')

# Regenerate coldkey
success = wallet.regenerate_key(
    key_type=KeyType.COLDKEY,
    mnemonic='${COLDKEY_MNEMONIC}',
    use_password=False
)
if not success:
    raise Exception('Failed to regenerate coldkey')

# Handle hotkey generation
auto_generate = os.getenv('AUTO_GENERATE_HOTKEY', '').lower() == 'true'
hotkey_mnemonic = os.getenv('HOTKEY_MNEMONIC')

if auto_generate:
    # Generate new hotkey
    success = wallet.create_new_key(
        key_type=KeyType.HOTKEY,
        use_password=False
    )
    if not success:
        raise Exception('Failed to generate new hotkey')
elif hotkey_mnemonic:
    # Use provided mnemonic
    success = wallet.regenerate_key(
        key_type=KeyType.HOTKEY,
        mnemonic=hotkey_mnemonic,
        use_password=False
    )
    if not success:
        raise Exception('Failed to regenerate hotkey')
else:
    raise Exception('Either HOTKEY_MNEMONIC must be provided or AUTO_GENERATE_HOTKEY must be set to true')
"

# Set secure permissions
chmod 600 /root/.bittensor/wallets/default/coldkey/default
chmod 600 /root/.bittensor/wallets/default/hotkeys/default

# Start the validator/miner
if [ "$ROLE" = "validator" ]; then
    exec python scripts/run_validator.py
else
    exec python -m neurons.miner
fi 