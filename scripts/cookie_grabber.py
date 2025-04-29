#!/usr/bin/env python3
import json
import time
import os
import logging
import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Fixed output directory
OUTPUT_DIR = "/app/cookies"

# Setup logging
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Twitter cookie names to extract
COOKIE_NAMES = ["personalization_id", "kdt", "twid", "ct0", "auth_token", "att"]


def create_cookie_template(name, value):
    """
    Create a standard cookie template with the given name and value.
    Note: Cookie values should not contain double quotes as they cause errors in Go's HTTP client.
    """
    # Ensure no quotes in cookie value to prevent HTTP header issues
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    value = value.replace('"', "")

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


def setup_driver():
    """Set up and return a Chromium browser driver instance."""
    logger.info("Setting up Chromium driver...")
    options = Options()

    # Run headless for Docker environment
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")

    # Add user agent to appear as a regular browser
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Get proxy settings from environment variables
    http_proxy = os.environ.get("http_proxy")
    if http_proxy and "http://" in http_proxy:
        logger.info(f"Using proxy: {http_proxy}")
        options.add_argument(f"--proxy-server={http_proxy}")

    # Disable automation detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        logger.info("Initializing Chromium driver...")
        # Use the system chromium-driver
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)

        # Additional anti-detection measures
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        logger.info("Chromium driver setup complete")
        return driver
    except Exception as e:
        logger.error(f"Error creating Chromium driver: {str(e)}")
        raise


def login_to_twitter(driver, username, password):
    """Login to Twitter and return True if successful."""
    try:
        # Navigate to Twitter login page
        logger.info("Navigating to Twitter login page")
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(5)  # Give page time to fully load

        logger.info("Current URL: " + driver.current_url)
        logger.info("Page title: " + driver.title)

        # Find and enter username
        username_input = None
        selectors = [
            'input[autocomplete="username"]',
            'input[name="text"]',
            'input[type="text"]',
        ]

        logger.info("Trying to find username input field")
        for selector in selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                username_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_input.is_displayed():
                    logger.info(f"Found username input with selector: {selector}")
                    break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {str(e)}")
                continue

        if not username_input:
            logger.error("Could not find username input field")
            return False

        # Enter username
        logger.info(f"Entering username: {username}")
        username_input.clear()
        username_input.send_keys(username)
        time.sleep(1)

        # Click next button - try different approaches
        logger.info("Attempting to click Next button")
        try:
            # First try by text content
            logger.info("Looking for Next button by text content")
            next_buttons = driver.find_elements(
                By.XPATH, '//*[contains(text(), "Next") or contains(text(), "next")]'
            )

            if next_buttons:
                logger.info(f"Found {len(next_buttons)} potential Next buttons by text")
            else:
                logger.info("No Next buttons found by text, trying by role")
                # Try visible buttons
                next_buttons = driver.find_elements(
                    By.CSS_SELECTOR, 'div[role="button"]'
                )
                logger.info(f"Found {len(next_buttons)} potential Next buttons by role")

            # Click the first visible button
            clicked = False
            for i, button in enumerate(next_buttons):
                if button.is_displayed():
                    logger.info(f"Clicking button #{i+1}")
                    button.click()
                    clicked = True
                    break

            if not clicked:
                logger.info("No visible Next button found, trying Enter key")
                # Try pressing Enter on username field as fallback
                username_input.send_keys("\n")
        except Exception as e:
            logger.error(f"Error clicking Next button: {str(e)}")

        # Wait for password field
        logger.info("Waiting for password field")
        time.sleep(3)

        # Find password field
        password_input = None
        password_selectors = ['input[type="password"]', 'input[name="password"]']

        logger.info("Trying to find password input field")
        for selector in password_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if password_input.is_displayed():
                    logger.info(f"Found password input with selector: {selector}")
                    break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {str(e)}")
                continue

        if not password_input:
            logger.error("Could not find password input field")
            return False

        # Enter password
        logger.info("Entering password")
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)

        # Click login button - try different approaches
        logger.info("Attempting to click Login button")
        try:
            # First try by text content
            logger.info("Looking for Login button by text content")
            login_buttons = driver.find_elements(
                By.XPATH,
                '//*[contains(text(), "Log in") or contains(text(), "Login") or contains(text(), "Sign in")]',
            )

            if login_buttons:
                logger.info(
                    f"Found {len(login_buttons)} potential Login buttons by text"
                )
            else:
                logger.info("No Login buttons found by text, trying by role")
                # Try visible buttons
                login_buttons = driver.find_elements(
                    By.CSS_SELECTOR, 'div[role="button"]'
                )
                logger.info(
                    f"Found {len(login_buttons)} potential Login buttons by role"
                )

            # Click the first visible button
            clicked = False
            for i, button in enumerate(login_buttons):
                if button.is_displayed():
                    logger.info(f"Clicking button #{i+1}")
                    button.click()
                    clicked = True
                    break

            if not clicked:
                logger.info("No visible Login button found, trying Enter key")
                # Try pressing Enter on password field as fallback
                password_input.send_keys("\n")
        except Exception as e:
            logger.error(f"Error clicking Login button: {str(e)}")

        # Wait for login to complete
        logger.info("Waiting for login to complete")
        try:
            # Wait until we're logged in
            WebDriverWait(driver, 30).until(
                lambda d: "home" in d.current_url
                or "twitter.com/home" in d.current_url
                or len(d.find_elements(By.CSS_SELECTOR, 'a[aria-label="Profile"]')) > 0
            )
            logger.info("Successfully logged in")
            return True
        except TimeoutException:
            logger.error("Timeout waiting for successful login")

            # Check if we need to handle verification
            if "verify" in driver.current_url or "challenge" in driver.current_url:
                logger.warning(
                    "Verification or challenge detected that requires manual action"
                )

            logger.info(f"Current URL after timeout: {driver.current_url}")
            return False

    except Exception as e:
        logger.error(f"Error during login process: {str(e)}")
        return False


