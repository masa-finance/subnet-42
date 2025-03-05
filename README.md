# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Prerequisites

- Docker and Docker Compose installed
- A registered Bittensor wallet with a hotkey registered on Subnet 42

## Quick Start

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/subnet-42.git
cd subnet-42
cp .env.sample .env
```

2. Edit `.env` with your configuration:
```env
# Required: Wallet Configuration
WALLET_NAME=your-wallet-name
HOTKEY_NAME=your-hotkey-name
WALLET_PATH=/path/to/your/wallet  # Defaults to ~/.bittensor

# Optional: Network Configuration
NETUID=165                        # 165 for testnet, 59 for mainnet
SUBTENSOR_NETWORK=test            # 'test' or 'finney'
```

3. Run your node:
```bash
# To run as a miner (includes TEE worker):
docker compose --profile miner up

# To run just the miner container without TEE worker:
docker compose --profile miner up subnet42

# To run as a validator (includes NATS):
docker compose --profile validator up

# To run just the validator container without NATS:
docker compose --profile validator up subnet42

# To build locally instead of pulling from Docker Hub:
BUILD_LOCAL=true docker compose --profile miner up
# or
BUILD_LOCAL=true docker compose --profile validator up

# To run the validator directly with Docker (development with local files):
docker run -it --rm \
  -v ~/.bittensor:/root/.bittensor \
  -v ./config:/app/config \
  -v ./neurons:/app/neurons \
  -v ./miner:/app/miner \
  -v ./validator:/app/validator \
  -v ./interfaces:/app/interfaces \
  -v ./scripts:/app/scripts \
  -e ROLE=validator \
  -e WALLET_NAME=your-wallet-name \
  -e HOTKEY_NAME=your-hotkey-name \
  -e NETUID=165 \
  -p 8081:8081 \
  masaengineering/subnet42:latest

# Minimal production deployment (e.g., for Kubernetes):
docker run -d \
  -v /path/to/wallet:/root/.bittensor \
  -e ROLE=validator \
  -e WALLET_NAME=your-wallet-name \
  -e HOTKEY_NAME=your-hotkey-name \
  -e NETUID=165 \
  -e SUBTENSOR_NETWORK=finney \
  -p 8081:8081 \
  masaengineering/subnet42:latest
```

## Monitoring

View logs for your node:
```bash
# For miner logs:
docker compose logs subnet42 -f

# For TEE worker logs (when running as miner):
docker compose logs tee-worker -f

# For NATS logs (when running as validator):
docker compose logs nats -f
```

## Troubleshooting

1. Ensure your Bittensor wallet is properly registered on Subnet 42
2. Check your .env configuration:
   - Verify wallet and hotkey names are correct
   - Ensure NETUID matches the network you're connecting to
3. For miners:
   - Check TEE worker logs for any initialization errors
4. For validators:
   - Verify NATS is running and accessible

## Development

To build the image locally instead of pulling from Docker Hub, use:
```bash
BUILD_LOCAL=true docker compose --profile [miner|validator] up
```

For more detailed information about the TEE worker requirements and setup, please refer to the [tee-worker repository](https://github.com/masa-finance/tee-worker).