# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Prerequisites

- Docker and Docker Compose installed
- A registered Bittensor wallet with a hotkey registered on Subnet 42
- For validators: Access to a TEE (Trusted Execution Environment) worker. See [tee-worker repository](https://github.com/masa-finance/tee-worker) for details.

## Quick Start

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/subnet-42.git
cd subnet-42
cp .env.example .env
```

2. Edit `.env` with your wallet details:
```env
BT_WALLET_PATH=/path/to/your/bittensor/wallet  # Optional, defaults to ~/.bittensor
BT_WALLET_NAME=your-wallet-name                # Optional, defaults to "default"
BT_HOTKEY_NAME=your-hotkey-name                # Optional, defaults to "default"
```

3. Run your node:
```bash
# For a miner:
docker compose up subnet42-miner

# For a validator:
docker compose up subnet42-validator tee-worker

# For both:
docker compose up subnet42-miner subnet42-validator tee-worker
```

## Monitoring

- Miner logs: `docker compose logs subnet42-miner -f`
- Validator logs: `docker compose logs subnet42-validator -f`
- TEE worker logs: `docker compose logs tee-worker -f`

## Troubleshooting

1. Ensure your Bittensor wallet is properly registered on Subnet 42
2. Check that your TEE worker is running and accessible (for validators)
3. Verify your network connectivity to the Bittensor network
4. Check the logs for specific error messages

For more detailed information about the TEE worker requirements and setup, please refer to the [tee-worker repository](https://github.com/masa-finance/tee-worker).