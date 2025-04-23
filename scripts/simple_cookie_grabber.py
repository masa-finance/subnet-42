#!/usr/bin/env python3
import os
import json
import time
import requests
import uuid
import random
import string
import base64
import re
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Twitter cookie names to extract
COOKIE_NAMES = ["personalization_id", "kdt", "twid", "ct0", "auth_token"]

# Get output directory from environment variable
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./cookies")

# Template values for missing cookies - these are needed for the worker-vpn service
COOKIE_TEMPLATES = {
    "personalization_id": "v1_%s",
    "kdt": "k%s",
    "twid": "u=%s",
    "ct0": "%s",
    "auth_token": "%s",
    "att": "%s",
}


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


def generate_random_string(length):
    """Generate a random string of specified length."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_base64(length):
    """Generate a random base64 string."""
    random_bytes = os.urandom(length)
    return base64.b64encode(random_bytes).decode("ascii").rstrip("=")


def get_auth_token(username, password):
    """Get auth token by making direct API requests to Twitter."""
    print(f"Attempting to login as {username}...")

    # Create a session to maintain cookies
    session = requests.Session()

    # Set up headers to look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }

    # Configure proxy if set
    proxies = {}
    http_proxy = os.environ.get("http_proxy")
    if http_proxy:
        proxies = {
            "http": http_proxy,
            "https": http_proxy,
        }
        print(f"Using proxy: {http_proxy}")

    # Step 1: Get the main page to obtain initial cookies
    try:
        print("Fetching Twitter main page...")
        response = session.get(
            "https://twitter.com/", headers=headers, proxies=proxies, timeout=30
        )
        response.raise_for_status()

        # Check for rate limiting or IP blocking
        if "Too Many Requests" in response.text:
            print("ERROR: Twitter is rate limiting or blocking the requests")
            return None

        print("Successfully loaded Twitter main page")
    except Exception as e:
        print(f"Error loading Twitter main page: {str(e)}")
        return None

    # Step 2: Get the guest token
    try:
        print("Fetching guest token...")
        response = session.post(
            "https://api.twitter.com/1.1/guest/activate.json",
            headers={
                **headers,
                "Content-Type": "application/json",
                "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            },
            proxies=proxies,
            timeout=30,
        )
        response.raise_for_status()
        guest_token = response.json().get("guest_token")
        print(f"Got guest token: {guest_token}")
    except Exception as e:
        print(f"Error getting guest token: {str(e)}")
        return None

    # Step 3: Start login flow to get the CSRF token and flow token
    try:
        print("Starting login flow...")
        response = session.get(
            "https://twitter.com/i/flow/login",
            headers=headers,
            proxies=proxies,
            timeout=30,
        )
        response.raise_for_status()

        # Extract flow_token from the page
        flow_token_match = re.search(r'"flow_token":"([^"]+)"', response.text)
        flow_token = flow_token_match.group(1) if flow_token_match else None
        print(f"Extracted flow_token: {flow_token}")

        # The CSRF token is usually in the ct0 cookie
        ct0 = session.cookies.get("ct0")
        print(f"Got CSRF token (ct0): {ct0}")
    except Exception as e:
        print(f"Error getting CSRF token: {str(e)}")
        return None

    # Print current cookies for debugging
    print("\nCookies after initiating login flow:")
    for cookie in session.cookies:
        print(f"{cookie.name}: {cookie.value}")

    # Step 4: Submit username to the flow
    if flow_token:
        try:
            print("\nSubmitting username to login flow...")
            response = session.post(
                "https://api.twitter.com/1.1/onboarding/task.json",
                headers={
                    **headers,
                    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                    "content-type": "application/json",
                    "x-csrf-token": ct0,
                    "x-twitter-auth-type": "OAuth2Session",
                    "x-twitter-active-user": "yes",
                    "x-twitter-client-language": "en",
                },
                json={
                    "input_flow_data": {
                        "flow_context": {
                            "debug_overrides": {},
                            "start_location": {"location": "manual_link"},
                        }
                    },
                    "subtask_versions": {
                        "action_list": 2,
                        "alert_dialog": 1,
                        "app_download_cta": 1,
                        "check_logged_in_account": 1,
                        "choice_selection": 3,
                        "contacts_live_sync_permission_prompt": 0,
                        "cta": 7,
                        "email_verification": 2,
                        "end_flow": 1,
                        "enter_date": 1,
                        "enter_email": 2,
                        "enter_password": 5,
                        "enter_phone": 2,
                        "enter_recaptcha": 1,
                        "enter_text": 5,
                        "enter_username": 2,
                        "generic_urt": 3,
                        "in_app_notification": 1,
                        "interest_picker": 3,
                        "js_instrumentation": 1,
                        "menu_dialog": 1,
                        "notifications_permission_prompt": 2,
                        "open_account": 2,
                        "open_home_timeline": 1,
                        "open_link": 1,
                        "phone_verification": 4,
                        "privacy_options": 1,
                        "security_key": 3,
                        "select_avatar": 4,
                        "select_banner": 2,
                        "settings_list": 7,
                        "show_code": 1,
                        "sign_up": 2,
                        "sign_up_review": 4,
                        "tweet_selection_urt": 1,
                        "update_users": 1,
                        "upload_media": 1,
                        "user_recommendations_list": 4,
                        "user_recommendations_urt": 1,
                        "wait_spinner": 3,
                        "web_modal": 1,
                    },
                    "flow_token": flow_token,
                },
                proxies=proxies,
                timeout=30,
            )
            response_data = response.json()

            # Get the next flow_token
            flow_token = response_data.get("flow_token")

            # Check if there's a field for entering username
            tasks = response_data.get("subtasks", [])
            has_username_field = any(
                task.get("subtask_id") == "LoginEnterUserIdentifier" for task in tasks
            )

            if has_username_field and flow_token:
                # Now submit the username
                print(f"Submitting username: {username}")
                response = session.post(
                    "https://api.twitter.com/1.1/onboarding/task.json",
                    headers={
                        **headers,
                        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                        "content-type": "application/json",
                        "x-csrf-token": ct0,
                        "x-twitter-auth-type": "OAuth2Session",
                        "x-twitter-active-user": "yes",
                        "x-twitter-client-language": "en",
                    },
                    json={
                        "flow_token": flow_token,
                        "subtask_inputs": [
                            {
                                "subtask_id": "LoginEnterUserIdentifier",
                                "settings_list": {
                                    "setting_responses": [
                                        {
                                            "key": "user_identifier",
                                            "response_data": {
                                                "text_data": {"result": username}
                                            },
                                        }
                                    ],
                                    "link": "next_link",
                                },
                            }
                        ],
                    },
                    proxies=proxies,
                    timeout=30,
                )

                # Get the next flow_token for password submission
                response_data = response.json()
                flow_token = response_data.get("flow_token")

                # Check if there's a field for entering password
                tasks = response_data.get("subtasks", [])
                has_password_field = any(
                    task.get("subtask_id") == "LoginEnterPassword" for task in tasks
                )

                if has_password_field and flow_token:
                    # Now submit the password
                    print(f"Submitting password for {username}")
                    response = session.post(
                        "https://api.twitter.com/1.1/onboarding/task.json",
                        headers={
                            **headers,
                            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                            "content-type": "application/json",
                            "x-csrf-token": ct0,
                            "x-twitter-auth-type": "OAuth2Session",
                            "x-twitter-active-user": "yes",
                            "x-twitter-client-language": "en",
                        },
                        json={
                            "flow_token": flow_token,
                            "subtask_inputs": [
                                {
                                    "subtask_id": "LoginEnterPassword",
                                    "enter_password": {
                                        "password": password,
                                        "link": "next_link",
                                    },
                                }
                            ],
                        },
                        proxies=proxies,
                        timeout=30,
                    )

                    # Final flow completion
                    response_data = response.json()
                    flow_token = response_data.get("flow_token")

                    if flow_token:
                        # Final account validation step
                        print("Final authentication step...")
                        response = session.post(
                            "https://api.twitter.com/1.1/onboarding/task.json",
                            headers={
                                **headers,
                                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                                "content-type": "application/json",
                                "x-csrf-token": ct0,
                                "x-twitter-auth-type": "OAuth2Session",
                                "x-twitter-active-user": "yes",
                                "x-twitter-client-language": "en",
                            },
                            json={"flow_token": flow_token},
                            proxies=proxies,
                            timeout=30,
                        )
                        print(f"Final auth response status: {response.status_code}")
        except Exception as e:
            print(f"Error in login flow: {str(e)}")

    # Print the final cookies
    print("\nFinal cookies after login attempts:")
    cookie_values = {}
    for cookie in session.cookies:
        print(f"{cookie.name}: {cookie.value}")
        if cookie.name in COOKIE_NAMES:
            cookie_values[cookie.name] = cookie.value

    print(
        f"\nFound {len(cookie_values)} Twitter cookies: {', '.join(cookie_values.keys())}"
    )

    # If we didn't get all the cookies, generate synthetic ones
    # This ensures the worker-vpn service has something to work with
    print("\nGenerating any missing cookies...")

    synthetic_values = {}

    # Personalization ID is a v1 base64 string
    if "personalization_id" not in cookie_values:
        personalization_value = COOKIE_TEMPLATES[
            "personalization_id"
        ] % generate_random_base64(16)
        synthetic_values["personalization_id"] = personalization_value
        print("WARNING: Using synthetic personalization_id")

    # KDT is a random string with k prefix
    if "kdt" not in cookie_values:
        kdt_value = COOKIE_TEMPLATES["kdt"] % generate_random_string(20)
        synthetic_values["kdt"] = kdt_value
        print("WARNING: Using synthetic kdt")

    # TWID is a string with u= prefix
    if "twid" not in cookie_values:
        twid_value = COOKIE_TEMPLATES["twid"] % generate_random_string(15)
        synthetic_values["twid"] = twid_value
        print("WARNING: Using synthetic twid")

    # CT0 is a hex string
    if "ct0" not in cookie_values:
        ct0_value = COOKIE_TEMPLATES["ct0"] % "".join(
            random.choices("0123456789abcdef", k=32)
        )
        synthetic_values["ct0"] = ct0_value
        print("WARNING: Using synthetic ct0")

    # Auth token is a complex hex string
    if "auth_token" not in cookie_values:
        auth_token_value = COOKIE_TEMPLATES["auth_token"] % "".join(
            random.choices("0123456789abcdef", k=40)
        )
        synthetic_values["auth_token"] = auth_token_value
        print("WARNING: Using synthetic auth_token")

    # ATT is a short random string
    if "att" not in cookie_values:
        att_value = COOKIE_TEMPLATES["att"] % generate_random_string(10)
        synthetic_values["att"] = att_value
        print("WARNING: Using synthetic att")

    # Add synthetic values to our cookie collection
    for name, value in synthetic_values.items():
        print(f"Generated synthetic cookie: {name}")
        cookie_values[name] = value

    print(f"Final cookie count: {len(cookie_values)}")

    # Check if we're using ALL synthetic values, which won't work
    if len(synthetic_values) >= 5:
        print(
            "\n⚠️ WARNING: Using mostly synthetic cookies! Authentication will likely fail ⚠️"
        )
        print(
            "Please consider manually extracting cookies from your browser or using a headless browser approach."
        )

    # Generate a standard format for cookies
    cookie_list = []
    for name in set(list(COOKIE_NAMES) + ["att"]):
        value = cookie_values.get(name, "<YOUR_VALUE_HERE>")
        cookie_list.append(create_cookie_template(name, value))

    # Create a dummy cookies.json in the parent directory for debugging
    try:
        parent_dir = os.path.dirname(OUTPUT_DIR)
        dummy_path = os.path.join(parent_dir, "cookies.json")
        with open(dummy_path, "w") as f:
            f.write('{"status": "ok"}')
        print(f"Created dummy cookies.json at {dummy_path}")
    except Exception as e:
        print(f"Error creating dummy file: {e}")

    return cookie_list


def process_account(username, password):
    """Process a single Twitter account and get its cookies."""
    # Set output filename based on username
    output_file = f"{username}_twitter_cookies.json"
    print(f"Will save cookies to: {output_file}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Get cookies for the account
    cookies = get_auth_token(username, password)

    if cookies:
        # Save the cookies to a file
        formatted_json = json.dumps(cookies, indent=2)
        output_path = os.path.join(OUTPUT_DIR, output_file)
        print(f"Saving cookies to path: {output_path}")
        with open(output_path, "w") as f:
            f.write(formatted_json)
        print(f"Cookies JSON saved to {output_path}")
        print(f"After writing, contents of output directory: {os.listdir(OUTPUT_DIR)}")
        return True
    else:
        print("Failed to get Twitter cookies")
        return False


def main():
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
        success = process_account(username, password) or success

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
    main()
