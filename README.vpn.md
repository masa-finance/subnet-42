# 🚀 Subnet-42 Miner with VPN Setup Guide

This guide helps you set up your Subnet-42 miner with a VPN for residential IP routing. This allows your miner to be publicly accessible while your worker routes outbound traffic through a residential VPN IP.

## 📋 Prerequisites

- Docker installed
- **TorGuard VPN subscription** (strongly recommended for residential IPs)
- Twitter account credentials

## 🔧 Setup Steps

### 1️⃣ Prepare Your VPN Configuration

#### TorGuard Setup for Residential IPs

TorGuard is specifically recommended because they offer residential IP addresses, which are crucial for this setup.

1. **Subscribe to TorGuard with Residential IP add-on**:

   - Sign up for TorGuard VPN
   - Purchase the "Residential IP" add-on
   - Request residential IPs in your desired location

2. Create the required directories:

   ```bash
   mkdir -p vpn cookies
   ```

3. **Create auth.txt file**:

   Create a file with your TorGuard credentials:

   ```
   your_torguard_username
   your_torguard_password
   ```

   Save this to `vpn/auth.txt`

4. **Configure OpenVPN**:

   - Log into your TorGuard account
   - Download the OpenVPN configuration files
   - Create a `config.ovpn` file in `vpn/` with your residential servers:

   ```
   client
   dev tun
   proto udp
   # Multiple residential servers for redundancy
   remote <ip-here> <port>
   remote <ip-here> <port>
   remote-random
   remote-cert-tls server
   auth SHA256
   key-direction 1
   # Add your TorGuard certificates and keys below
   ... (rest of configuration) ...
   ```

### 2️⃣ Generate Twitter Cookies

You have two options for generating Twitter cookies:

#### Option 1: Use the Docker Cookie Generator Service (Automated)

1. **Configure Twitter Credentials**:

   Add your Twitter account credentials to your .env file:

   ```
   # Add your Twitter accounts in this format
   TWITTER_ACCOUNTS="username1:password1,username2:password2"
   # Add backup email for verification (REQUIRED)
   TWITTER_EMAIL="your_email@example.com"
   ```

   The `TWITTER_EMAIL` is used for verification challenges during login.

2. **Run the Cookie Generator Service**:

   ```bash
   docker compose --profile cookies up
   ```

   This service will:

   - Log in to your Twitter accounts
   - Generate authentication cookies
   - Save them to the `cookies/` directory in your project
   - Handle verification challenges with manual intervention if needed

3. **Verify Cookie Generation**:

   ```bash
   ls -la ./cookies/
   ```

   You should see files named `<username>_twitter_cookies.json` for each account.

#### Option 2: Run the Manual CAPTCHA Intervention Script (Recommended)

If you're encountering CAPTCHA challenges or authentication issues with the automated method, use this approach:

1. **Install Required Dependencies**:

   ```bash
   # For running cookie_grabber.py directly with Python (non-headless mode)
   pip install selenium selenium-stealth python-dotenv
   ```

   > **Note**: Running the script with Python directly opens a visible Chrome browser window, allowing you to interact with CAPTCHAs and verification challenges. This is different from the Docker approach which runs in headless mode.

2. **Set Environment Variables**:

   ```bash
   export TWITTER_ACCOUNTS="username1:password1,username2:password2"
   export TWITTER_EMAIL="your_email@example.com"
   ```

   Or create a `.env` file in the scripts directory with these variables.

3. **Run the Cookie Grabber Script**:

   ```bash
   cd scripts
   python cookie_grabber.py
   ```

4. **Manual CAPTCHA Solving**:

   - The script opens a visible browser window
   - When a CAPTCHA/authentication challenge appears, you'll see:
     ```
     ================================================================================
     MANUAL INTERVENTION REQUIRED for account: username
     Please solve the CAPTCHA or authentication challenge in the browser window
     ================================================================================
     ```
   - Manually solve the challenge in the browser window
   - The script will detect when you've solved it and continue automatically
   - Cookies will be saved to the `../cookies` directory

This manual approach is more reliable for accounts that frequently encounter verification challenges, as you can directly interact with the browser to complete any verification steps.

### 3️⃣ Launch Everything with One Command

Once you have:

- VPN files in `vpn/` (auth.txt and config.ovpn)
- Cookie files in the `cookies/` directory

You can start the full system:

```bash
docker compose --profile miner-vpn up -d
```

This command will:

1. Start the VPN service using your TorGuard residential IPs
2. Launch the TEE worker using the VPN
3. Start your subnet-42 miner

## 🧪 Testing Your Setup

### Verify Worker-VPN Routing

To make sure your worker-vpn container is properly routing through the VPN:

1. **Install curl in the worker-vpn container**:

   ```bash
   docker exec -it worker-vpn apt-get update && docker exec -it worker-vpn apt-get install -y curl
   ```

2. **Check the IP address of the worker-vpn container**:

   ```bash
   # Get the worker-vpn IP
   docker exec worker-vpn curl -s https://ifconfig.me
   ```

   Verify that this shows a different IP than your host machine, confirming traffic is routing through the VPN.

### Why Residential IPs Matter

Regular datacenter VPN IPs are often flagged and blocked by services. Residential IPs are much less likely to be detected, making them essential for reliable operation.

## 🛠️ Troubleshooting

### Cookie Generator Issues

- If the Docker cookie generator fails with `'ChromeOptions' object has no attribute 'headless'` error, use the manual script approach (Option 2)
- If manual cookie generation fails with timeout errors, you can modify the `WAITING_TIME` constant in the script (default: 3600 seconds)
- For accounts that require verification, ensure you've set the `TWITTER_EMAIL` environment variable correctly
- If using email verification, check that the email account is accessible and can receive Twitter verification codes
- Make sure Chrome is properly installed on your system when using the manual script

### Monitoring the Cookie Generation Process

- When using the Docker cookie generator, you can enable VNC to view the browser:
  ```
  ENABLE_VNC=true docker compose --profile cookies up
  ```
  Then connect to the container using a VNC viewer on port 5900

### Advanced Email Verification

For accounts that frequently require email verification:

- The script supports a special password format: `himynameisjohn`
- It will use your `TWITTER_EMAIL` with plus addressing, like: `your_email+john@example.com`
- This helps manage multiple verification emails in a single inbox
