#!/bin/bash

# Environment variables are passed from docker-compose
# REMOTE_HOST or COOKIES_REMOTE_HOSTS should be set
# REMOTE_USER or COOKIES_REMOTE_USER should be set
# REMOTE_DIR or COOKIES_REMOTE_DIR should be set

# Support both singular and plural env var names
HOSTS=${COOKIES_REMOTE_HOSTS:-$REMOTE_HOST}
USER=${COOKIES_REMOTE_USER:-$REMOTE_USER}
DIR=${COOKIES_REMOTE_DIR:-$REMOTE_DIR}

# Split hosts by commas if multiple are provided
IFS=',' read -ra HOST_ARRAY <<< "$HOSTS"

# Process each host individually
for CURRENT_HOST in "${HOST_ARRAY[@]}"; do
  # Trim any whitespace
  CURRENT_HOST=$(echo "$CURRENT_HOST" | xargs)
  echo "Transferring cookies from /app/cookies to $CURRENT_HOST..."
  
  # Create a temporary directory on the remote server
  ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_rsa $USER@$CURRENT_HOST "mkdir -p $DIR"

  # Copy cookies to the remote server
  scp -o StrictHostKeyChecking=no -i /root/.ssh/id_rsa -r /app/cookies/*.json $USER@$CURRENT_HOST:$DIR/

  # Copy cookies from temporary directory to each worker's volume
  ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_rsa $USER@$CURRENT_HOST "
    # List files to make sure they were transferred
    echo 'Files in the temporary directory:'
    ls -la $DIR/
    
    # Find all cookies-volume volumes using a pattern match (both with and without project prefix)
    echo 'Finding all cookies volumes...'
    worker_volumes=\$(docker volume ls --format '{{.Name}}' | grep -E '(miner-[0-9]+_)?cookies-volume')
    
    if [ -z \"\$worker_volumes\" ]; then
      echo 'No cookies volumes found! Are the miners running?'
    else
      # Update each volume found
      echo \"\$worker_volumes\" | while read volume; do
        echo \"Updating volume: \$volume\"
        docker run --rm -v \"\$volume\":/volume -v $DIR:/source --user root alpine sh -c \"
          # Copy JSON files to volume
          echo 'Copying JSON files to volume...'
          cp -v /source/*.json /volume/ 2>/dev/null || echo 'No JSON files to copy'
          echo 'Files in the volume:'
          ls -la /volume/*.json 2>/dev/null || echo 'No JSON files found'
        \"
      done
    fi
    
    # Clean up temporary directory
    rm -rf $DIR || echo 'Could not remove temporary directory - you may need to clean it up manually'
  "

  echo "Cookies successfully updated in all miner volumes on $CURRENT_HOST!"
done

echo "All remote cookie updates completed!" 