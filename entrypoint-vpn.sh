#!/bin/bash
set -e

echo "Starting VPN service..."

# Update tinyproxy port configuration
echo "Configuring tinyproxy..."
sed -i "s/Port 8888/Port ${VPN_PORT:-3128}/g" /etc/tinyproxy/tinyproxy.conf

# Make sure tinyproxy will accept connections from all IPs
grep -q "^Allow 0.0.0.0/0" /etc/tinyproxy/tinyproxy.conf || echo "Allow 0.0.0.0/0" >> /etc/tinyproxy/tinyproxy.conf

# Set additional tinyproxy configs for stability
sed -i 's/^#DisableViaHeader Yes/DisableViaHeader Yes/' /etc/tinyproxy/tinyproxy.conf
sed -i 's/^MaxClients 100/MaxClients 200/' /etc/tinyproxy/tinyproxy.conf
sed -i 's/^Timeout 600/Timeout 1800/' /etc/tinyproxy/tinyproxy.conf

# Randomize User-Agent
echo "RandomizeUserAgent Yes" >> /etc/tinyproxy/tinyproxy.conf

# Apply sysctl setting
echo "Setting up IP forwarding..."
sysctl -p

# Start tinyproxy in background
echo "Starting tinyproxy service..."
service tinyproxy restart

# Setup NAT for VPN tunnel
echo "Setting up NAT routing..."
iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE

# Setting up DNS leak protection
echo "Setting up DNS leak protection..."
iptables -t nat -A PREROUTING -i eth0 -p udp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 53 -j REDIRECT --to-ports 5353

# Setting up kill-switch
echo "Setting up kill-switch..."
iptables -A OUTPUT -o eth0 ! -d 144.229.29.0/24 -j DROP
# Allow VPN server IPs
for ip in 144.229.29.31 144.229.29.33 144.229.29.35 144.229.29.37 144.229.29.102 144.229.28.9 144.229.28.241; do
    iptables -A OUTPUT -o eth0 -d $ip -j ACCEPT
done

# Create a status file that the healthcheck will check
touch /tmp/vpn_ready
echo "0" > /tmp/vpn_ready

# Start a background process to watch for the initialization message
echo "Starting OpenVPN log monitor..."
openvpn --config /etc/openvpn/config/config.ovpn --auth-user-pass /etc/openvpn/config/auth.txt --auth-nocache --verb 3 2>&1 | tee /var/log/openvpn.log | while read line; do
    echo "$line"
    if [[ "$line" == *"Initialization Sequence Completed"* ]]; then
        echo "VPN CONNECTED SUCCESSFULLY!"
        echo "1" > /tmp/vpn_ready
    fi
done &

# Connection monitor
echo "Setting up connection monitor..."
(
while true; do
    sleep 60
    if ! ping -c 1 1.1.1.1 > /dev/null 2>&1; then
        echo "Connection seems down, restarting VPN..."
        pkill -f "openvpn --config"
        sleep 5
        # Start OpenVPN again
        openvpn --config /etc/openvpn/config/config.ovpn --auth-user-pass /etc/openvpn/config/auth.txt --auth-nocache --verb 3 2>&1 | tee /var/log/openvpn.log | while read line; do
            echo "$line"
            if [[ "$line" == *"Initialization Sequence Completed"* ]]; then
                echo "VPN RECONNECTED SUCCESSFULLY!"
                echo "1" > /tmp/vpn_ready
            fi
        done &
    fi
done
) &

# Keep container running
echo "VPN setup complete, keeping container alive..."
tail -f /dev/null 