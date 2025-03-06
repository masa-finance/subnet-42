# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Prerequisites

1. A registered hotkey on subnet 165 (glagolitic_yu) on the test network
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

3. Run as a validator:
```bash
# Run as a validator
docker compose --profile validator up
```

The container will automatically pull the latest image from Docker Hub.

## Configuration

Required environment variables in `.env`:
```env
COLDKEY_MNEMONIC           # Your coldkey mnemonic
HOTKEY_MNEMONIC           # Your hotkey mnemonic (must be registered on subnet 165)
```

Optional environment variables in `.env`:
```env
NETUID=165                # Subnet ID (default: 165)
SUBTENSOR_NETWORK=test    # Network (default: test)
VALIDATOR_PORT=8092       # Port for validator API (default: 8092)
```

## Monitoring

View logs:
```bash
# All logs
docker compose logs -f

# Specific service logs
docker compose logs subnet42 -f      # Main service
```

## Verification

To verify your validator is running correctly:

1. Check if your hotkey is registered:
```bash
btcli s metagraph --netuid 165 --network test
```

2. Check the validator logs:
```bash
docker compose logs subnet42 -f
```

You should see:
- Successful connection to the test network
- Your hotkey being loaded
- Connection attempts to miners (note: on testnet, many miners may be offline which is normal)

## Troubleshooting

1. Pull latest images:
```bash
docker compose pull
```

2. Clean start:
```bash
# Stop and remove everything
docker compose down -v

# Start fresh
docker compose --profile validator up
```

3. Common issues:
- Ensure your hotkey is registered on subnet 165 (glagolitic_yu) on the test network
- Check logs for any initialization errors
- Verify your mnemonics are correct
- Connection errors to miners on testnet are normal as many may be offline

## Kubernetes Deployment

1. Create secrets for your mnemonics:
```bash
kubectl create secret generic subnet42-validator-keys \
  --from-literal=coldkey-mnemonic="your coldkey mnemonic" \
  --from-literal=hotkey-mnemonic="your hotkey mnemonic"
```

2. Create deployment:
```yaml
# validator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: subnet42-validator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: subnet42-validator
  template:
    metadata:
      labels:
        app: subnet42-validator
    spec:
      containers:
      - name: subnet42
        image: masaengineering/subnet-42:latest
        imagePullPolicy: Always
        env:
        - name: ROLE
          value: "validator"
        - name: NETUID
          value: "165"
        - name: SUBTENSOR_NETWORK
          value: "test"
        - name: COLDKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: subnet42-validator-keys
              key: coldkey-mnemonic
        - name: HOTKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: subnet42-validator-keys
              key: hotkey-mnemonic
```

3. Deploy:
```bash
kubectl apply -f validator-deployment.yaml
```

4. View logs:
```bash
kubectl logs -f deployment/subnet42-validator -c subnet42
```