def extract_cookies(driver):
    """Extract cookies from the browser."""
    logger.info("Extracting cookies")
    browser_cookies = driver.get_cookies()
    logger.info(f"Found {len(browser_cookies)} cookies total")

    cookie_values = {}
    for cookie in browser_cookies:
        if cookie["name"] in COOKIE_NAMES:
            # Strip double quotes from cookie values to prevent HTTP header issues
            value = cookie["value"]
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]  # Remove surrounding quotes
            # Replace any remaining quotes with empty string
            value = value.replace('"', "")

            cookie_values[cookie["name"]] = value
            logger.info(f"Found cookie: {cookie['name']}")

    # Log missing cookies
    missing_cookies = [name for name in COOKIE_NAMES if name not in cookie_values]
    if missing_cookies:
        logger.warning(f"Missing cookies: {', '.join(missing_cookies)}")
    else:
        logger.info("All required cookies found")

    return cookie_values


def generate_cookies_json(cookie_values):
    """Generate the cookies JSON from the provided cookie values."""
    logger.info("Generating cookies JSON")
    cookies = []
    for name in COOKIE_NAMES:
        value = cookie_values.get(name, "<YOUR_VALUE_HERE>")
        if value == "<YOUR_VALUE_HERE>":
            logger.warning(f"Using placeholder for missing cookie: {name}")
        cookies.append(create_cookie_template(name, value))
    return cookies


def process_account(username, password):
    """Process a single Twitter account and get its cookies."""
    logger.info(f"==========================================")
    logger.info(f"Starting to process account: {username}")
    output_file = f"{username}_twitter_cookies.json"

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        driver = setup_driver()
    except Exception as e:
        logger.error(f"Failed to setup driver: {str(e)}")
        return

    try:
        success = login_to_twitter(driver, username, password)

        if success:
            logger.info(f"Login successful for {username}")
            # Go to twitter.com to ensure all cookies are set
            logger.info("Navigating to Twitter home to ensure all cookies are set")
            driver.get("https://twitter.com/home")
            time.sleep(3)  # Wait for cookies to be fully set

            cookie_values = extract_cookies(driver)
            cookies_json = generate_cookies_json(cookie_values)

            # Save cookies to file
            output_path = os.path.join(OUTPUT_DIR, output_file)
            with open(output_path, "w") as f:
                f.write(json.dumps(cookies_json, indent=2))
            logger.info(f"Saved cookies for {username} to {output_path}")
        else:
            logger.error(f"Failed to login for {username}")
    except Exception as e:
        logger.error(f"Unexpected error processing account {username}: {str(e)}")
    finally:
        logger.info("Closing Chromium driver")
        driver.quit()
        logger.info(f"Finished processing account: {username}")
        logger.info(f"==========================================")


def main():
    """Main function to process Twitter accounts from environment variable."""
    logger.info("Starting cookie grabber")

    # Get Twitter accounts from environment variable
    twitter_accounts_str = os.environ.get("TWITTER_ACCOUNTS", "")

    if not twitter_accounts_str:
        logger.error("TWITTER_ACCOUNTS environment variable is not set.")
        logger.error("Format should be: username1:password1,username2:password2")
        return

    account_pairs = twitter_accounts_str.split(",")
    logger.info(f"Found {len(account_pairs)} accounts to process")

    for account_pair in account_pairs:
        if ":" not in account_pair:
            logger.error(
                f"Invalid account format: {account_pair}. Expected format: username:password"
            )
            continue

        username, password = account_pair.split(":", 1)
        username = username.strip()
        password = password.strip()

        process_account(username, password)

    logger.info("Cookie grabber completed")


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    logger.info("Starting cookie grabber script")
    main()
