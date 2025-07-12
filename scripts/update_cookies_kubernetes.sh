#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if DEPLOYMENTS variable is set
if [ -z "$DEPLOYMENTS" ]; then
    echo "Error: DEPLOYMENTS variable not set in .env file"
    echo "Please add DEPLOYMENTS=deployment1,deployment2,deployment3 to your .env file"
    exit 1
fi

# Check if NAMESPACE variable is set
if [ -z "$NAMESPACE" ]; then
    echo "Error: NAMESPACE variable not set in .env file"
    echo "Please add NAMESPACE=your-namespace to your .env file"
    exit 1
fi

# Configuration for timeouts and retries
KUBECTL_TIMEOUT=${KUBECTL_TIMEOUT:-300}  # 5 minutes default
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-5}

echo "Deployments to process: $DEPLOYMENTS"
echo "Namespace: $NAMESPACE"
echo "Kubectl timeout: ${KUBECTL_TIMEOUT}s"
echo "Max retries: $MAX_RETRIES"

# Function to copy file with retry logic
copy_file_with_retry() {
    local file="$1"
    local pod_name="$2"
    local namespace="$3"
    local max_retries="$4"
    local filename=$(basename "$file")
    
    for ((i=1; i<=max_retries; i++)); do
        echo "Copying $filename (attempt $i/$max_retries)..."
        
        # Use timeout command to limit kubectl execution time
        if timeout $KUBECTL_TIMEOUT kubectl --kubeconfig ./kubeconfig.yaml cp "$file" "$namespace/$pod_name:/home/masa/" -c tee-worker --request-timeout=${KUBECTL_TIMEOUT}s; then
            echo "✓ Successfully copied $filename"
            return 0
        else
            local exit_code=$?
            if [ $exit_code -eq 124 ]; then
                echo "⚠ Timeout occurred while copying $filename (attempt $i/$max_retries)"
            else
                echo "⚠ Failed to copy $filename (attempt $i/$max_retries, exit code: $exit_code)"
            fi
            
            if [ $i -lt $max_retries ]; then
                echo "Waiting ${RETRY_DELAY}s before retry..."
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    echo "✗ Failed to copy $filename after $max_retries attempts"
    return 1
}

# Convert comma-separated list to array
IFS=',' read -ra DEPLOYMENT_ARRAY <<< "$DEPLOYMENTS"

# Track overall success
OVERALL_SUCCESS=true
FAILED_FILES=()

# Process each deployment
for deployment in "${DEPLOYMENT_ARRAY[@]}"; do
    echo ""
    echo "Processing deployment: $deployment"
    
    # Get the current pod name for the deployment
    POD_NAME=$(kubectl --kubeconfig ./kubeconfig.yaml get pods -n "$NAMESPACE" -l app="$deployment" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$POD_NAME" ]; then
        echo "Warning: No pod found for deployment $deployment in namespace $NAMESPACE, skipping..."
        continue
    fi
    
    echo "Found pod: $POD_NAME in namespace: $NAMESPACE"
    echo "Copying cookie files to /home/masa/..."
    
    # Copy all JSON cookie files to the tee-worker container
    for file in ./cookies/*.json; do
        if [ -f "$file" ]; then
            if ! copy_file_with_retry "$file" "$POD_NAME" "$NAMESPACE" "$MAX_RETRIES"; then
                OVERALL_SUCCESS=false
                FAILED_FILES+=("$(basename "$file") -> $deployment")
            fi
        fi
    done
    
    echo "Cookie files processing completed for $deployment!"
done

echo ""
echo "All deployments processed!"

# Report final status
if [ "$OVERALL_SUCCESS" = true ]; then
    echo "✓ All cookie files copied successfully!"
    exit 0
else
    echo "⚠ Some files failed to copy:"
    for failed in "${FAILED_FILES[@]}"; do
        echo "  - $failed"
    done
    echo "Consider increasing KUBECTL_TIMEOUT or MAX_RETRIES environment variables"
    exit 1
fi