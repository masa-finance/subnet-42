#!/usr/bin/env python3
import json
import time
import os
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import random

# Twitter cookie names to extract
COOKIE_NAMES = ["personalization_id", "kdt", "twid", "ct0", "auth_token", "att"]

# Get output directory from environment variable
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./cookies")


def create_cookie_template(name, value):
    """Create a standard cookie template with the given name and value."""
    return {
        "Name": name,
        "Value": value,
        "Path": "",
        "Domain": "twitter.com",
        "Expires": "0001-01-01T00:00:00Z",
        "RawExpires": "",
        "MaxAge": 0,
        "Secure": False,
        "HttpOnly": False,
        "SameSite": 0,
        "Raw": "",
        "Unparsed": None,
    }


async def login_to_twitter(page, username, password):
    """Login to Twitter and return True if successful."""
    try:
        # Navigate to Twitter login page
        print("Opening Twitter login page...")

        # More stealth: Add random mouse movements
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

        # Open Twitter with a realistic browser wait time
        await page.goto("https://twitter.com", wait_until="networkidle")
        await page.wait_for_timeout(random.randint(2000, 4000))

        # Move around randomly to simulate human behavior
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

        # Now go to login page (more natural flow)
        print("Navigating to login page...")
        await page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")
        await page.wait_for_timeout(random.randint(1000, 3000))
        print("Twitter login page loaded")

        # Save screenshot for debugging
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "login-page.png"))

        # Wait for and enter username
        print("Looking for username field...")
        await page.wait_for_selector('input[autocomplete="username"]', timeout=15000)

        # Type username slowly like a human
        await page.type(
            'input[autocomplete="username"]', username, delay=random.randint(50, 150)
        )
        print(f"Entered username: {username}")

        # Random wait before clicking next
        await page.wait_for_timeout(random.randint(500, 1500))

        # Click next button
        next_button = await page.query_selector('div[role="button"]:has-text("Next")')
        if not next_button:
            # Try alternate selector
            next_button = await page.query_selector(
                'div[data-testid="auth_input_next_button"]'
            )

        if next_button:
            # Move mouse to button first
            box = await next_button.bounding_box()
            if box:
                await page.mouse.move(
                    box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                )
                await page.wait_for_timeout(random.randint(300, 800))

            await next_button.click()
            print("Clicked next button")
        else:
            # Try pressing Enter as fallback
            await page.press('input[autocomplete="username"]', "Enter")
            print("Pressed Enter on username field")

        # Wait for password field with longer timeout
        print("Waiting for password field...")
        await page.wait_for_selector('input[type="password"]', timeout=20000)

        # Random wait before entering password
        await page.wait_for_timeout(random.randint(500, 1500))

        # Save screenshot for debugging
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "password-page.png"))

        # Type password slowly like a human
        await page.type(
            'input[type="password"]', password, delay=random.randint(50, 150)
        )
        print("Entered password")

        # Random wait before clicking login
        await page.wait_for_timeout(random.randint(500, 1500))

        # Click login button
        login_button = await page.query_selector(
            'div[data-testid="LoginForm_Login_Button"]'
        )
        if not login_button:
            # Try alternate selector
            login_button = await page.query_selector(
                'div[role="button"]:has-text("Log in")'
            )

        if login_button:
            # Move mouse to button first
            box = await login_button.bounding_box()
            if box:
                await page.mouse.move(
                    box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                )
                await page.wait_for_timeout(random.randint(300, 800))

            await login_button.click()
            print("Clicked login button")
        else:
            # Try pressing Enter as fallback
            await page.press('input[type="password"]', "Enter")
            print("Pressed Enter on password field")

        # Wait for home page to load or verification page with longer timeout
        try:
            # Wait for a success indicator (home timeline or profile icon)
            print("Waiting for successful login...")
            success = await page.wait_for_selector(
                'a[data-testid="AppTabBar_Profile_Link"]', timeout=25000
            )
            if success:
                print("Successfully logged in!")

                # Random wait before taking screenshot
                await page.wait_for_timeout(random.randint(1000, 2000))

                # Save screenshot for debugging
                await page.screenshot(path=os.path.join(OUTPUT_DIR, "home-page.png"))
                return True
        except Exception as e:
            print(f"Could not verify successful login: {str(e)}")

            # Check if we're at verification page
            verification_detected = await page.query_selector(
                "text=Verify your identity"
            )
            if verification_detected:
                print("Identity verification required - can't continue automatically")
                await page.screenshot(
                    path=os.path.join(OUTPUT_DIR, "verification-page.png")
                )
                return False

        # Check if there's an error
        error_msg = await page.query_selector("text=Wrong password")
        if error_msg:
            print("Login failed: Wrong password")
            return False

        # Save final state for debugging
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "final-state.png"))

        # If we get here, we're not sure if login succeeded - try visiting home
        print("Checking if login was successful by visiting home page...")
        await page.goto("https://twitter.com/home", wait_until="networkidle")
        await page.wait_for_timeout(random.randint(2000, 4000))

        # If we're on the home page, login succeeded
        home_check = await page.query_selector('a[data-testid="AppTabBar_Home_Link"]')
        if home_check:
            print("Successfully navigated to home page!")
            return True

        return False

    except Exception as e:
        print(f"Error during login: {str(e)}")
        try:
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "error-page.png"))
        except:
            pass
        return False


