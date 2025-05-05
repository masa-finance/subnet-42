#!/bin/bash

# Script to transfer locally generated cookies to the Docker named volume on the remote server

# Environment variables are passed from docker-compose
# REMOTE_HOST, REMOTE_USER, REMOTE_DIR should be set

echo "Transferring cookies from /app/cookies to $REMOTE_HOST..."

# Create a temporary directory on the remote server
ssh -i /root/.ssh/id_rsa $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_DIR"

# Copy cookies to the remote server
scp -i /root/.ssh/id_rsa -r /app/cookies/* $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# Copy cookies from temporary directory to the Docker volume
ssh -i /root/.ssh/id_rsa $REMOTE_USER@$REMOTE_HOST "
  # List files to make sure they were transferred
  echo 'Files in the temporary directory:'
  ls -la $REMOTE_DIR/
  
  # Create a temporary container to access the volume and copy files
  docker run --rm -v cookies-volume:/volume -v $REMOTE_DIR:/source --user root alpine sh -c \"
    echo 'Copying files to volume...'
    # Copy files to the root of the volume - they'll be accessed at /home/masa in worker-vpn
    cp -r /source/* /volume/
    # List files to confirm copy
    echo 'Files in the volume:'
    ls -la /volume/
  \"
  
  # Clean up temporary directory
  rm -rf $REMOTE_DIR
"

echo "Cookies successfully updated in the cookies-volume!" 