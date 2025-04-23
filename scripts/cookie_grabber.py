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

    # Use Chromium binary path if we're in the Docker container with Chromium installed
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        print("Using Chromium binary from /usr/bin/chromium")

    # Try to create the driver
    try:
        # First try with webdriver_manager
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Error creating driver with default approach: {str(e)}")
        try:
            # Try with explicitly finding chromedriver
            if os.path.exists("/usr/bin/chromedriver"):
                print("Using chromedriver from /usr/bin/chromedriver")
                driver = webdriver.Chrome(
                    service=Service("/usr/bin/chromedriver"), options=options
                )
            else:
                # Last resort: try with webdriver_manager
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()), options=options
                )
        except Exception as e2:
            print(f"Error creating driver with fallback approach: {str(e2)}")
            raise

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
            print("Could not find username field.")
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
            print("Could not find password field.")
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
            print("Timed out waiting for home page.")

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


def process_account(username, password):
    """Process a single Twitter account and get its cookies."""
    # Set output filename based on username
    output_file = f"{username}_twitter_cookies.json"
    print(f"Will save cookies to: {output_file}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Contents of current directory: {os.listdir('.')}")
    print(f"Contents of cookies directory: {os.listdir('./cookies')}")

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

            # Save to a file in the cookies directory
            output_path = os.path.join("./cookies", output_file)
            print(f"Saving cookies to path: {output_path}")

            with open(output_path, "w") as f:
                f.write(formatted_json)
            print(f"Cookies JSON saved to {output_path}")
            print(
                f"After writing, contents of cookies directory: {os.listdir('./cookies')}"
            )
        else:
            print("Failed to login to Twitter.")
    finally:
        driver.quit()


def main():
    """Main function to process Twitter accounts from environment variable."""
    # Create cookies directory if it doesn't exist
    os.makedirs("./cookies", exist_ok=True)

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

        print(f"\n--- Processing account: {username} ---")
        process_account(username, password)


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    main()
