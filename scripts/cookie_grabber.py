#!/usr/bin/env python3
import json
import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

# Twitter cookie names to extract
COOKIE_NAMES = ["personalization_id", "kdt", "twid", "ct0", "auth_token", "att"]

# Fixed output directory
OUTPUT_DIR = "/app/cookies"


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
    print("Setting up Firefox driver...")
    options = Options()

    # Run headless for Docker environment
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    options.add_argument("--disable-extensions")

    # Get proxy settings from environment variables
    http_proxy = os.environ.get("http_proxy")
    if http_proxy and "http://" in http_proxy:
        options.set_preference("network.proxy.type", 1)
        proxy_parts = http_proxy.replace("http://", "").split(":")
        if len(proxy_parts) == 2:
            proxy_host, proxy_port = proxy_parts
            options.set_preference("network.proxy.http", proxy_host)
            options.set_preference("network.proxy.http_port", int(proxy_port))
            options.set_preference("network.proxy.ssl", proxy_host)
            options.set_preference("network.proxy.ssl_port", int(proxy_port))

    # Add user agent and anti-detection settings
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    )
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)

    # Force disable GPU acceleration
    os.environ["MOZ_HEADLESS_WIDTH"] = "1920"
    os.environ["MOZ_HEADLESS_HEIGHT"] = "1080"

    # Create Firefox profile directory
    os.makedirs("/tmp/firefox_profile", exist_ok=True)
    os.chmod("/tmp/firefox_profile", 0o755)
    options.set_preference("profile", "/tmp/firefox_profile")

    try:
        service = Service(
            executable_path="/usr/local/bin/geckodriver",
            log_path="/app/geckodriver.log",
        )
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error creating driver: {str(e)}")
        raise


def login_to_twitter(driver, username, password):
    """Login to Twitter and return True if successful."""
    try:
        # Navigate to Twitter login page
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(5)  # Give page time to fully load

        # Find and enter username
        username_input = None
        selectors = [
            'input[autocomplete="username"]',
            'input[name="text"]',
            'input[type="text"]',
        ]

        for selector in selectors:
            try:
                username_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_input.is_displayed():
                    break
            except:
                continue

        if not username_input:
            driver.save_screenshot("/app/login_page.png")
            return False

        # Enter username
        username_input.clear()
        username_input.send_keys(username)
        time.sleep(1)

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
            clicked = False
            for button in next_buttons:
                if button.is_displayed():
                    button.click()
                    clicked = True
                    break

            if not clicked:
                # Try pressing Enter on username field as fallback
                username_input.send_keys("\n")
        except Exception:
            pass

        # Wait for password field
        time.sleep(3)

        # Find password field
        password_input = None
        password_selectors = ['input[type="password"]', 'input[name="password"]']

        for selector in password_selectors:
            try:
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if password_input.is_displayed():
                    break
            except:
                continue

        if not password_input:
            driver.save_screenshot("/app/password_field.png")
            return False

        # Enter password
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)

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
                    break

            if not clicked:
                # Try pressing Enter on password field as fallback
                password_input.send_keys("\n")
        except Exception:
            pass

        # Wait for login to complete
        try:
            # Wait until we're logged in
            WebDriverWait(driver, 30).until(
                lambda d: "home" in d.current_url
                or "twitter.com/home" in d.current_url
                or len(d.find_elements(By.CSS_SELECTOR, 'a[aria-label="Profile"]')) > 0
            )
            return True
        except TimeoutException:
            # Check if we need to handle verification
            if "verify" in driver.current_url or "challenge" in driver.current_url:
                print("Verification or challenge detected that requires manual action.")
            return False

    except Exception as e:
        print(f"Error during login: {str(e)}")
        return False


def extract_cookies(driver):
    """Extract cookies from the browser."""
    browser_cookies = driver.get_cookies()

    cookie_values = {}
    for cookie in browser_cookies:
        if cookie["name"] in COOKIE_NAMES:
            cookie_values[cookie["name"]] = cookie["value"]

    # Log missing cookies
    missing_cookies = [name for name in COOKIE_NAMES if name not in cookie_values]
    if missing_cookies:
        print(f"Missing cookies: {', '.join(missing_cookies)}")

    return cookie_values


def generate_cookies_json(cookie_values):
    """Generate the cookies JSON from the provided cookie values."""
    cookies = []
    for name in COOKIE_NAMES:
        value = cookie_values.get(name, "<YOUR_VALUE_HERE>")
        cookies.append(create_cookie_template(name, value))
    return cookies


def process_account(username, password):
    """Process a single Twitter account and get its cookies."""
    output_file = f"{username}_twitter_cookies.json"

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    driver = setup_driver()

    try:
        print(f"Processing account: {username}")
        success = login_to_twitter(driver, username, password)

        if success:
            print(f"Login successful for {username}")
            # Go to twitter.com to ensure all cookies are set
            driver.get("https://twitter.com/home")
            time.sleep(3)  # Wait for cookies to be fully set

            cookie_values = extract_cookies(driver)
            cookies_json = generate_cookies_json(cookie_values)

            # Save cookies to file
            output_path = os.path.join(OUTPUT_DIR, output_file)
            with open(output_path, "w") as f:
                f.write(json.dumps(cookies_json, indent=2))
            print(f"Saved cookies for {username}")
        else:
            print(f"Failed to login for {username}")
    finally:
        driver.quit()


def main():
    """Main function to process Twitter accounts from environment variable."""
    # Get Twitter accounts from environment variable
    twitter_accounts_str = os.environ.get("TWITTER_ACCOUNTS", "")

    if not twitter_accounts_str:
        print("Error: TWITTER_ACCOUNTS environment variable is not set.")
        print("Format should be: username1:password1,username2:password2")
        return

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

        process_account(username, password)


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    main()
