#!/usr/bin/env python3
import json
import time
import os
import logging
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import random
from selenium_stealth import stealth
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Set output directory based on environment
running_in_docker = os.environ.get("RUNNING_IN_DOCKER", "false").lower() == "true"
if running_in_docker:
    OUTPUT_DIR = "/app/cookies"
    logger.info("Docker environment detected, saving cookies to /app/cookies")
else:
    OUTPUT_DIR = "../cookies"
    logger.info("Local environment detected, saving cookies to ../cookies")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Twitter cookie names to extract
COOKIE_NAMES = ["personalization_id", "kdt", "twid", "ct0", "auth_token", "att"]

# Twitter domains to handle
TWITTER_DOMAINS = ["twitter.com", "x.com"]

# Constants for manual intervention
POLLING_INTERVAL = 5  # seconds between home page checks during manual intervention
MAX_WAITING_TIME = 300  # maximum seconds to wait for manual intervention (5 minutes)


def take_screenshot(driver, name):
    """Take a screenshot for debugging purposes."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/{timestamp}_{name}.png"
    try:
        driver.save_screenshot(filename)
        logger.info(f"Screenshot saved: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to take screenshot {name}: {str(e)}")
        return None


def create_cookie_template(name, value, domain="twitter.com"):
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
        "Domain": domain,
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
    """Set up and return a visible (non-headless) Chromium browser driver instance."""
    logger.info("Setting up visible Chromium driver...")

    # Create Chrome options manually instead of using uc.ChromeOptions()
    # This helps avoid the headless attribute error in undetected-chromedriver
    options = webdriver.ChromeOptions()

    # Common options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=IsolateOrigins")
    options.add_argument("--disable-site-isolation-trials")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Add a random viewport size
    width = random.randint(1050, 1200)
    height = random.randint(800, 950)
    options.add_argument(f"--window-size={width},{height}")

    # Add more randomized user agents
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.44",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    ]
    user_agent = random.choice(user_agents)
    options.add_argument(f"--user-agent={user_agent}")

    # Get proxy settings from environment variables
    http_proxy = os.environ.get("http_proxy")
    if http_proxy and "http://" in http_proxy:
        logger.info(f"Using proxy: {http_proxy}")
        options.add_argument(f"--proxy-server={http_proxy}")

    try:
        logger.info("Initializing visible Chrome driver...")

        # Use Selenium's ChromeDriver directly with undetected_chromedriver modifications
        # instead of uc.Chrome which has the headless attribute issue
        driver = webdriver.Chrome(options=options)

        logger.info("Successfully initialized Chrome driver")

        # Additional anti-detection measures
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Apply stealth settings
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        return driver
    except Exception as e:
        logger.error(f"Error creating Chrome driver: {str(e)}")
        raise


def human_like_typing(element, text):
    """Simulate human-like typing with random delays between keypresses."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.25))  # Random delay between keypresses


