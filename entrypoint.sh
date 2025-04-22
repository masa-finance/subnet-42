#!/bin/bash
set -e
# Trap all exits
trap 'echo "Script exiting with code $?"' EXIT

# Turn off command echoing before handling sensitive data
set +x

# If there's a mnemonic, initialize the wallet, otherwise use mounted wallet
if [ ! -z "${COLDKEY_MNEMONIC+x}" ]; then    # Check if mnemonic exists
    echo "Mnemonic found, initializing wallet..."
    # Redirect all output to /dev/null during wallet initialization
    if ! python scripts/init_wallet.py > /dev/null 2>&1; then
        echo "Error: Wallet initialization failed"
        exit 1
    fi
    echo "Wallet initialization complete"
else
    # Use mounted wallet
    echo "No mnemonic found, using mounted wallet..."
    if [ ! -d "$HOME/.bittensor/wallets" ] || [ ! "$(ls -A $HOME/.bittensor/wallets)" ]; then
        echo "Error: No mounted wallets found at $HOME/.bittensor/wallets"
        exit 1
    fi
fi

# Re-enable command echoing for the rest of the script
set -x

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