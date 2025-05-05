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
  # Create a temporary container to access the volume
  # Mount the volume at /data and ensure cookies go directly to /home/masa
  docker run --rm -v cookies-volume:/data -v $REMOTE_DIR:/source alpine sh -c '
    # Create the directory structure to match worker-vpn's expected path
    mkdir -p /data/home/masa
    # Copy the files to the correct location - directly under /home/masa
    cp -r /source/* /data/home/masa/
    # Set the correct permissions
    chown -R 1000:1000 /data
    # List the files to confirm they were copied
    echo "Files in the volume:"
    ls -la /data/home/masa/
  '
  
  # Clean up temporary directory
  rm -rf $REMOTE_DIR
"

echo "Cookies successfully updated in the cookies-volume!" 