def login_to_twitter(driver, username, password):
    """Login to Twitter with manual intervention capability for authentication challenges."""
    try:
        # Navigate to Twitter login page
        logger.info(f"Navigating to Twitter login page for account: {username}")
        driver.get("https://twitter.com/i/flow/login")

        # Random initial wait (4-7 seconds) to mimic human page load observation
        load_wait = random.uniform(4, 7)
        time.sleep(load_wait)

        logger.info("Current URL: " + driver.current_url)
        logger.info("Page title: " + driver.title)

        # Simulate some random mouse movements before interacting with the page
        try:
            # Move to random positions on the page
            action = ActionChains(driver)
            for _ in range(3):  # Make 3 random movements
                x = random.randint(100, 700)
                y = random.randint(100, 500)
                action.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.5, 1.5))
                # Reset position to (0,0) to avoid moving off-screen
                action.move_by_offset(-x, -y).perform()
        except Exception as e:
            logger.warning(f"Mouse movement simulation failed: {str(e)}")

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
        human_like_typing(username_input, username)
        # Pause after typing (like a human would)
        time.sleep(random.uniform(0.8, 1.5))

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
                    # Move mouse to the button first (more human-like)
                    try:
                        ActionChains(driver).move_to_element(button).pause(
                            random.uniform(0.3, 0.7)
                        ).perform()
                    except Exception as e:
                        logger.warning(f"Failed to move mouse to button: {str(e)}")
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
        human_like_typing(password_input, password)
        # Pause after typing (like a human would)
        time.sleep(random.uniform(0.8, 1.5))

        # Sometimes humans pause/think before clicking login
        time.sleep(random.uniform(1, 3))

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
                    # Move mouse to the button first (more human-like)
                    try:
                        ActionChains(driver).move_to_element(button).pause(
                            random.uniform(0.3, 0.7)
                        ).perform()
                    except Exception as e:
                        logger.warning(f"Failed to move mouse to button: {str(e)}")
                    button.click()
                    clicked = True
                    break

            if not clicked:
                logger.info("No visible Login button found, trying Enter key")
                # Try pressing Enter on password field as fallback
                password_input.send_keys("\n")
        except Exception as e:
            logger.error(f"Error clicking Login button: {str(e)}")

        # Wait and check for authentication challenges
        logger.info("Checking for authentication challenges or successful login")
        wait_start_time = time.time()

        while time.time() - wait_start_time < 15:  # Initial check timeout (15 seconds)
            current_url = driver.current_url

            # Check if we're already on the home page (immediate success)
            if "twitter.com/home" in current_url or "x.com/home" in current_url:
                logger.info("Successfully logged in - reached home page")
                return True

            # Check for authentication challenge elements
            auth_elements = driver.find_elements(
                By.XPATH,
                '//*[contains(text(), "Authenticate") or contains(text(), "Verify") or contains(text(), "Challenge") or contains(text(), "Confirm your identity") or contains(text(), "Unusual login") or contains(text(), "CAPTCHA")]',
            )

            if auth_elements:
                logger.warning(f"Authentication challenge detected for {username}")
                return handle_manual_intervention(driver, username)

            time.sleep(1)

        # After initial timeout, check if we need manual intervention
        if "verify" in driver.current_url or "challenge" in driver.current_url:
            logger.warning(
                "Verification or challenge detected that requires manual action"
            )
            return handle_manual_intervention(driver, username)

        # Final check for successful login
        if is_logged_in(driver):
            logger.info("Successfully logged in")
            return True
        else:
            logger.error("Login process failed - not logged in after attempts")
            return False

    except Exception as e:
        logger.error(f"Error during login process: {str(e)}")
        return False


def handle_manual_intervention(driver, username):
    """Handle manual intervention for authentication challenges"""
    logger.info("=" * 80)
    logger.info(f"MANUAL INTERVENTION REQUIRED for account: {username}")
    logger.info(
        "Please solve the CAPTCHA or authentication challenge in the browser window"
    )
    logger.info("=" * 80)

    wait_start_time = time.time()

    # Poll for successful login
    while time.time() - wait_start_time < MAX_WAITING_TIME:
        if is_logged_in(driver):
            logger.info("=" * 80)
            logger.info("Manual authentication successful - proceeding with automation")
            logger.info("=" * 80)
            return True

        # Show ongoing notification every 30 seconds
        elapsed = time.time() - wait_start_time
        if int(elapsed) % 30 == 0:
            logger.info(
                f"Still waiting for manual intervention ({int(elapsed)} seconds elapsed)..."
            )

        time.sleep(POLLING_INTERVAL)

    logger.error("=" * 80)
    logger.error(f"Maximum waiting time ({MAX_WAITING_TIME} seconds) exceeded")
    logger.error("Manual intervention unsuccessful - skipping this account")
    logger.error("=" * 80)
    return False


