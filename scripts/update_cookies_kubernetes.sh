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

echo "Deployments to process: $DEPLOYMENTS"
echo "Namespace: $NAMESPACE"

# Convert comma-separated list to array
IFS=',' read -ra DEPLOYMENT_ARRAY <<< "$DEPLOYMENTS"

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
            echo "Copying $(basename "$file")..."
            kubectl --kubeconfig ./kubeconfig.yaml cp "$file" "$NAMESPACE/$POD_NAME:/home/masa/" -c tee-worker
        fi
    done
    
    echo "Cookie files copied successfully for $deployment!"
done

echo ""
echo "All deployments processed!"