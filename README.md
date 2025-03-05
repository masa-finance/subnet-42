# SUBNET 42

A Bittensor subnet for MASA's Subnet 42.

## Prerequisites

- Docker and Docker Compose installed
- Your Bittensor coldkey mnemonic (hotkey will be auto-generated)

## Quick Start

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/subnet-42.git
cd subnet-42
cp .env.example .env
```

2. Edit `.env` with just your coldkey:
```env
# Required: Your coldkey mnemonic phrase
COLDKEY_MNEMONIC="your coldkey mnemonic here"

# Optional: These will use defaults if not set
NETUID=165                  # defaults to 165 (testnet)
SUBTENSOR_NETWORK=test      # defaults to test
```

3. Start your miner:
```bash
docker compose up
```

That's it! The miner will automatically:
- Generate a new hotkey
- Register it to the subnet
- Start mining

To view logs:
```bash
docker compose logs -f
```

### Advanced Configuration

For more complex setups, you can:

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

### Running Multiple Miners with Docker Compose

For testnet development, you can run multiple miners using Docker Compose. This setup will automatically generate and manage hotkeys for each miner instance.

1. Create a `.env` file with your coldkey (no hotkey needed):
```env
# Required: Wallet Configuration
# Your coldkey mnemonic phrase
COLDKEY_MNEMONIC="your coldkey mnemonic here"

# Network Configuration
# Network UID (165 for testnet, 59 for mainnet)
NETUID=165

# Network name (test or finney)
SUBTENSOR_NETWORK=test
```

2. Use the multi-miner compose configuration:
```bash
# Start 5 miners (adjust number as needed)
MINER_COUNT=5 docker compose --profile multi-miner up -d

# View logs for all miners
docker compose logs -f

# Scale up or down
docker compose up -d --scale subnet42-miner=10
```

The multi-miner setup:
- Uses a shared coldkey across all instances
- Automatically generates unique hotkeys for each miner
- Stores hotkeys in a local volume for persistence
- Names instances consistently (subnet42-miner-1, subnet42-miner-2, etc.)
- Preserves hotkey assignments across restarts

Example docker-compose.yml section for multiple miners:
```yaml
services:
  subnet42-miner:
    image: masaengineering/subnet42:latest
    command: ["/bin/bash", "/app/entrypoint-multi.sh"]
    environment:
      - COLDKEY_MNEMONIC=${COLDKEY_MNEMONIC}
      - NETUID=${NETUID:-165}
      - SUBTENSOR_NETWORK=${SUBTENSOR_NETWORK:-test}
      - ROLE=miner
      - AUTO_GENERATE_HOTKEY=true
    volumes:
      - hotkeys:/root/.bittensor/wallets
    deploy:
      mode: replicated
      replicas: ${MINER_COUNT:-1}

volumes:
  hotkeys:
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

## Running Multiple Miners

For testnet development or large-scale deployments, you can run multiple miners that automatically generate and register their hotkeys. This feature uses Kubernetes StatefulSets to maintain consistent instance identities and automatically manages hotkey generation and storage.

### Prerequisites
- All standard Kubernetes prerequisites
- A coldkey with sufficient TAO for registrations
- Kubernetes cluster with RBAC enabled

### Setup Multiple Miners

1. Create the coldkey secret (this will be shared across all miners):
```bash
kubectl create secret generic bittensor-miner-mnemonics \
  --from-literal=coldkey-mnemonic="your coldkey mnemonic here"
```

2. Apply the StatefulSet configuration:
```bash
# miner-statefulset.yaml provided in the repository
kubectl apply -f miner-statefulset.yaml
```

3. Scale to desired number of miners:
```bash
# Example: Scale to 128 miners
kubectl scale statefulset subnet42-miner --replicas=128
```

### How It Works

The multi-miner setup:
- Uses a shared coldkey across all instances
- Automatically generates unique hotkeys for each miner instance
- Stores hotkeys in Kubernetes secrets for persistence
- Maintains consistent instance numbering (subnet42-miner-0, subnet42-miner-1, etc.)
- Preserves hotkey assignments across pod restarts

To use this feature:
1. Replace the standard `entrypoint.sh` with `entrypoint-multi.sh` in your deployment
2. Ensure your ServiceAccount has permissions to manage secrets
3. Set `AUTO_GENERATE_HOTKEY=true` in your deployment

Example StatefulSet configuration:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: subnet42-miner
spec:
  serviceName: subnet42-miner
  replicas: 1  # Adjust as needed
  template:
    spec:
      containers:
      - name: miner
        image: masaengineering/subnet42:latest
        command: ["/bin/bash"]
        args: ["/app/entrypoint-multi.sh"]
        env:
        - name: AUTO_GENERATE_HOTKEY
          value: "true"
        # ... other standard environment variables ...
```

### Security Considerations

When running multiple miners:
1. Protect the coldkey mnemonic carefully - it's shared across all instances
2. Monitor hotkey secret creation and management
3. Use network policies to restrict pod communication
4. Consider using node anti-affinity rules to spread miners across nodes
5. Implement proper monitoring for all instances

### Resource Management

For large deployments:
1. Calculate total resource requirements before scaling
2. Consider using node selectors or taints/tolerations for specialized hardware
3. Monitor network bandwidth and adjust accordingly
4. Use horizontal pod autoscaling based on custom metrics if needed