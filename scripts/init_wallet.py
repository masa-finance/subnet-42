import os
import bittensor as bt
import pathlib

def init_wallet():
    # Initialize wallet
    wallet = bt.wallet(name='default', path='/root/.bittensor/wallets/')

    # Only regenerate coldkey if it doesn't exist
    coldkey_path = pathlib.Path('/root/.bittensor/wallets/default/coldkey/default')
    if not coldkey_path.exists():
        coldkey_mnemonic = os.getenv('COLDKEY_MNEMONIC')
        if not coldkey_mnemonic:
            raise Exception('COLDKEY_MNEMONIC environment variable is required')
            
        success = wallet.regenerate_coldkey(
            mnemonic=coldkey_mnemonic,
            use_password=False,
            overwrite=True
        )
        if not success:
            raise Exception('Failed to regenerate coldkey')

    # Handle hotkey generation
    auto_generate = os.getenv('AUTO_GENERATE_HOTKEY', '').lower() == 'true'
    hotkey_mnemonic = os.getenv('HOTKEY_MNEMONIC')

    if auto_generate:
        # Generate new hotkey
        success = wallet.create_new_hotkey(use_password=False)
        if not success:
            raise Exception('Failed to generate new hotkey')
    elif hotkey_mnemonic:
        # Use provided mnemonic
        success = wallet.regenerate_hotkey(
            mnemonic=hotkey_mnemonic,
            use_password=False,
            overwrite=True
        )
        if not success:
            raise Exception('Failed to regenerate hotkey')
    else:
        msg = ('Either HOTKEY_MNEMONIC must be provided or '
               'AUTO_GENERATE_HOTKEY must be set to true')
        raise Exception(msg)

if __name__ == '__main__':
    init_wallet() 