#!/bin/bash
set -e

# Create an auth file with credentials
if [ ! -z "$OVPN_USERNAME" ] && [ ! -z "$OVPN_PASSWORD" ]; then
    echo "$OVPN_USERNAME" > /etc/openvpn/auth.txt
    echo "$OVPN_PASSWORD" >> /etc/openvpn/auth.txt
    chmod 600 /etc/openvpn/auth.txt
    echo "Auth file created."
fi

# Modify OpenVPN config to use auth file explicitly
if [ -f /etc/openvpn/config.ovpn ]; then
    # Remove any existing auth-user-pass lines
    sed -i '/auth-user-pass/d' /etc/openvpn/config.ovpn
    
    # Add our auth file directive
    echo "auth-user-pass auth.txt" >> /etc/openvpn/config.ovpn
    
    # Add auth-nocache to prevent OpenVPN from trying to ask for credentials
    if ! grep -q "auth-nocache" /etc/openvpn/config.ovpn; then
        echo "auth-nocache" >> /etc/openvpn/config.ovpn
    fi
    
    # Add daemon and log options to run in background
    echo "daemon" >> /etc/openvpn/config.ovpn
    echo "log /var/log/openvpn.log" >> /etc/openvpn/config.ovpn
    
    echo "OpenVPN config modified for non-interactive use."
fi

# Start OpenVPN
echo "Starting OpenVPN..."
openvpn --config /etc/openvpn/config.ovpn

# Wait for VPN connection to establish
sleep 10

# Print the current external IP
echo "External IP after VPN connection:"
curl -s https://ifconfig.me

# Keep the container running
tail -f /var/log/openvpn.log