def is_logged_in(driver):
    """Check if user is logged in by looking for home page elements"""
    try:
        # Check URL
        current_url = driver.current_url.lower()
        if "twitter.com/home" in current_url or "x.com/home" in current_url:
            return True

        # Check for profile elements that indicate logged-in state
        profile_elements = driver.find_elements(
            By.CSS_SELECTOR, 'a[aria-label="Profile"]'
        )
        if profile_elements and any(elem.is_displayed() for elem in profile_elements):
            return True

        app_tab_elements = driver.find_elements(
            By.CSS_SELECTOR, 'a[data-testid="AppTabBar_Profile_Link"]'
        )
        if app_tab_elements and any(elem.is_displayed() for elem in app_tab_elements):
            return True

        # Check for navigation elements typically present when logged in
        nav_elements = driver.find_elements(By.CSS_SELECTOR, 'nav[role="navigation"]')
        if nav_elements and any(elem.is_displayed() for elem in nav_elements):
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking login status: {str(e)}")
        return False


def logout_from_twitter(driver):
    """Logout from Twitter."""
    try:
        logger.info("Logging out from Twitter")

        # Try to navigate to home to ensure we're on Twitter
        driver.get("https://twitter.com/home")
        time.sleep(3)

        # Click on the account menu
        try:
            # Try to find the account menu by different methods
            menu_selectors = [
                'a[data-testid="AppTabBar_Profile_Link"]',
                'a[aria-label="Profile"]',
                'div[data-testid="SideNav_AccountSwitcher_Button"]',
            ]

            menu_element = None
            for selector in menu_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            menu_element = elem
                            break
                    if menu_element:
                        break
                except:
                    continue

            if menu_element:
                logger.info("Found account menu, clicking it")
                menu_element.click()
                time.sleep(2)

                # Look for logout button
                logout_selectors = [
                    'a[data-testid="logout"]',
                    'div[data-testid="logout"]',
                    'div[role="menuitem"]:last-child',
                    'a[href="/logout"]',
                ]

                logout_element = None
                for selector in logout_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and (
                                "log out" in elem.text.lower()
                                or "logout" in elem.text.lower()
                            ):
                                logout_element = elem
                                break
                        if logout_element:
                            break
                    except:
                        continue

                if logout_element:
                    logger.info("Found logout button, clicking it")
                    logout_element.click()
                    time.sleep(2)

                    # Confirm logout if needed
                    confirm_buttons = driver.find_elements(
                        By.CSS_SELECTOR, 'div[role="button"]'
                    )
                    for button in confirm_buttons:
                        if button.is_displayed() and (
                            "log out" in button.text.lower()
                            or "logout" in button.text.lower()
                        ):
                            logger.info("Confirming logout")
                            button.click()
                            time.sleep(2)
                            break

                    # Wait until we're on the login page or a non-authenticated page
                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: "login" in d.current_url
                            or "?lang=" in d.current_url
                        )
                        logger.info("Successfully logged out")
                        return True
                    except TimeoutException:
                        logger.warning(
                            "Timeout waiting for logout completion, trying alternative method"
                        )
                else:
                    logger.warning("Could not find logout button in menu")
            else:
                logger.warning("Could not find account menu")

        except Exception as e:
            logger.error(f"Error during menu navigation: {str(e)}")

        # Alternative logout method - directly go to logout URL
        logger.info("Using alternative logout method - direct URL")
        driver.get("https://twitter.com/logout")
        time.sleep(2)

        # Look for confirm logout button
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
            for button in buttons:
                if button.is_displayed() and (
                    "log out" in button.text.lower() or "logout" in button.text.lower()
                ):
                    logger.info("Confirming logout")
                    button.click()
                    time.sleep(2)
                    return True
        except Exception as e:
            logger.error(f"Error during alternative logout: {str(e)}")

        # Final fallback - clear cookies and return to login page
        logger.warning("Clearing cookies and resetting to login page")
        driver.delete_all_cookies()
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(2)
        return True

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return False


def extract_cookies(driver):
    """Extract cookies from the browser."""
    logger.info("Extracting cookies")
    browser_cookies = driver.get_cookies()
    logger.info(f"Found {len(browser_cookies)} cookies total")

    cookie_values = {}
    used_domain = "twitter.com"  # Default domain

    # Check which domain we're on
    current_url = driver.current_url.lower()
    if "x.com" in current_url:
        used_domain = "x.com"
        logger.info(f"Detected x.com domain in use")

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

    return cookie_values, used_domain


