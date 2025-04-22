#!/usr/bin/env python3
import json
import time
import os
import argparse
import urllib.parse
import base64
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Twitter cookie names to extract
COOKIE_NAMES = ["personalization_id", "kdt", "twid", "ct0", "auth_token", "att"]


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


def setup_driver():
    """Set up and return a browser driver instance."""
    options = webdriver.ChromeOptions()
    # Run headless for Docker environment
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Additional options for running in Docker
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")

    # Add user agent to avoid detection
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )

    # Create the driver using webdriver_manager to handle ChromeDriver installation
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
    except:
        # Fallback to standard initialization if webdriver_manager fails
        driver = webdriver.Chrome(options=options)

    return driver


def login_to_twitter(driver, username, password):
    """Login to Twitter and return True if successful."""
    try:
        # Navigate to Twitter login page
        driver.get("https://twitter.com/i/flow/login")
        print("Waiting for login page to load...")
        time.sleep(3)  # Give page time to fully load

        # Wait for and enter username
        print("Looking for username field...")
        username_input = None

        # Try different selectors for the username field
        selectors = [
            'input[autocomplete="username"]',
            'input[name="text"]',
            'input[type="text"]',
        ]

        for selector in selectors:
            try:
                username_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_input.is_displayed():
                    print(f"Found username field with selector: {selector}")
                    break
            except:
                continue

        if not username_input:
            print("Could not find username field. Taking screenshot for debugging...")
            driver.save_screenshot("login_page.png")
            print(f"Screenshot saved as login_page.png")
            return False

        # Enter username
        username_input.clear()
        username_input.send_keys(username)
        print("Entered username")

        # Click next button - try different approaches
        try:
            # First try by text content
            next_buttons = driver.find_elements(
                By.XPATH, '//*[contains(text(), "Next") or contains(text(), "next")]'
            )

            # Try visible buttons
            if not next_buttons:
                next_buttons = driver.find_elements(
                    By.CSS_SELECTOR, 'div[role="button"]'
                )

            # Click the first visible button
            for button in next_buttons:
                if button.is_displayed():
                    button.click()
                    print("Clicked next button")
                    break
        except Exception as e:
            print(f"Error clicking next button: {str(e)}")
            driver.save_screenshot("next_button_error.png")

        # Wait for password field
        print("Waiting for password field...")
        time.sleep(2)

        # Try different selectors for password field
        password_input = None
        password_selectors = ['input[type="password"]', 'input[name="password"]']

        for selector in password_selectors:
            try:
                password_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if password_input.is_displayed():
                    print(f"Found password field with selector: {selector}")
                    break
            except:
                continue

        if not password_input:
            print("Could not find password field. Taking screenshot for debugging...")
            driver.save_screenshot("password_field.png")
            print(f"Screenshot saved as password_field.png")
            return False

        # Enter password
        password_input.clear()
        password_input.send_keys(password)
        print("Entered password")

        # Click login button - try different approaches
        try:
            # First try by text content
            login_buttons = driver.find_elements(
                By.XPATH,
                '//*[contains(text(), "Log in") or contains(text(), "Login") or contains(text(), "Sign in")]',
            )

            # Try visible buttons
            if not login_buttons:
                login_buttons = driver.find_elements(
                    By.CSS_SELECTOR, 'div[role="button"]'
                )

            # Click the first visible button
            clicked = False
            for button in login_buttons:
                if button.is_displayed():
                    button.click()
                    clicked = True
                    print("Clicked login button")
                    break

            if not clicked:
                # Try pressing Enter on password field as fallback
                password_input.send_keys("\n")
                print("Pressed Enter on password field")
        except Exception as e:
            print(f"Error clicking login button: {str(e)}")
            driver.save_screenshot("login_button_error.png")

        # Wait for login to complete
        print("Waiting for login to complete...")
        try:
            # Wait until we're logged in (URL changes or home page elements appear)
            WebDriverWait(driver, 20).until(
                lambda d: "home" in d.current_url
                or "twitter.com/home" in d.current_url
                or len(d.find_elements(By.CSS_SELECTOR, 'a[aria-label="Profile"]')) > 0
            )
            print("Successfully logged in!")
            return True
        except TimeoutException:
            print("Timed out waiting for home page. Taking screenshot...")
            driver.save_screenshot("login_timeout.png")
            print(f"Screenshot saved as login_timeout.png")

            # Check if we need to handle verification
            if "verify" in driver.current_url or "challenge" in driver.current_url:
                print(
                    "Verification or challenge detected. Please complete it manually in the browser."
                )
                print("Waiting 60 seconds for manual verification...")
                time.sleep(60)  # Give user time to complete verification

                # Check if we're logged in after verification
                if (
                    "home" in driver.current_url
                    or "twitter.com/home" in driver.current_url
                ):
                    print("Successfully logged in after verification!")
                    return True

            return False

    except Exception as e:
        print(f"Unexpected error during login: {str(e)}")
        driver.save_screenshot("login_error.png")
        print(f"Screenshot saved as login_error.png")
        return False


