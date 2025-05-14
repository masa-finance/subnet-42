#!/usr/bin/env python3
import json
import time
import os
import logging
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import random
from selenium_stealth import stealth
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

# Twitter domains to handle - We will only use twitter.com
TWITTER_DOMAINS = ["twitter.com"]

# Twitter login URL
TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"

# Constants
POLLING_INTERVAL = 1  # Check every 1 second
WAITING_TIME = 300  # Wait up to 5 minutes for manual verification
CLICK_WAIT = 5  # Wait 5 seconds after clicking buttons


def get_future_date(days=7, hours=0, minutes=0, seconds=0):
    """
    Generate a slightly randomized ISO 8601 date string for a specified time in the future.

    Args:
        days: Number of days in the future
        hours: Number of hours to add
        minutes: Number of minutes to add
        seconds: Number of seconds to add

    Returns:
        ISO 8601 formatted date string with slight randomization
    """
    # Add slight randomization to make cookies appear more natural
    random_seconds = random.uniform(0, 3600)  # Random seconds (up to 1 hour)
    random_minutes = random.uniform(0, 60)  # Random minutes (up to 1 hour)

    future_date = datetime.datetime.now() + datetime.timedelta(
        days=days,
        hours=hours,
        minutes=minutes + random_minutes,
        seconds=seconds + random_seconds,
    )

    # Format in ISO 8601 format with timezone information
    return future_date.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_cookie_template(name, value, domain="twitter.com", expires=None):
    """
    Create a standard cookie template with the given name and value.
    Note: Cookie values should not contain double quotes as they cause errors in Go's HTTP client.

    Args:
        name: Name of the cookie
        value: Value of the cookie
        domain: Domain for the cookie
        expires: Optional expiration date string in ISO 8601 format
    """
    # Ensure no quotes in cookie value to prevent HTTP header issues
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    value = value.replace('"', "")

    # If no expiration date is provided, use the default "0001-01-01T00:00:00Z"
    if expires is None:
        expires = "0001-01-01T00:00:00Z"

    return {
        "Name": name,
        "Value": value,
        "Path": "",
        "Domain": domain,
        "Expires": expires,
        "RawExpires": "",
        "MaxAge": 0,
        "Secure": False,
        "HttpOnly": False,
        "SameSite": 0,
        "Raw": "",
        "Unparsed": None,
    }


