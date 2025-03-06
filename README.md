# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Quick Start

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/subnet-42.git
cd subnet-42
cp .env.example .env
```

2. Edit `.env` with your existing keys:
```env
# Your coldkey mnemonic
COLDKEY_MNEMONIC="your coldkey mnemonic here"

# Your hotkey mnemonic (must be already registered on the subnet)
HOTKEY_MNEMONIC="your hotkey mnemonic here"
```

3. Run as a miner or validator:
```bash
# Run as a miner
docker compose --profile miner up

# Run as a validator
docker compose --profile validator up
```

The containers will automatically pull the latest images from Docker Hub.

## Advanced Configuration

Optional environment variables in `.env`:
```env
NETUID=42                   # Subnet ID (default: 42)
SUBTENSOR_NETWORK=finney    # Network (default: finney)
MINER_PORT=8082            # Port for miner API (default: 8082)
```

## Monitoring

View logs:
```bash
# All logs
docker compose logs -f

# Specific service logs
docker compose logs subnet42 -f      # Main service
docker compose logs tee-worker -f    # TEE worker (miner only)
docker compose logs nats -f          # NATS (validator only)
```

## Troubleshooting

1. Pull latest images:
```bash
docker compose pull
```

2. Clean start:
```bash
# Stop and remove everything
docker compose --profile miner down -v

# Start fresh
docker compose --profile miner up
```

3. Common issues:
- Ensure your hotkey is already registered on the subnet
- Check logs for any initialization errors
- Verify your mnemonics are correct