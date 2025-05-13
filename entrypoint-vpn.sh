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

# Apply sysctl setting
echo "Setting up IP forwarding..."
sysctl -p

# Start tinyproxy in background
echo "Starting tinyproxy service..."
service tinyproxy restart

# Setup NAT for VPN tunnel
echo "Setting up NAT routing..."
iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE

# Create a status file that the healthcheck will check
touch /tmp/vpn_ready
echo "0" > /tmp/vpn_ready

# Add IP verification function
verify_ip() {
    CURRENT_IP=$(curl -s -x http://localhost:${VPN_PORT:-3128} https://api.ipify.org || echo "")
    if [ -z "$CURRENT_IP" ]; then
        echo "Failed to verify IP address"
        return 1
    else
        echo "Current IP: $CURRENT_IP"
        return 0
    fi
}

# VPN reconnection function with max retries
vpn_reconnect() {
    local max_retries=5
    local retry=0
    
    echo "Reconnecting VPN..."
    killall openvpn || true
    echo "0" > /tmp/vpn_ready
    sleep 2
    
    while [ $retry -lt $max_retries ]; do
        openvpn --config /etc/openvpn/config/config.ovpn --auth-user-pass /etc/openvpn/config/auth.txt --auth-nocache --verb 3 > /var/log/openvpn.log 2>&1 &
        local pid=$!
        
        # Wait for connection to establish
        for i in {1..30}; do
            if grep -q "Initialization Sequence Completed" /var/log/openvpn.log; then
                echo "VPN CONNECTED SUCCESSFULLY!"
                echo "1" > /tmp/vpn_ready
                
                # Verify IP after connection
                sleep 5
                if verify_ip; then
                    return 0
                else
                    echo "IP verification failed, retrying..."
                    break
                fi
            fi
            sleep 1
        done
        
        echo "VPN connection attempt $((retry+1)) failed"
        kill $pid || true
        sleep 5
        retry=$((retry+1))
    done
    
    echo "Failed to establish VPN connection after $max_retries attempts"
    return 1
}

# Function to check if IP rotation is needed
check_rotation() {
    # Random rotation interval between 30-60 minutes
    ROTATION_INTERVAL=$((RANDOM % 1800 + 1800))  # 30-60 minutes in seconds
    
    echo "IP rotation will occur every $((ROTATION_INTERVAL/60)) minutes"
    
    while true; do
        sleep $ROTATION_INTERVAL
        echo "Performing scheduled IP rotation"
        vpn_reconnect
        
        # If rotation successful, reset timer with a new random interval
        if [ $? -eq 0 ]; then
            ROTATION_INTERVAL=$((RANDOM % 1800 + 1800))
            echo "Next IP rotation in $((ROTATION_INTERVAL/60)) minutes"
        else
            echo "IP rotation failed, will retry in 5 minutes"
            sleep 300
        fi
    done
}

# Start OpenVPN connection
echo "Starting OpenVPN log monitor..."
openvpn --config /etc/openvpn/config/config.ovpn --auth-user-pass /etc/openvpn/config/auth.txt --auth-nocache --verb 3 2>&1 | tee /var/log/openvpn.log | while read line; do
    echo "$line"
    if [[ "$line" == *"Initialization Sequence Completed"* ]]; then
        echo "VPN CONNECTED SUCCESSFULLY!"
        echo "1" > /tmp/vpn_ready
        
        # Verify initial IP
        sleep 5
        verify_ip
    fi
done &

# Start IP rotation in background
check_rotation &

# Keep container running
echo "VPN setup complete, keeping container alive..."
tail -f /dev/null 