def setup_realistic_profile(temp_profile):
    """Set up a more realistic browser profile with history and common extensions."""

    # Create history file structure
    history_dir = os.path.join(temp_profile, "Default")
    os.makedirs(history_dir, exist_ok=True)

    # Sample visited sites for history (just structure, not actual data)
    common_sites = [
        "google.com",
        "youtube.com",
        "facebook.com",
        "amazon.com",
        "wikipedia.org",
    ]

    # Create a dummy history file
    history_file = os.path.join(history_dir, "History")
    try:
        with open(history_file, "w") as f:
            # Just create an empty file to simulate history presence
            f.write("")

        # Create bookmark file with common sites
        bookmarks_file = os.path.join(history_dir, "Bookmarks")
        bookmarks_data = {
            "roots": {
                "bookmark_bar": {
                    "children": [
                        {"name": site, "url": f"https://{site}"}
                        for site in common_sites
                    ],
                    "date_added": str(int(time.time())),
                    "date_modified": str(int(time.time())),
                    "name": "Bookmarks Bar",
                    "type": "folder",
                }
            },
            "version": 1,
        }
        with open(bookmarks_file, "w") as f:
            json.dump(bookmarks_data, f)

        # Create preferences file with some realistic settings
        preferences_file = os.path.join(history_dir, "Preferences")
        preferences_data = {
            "browser": {
                "last_known_google_url": "https://www.google.com/",
                "last_prompted_google_url": "https://www.google.com/",
                "show_home_button": True,
                "custom_chrome_frame": False,
            },
            "homepage": "https://www.google.com",
            "session": {
                "restore_on_startup": 1,
                "startup_urls": [f"https://{random.choice(common_sites)}"],
            },
            "search": {"suggest_enabled": True},
            "translate": {"enabled": True},
        }
        with open(preferences_file, "w") as f:
            json.dump(preferences_data, f)

        logger.info("Created realistic browser profile with history and preferences")
    except Exception as e:
        logger.warning(f"Failed to create history files: {str(e)}")

    # Add a dummy extension folder to simulate common extensions
    ext_dir = os.path.join(temp_profile, "Default", "Extensions")
    os.makedirs(ext_dir, exist_ok=True)

    # Create dummy extension folders for common extensions
    common_extensions = [
        "aapbdbdomjkkjkaonfhkkikfgjllcleb",  # Google Translate
        "ghbmnnjooekpmoecnnnilnnbdlolhkhi",  # Google Docs
        "cjpalhdlnbpafiamejdnhcphjbkeiagm",  # uBlock Origin
    ]

    for ext_id in common_extensions:
        ext_path = os.path.join(ext_dir, ext_id)
        os.makedirs(ext_path, exist_ok=True)
        # Create a minimal manifest file
        manifest_path = os.path.join(ext_path, "manifest.json")
        try:
            with open(manifest_path, "w") as f:
                f.write("{}")
        except Exception as e:
            logger.warning(f"Failed to create extension manifest: {str(e)}")

    return temp_profile


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

    # CDP detection evasion
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--remote-allow-origins=*")

    # Set up more realistic browser profile
    temp_profile = setup_realistic_profile(temp_profile)

    # Add headers to appear more like a genuine browser
    options.add_argument("--accept-lang=en-US,en;q=0.9")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")

    # Check for proxy environment variables and configure proxy if available
    # This is especially important when running behind a VPN
    proxy_http = os.environ.get("http_proxy")
    proxy_https = os.environ.get("https_proxy")

    if proxy_http or proxy_https:
        proxy_to_use = proxy_http or proxy_https
        logger.info(f"Detected proxy settings: {proxy_to_use}")

        # Format the proxy properly for Chrome
        if proxy_to_use.startswith("http://"):
            proxy_to_use = proxy_to_use[7:]  # Remove http:// prefix

        options.add_argument(f"--proxy-server={proxy_to_use}")
        logger.info(f"Configured Chrome to use proxy: {proxy_to_use}")

        # Add additional settings to help with proxy connectivity
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-extensions")

    try:
        logger.info("Initializing Chrome driver...")
        driver = webdriver.Chrome(options=options)
        logger.info("Successfully initialized Chrome driver")

        # Additional anti-detection measures
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Apply more comprehensive stealth settings
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            # New parameters
            hardware_concurrency=4,  # Spoof CPU core count
            media_codecs=True,  # Mask media codec capabilities
            audio_context=True,  # Prevent audio fingerprinting
            fonts_languages=["en-US"],  # Standardize font rendering
        )

        # Timezone and geolocation spoofing
        driver.execute_script(
            """
          const fakeTime = new Date('2023-01-01T12:00:00');
          const dateNowStub = () => fakeTime.getTime();
          const realDateNow = Date.now;
          Date.now = dateNowStub;
          const timeStub = () => 12 * 60 * 60 * 1000;
          const realPerformanceNow = performance.now;
          performance.now = timeStub;
        """
        )

        # Spoof geolocation API
        driver.execute_script(
            """
          navigator.geolocation.getCurrentPosition = function(success) {
            success({
              coords: {
                latitude: 37.7749,
                longitude: -122.4194,
                accuracy: 100,
                altitude: null,
                altitudeAccuracy: null,
                heading: null,
                speed: null
              },
              timestamp: Date.now()
            });
          };
        """
        )

        # More comprehensive anti-detection script
        driver.execute_script(
            """
        // Overwrite navigator properties that reveal automation
        const overrideNavigator = () => {
          Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 5
          });
          
          Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
          });
          
          Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
          });
          
          // Override connection type
          if (navigator.connection) {
            Object.defineProperty(navigator.connection, 'type', {
              get: () => 'wifi'
            });
          }
          
          // Override webRTC
          if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
            navigator.mediaDevices.enumerateDevices = () => Promise.resolve([
              {deviceId: 'default', kind: 'audioinput', label: '', groupId: 'default'},
              {deviceId: 'default', kind: 'audiooutput', label: '', groupId: 'default'},
              {deviceId: 'default', kind: 'videoinput', label: '', groupId: 'default'}
            ]);
          }
        };

        // Canvas fingerprint protection
        const overrideCanvas = () => {
          const oldGetContext = HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext = function(type, attributes) {
            const context = oldGetContext.apply(this, arguments);
            if (type === '2d') {
              const oldFillText = context.fillText;
              context.fillText = function() {
                arguments[0] = arguments[0].toString();
                return oldFillText.apply(this, arguments);
              };
              const oldMeasureText = context.measureText;
              context.measureText = function() {
                arguments[0] = arguments[0].toString();
                const result = oldMeasureText.apply(this, arguments);
                result.width += Math.random() * 0.0001;
                return result;
              };
            }
            return context;
          };
        };

        overrideNavigator();
        overrideCanvas();
        """
        )

        return driver
    except Exception as e:
        logger.error(f"Error creating Chrome driver: {str(e)}")
        # Ultimate fallback with minimal options
        try:
            logger.info("Trying with minimal Chrome options...")
            minimal_options = webdriver.ChromeOptions()
            minimal_options.add_argument("--no-sandbox")

            # Add proxy settings to minimal options if available
            if proxy_http or proxy_https:
                proxy_to_use = proxy_http or proxy_https
                if proxy_to_use.startswith("http://"):
                    proxy_to_use = proxy_to_use[7:]  # Remove http:// prefix
                minimal_options.add_argument(f"--proxy-server={proxy_to_use}")
                minimal_options.add_argument("--ignore-certificate-errors")

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
    # Get base email from environment variable - required
    base_email = os.environ.get("TWITTER_EMAIL")
    if not base_email:
        logger.error("TWITTER_EMAIL environment variable not set. This is required.")
        # Return a placeholder that will likely fail but doesn't expose personal info
        return "email_not_configured@example.com"

    # Extract the username part from base email for plus addressing
    base_username = base_email.split("@")[0]
    domain = base_email.split("@")[1]

    try:
        # Check if password starts with 'himynameis'
        if password.startswith("himynameis"):
            name = password[10:]  # Extract everything after 'himynameis'
            return f"{base_username}+{name}@{domain}"
    except:
        pass

    # Fall back to the base email
    return base_email


