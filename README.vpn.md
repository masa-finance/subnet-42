# 🚀 Subnet-42 Miner with VPN Setup Guide

This guide will help you set up your Subnet-42 miner with a VPN for residential IP routing. This configuration allows your miner to be publicly accessible while your worker routes outbound traffic through a VPN to appear as if it's coming from a residential IP.

## 📋 Prerequisites

- Docker installed
- ExpressVPN subscription (or another OpenVPN-compatible VPN)
- TWITTER_ACCOUNTS defined in .env, with username:password for each account, comma separated

## 🔧 Setup Steps

### 1️⃣ Prepare Your VPN Configuration

**Create auth.txt file:**

```
your_expressvpn_username
your_expressvpn_password
```

**Get your OpenVPN configuration:**

1. Log into your ExpressVPN account
2. Go to "Set Up ExpressVPN" > "Manual Configuration" > "OpenVPN"
3. Download the .ovpn file for your preferred location
4. Rename it to `config.ovpn` and place it in your project root
5. Edit the file to remove any `auth-user-pass` lines

### 2️⃣ Configure Twitter Accounts

Add your Twitter account credentials to your .env file:

```
# Add your Twitter accounts in this format
TWITTER_ACCOUNTS="username1:password1,username2:password2"
```

The system will automatically log in to Twitter and generate the required cookie files when you start the services. No manual cookie extraction is needed anymore!

### 3️⃣ Launch Everything

Start your services with:

```bash
docker compose --profile miner-vpn up -d
```

This will start four containers:

- `neuron`: Your subnet-42 miner (accessible on port 8091)
- `cookie-generator`: Automatically logs in to Twitter and extracts cookies
- `worker-vpn`: Your TEE worker with VPN routing (accessible on port 8080)
- `vpn`: OpenVPN client with TinyProxy (routes worker traffic through VPN)

The cookie-generator service will run once, create the necessary cookie files in the `cookies/` directory, and then exit. The worker-vpn service will wait for the cookie generation to complete before starting. The `cookies/` directory will be created automatically if it doesn't exist.

## 🧪 Testing Your Setup

### Install Testing Tools

```bash
# Install curl in the worker container
docker exec worker-vpn apt-get update && docker exec worker-vpn apt-get install -y curl iputils-ping
```

### Test VPN Connectivity

```bash
# Check if worker can reach the VPN container
docker exec worker-vpn ping -c 2 vpn

# Test if the VPN proxy is working
docker exec vpn curl -x http://localhost:3128 https://ifconfig.me

# Test if worker can access the internet through the proxy
docker exec worker-vpn curl -v -x http://vpn:3128 https://ifconfig.me
```

If everything is working, these commands should return the ExpressVPN IP address, not your server's IP.

### Test Service Accessibility

- Miner: `curl http://your-server-ip:8091`
- Worker: `curl http://your-server-ip:8080`

Both should be accessible from the public internet.

## 🔍 Troubleshooting

### Cookie Generation Issues

If you encounter issues with automatic cookie generation:

```bash
# View cookie generator logs
docker compose --profile miner-vpn logs cookie-generator

# Restart cookie generation if needed
docker compose --profile miner-vpn up --force-recreate cookie-generator
```

### "LoginAcid" Error

If you see `login failed: auth error: LoginAcid`, try:

- Using a different ExpressVPN server location
- Checking your Twitter account credentials in .env
- Testing with different VPN server locations to find one that isn't flagged

### VPN Connection Issues

Check the VPN container logs:

```bash
docker logs vpn
```

Look for successful connection messages or error details.
