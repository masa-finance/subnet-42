#!/bin/bash
set -e

# Check for required environment variables
if [ -z "$COLDKEY_MNEMONIC" ]; then
    echo "Error: COLDKEY_MNEMONIC environment variable is required"
    exit 1
fi

if [ -z "$HOTKEY_MNEMONIC" ]; then
    echo "Error: HOTKEY_MNEMONIC environment variable is required"
    exit 1
fi

# Create necessary directories
mkdir -p /root/.bittensor/wallets/default/coldkey
mkdir -p /root/.bittensor/wallets/default/hotkeys

# Regenerate coldkey and hotkey from mnemonics using fiber
python3 -c "
from fiber.wallet import Wallet
from fiber.keys import KeyType

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

# Regenerate hotkey
success = wallet.regenerate_key(
    key_type=KeyType.HOTKEY,
    mnemonic='${HOTKEY_MNEMONIC}',
    use_password=False
)
if not success:
    raise Exception('Failed to regenerate hotkey')
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