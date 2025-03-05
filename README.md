# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Prerequisites

- Docker and Docker Compose installed
- Your Bittensor wallet mnemonics (both coldkey and hotkey)
- Your hotkey must be registered on Subnet 42

## Quick Start

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/subnet-42.git
cd subnet-42
cp .env.example .env
```

2. Edit `.env` with your configuration:
```env
# Required: Wallet Configuration
# Your coldkey mnemonic phrase
COLDKEY_MNEMONIC=""

# Your hotkey mnemonic phrase
HOTKEY_MNEMONIC=""

# Network Configuration
# Network UID (165 for testnet, 59 for mainnet)
NETUID=165

# Network name (test or finney)
SUBTENSOR_NETWORK=test

# Role Configuration
# Node role (validator or miner)
ROLE=validator
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
```

### Direct Docker Usage

For development with local files:
```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./neurons:/app/neurons \
  -v ./miner:/app/miner \
  -v ./validator:/app/validator \
  -v ./interfaces:/app/interfaces \
  -v ./scripts:/app/scripts \
  -e ROLE=validator \
  -e COLDKEY_MNEMONIC="your coldkey mnemonic phrase here" \
  -e HOTKEY_MNEMONIC="your hotkey mnemonic phrase here" \
  -e NETUID=165 \
  -p 8081:8081 \
  masaengineering/subnet42:latest
```

Minimal production deployment:
```bash
docker run -d \
  -e ROLE=validator \
  -e COLDKEY_MNEMONIC="your coldkey mnemonic phrase here" \
  -e HOTKEY_MNEMONIC="your hotkey mnemonic phrase here" \
  -e NETUID=165 \
  -e SUBTENSOR_NETWORK=finney \
  -p 8081:8081 \
  masaengineering/subnet42:latest
```

### Security Note

The mnemonic phrases are sensitive information. In production:
1. Use environment files or secure secret management systems
2. Never commit mnemonics to version control
3. Consider using hardware security modules (HSMs) for key storage
4. Rotate keys periodically following security best practices

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

## Kubernetes Deployment

### Prerequisites
- A Kubernetes cluster
- `kubectl` configured to access your cluster
- Your Bittensor wallet mnemonics (coldkey and hotkey)

### Validator Deployment

1. Create secrets for your validator mnemonics:
```bash
# Create secrets for coldkey and hotkey mnemonics
kubectl create secret generic bittensor-mnemonics \
  --from-literal=coldkey-mnemonic="your coldkey mnemonic phrase here" \
  --from-literal=hotkey-mnemonic="your hotkey mnemonic phrase here"
```

2. Create the validator deployment:
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
      - name: validator
        image: masaengineering/subnet42:latest
        command: ["/bin/bash"]
        args: ["/app/entrypoint.sh"]
        env:
        - name: COLDKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: bittensor-mnemonics
              key: coldkey-mnemonic
        - name: HOTKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: bittensor-mnemonics
              key: hotkey-mnemonic
        - name: NETUID
          value: "165"  # Change to 59 for mainnet
        - name: SUBTENSOR_NETWORK
          value: "finney"  # Change to "test" for testnet
        - name: ROLE
          value: "validator"
        ports:
        - containerPort: 8081
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

3. Apply the deployment:
```bash
kubectl apply -f validator-deployment.yaml
```

### Miner Deployment

1. Create secrets for your miner mnemonics:
```bash
# Create secrets for coldkey and hotkey mnemonics
kubectl create secret generic bittensor-miner-mnemonics \
  --from-literal=coldkey-mnemonic="your miner coldkey mnemonic phrase here" \
  --from-literal=hotkey-mnemonic="your miner hotkey mnemonic phrase here"
```

2. Create the miner deployment:
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
      - name: miner
        image: masaengineering/subnet42:latest
        command: ["/bin/bash"]
        args: ["/app/entrypoint.sh"]
        env:
        - name: COLDKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: bittensor-miner-mnemonics
              key: coldkey-mnemonic
        - name: HOTKEY_MNEMONIC
          valueFrom:
            secretKeyRef:
              name: bittensor-miner-mnemonics
              key: hotkey-mnemonic
        - name: NETUID
          value: "165"  # Change to 59 for mainnet
        - name: SUBTENSOR_NETWORK
          value: "finney"  # Change to "test" for testnet
        - name: ROLE
          value: "miner"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      # Optional: Add node selector for GPU nodes if needed
      # nodeSelector:
      #   cloud.google.com/gke-accelerator: nvidia-tesla-t4
```

3. Apply the deployment:
```bash
kubectl apply -f miner-deployment.yaml
```

### Security Note

The mnemonic phrases are sensitive information. In production:
1. Use a secure secret management system (e.g., HashiCorp Vault, AWS Secrets Manager)
2. Consider using Kubernetes External Secrets Operator
3. Rotate secrets periodically
4. Use network policies to restrict pod communication
5. Enable Kubernetes RBAC with minimal permissions

### Monitoring in Kubernetes

View pod logs:
```bash
# For validator logs:
kubectl logs -f deployment/subnet42-validator

# For miner logs:
kubectl logs -f deployment/subnet42-miner
```

Check pod status:
```bash
kubectl get pods -l app=subnet42-validator
kubectl get pods -l app=subnet42-miner
```

### Kubernetes Troubleshooting

1. Check pod status:
```bash
kubectl describe pod -l app=subnet42-validator
# or
kubectl describe pod -l app=subnet42-miner
```

2. Verify secrets are properly mounted:
```bash
kubectl describe secret bittensor-mnemonics
kubectl describe secret bittensor-miner-mnemonics
```

3. Check container logs for detailed error messages:
```bash
kubectl logs -f <pod-name>
```

4. Verify environment variables:
```bash
kubectl exec -it <pod-name> -- env | grep BITTENSOR
```