async def extract_cookies(context):
    """Extract cookies from the browser."""
    browser_cookies = await context.cookies()
    print(f"Found {len(browser_cookies)} cookies in total")

    cookie_values = {}
    for cookie in browser_cookies:
        if cookie["name"] in COOKIE_NAMES:
            cookie_values[cookie["name"]] = cookie["value"]

    print(
        f"Extracted {len(cookie_values)} Twitter cookies: {', '.join(cookie_values.keys())}"
    )

    return cookie_values


def generate_cookies_json(cookie_values):
    """Generate the cookies JSON from the provided cookie values."""
    cookies_json = []

    for name in COOKIE_NAMES:
        value = cookie_values.get(name, f"<MISSING_{name}>")
        cookies_json.append(create_cookie_template(name, value))

    return cookies_json


async def process_account(username, password):
    """Process a single Twitter account and get its cookies."""
    # Set output filename based on username
    output_file = f"{username}_twitter_cookies.json"
    print(f"Will save cookies to: {output_file}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as playwright:
        # Configure proxy if set
        proxy = None
        http_proxy = os.environ.get("http_proxy")
        if http_proxy:
            print(f"Using proxy: {http_proxy}")
            if http_proxy.startswith("http://"):
                http_proxy = http_proxy[7:]  # Remove http:// prefix
            server = http_proxy
            proxy = {"server": server}
            print(f"Configured proxy server: {server}")

        # Launch the browser with appropriate flags
        print("Launching browser...")
        browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--lang=en-US,en",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
        ]

        browser = await playwright.chromium.launch(
            headless=True,
            proxy=proxy,
            args=browser_args,
        )

        # Create a browser context with realistic profile
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

        # Create a context that appears more like a real browser
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            java_script_enabled=True,
            ignore_https_errors=False,
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Chromium";v="119", "Google Chrome";v="119"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": "Windows",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )

        # Set browser permissions
        await context.grant_permissions(["geolocation"])

        # Add JavaScript to avoid detection
        await context.add_init_script(
            """
        // Overwrite the automation detection methods
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        
        // Disable notifications
        if (window.Notification) {
            window.Notification.permission = 'denied';
        }
        
        // Fix iframe focus issues
        if (window.top !== window.self) {
            window.top.focus();
        }
        """
        )

        # Create a new page
        page = await context.new_page()

        try:
            print(f"Starting login process for user: {username}")
            success = await login_to_twitter(page, username, password)

            if success:
                print("Login successful. Extracting cookies...")
                # Go to twitter.com to ensure all cookies are set
                await page.goto("https://twitter.com/home", wait_until="networkidle")
                await page.wait_for_timeout(
                    5000
                )  # Wait 5 seconds for cookies to fully set

                cookie_values = await extract_cookies(context)

                # Check if we got all the cookies
                missing_cookies = [
                    name for name in COOKIE_NAMES if name not in cookie_values
                ]
                if missing_cookies:
                    print(
                        f"Warning: The following cookies could not be extracted: {', '.join(missing_cookies)}"
                    )

                # Generate cookies JSON
                cookies_json = generate_cookies_json(cookie_values)

                # Save individual file
                formatted_json = json.dumps(cookies_json, indent=2)
                output_path = os.path.join(OUTPUT_DIR, output_file)
                print(f"Saving cookies to path: {output_path}")
                with open(output_path, "w") as f:
                    f.write(formatted_json)
                print(f"Cookies JSON saved to {output_path}")

                # Create a dummy cookies.json in the parent directory for compatibility
                parent_dir = os.path.dirname(OUTPUT_DIR)
                dummy_path = os.path.join(parent_dir, "cookies.json")
                with open(dummy_path, "w") as f:
                    f.write('{"status": "ok"}')
                print(f"Created dummy cookies.json at {dummy_path}")

                print(
                    f"After writing, contents of output directory: {os.listdir(OUTPUT_DIR)}"
                )
                return True
            else:
                print("Failed to login to Twitter.")
                return False
        finally:
            await browser.close()
            print("Browser closed")


async def main():
    """Main function to process Twitter accounts from environment variable."""
    # Get Twitter accounts from environment variable
    twitter_accounts_str = os.environ.get("TWITTER_ACCOUNTS", "")

    if not twitter_accounts_str:
        print("Error: TWITTER_ACCOUNTS environment variable is not set.")
        print("Format should be: username1:password1,username2:password2")
        return

    account_pairs = twitter_accounts_str.split(",")
    success = False

    for account_pair in account_pairs:
        if ":" not in account_pair:
            print(
                f"Invalid account format: {account_pair}. Expected format: username:password"
            )
            continue

        username, password = account_pair.split(":", 1)
        username = username.strip()
        password = password.strip()

        print(f"\n--- Processing account: {username} ---")
        result = await process_account(username, password)
        success = success or result

    if not success:
        print("\nAll cookie generation attempts failed!")
        # Create placeholder file if all attempts failed
        try:
            placeholder_path = os.path.join(OUTPUT_DIR, "placeholder_cookies.json")
            with open(placeholder_path, "w") as f:
                placeholder = [
                    create_cookie_template(name, f"<PLACEHOLDER_{name}>")
                    for name in COOKIE_NAMES
                ]
                f.write(json.dumps(placeholder, indent=2))
            print(f"Created placeholder cookies file at {placeholder_path}")
        except Exception as e:
            print(f"Error creating placeholder file: {e}")


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    asyncio.run(main())
