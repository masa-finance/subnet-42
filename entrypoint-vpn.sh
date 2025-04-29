#!/bin/bash
set -e

# Create status directory
mkdir -p /var/run/vpn

# Update tinyproxy port configuration
sed -i "s/Port 8888/Port ${VPN_PORT:-3128}/g" /etc/tinyproxy/tinyproxy.conf
service tinyproxy restart

# Setup NAT for VPN tunnel
iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE

# Start OpenVPN in the background
openvpn --config /etc/openvpn/config/config.ovpn --auth-user-pass /etc/openvpn/config/auth.txt --auth-nocache --verb 3 &

# Keep container running
tail -f /dev/null 