def generate_cookies_json(cookie_values, domain="twitter.com"):
    """Generate the cookies JSON from the provided cookie values."""
    logger.info(f"Generating cookies JSON for domain: {domain}")
    cookies = []
    for name in COOKIE_NAMES:
        value = cookie_values.get(name, "")
        if value == "":
            logger.warning(f"Using empty string for missing cookie: {name}")
        cookies.append(create_cookie_template(name, value, domain))
    return cookies


def reset_browser_state(driver):
    """Reset the browser state to prepare for the next account."""
    try:
        logger.info("Resetting browser state")
        # Clear cookies and storage
        driver.delete_all_cookies()
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        # Navigate back to login page
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(3)  # Wait for page to load
        return True
    except Exception as e:
        logger.error(f"Failed to reset browser state: {str(e)}")
        return False


def process_account(driver, username, password):
    """Process a single Twitter account and get its cookies."""
    logger.info(f"==========================================")
    logger.info(f"Starting to process account: {username}")
    output_file = f"{username}_twitter_cookies.json"

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        success = login_to_twitter(driver, username, password)

        if success:
            logger.info(f"Login successful for {username}")
            # Go to twitter.com to ensure all cookies are set
            logger.info("Navigating to Twitter home to ensure all cookies are set")

            # Try both domains in case one is redirected
            current_url = driver.current_url.lower()
            if "x.com" in current_url:
                driver.get("https://x.com/home")
            else:
                driver.get("https://twitter.com/home")

            time.sleep(3)  # Wait for cookies to be fully set

            cookie_values, domain = extract_cookies(driver)
            cookies_json = generate_cookies_json(cookie_values, domain)

            # Save cookies to file
            output_path = os.path.join(OUTPUT_DIR, output_file)
            with open(output_path, "w") as f:
                f.write(json.dumps(cookies_json, indent=2))
            logger.info(f"Saved cookies for {username} to {output_path}")

            # Logout after extracting cookies
            logout_from_twitter(driver)
        else:
            logger.error(f"Failed to login for {username}")
    except Exception as e:
        logger.error(f"Unexpected error processing account {username}: {str(e)}")
    finally:
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

    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Maximum number of retries for ChromeDriver initialization
    max_retries = 3
    retry_count = 0
    driver = None

    while retry_count < max_retries:
        try:
            # Initialize browser once for all accounts
            if driver is not None:
                try:
                    driver.quit()
                except:
                    pass

            driver = setup_driver()

            for account_pair in account_pairs:
                if ":" not in account_pair:
                    logger.error(
                        f"Invalid account format: {account_pair}. Expected format: username:password"
                    )
                    continue

                username, password = account_pair.split(":", 1)
                username = username.strip()
                password = password.strip()

                process_account(driver, username, password)

                # Reset browser state before the next account
                if account_pair != account_pairs[-1]:  # If not the last account
                    reset_browser_state(driver)

                    # Add a short cooling period between accounts
                    cool_down = random.uniform(1, 2)  # 1-2 seconds
                    logger.info(
                        f"Cooling down for {cool_down:.1f} seconds before next account"
                    )
                    time.sleep(cool_down)

            logger.info("All accounts processed, closing browser")
            driver.quit()
            break  # Exit the retry loop on success

        except Exception as e:
            retry_count += 1
            logger.error(
                f"Critical error (attempt {retry_count}/{max_retries}): {str(e)}"
            )
            try:
                if driver:
                    driver.quit()
            except:
                pass

            if retry_count < max_retries:
                logger.info(f"Waiting 30 seconds before retrying...")
                time.sleep(30)
            else:
                logger.error("Maximum retry attempts reached. Giving up.")

    logger.info("Cookie grabber completed")


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    logger.info("Starting cookie grabber script")
    main()