def extract_cookies(driver):
    """Extract cookies from the browser."""
    logger.info("Extracting cookies")
    browser_cookies = driver.get_cookies()
    logger.info(f"Found {len(browser_cookies)} cookies total")

    cookie_values = {}
    used_domain = "twitter.com"  # Always use twitter.com domain, no conditional check

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
    # Always use twitter.com domain regardless of what's passed in
    domain = "twitter.com"
    logger.info(f"Generating cookies JSON for domain: {domain}")

    # Determine expiration dates for different cookie types
    one_week_future = get_future_date(days=7)
    one_month_future = get_future_date(days=30)

    cookies = []
    for name in COOKIE_NAMES:
        value = cookie_values.get(name, "")
        if value == "":
            logger.warning(f"Using empty string for missing cookie: {name}")

        # Set appropriate expiration date based on cookie type
        if name in ["personalization_id", "kdt"]:
            # 1 month expiration for these cookies
            expires = one_month_future
            logger.info(f"Setting {name} cookie to expire in 1 month: {expires}")
        elif name in ["auth_token", "ct0"]:
            # 1 week expiration for these cookies
            expires = one_week_future
            logger.info(f"Setting {name} cookie to expire in 1 week: {expires}")
        else:
            # Default 1 week for all other cookies
            expires = one_week_future
            logger.info(
                f"Setting {name} cookie to default expiration (1 week): {expires}"
            )

        cookies.append(create_cookie_template(name, value, domain, expires))

    return cookies


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
        driver.get(TWITTER_LOGIN_URL)

        # Wait for page to load using document readyState
        wait_start = time.time()
        max_wait = 10  # Maximum seconds to wait

        while time.time() - wait_start < max_wait:
            # Check if document is ready
            try:
                ready_state = driver.execute_script("return document.readyState")

                # Check if login form elements are visible
                login_elements = driver.find_elements(
                    By.CSS_SELECTOR,
                    'input[name="text"], div[role="button"], form[data-testid="LoginForm"]',
                )

                if ready_state == "complete" and any(
                    elem.is_displayed() for elem in login_elements if login_elements
                ):
                    logger.info("Login page loaded successfully")
                    break
            except WebDriverException as e:
                # Check if window was closed - if so, propagate this up immediately
                if (
                    "no such window" in str(e).lower()
                    or "no such session" in str(e).lower()
                ):
                    logger.info(
                        "Browser window was closed during page load. Might be for VPN switching."
                    )
                    raise
                logger.warning(f"Error checking page load: {str(e)}")

            # Short sleep between checks
            time.sleep(0.5)

        # If we got here and timed out, log a warning but continue
        if time.time() - wait_start >= max_wait:
            logger.warning(
                "Timed out waiting for login page to fully load, but continuing anyway"
            )
    except WebDriverException as e:
        # Check if window was closed - if so, propagate this up immediately
        if "no such window" in str(e).lower() or "no such session" in str(e).lower():
            logger.info(
                "Browser window was closed during navigation. Might be for VPN switching."
            )
            raise
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
            # Immediately propagate window closing exceptions
            if (
                "no such window" in str(e).lower()
                or "no such session" in str(e).lower()
            ):
                logger.info("Browser window was closed. Might be for VPN switching.")
                raise

            # Handle other WebDriver exceptions
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
                    # Always navigate to twitter.com, never x.com
                    driver.get("https://twitter.com/home")
                    time.sleep(3)
                except WebDriverException as e:
                    # Check if window was closed
                    if (
                        "no such window" in str(e).lower()
                        or "no such session" in str(e).lower()
                    ):
                        logger.info(
                            "Browser window was closed after login. Might be for VPN switching."
                        )
                        raise
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
        except WebDriverException as e:
            # Check if window was closed
            if (
                "no such window" in str(e).lower()
                or "no such session" in str(e).lower()
            ):
                logger.info(
                    "Browser window was closed after login. Might be for VPN switching."
                )
                raise
            logger.error(f"Error after successful login: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error after successful login: {str(e)}")
            return False
    else:
        logger.error(f"Failed to login for {username} within the time limit")
        return False


