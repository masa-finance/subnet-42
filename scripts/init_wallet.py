import os
import bittensor as bt
import pathlib


def init_wallet():
    # Use miner for miner role, validator for validator role
    wallet_name = 'validator' if os.getenv('ROLE') == 'validator' else 'miner'

    # Disable bittensor logging during wallet operations
    bt.logging.disable_logging()

    try:
        # Initialize wallet
        wallet = bt.wallet(name=wallet_name, path='/root/.bittensor/wallets/')

        coldkey_mnemonic = os.getenv('COLDKEY_MNEMONIC')
        if not coldkey_mnemonic:
            raise Exception('COLDKEY_MNEMONIC environment variable is required')
            
        # Regenerate coldkey - ignore return value since it outputs success message
        wallet.regenerate_coldkey(
            mnemonic=coldkey_mnemonic,
            use_password=False
        )

        # Check if hotkey exists before regenerating
        hotkey_path = pathlib.Path(f'/root/.bittensor/wallets/{wallet_name}/hotkeys/default')
        if not hotkey_path.exists():
            hotkey_mnemonic = os.getenv('HOTKEY_MNEMONIC')
            if hotkey_mnemonic:
                # Use provided mnemonic - ignore return value
                wallet.regenerate_hotkey(
                    mnemonic=hotkey_mnemonic,
                    use_password=False
                )
            elif os.getenv('AUTO_GENERATE_HOTKEY', '').lower() == 'true':
                # Generate new hotkey - ignore return value
                wallet.create_new_hotkey(use_password=False)
            else:
                msg = ('Either HOTKEY_MNEMONIC must be provided or '
                       'AUTO_GENERATE_HOTKEY must be set to true')
                raise Exception(msg)
    finally:
        # Re-enable default logging
        bt.logging.enable_default()


if __name__ == '__main__':
    init_wallet() 