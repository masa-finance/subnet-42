#!/bin/bash

# Wait for VPN container to be up
echo "Waiting for VPN container to be ready..."
sleep 15

# Get VPN container IP
VPN_IP=$(getent hosts vpn | awk '{ print $1 }')
echo "VPN container IP: $VPN_IP"

# Add route to send internet traffic through VPN
ip route add default via $VPN_IP
echo "Added route via $VPN_IP"