def main():
    """Main function to process Twitter accounts from environment variable."""
    logger.info("Starting cookie grabber")

    # Check for required environment variables
    if not os.environ.get("TWITTER_EMAIL"):
        logger.error("TWITTER_EMAIL environment variable is not set.")
        logger.error("This is required for email verification during login.")
        return

    # Get Twitter accounts from environment variable
    twitter_accounts_str = os.environ.get("TWITTER_ACCOUNTS", "")

    if not twitter_accounts_str:
        logger.error("TWITTER_ACCOUNTS environment variable is not set.")
        logger.error("Format should be: username1:password1,username2:password2")
        return

    account_pairs = twitter_accounts_str.split(",")
    logger.info(f"Found {len(account_pairs)} accounts to process")
    logger.info(
        "Browser reset between accounts is disabled to reduce verification challenges"
    )

    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Process accounts one by one
    current_account_index = 0
    while current_account_index < len(account_pairs):
        # Maximum number of retries for account processing
        max_retries = 5  # Increased retries to allow for VPN switches
        retry_count = 0
        driver = None

        account_pair = account_pairs[current_account_index]
        if ":" not in account_pair:
            logger.error(
                f"Invalid account format: {account_pair}. Expected format: username:password"
            )
            current_account_index += 1
            continue

        username, password = account_pair.split(":", 1)
        username = username.strip()
        password = password.strip()

        logger.info(
            f"Processing account {current_account_index+1}/{len(account_pairs)}: {username}"
        )

        # Process account with potential window closing for VPN switching
        success = False
        while retry_count < max_retries and not success:
            try:
                # Initialize a new driver for each retry
                if driver is not None:
                    try:
                        driver.quit()
                    except:
                        pass

                driver = setup_driver()
                logger.info(
                    f"Browser initialized for account: {username} (attempt {retry_count+1}/{max_retries})"
                )

                # Process the current account
                success = process_account_state_machine(driver, username, password)

                if success:
                    logger.info(f"Successfully processed account: {username}")
                else:
                    retry_count += 1
                    logger.info(
                        f"Account processing unsuccessful. Retries left: {max_retries - retry_count}"
                    )
                    time.sleep(10)  # Brief pause before retry

            except WebDriverException as e:
                # Special handling for closed window (VPN switching)
                if (
                    "no such window" in str(e).lower()
                    or "no such session" in str(e).lower()
                ):
                    logger.info(
                        "Browser window was closed. This might be for VPN switching."
                    )
                    logger.info(
                        "Waiting 30 seconds for VPN to stabilize before retrying..."
                    )

                    # Clean up the driver
                    try:
                        if driver:
                            driver.quit()
                    except:
                        pass

                    # Wait for VPN switch to complete
                    time.sleep(30)

                    # Don't increment retry count for intentional window closing
                    # This allows unlimited VPN switches
                    logger.info(f"Resuming after window close for account: {username}")
                else:
                    # Handle other WebDriver exceptions
                    retry_count += 1
                    logger.error(
                        f"WebDriver error (attempt {retry_count}/{max_retries}): {str(e)}"
                    )
                    time.sleep(15)

            except Exception as e:
                retry_count += 1
                logger.error(
                    f"Unexpected error (attempt {retry_count}/{max_retries}): {str(e)}"
                )
                time.sleep(15)

                try:
                    if driver:
                        driver.quit()
                except:
                    pass

        # Clean up the driver
        try:
            if driver:
                driver.quit()
        except:
            pass

        # Move to next account only if successful or max retries reached
        if success or retry_count >= max_retries:
            if success:
                logger.info(f"Successfully completed account: {username}")
            else:
                logger.warning(
                    f"Failed to process account after {max_retries} attempts: {username}"
                )

            current_account_index += 1

            # Cooldown between accounts
            if current_account_index < len(account_pairs):
                cool_down = random.uniform(5, 10)  # 5-10 seconds cooldown
                logger.info(
                    f"Cooling down for {cool_down:.1f} seconds before next account"
                )
                time.sleep(cool_down)

    logger.info("All accounts processed")


if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    logger.info("Starting cookie grabber script")
    main()
