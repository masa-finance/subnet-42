#!/bin/bash
set -e

# If auth file is provided as environment variables, create it
if [ ! -z "$OVPN_USERNAME" ] && [ ! -z "$OVPN_PASSWORD" ]; then
    echo "$OVPN_USERNAME" > /etc/openvpn/auth.txt
    echo "$OVPN_PASSWORD" >> /etc/openvpn/auth.txt
    chmod 600 /etc/openvpn/auth.txt
    
    # If auth-user-pass is not in the config, add it
    if ! grep -q "auth-user-pass" /etc/openvpn/config.ovpn; then
        echo "auth-user-pass auth.txt" >> /etc/openvpn/config.ovpn
    fi
fi

# Start OpenVPN
echo "Starting OpenVPN..."
openvpn --config /etc/openvpn/config.ovpn