def extract_cookies(driver):
    """Extract cookies from the browser."""
    browser_cookies = driver.get_cookies()

    cookie_values = {}
    for cookie in browser_cookies:
        if cookie["name"] in COOKIE_NAMES:
            cookie_values[cookie["name"]] = cookie["value"]

    return cookie_values


def generate_cookies_json(cookie_values):
    """Generate the cookies JSON from the provided cookie values."""
    cookies = []

    for name in COOKIE_NAMES:
        value = cookie_values.get(name, "<YOUR_VALUE_HERE>")
        cookies.append(create_cookie_template(name, value))

    return cookies


def main():
    parser = argparse.ArgumentParser(description="Login to Twitter and grab cookies")
    parser.add_argument("--username", help="Twitter username or email")
    parser.add_argument("--password", help="Twitter password")
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional, defaults to <TWITTER_USERNAME>_twitter_cookies.json)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with screenshots"
    )

    args = parser.parse_args()

    # Get multiple accounts from TWITTER_ACCOUNTS env variable
    twitter_accounts_str = os.environ.get("TWITTER_ACCOUNTS", "")

    # If command line args are provided, they take precedence
    if args.username and args.password:
        process_single_account(args.username, args.password, args.output, args.debug)
    # If TWITTER_ACCOUNTS env variable is set
    elif twitter_accounts_str:
        account_pairs = twitter_accounts_str.split(",")

        for account_pair in account_pairs:
            if ":" not in account_pair:
                print(
                    f"Invalid account format: {account_pair}. Expected format: username:password"
                )
                continue

            username, password = account_pair.split(":", 1)
            username = username.strip()
            password = password.strip()

            output_file = f"{username}_twitter_cookies.json"
            print(f"\n--- Processing account: {username} ---")
            process_single_account(username, password, output_file, args.debug)
    else:
        # Fallback to manual input
        username = input("Enter your Twitter username or email: ")
        password = input("Enter your Twitter password: ")
        process_single_account(username, password, None, args.debug)


def process_single_account(username, password, output_file=None, debug=False):
    """Process a single Twitter account and get its cookies."""
    # Set default output filename based on username
    if not output_file:
        output_file = f"{username}_twitter_cookies.json"

    driver = setup_driver()

    try:
        print(f"Starting login process for user: {username}")
        success = login_to_twitter(driver, username, password)

        if success:
            print("Login successful. Extracting cookies...")
            # Go to twitter.com to ensure all cookies are set
            driver.get("https://twitter.com/home")
            time.sleep(2)  # Wait for cookies to be fully set

            cookie_values = extract_cookies(driver)

            # Check if we got all the cookies
            missing_cookies = [
                name for name in COOKIE_NAMES if name not in cookie_values
            ]
            if missing_cookies:
                print(
                    f"Warning: The following cookies could not be extracted: {', '.join(missing_cookies)}"
                )

            # Generate cookies with no encoding
            cookies_json = generate_cookies_json(cookie_values)
            formatted_json = json.dumps(cookies_json, indent=2)

            # Always save to a file
            with open(output_file, "w") as f:
                f.write(formatted_json)
            print(f"Cookies JSON saved to {output_file}")

            # Also print to stdout if no output file was explicitly specified
            if not output_file:
                print("Cookie values:")
                print(formatted_json)
        else:
            print("Failed to login to Twitter.")
    finally:
        if not debug:  # Only close browser if not in debug mode
            driver.quit()


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    main()
