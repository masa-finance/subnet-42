#!/bin/bash

# Script to transfer locally generated cookies to worker volumes on the remote server

# Environment variables are passed from docker-compose
# REMOTE_HOST, REMOTE_USER, REMOTE_DIR should be set

echo "Transferring cookies from /app/cookies to $REMOTE_HOST..."

# Create a temporary directory on the remote server
ssh -i /root/.ssh/id_rsa $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_DIR"

# Copy cookies to the remote server
scp -i /root/.ssh/id_rsa -r /app/cookies/* $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# Copy cookies from temporary directory to each worker's volume
ssh -i /root/.ssh/id_rsa $REMOTE_USER@$REMOTE_HOST "
  # List files to make sure they were transferred
  echo 'Files in the temporary directory:'
  ls -la $REMOTE_DIR/
  
  # Find all cookies-volume volumes using a pattern match (both with and without project prefix)
  echo 'Finding all cookies volumes...'
  worker_volumes=\$(docker volume ls --format '{{.Name}}' | grep -E '(miner-[0-9]+_)?cookies-volume')
  
  if [ -z \"\$worker_volumes\" ]; then
    echo 'No cookies volumes found! Are the miners running?'
  else
    # Update each volume found
    echo \"\$worker_volumes\" | while read volume; do
      echo \"Updating volume: \$volume\"
      docker run --rm -v \"\$volume\":/volume -v $REMOTE_DIR:/source --user root alpine sh -c \"
        # Update only JSON files in the volume, don't touch other files
        echo 'Copying JSON files to volume...'
        cp -v /source/*.json /volume/
        echo 'Files in the volume:'
        ls -la /volume/*.json 2>/dev/null || echo 'No JSON files found'
      \"
    done
  fi
  
  # Clean up temporary directory
  rm -rf $REMOTE_DIR
"

echo "Cookies successfully updated in all miner volumes!" 