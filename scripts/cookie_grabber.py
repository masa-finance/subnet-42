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
from selenium.common.exceptions import TimeoutException, WebDriverException
import random
from selenium_stealth import stealth
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
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

# Constants
POLLING_INTERVAL = 1  # Check every 1 second
WAITING_TIME = 3600  # Wait up to 1 hour for manual verification
CLICK_WAIT = 5  # Wait 5 seconds after clicking buttons


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
    """Set up and return a Chrome driver using a dedicated profile."""
    logger.info("Setting up Chrome driver...")

    options = webdriver.ChromeOptions()

    # Create a temporary profile directory to avoid conflicts with existing Chrome
    import tempfile

    temp_profile = os.path.join(
        tempfile.gettempdir(), f"chrome_profile_{int(time.time())}"
    )
    os.makedirs(temp_profile, exist_ok=True)
    logger.info(f"Using dedicated Chrome profile at: {temp_profile}")
    options.add_argument(f"--user-data-dir={temp_profile}")

    # Common options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Add anti-cloudflare options
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")

    # Add a random viewport size
    width = random.randint(1050, 1200)
    height = random.randint(800, 950)
    options.add_argument(f"--window-size={width},{height}")

    # Add more randomized user agents
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    ]
    user_agent = random.choice(user_agents)
    options.add_argument(f"--user-agent={user_agent}")

    try:
        logger.info("Initializing Chrome driver...")
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
        # Ultimate fallback with minimal options
        try:
            logger.info("Trying with minimal Chrome options...")
            minimal_options = webdriver.ChromeOptions()
            minimal_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=minimal_options)
            return driver
        except Exception as e2:
            logger.error(f"Final driver creation attempt failed: {str(e2)}")
            raise


