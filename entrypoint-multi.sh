#!/bin/bash
set -e

# Check for required environment variables
if [ -z "$COLDKEY_MNEMONIC" ]; then
    echo "Error: COLDKEY_MNEMONIC environment variable is required"
    exit 1
fi

# Check for instance ID
if [ -z "$INSTANCE_ID" ]; then
    echo "Error: INSTANCE_ID environment variable is required"
    exit 1
fi

# Initialize wallet using our Python script
python scripts/init_wallet.py

# Function to create Kubernetes secret
create_k8s_secret() {
    local secret_name="$1"
    local mnemonic="$2"
    
    # Check if secret already exists
    if ! kubectl get secret "$secret_name" &> /dev/null; then
        kubectl create secret generic "$secret_name" --from-literal=mnemonic="$mnemonic"
    fi
}

# Regenerate coldkey and handle hotkey using fiber
python3 -c "
import os
from fiber.wallet import Wallet
from fiber.keys import KeyType
import subprocess
import json

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

# Handle hotkey
role = os.getenv('ROLE', 'validator').lower()
instance_id = os.getenv('INSTANCE_ID')
secret_name = f'hotkey-{role}-{instance_id}'

# Try to get existing hotkey secret
try:
    secret_data = subprocess.check_output(['kubectl', 'get', 'secret', secret_name, '-o', 'json'])
    secret = json.loads(secret_data)
    mnemonic = subprocess.check_output(
        ['kubectl', 'get', 'secret', secret_name, '-o', 'jsonpath={.data.mnemonic}']
    ).decode()
    mnemonic = subprocess.check_output(['base64', '--decode'], input=mnemonic.encode()).decode()
    
    # Use existing hotkey
    success = wallet.regenerate_key(
        key_type=KeyType.HOTKEY,
        mnemonic=mnemonic,
        use_password=False
    )
    if not success:
        raise Exception(f'Failed to regenerate hotkey from secret {secret_name}')
    print(f'Successfully restored hotkey from secret {secret_name}')
    
except subprocess.CalledProcessError:
    # No existing secret, generate new hotkey
    if os.getenv('HOTKEY_MNEMONIC'):
        # Use provided hotkey if available
        mnemonic = os.getenv('HOTKEY_MNEMONIC')
    else:
        # Generate new hotkey
        new_hotkey = wallet.create_new_key(key_type=KeyType.HOTKEY, use_password=False)
        mnemonic = wallet.get_key_mnemonic(key_type=KeyType.HOTKEY)
    
    # Store new hotkey in Kubernetes secret
    subprocess.run([
        'kubectl', 'create', 'secret', 'generic', secret_name,
        f'--from-literal=mnemonic={mnemonic}'
    ], check=True)
    print(f'Created new hotkey and stored in secret {secret_name}')
    
    # Use the hotkey
    success = wallet.regenerate_key(
        key_type=KeyType.HOTKEY,
        mnemonic=mnemonic,
        use_password=False
    )
    if not success:
        raise Exception('Failed to regenerate new hotkey')
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