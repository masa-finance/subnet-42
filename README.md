# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Prerequisites

1. A registered hotkey on subnet 165 on the test network, or 42 on finney (mainnet)
2. Docker and Docker Compose installed
3. Your coldkey and hotkey mnemonics

## Quick Start

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/subnet-42.git
cd subnet-42
cp .env.example .env
```

2. Edit `.env` with your keys:
```env
# Your coldkey mnemonic
COLDKEY_MNEMONIC="your coldkey mnemonic here"

# Your hotkey mnemonic (must be already registered on subnet 165)
HOTKEY_MNEMONIC="your hotkey mnemonic here"
```

3. Run as a validator or miner:
```bash
# Run as a validator
docker compose --profile validator up

# Run as a miner
docker compose --profile miner up
```

The containers will automatically pull the latest images from Docker Hub.

## Configuration

Required environment variables in `.env`:
```env
COLDKEY_MNEMONIC           # Your coldkey mnemonic
HOTKEY_MNEMONIC           # Your hotkey mnemonic (must be registered on subnet 165)
ROLE                      # Either "validator" or "miner"
```

Optional environment variables in `.env`:
```env
NETUID=165                # Subnet ID (default: 165)
SUBTENSOR_NETWORK=test    # Network (default: test)
VALIDATOR_PORT=8092       # Port for validator API (default: 8092)
MINER_PORT=8091          # Port for miner API (default: 8091)
```

## Monitoring

View logs:
```bash
# All logs
docker compose logs -f

# Specific service logs
docker compose logs subnet42 -f      # Main service
docker compose logs tee-worker -f    # TEE worker (miner only)
```

## Verification

To verify your node is running correctly:

1. Check if your hotkey is registered:
```bash
btcli s metagraph --netuid 165 --network test
```

2. Check the logs:
```bash
docker compose logs subnet42 -f
```

You should see:
- Successful connection to the test network
- Your hotkey being loaded
- For validators: Connection attempts to miners (note: on testnet, many miners may be offline which is normal)
- For miners: TEE worker initialization and connection to validators

## Troubleshooting

1. Pull latest images:
```bash
docker compose pull
```

2. Clean start:
```bash
# Stop and remove everything
docker compose down -v

# Start fresh as validator
docker compose --profile validator up

# Or start fresh as miner
docker compose --profile miner up
```

3. Common issues:
- Ensure your hotkey is registered on subnet 165 (glagolitic_yu) on the test network
- Check logs for any initialization errors
- Verify your mnemonics are correct
- For validators: Connection errors to miners on testnet are normal as many may be offline
- For miners: Ensure TEE worker is running and accessible