def human_like_typing(element, text):
    """Simulate human-like typing with random delays between keypresses."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.25))  # Random delay between keypresses


def add_manual_action_notice(driver, message="MANUAL ACTION REQUIRED"):
    """Add a visual notification for manual action."""
    # Disabled as requested
    pass


def remove_manual_action_notice(driver):
    """Remove the manual action notice."""
    # Disabled as requested
    pass


def find_and_fill_input(driver, input_type, value):
    """Find and fill an input field of a specific type."""
    selectors = {
        "username": [
            'input[autocomplete="username"]',
            'input[name="text"]',
            'input[name="username"]',
            'input[placeholder*="username" i]',
            'input[placeholder*="phone" i]',
            'input[placeholder*="email" i]',
        ],
        "password": [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="password" i]',
        ],
        "email": [
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="email" i]',
            'input[autocomplete="email"]',
        ],
        "phone": [
            'input[type="tel"]',
            'input[name="phone"]',
            'input[placeholder*="phone" i]',
            'input[autocomplete="tel"]',
        ],
        "code": [
            'input[autocomplete="one-time-code"]',
            'input[name="code"]',
            'input[placeholder*="code" i]',
            'input[placeholder*="verification" i]',
        ],
    }

    if input_type not in selectors:
        logger.warning(f"Unknown input type: {input_type}")
        return False

    input_found = False

    for selector in selectors[input_type]:
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, selector)
            for input_field in inputs:
                if input_field.is_displayed():
                    # Clear the field first (sometimes needed)
                    try:
                        input_field.clear()
                    except:
                        pass

                    # Type the value
                    human_like_typing(input_field, value)
                    logger.info(f"Filled {input_type} field with value: {value}")

                    # Add a small delay after typing
                    time.sleep(random.uniform(0.5, 1.5))
                    input_found = True
                    return True
        except Exception as e:
            logger.debug(
                f"Couldn't find or fill {input_type} field with selector {selector}: {str(e)}"
            )

    if not input_found:
        logger.info(f"No {input_type} input field found")

    return False


def click_next_button(driver):
    """Try to click a 'Next' or submit button."""
    button_clicked = False

    # Try buttons with "Next" text
    try:
        next_buttons = driver.find_elements(
            By.XPATH, '//*[contains(text(), "Next") or contains(text(), "next")]'
        )
        for button in next_buttons:
            if button.is_displayed():
                button.click()
                logger.info("Clicked Next button by text")
                button_clicked = True
                break
    except Exception as e:
        logger.debug(f"Couldn't click Next button by text: {str(e)}")

    # Try buttons with "Continue" text
    if not button_clicked:
        try:
            continue_buttons = driver.find_elements(
                By.XPATH,
                '//*[contains(text(), "Continue") or contains(text(), "continue")]',
            )
            for button in continue_buttons:
                if button.is_displayed():
                    button.click()
                    logger.info("Clicked Continue button by text")
                    button_clicked = True
                    break
        except Exception as e:
            logger.debug(f"Couldn't click Continue button by text: {str(e)}")

    # Try buttons with "Log in" or "Sign in" text
    if not button_clicked:
        try:
            login_buttons = driver.find_elements(
                By.XPATH,
                '//*[contains(text(), "Log in") or contains(text(), "Login") or contains(text(), "Sign in")]',
            )
            for button in login_buttons:
                if button.is_displayed():
                    button.click()
                    logger.info("Clicked Login button by text")
                    button_clicked = True
                    break
        except Exception as e:
            logger.debug(f"Couldn't click Login button by text: {str(e)}")

    # Try generic button elements by role
    if not button_clicked:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
            for button in buttons:
                if button.is_displayed():
                    button.click()
                    logger.info("Clicked button by role")
                    button_clicked = True
                    break
        except Exception as e:
            logger.debug(f"Couldn't click button by role: {str(e)}")

    # Try submitting the form with Enter key (last resort)
    if not button_clicked:
        try:
            active_element = driver.switch_to.active_element
            active_element.send_keys(Keys.ENTER)
            logger.info("Pressed Enter key on active element")
            button_clicked = True
        except Exception as e:
            logger.debug(f"Couldn't press Enter key: {str(e)}")

    return button_clicked


def is_logged_in(driver):
    """Check if user is logged in to Twitter."""
    try:
        current_url = driver.current_url.lower()

        # URL check (most reliable)
        if "twitter.com/home" in current_url or "x.com/home" in current_url:
            return True

        # Home timeline check
        home_timeline = driver.find_elements(
            By.CSS_SELECTOR, 'div[aria-label="Timeline: Your Home Timeline"]'
        )
        if home_timeline and any(elem.is_displayed() for elem in home_timeline):
            return True

        # Tweet/Post button check
        tweet_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            'a[data-testid="SideNav_NewTweet_Button"], [data-testid="tweetButtonInline"]',
        )
        if tweet_buttons and any(btn.is_displayed() for btn in tweet_buttons):
            return True

        # Navigation elements check
        nav_elements = driver.find_elements(
            By.CSS_SELECTOR,
            'nav[role="navigation"], a[data-testid="AppTabBar_Home_Link"]',
        )
        if nav_elements and any(elem.is_displayed() for elem in nav_elements):
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking login status: {str(e)}")
        return False


def needs_verification(driver):
    """Check if the page is showing a verification or authentication screen."""
    try:
        # Check for verification text
        verification_texts = [
            "Authenticate your account",
            "Enter your phone number",
            "Enter your email",
            "Check your phone",
            "Check your email",
            "Verification code",
            "verify your identity",
            "unusual login activity",
            "suspicious activity",
            "Help us keep your account safe",
            "Verify your identity",
            "keep your account safe",
        ]

        for text in verification_texts:
            try:
                elements = driver.find_elements(
                    By.XPATH, f"//*[contains(text(), '{text}')]"
                )
                if elements and any(elem.is_displayed() for elem in elements):
                    logger.info(f"Verification needed: Found text '{text}'")
                    return True
            except:
                pass

        # Check for verification URLs
        current_url = driver.current_url.lower()
        verification_url_patterns = [
            "verify",
            "challenge",
            "confirm",
            "auth",
            "login_challenge",
        ]

        for pattern in verification_url_patterns:
            if pattern in current_url:
                logger.info(f"Verification needed: URL contains '{pattern}'")
                return True

        return False
    except Exception as e:
        logger.error(f"Error checking for verification: {str(e)}")
        return False


def extract_email_from_password(password):
    """Extract email from password assuming format 'himynameis<name>'."""
    try:
        # Check if password starts with 'himynameis'
        if password.startswith("himynameis"):
            name = password[10:]  # Extract everything after 'himynameis'
            return f"grantdfoster+{name}@gmail.com"
    except:
        pass

    # Fall back to a default
    return "grantdfoster@gmail.com"


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
            value = cookie["value"]
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]  # Remove surrounding quotes
            value = value.replace('"', "")  # Replace any remaining quotes

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


def process_account_state_machine(driver, username, password):
    """Process an account using a state machine approach with continuous polling."""
    logger.info(f"==========================================")
    logger.info(f"Starting to process account: {username}")
    output_file = f"{username}_twitter_cookies.json"

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Extract email from password if needed for verification
    email = extract_email_from_password(password)
    logger.info(f"Using email {email} for account {username}")

    # Navigate to login page
    try:
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(5)  # Initial wait for page load
    except Exception as e:
        logger.error(f"Failed to navigate to login page: {str(e)}")
        return False

    # Setup state machine variables
    start_time = time.time()
    last_action_time = start_time
    last_url = driver.current_url
    login_successful = False
    manual_intervention_active = False

    # State machine loop
    while time.time() - start_time < WAITING_TIME:
        try:
            current_url = driver.current_url

            # Check if already logged in
            if is_logged_in(driver):
                logger.info("Login successful!")
                login_successful = True
                break

            # Check if URL changed since last check
            if current_url != last_url:
                logger.info(f"URL changed to: {current_url}")
                last_url = current_url
                last_action_time = time.time()  # Reset the idle timer when URL changes

            # Check if we need verification
            if needs_verification(driver):
                if not manual_intervention_active:
                    logger.info("Manual verification required")
                    manual_intervention_active = True

                # Try to help with the verification by filling known fields
                # Check for phone/email verification screen
                verification_inputs = driver.find_elements(
                    By.CSS_SELECTOR,
                    'input[placeholder*="Phone or email"], input[placeholder*="phone number or email"], input[aria-label*="phone"], input[aria-label*="email"], input[name="text"], input.r-30o5oe, input[placeholder*="Email address"]',
                )
                if verification_inputs and any(
                    inp.is_displayed() for inp in verification_inputs
                ):
                    logger.info(
                        "Phone/email verification screen detected - filling with email"
                    )
                    for input_field in verification_inputs:
                        if input_field.is_displayed():
                            try:
                                # Clear the field completely
                                input_field.clear()
                                input_field.send_keys(Keys.CONTROL + "a")
                                input_field.send_keys(Keys.DELETE)
                                time.sleep(0.5)
                            except:
                                pass
                            # Only type the email, nothing else
                            human_like_typing(input_field, email)
                            logger.info(
                                f"Filled verification input with email: {email}"
                            )
                            time.sleep(1)
                            click_next_button(driver)
                            time.sleep(CLICK_WAIT)
                            last_action_time = time.time()
                            continue

                # Check specifically for the "Help us keep your account safe" screen
                help_safe_elements = driver.find_elements(
                    By.XPATH, "//*[contains(text(), 'Help us keep your account safe')]"
                )
                if help_safe_elements and any(
                    elem.is_displayed() for elem in help_safe_elements
                ):
                    logger.info("Account safety verification screen detected")
                    # Try to find email input field
                    email_inputs = driver.find_elements(
                        By.CSS_SELECTOR, 'input[placeholder="Email address"]'
                    )
                    if email_inputs and any(inp.is_displayed() for inp in email_inputs):
                        for input_field in email_inputs:
                            if input_field.is_displayed():
                                try:
                                    # Clear the field completely
                                    input_field.clear()
                                    input_field.send_keys(Keys.CONTROL + "a")
                                    input_field.send_keys(Keys.DELETE)
                                    time.sleep(0.5)
                                except:
                                    pass
                                # Type the email address
                                human_like_typing(input_field, email)
                                logger.info(
                                    f"Filled account safety email with: {email}"
                                )
                                time.sleep(1)
                                # Look for the Next button
                                next_buttons = driver.find_elements(
                                    By.XPATH,
                                    '//div[@role="button" and contains(text(), "Next")]',
                                )
                                if next_buttons and any(
                                    btn.is_displayed() for btn in next_buttons
                                ):
                                    for btn in next_buttons:
                                        if btn.is_displayed():
                                            btn.click()
                                            logger.info(
                                                "Clicked Next button on account safety screen"
                                            )
                                            time.sleep(CLICK_WAIT)
                                            last_action_time = time.time()
                                            break
                                else:
                                    # If can't find specific Next button, try generic button click
                                    click_next_button(driver)
                                    time.sleep(CLICK_WAIT)
                                    last_action_time = time.time()
                                continue

                # Check for email input (older style)
                if find_and_fill_input(driver, "email", email):
                    click_next_button(driver)
                    time.sleep(CLICK_WAIT)
                    last_action_time = time.time()
                    continue

                # Check for phone input (we'll let the user handle this)
                phone_inputs = driver.find_elements(
                    By.CSS_SELECTOR, 'input[type="tel"], input[placeholder*="phone" i]'
                )
                if phone_inputs and any(inp.is_displayed() for inp in phone_inputs):
                    logger.info(
                        "Phone verification required - waiting for manual completion"
                    )
                    # Just continue polling, user needs to complete this manually
                    time.sleep(POLLING_INTERVAL)
                    continue
            else:
                # If we no longer need verification, update the flag
                if manual_intervention_active:
                    logger.info("Manual verification appears to be completed")
                    manual_intervention_active = False

            # Normal login flow - try to identify and fill inputs
            # Username field
            if find_and_fill_input(driver, "username", username):
                click_next_button(driver)
                time.sleep(CLICK_WAIT)
                last_action_time = time.time()
                continue

            # Password field
            if find_and_fill_input(driver, "password", password):
                click_next_button(driver)
                time.sleep(CLICK_WAIT)
                last_action_time = time.time()
                continue

            # If we haven't taken any action for a while, try clicking a button
            if time.time() - last_action_time > 30:  # 30 seconds of no action
                if click_next_button(driver):
                    logger.info("Clicked a button after 30 seconds of inactivity")
                    time.sleep(CLICK_WAIT)
                    last_action_time = time.time()
                    continue

            # If we're not logged in and can't find any inputs, wait
            time.sleep(POLLING_INTERVAL)

        except WebDriverException as e:
            if "no such window" in str(e).lower():
                logger.error("Browser window was closed")
                return False
            logger.error(f"WebDriver error: {str(e)}")
            # Continue the loop to try again
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            # Continue the loop to try again

    # After the loop, check if login was successful
    if login_successful:
        try:
            # Ensure we're on the home page
            if "home" not in driver.current_url.lower():
                logger.info("Navigating to home page to ensure all cookies are set")
                try:
                    if "x.com" in driver.current_url:
                        driver.get("https://x.com/home")
                    else:
                        driver.get("https://twitter.com/home")
                    time.sleep(3)
                except Exception as e:
                    logger.warning(f"Failed to navigate to home page: {str(e)}")

            # Extract and save cookies
            cookie_values, domain = extract_cookies(driver)
            cookies_json = generate_cookies_json(cookie_values, domain)

            # Save cookies to file
            output_path = os.path.join(OUTPUT_DIR, output_file)
            with open(output_path, "w") as f:
                f.write(json.dumps(cookies_json, indent=2))
            logger.info(f"Saved cookies for {username} to {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error after successful login: {str(e)}")
            return False
    else:
        logger.error(f"Failed to login for {username} within the time limit")
        return False


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

            # Process accounts
            for account_pair in account_pairs:
                if ":" not in account_pair:
                    logger.error(
                        f"Invalid account format: {account_pair}. Expected format: username:password"
                    )
                    continue

                username, password = account_pair.split(":", 1)
                username = username.strip()
                password = password.strip()

                success = process_account_state_machine(driver, username, password)
                logger.info(
                    f"Account {username} processed with {'success' if success else 'failure'}"
                )

                # Reset browser state before the next account
                if account_pair != account_pairs[-1]:  # If not the last account
                    reset_browser_state(driver)
                    cool_down = random.uniform(2, 5)  # 2-5 seconds cooldown
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
