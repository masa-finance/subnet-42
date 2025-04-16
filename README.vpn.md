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

### 2️⃣ Prepare Twitter Cookies

1. Log into Twitter in your browser
2. Open developer tools (F12) > Application tab > Cookies
3. Create a file called `cookies.json` in your project root with the following format:

```json
[
  {
    "Name": "personalization_id",
    "Value": "<YOUR_VALUE_HERE>",
    "Path": "",
    "Domain": "twitter.com",
    "Expires": "0001-01-01T00:00:00Z",
    "RawExpires": "",
    "MaxAge": 0,
    "Secure": false,
    "HttpOnly": false,
    "SameSite": 0,
    "Raw": "",
    "Unparsed": null
  },
  {
    "Name": "kdt",
    "Value": "<YOUR_VALUE_HERE>",
    "Path": "",
    "Domain": "twitter.com",
    "Expires": "0001-01-01T00:00:00Z",
    "RawExpires": "",
    "MaxAge": 0,
    "Secure": false,
    "HttpOnly": false,
    "SameSite": 0,
    "Raw": "",
    "Unparsed": null
  },
  {
    "Name": "twid",
    "Value": "<YOUR_VALUE_HERE>",
    "Path": "",
    "Domain": "twitter.com",
    "Expires": "0001-01-01T00:00:00Z",
    "RawExpires": "",
    "MaxAge": 0,
    "Secure": false,
    "HttpOnly": false,
    "SameSite": 0,
    "Raw": "",
    "Unparsed": null
  },
  {
    "Name": "ct0",
    "Value": "<YOUR_VALUE_HERE>",
    "Path": "",
    "Domain": "twitter.com",
    "Expires": "0001-01-01T00:00:00Z",
    "RawExpires": "",
    "MaxAge": 0,
    "Secure": false,
    "HttpOnly": false,
    "SameSite": 0,
    "Raw": "",
    "Unparsed": null
  },
  {
    "Name": "auth_token",
    "Value": "<YOUR_VALUE_HERE>",
    "Path": "",
    "Domain": "twitter.com",
    "Expires": "0001-01-01T00:00:00Z",
    "RawExpires": "",
    "MaxAge": 0,
    "Secure": false,
    "HttpOnly": false,
    "SameSite": 0,
    "Raw": "",
    "Unparsed": null
  },
  {
    "Name": "att",
    "Value": "<YOUR_VALUE_HERE>",
    "Path": "",
    "Domain": "twitter.com",
    "Expires": "0001-01-01T00:00:00Z",
    "RawExpires": "",
    "MaxAge": 0,
    "Secure": false,
    "HttpOnly": false,
    "SameSite": 0,
    "Raw": "",
    "Unparsed": null
  }
]
```

⚠️ **Update the `worker-vpn` service in the docker-compose.yml file to use your Twitter username:**

```yaml
volumes:
  - ./.env:/home/masa/.env
  - ./cookies.json:/home/masa/<your_twitter_username>_twitter_cookies.json
```

### 3️⃣ Launch Everything

Start your services with:

```bash
docker compose --profile miner-vpn up -d
```

This will start three containers:

- `neuron`: Your subnet-42 miner (accessible on port 8091)
- `worker-vpn`: Your TEE worker with VPN routing (accessible on port 8080)
- `vpn`: OpenVPN client with TinyProxy (routes worker traffic through VPN)

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

### "LoginAcid" Error

If you see `login failed: auth error: LoginAcid`, try:

- Using a different ExpressVPN server location
- Checking your Twitter cookies are correct and up-to-date
- Testing with different VPN server locations to find one that isn't flagged

### VPN Connection Issues

Check the VPN container logs:

```bash
docker logs vpn
```

Look for successful connection messages or error details.

## 📝 Notes

- The `miner` profile starts the standard setup without VPN
- The `miner-vpn` profile starts everything with VPN routing
- You can have multiple cookie files for different Twitter accounts

Good luck and happy mining! 🎮🚀
