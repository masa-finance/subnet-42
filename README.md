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

## Kubernetes Deployment

1. Create secrets for your mnemonics:
```bash
# For a miner
kubectl create secret generic subnet42-miner-keys \
  --from-literal=coldkey-mnemonic="your coldkey mnemonic" \
  --from-literal=hotkey-mnemonic="your hotkey mnemonic"

# For a validator
kubectl create secret generic subnet42-validator-keys \
  --from-literal=coldkey-mnemonic="your coldkey mnemonic" \
  --from-literal=hotkey-mnemonic="your hotkey mnemonic"
```

2. Create deployment:
```yaml
# miner-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: subnet42-miner
spec:
  replicas: 1
  selector:
    matchLabels:
      app: subnet42-miner
  template:
    metadata:
      labels:
        app: subnet42-miner
    spec:
      containers:
      - name: subnet42
        image: masaengineering/subnet-42:latest
        imagePullPolicy: Always
        env:
        - name: ROLE
          value: "miner"
        - name: COLDKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: subnet42-miner-keys
              key: coldkey-mnemonic
        - name: HOTKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: subnet42-miner-keys
              key: hotkey-mnemonic
      - name: tee-worker
        image: masaengineering/tee-worker:latest
        imagePullPolicy: Always
```

For a validator, use:
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
      - name: nats
        image: nats:latest
        args: ["--jetstream"]
      - name: subnet42
        image: masaengineering/subnet-42:latest
        imagePullPolicy: Always
        env:
        - name: ROLE
          value: "validator"
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
# For miner
kubectl apply -f miner-deployment.yaml

# For validator
kubectl apply -f validator-deployment.yaml
```

4. View logs:
```bash
# For miner
kubectl logs -f deployment/subnet42-miner -c subnet42
kubectl logs -f deployment/subnet42-miner -c tee-worker

# For validator
kubectl logs -f deployment/subnet42-validator -c subnet42
kubectl logs -f deployment/subnet42-validator -c nats
```
