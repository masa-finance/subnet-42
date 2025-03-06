import os
import bittensor as bt
import pathlib


def init_wallet():
    # Check if wallet directory exists and has files (mounted from host)
    wallet_dir = pathlib.Path('/root/.bittensor/wallets')
    if wallet_dir.exists() and any(wallet_dir.iterdir()):
        print("Found existing mounted wallet directory, skipping initialization")
        return

    # Disable bittensor logging during wallet operations
    bt.logging.disable_logging()

    try:
        # Initialize wallet only after we've confirmed we need to create/regenerate keys
        wallet = bt.wallet(name='default', path='/root/.bittensor/wallets/')

        coldkey_mnemonic = os.getenv('COLDKEY_MNEMONIC')
        if not coldkey_mnemonic:
            raise Exception('COLDKEY_MNEMONIC environment variable is required')
            
        # Regenerate coldkey - ignore return value since it outputs success message
        wallet.regenerate_coldkey(
            mnemonic=coldkey_mnemonic,
            use_password=False
        )

        # Handle hotkey generation
        auto_generate = os.getenv('AUTO_GENERATE_HOTKEY', '').lower() == 'true'
        hotkey_mnemonic = os.getenv('HOTKEY_MNEMONIC')

        # Only generate/regenerate hotkey if it doesn't exist
        hotkey_path = pathlib.Path('/root/.bittensor/wallets/default/hotkeys/default')
        if not hotkey_path.exists():
            if auto_generate:
                # Generate new hotkey - ignore return value
                wallet.create_new_hotkey(use_password=False)
            elif hotkey_mnemonic:
                # Use provided mnemonic - ignore return value
                wallet.regenerate_hotkey(
                    mnemonic=hotkey_mnemonic,
                    use_password=False
                )
            else:
                msg = ('Either HOTKEY_MNEMONIC must be provided or '
                       'AUTO_GENERATE_HOTKEY must be set to true')
                raise Exception(msg)
    finally:
        # Re-enable default logging
        bt.logging.enable_default()


if __name__ == '__main__':
    init_wallet() 