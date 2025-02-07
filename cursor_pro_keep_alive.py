import os
import platform
import json
import sys
from colorama import Fore, Style
from enum import Enum
from typing import Optional

from exit_cursor import ExitCursor
import patch_cursor_get_machine_id
from reset_machine import MachineIDResetter

os.environ["PYTHONVERBOSE"] = "0"
os.environ["PYINSTALLER_VERBOSE"] = "0"

import time
import random
from cursor_auth_manager import CursorAuthManager
import os
from logger import logging
from browser_utils import BrowserManager
from get_email_code import EmailVerificationHandler
from logo import print_logo
from config import Config
from datetime import datetime

# Define EMOJI dictionary
EMOJI = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}


class VerificationStatus(Enum):
    """Verification status enumeration"""

    PASSWORD_PAGE = "@name=password"
    CAPTCHA_PAGE = "@data-index=0"
    ACCOUNT_SETTINGS = "Account Settings"


class TurnstileError(Exception):
    """Turnstile verification related exception"""

    pass


def save_screenshot(tab, stage: str, timestamp: bool = True) -> None:
    """
    Save page screenshot

    Args:
        tab: Browser tab object
        stage: Screenshot stage identifier
        timestamp: Whether to add timestamp
    """
    try:
        # Create screenshots directory
        screenshot_dir = "screenshots"
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        # Generate filename
        if timestamp:
            filename = f"turnstile_{stage}_{int(time.time())}.png"
        else:
            filename = f"turnstile_{stage}.png"

        filepath = os.path.join(screenshot_dir, filename)

        # Save screenshot
        tab.get_screenshot(filepath)
        logging.debug(f"Screenshot saved: {filepath}")
    except Exception as e:
        logging.warning(f"Failed to save screenshot: {str(e)}")


def check_verification_success(tab) -> Optional[VerificationStatus]:
    """
    Check if verification is successful

    Returns:
        VerificationStatus: Returns corresponding status if successful, None if failed
    """
    for status in VerificationStatus:
        if tab.ele(status.value):
            logging.info(f"Verification successful - Reached {status.name} page")
            return status
    return None


def handle_turnstile(tab, max_retries: int = 2, retry_interval: tuple = (1, 2)) -> bool:
    """
    Handle Turnstile verification

    Args:
        tab: Browser tab object
        max_retries: Maximum number of retries
        retry_interval: Retry interval time range (min, max)

    Returns:
        bool: Whether verification was successful

    Raises:
        TurnstileError: Exception during verification process
    """
    logging.info("Checking Turnstile verification...")
    save_screenshot(tab, "start")

    retry_count = 0

    try:
        while retry_count < max_retries:
            retry_count += 1
            logging.debug(f"Attempt {retry_count} at verification")

            try:
                # Locate verification frame element
                challenge_check = (
                    tab.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )

                if challenge_check:
                    logging.info("Detected Turnstile verification frame, starting process...")
                    # Random delay before clicking verification
                    time.sleep(random.uniform(1, 3))
                    challenge_check.click()
                    time.sleep(2)

                    # Save post-verification screenshot
                    save_screenshot(tab, "clicked")

                    # Check verification result
                    if check_verification_success(tab):
                        logging.info("Turnstile verification passed")
                        save_screenshot(tab, "success")
                        return True

            except Exception as e:
                logging.debug(f"Current attempt unsuccessful: {str(e)}")

            # Check if already verified
            if check_verification_success(tab):
                return True

            # Random delay before next attempt
            time.sleep(random.uniform(*retry_interval))

        # Maximum retries exceeded
        logging.error(f"Verification failed - Maximum retries {max_retries} reached")
        save_screenshot(tab, "failed")
        return False

    except Exception as e:
        error_msg = f"Exception occurred during Turnstile verification: {str(e)}"
        logging.error(error_msg)
        save_screenshot(tab, "error")
        raise TurnstileError(error_msg)


def get_cursor_session_token(tab, max_attempts=3, retry_interval=2):
    """
    Get Cursor session token with retry mechanism
    :param tab: Browser tab
    :param max_attempts: Maximum number of attempts
    :param retry_interval: Retry interval (seconds)
    :return: session token or None
    """
    logging.info("Starting to get cookie")
    attempts = 0

    while attempts < max_attempts:
        try:
            cookies = tab.cookies()
            for cookie in cookies:
                if cookie.get("name") == "WorkosCursorSessionToken":
                    return cookie["value"].split("%3A%3A")[1]

            attempts += 1
            if attempts < max_attempts:
                logging.warning(
                    f"Attempt {attempts} failed to get CursorSessionToken, retrying in {retry_interval} seconds..."
                )
                time.sleep(retry_interval)
            else:
                logging.error(
                    f"Maximum attempts ({max_attempts}) reached, failed to get CursorSessionToken"
                )

        except Exception as e:
            logging.error(f"Failed to get cookie: {str(e)}")
            attempts += 1
            if attempts < max_attempts:
                logging.info(f"Will retry in {retry_interval} seconds...")
                time.sleep(retry_interval)

    return None


def update_cursor_auth(email=None, access_token=None, refresh_token=None):
    """
    Convenience function to update Cursor authentication information
    """
    auth_manager = CursorAuthManager()
    return auth_manager.update_auth(email, access_token, refresh_token)


def sign_up_account(browser, tab):
    logging.info("=== Starting account registration process ===")
    logging.info(f"Visiting registration page: {sign_up_url}")
    tab.get(sign_up_url)

    try:
        if tab.ele("@name=first_name"):
            logging.info("Filling in personal information...")
            tab.actions.click("@name=first_name").input(first_name)
            logging.info(f"First name entered: {first_name}")
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=last_name").input(last_name)
            logging.info(f"Last name entered: {last_name}")
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=email").input(account)
            logging.info(f"Email entered: {account}")
            time.sleep(random.uniform(1, 3))

            logging.info("Submitting personal information...")
            tab.actions.click("@type=submit")

    except Exception as e:
        logging.error(f"Registration page access failed: {str(e)}")
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            logging.info("Setting password...")
            tab.ele("@name=password").input(password)
            time.sleep(random.uniform(1, 3))

            logging.info("Submitting password...")
            tab.ele("@type=submit").click()
            logging.info("Password setup complete, waiting for system response...")

    except Exception as e:
        logging.error(f"Password setup failed: {str(e)}")
        return False

    if tab.ele("This email is not available."):
        logging.error("Registration failed: Email already in use")
        return False

    handle_turnstile(tab)

    while True:
        try:
            if tab.ele("Account Settings"):
                logging.info("Registration successful - Entered account settings page")
                break
            if tab.ele("@data-index=0"):
                logging.info("Getting email verification code...")
                code = email_handler.get_verification_code()
                if not code:
                    logging.error("Failed to get verification code")
                    return False

                logging.info(f"Successfully got verification code: {code}")
                logging.info("Inputting verification code...")
                i = 0
                for digit in code:
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                    i += 1
                logging.info("Verification code input complete")
                break
        except Exception as e:
            logging.error(f"Verification code processing error: {str(e)}")

    handle_turnstile(tab)
    wait_time = random.randint(3, 6)
    for i in range(wait_time):
        logging.info(f"Waiting for system processing... {wait_time-i} seconds remaining")
        time.sleep(1)

    logging.info("Getting account information...")
    tab.get(settings_url)
    try:
        usage_selector = (
            "css:div.col-span-2 > div > div > div > div > "
            "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
            "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
        )
        usage_ele = tab.ele(usage_selector)
        if usage_ele:
            usage_info = usage_ele.text
            total_usage = usage_info.split("/")[-1].strip()
            logging.info(f"Account available credit limit: {total_usage}")
    except Exception as e:
        logging.error(f"Failed to get account credit limit information: {str(e)}")

    logging.info("\n=== Registration completed ===")
    account_info = f"Cursor account information:\nEmail: {account}\nPassword: {password}"
    logging.info(account_info)
    time.sleep(5)
    return True


class EmailGenerator:
    def __init__(
        self,
        password="".join(
            random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
                k=12,
            )
        ),
    ):
        configInstance = Config()
        configInstance.print_config()
        self.domain = configInstance.get_domain()
        self.default_password = password
        self.default_first_name = self.generate_random_name()
        self.default_last_name = self.generate_random_name()

    def generate_random_name(self, length=6):
        """Generate random username"""
        first_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        rest_letters = "".join(
            random.choices("abcdefghijklmnopqrstuvwxyz", k=length - 1)
        )
        return first_letter + rest_letters

    def generate_email(self, length=8):
        """Generate random email address"""
        random_str = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=length))
        timestamp = str(int(time.time()))[-6:]  # Use last 6 digits of timestamp
        return f"{random_str}{timestamp}@{self.domain}"

    def get_account_info(self):
        """Get complete account information"""
        return {
            "email": self.generate_email(),
            "password": self.default_password,
            "first_name": self.default_first_name,
            "last_name": self.default_last_name,
        }


def get_user_agent():
    """Get user_agent"""
    try:
        # Use JavaScript to get user agent
        browser_manager = BrowserManager()
        browser = browser_manager.init_browser()
        user_agent = browser.latest_tab.run_js("return navigator.userAgent")
        browser_manager.quit()
        return user_agent
    except Exception as e:
        logging.error(f"Failed to get user agent: {str(e)}")
        return None


def check_cursor_version():
    """Check cursor version"""
    pkg_path, main_path = patch_cursor_get_machine_id.get_cursor_paths()
    with open(pkg_path, "r", encoding="utf-8") as f:
        version = json.load(f)["version"]
    return patch_cursor_get_machine_id.version_check(version, min_version="0.45.0")


def reset_machine_id(greater_than_0_45):
    if greater_than_0_45:
        # Prompt user to manually run script https://github.com/chengazhen/cursor-auto-free/blob/main/patch_cursor_get_machine_id.py
        patch_cursor_get_machine_id.patch_cursor_get_machine_id()
    else:
        MachineIDResetter().reset_machine_ids()


if __name__ == "__main__":
    print_logo()
    greater_than_0_45 = check_cursor_version()
    browser_manager = None
    try:
        logging.info("\n=== Starting program ===")
        # ExitCursor()

        # Prompt user to choose operation mode
        print("\nPlease choose operation mode:")
        print("1. Reset machine code only")
        print("2. Complete registration process")

        while True:
            try:
                choice = int(input("Please enter option (1 or 2): ").strip())
                if choice in [1, 2]:
                    break
                else:
                    print("Invalid option, please enter again")
            except ValueError:
                print("Please enter a valid number")

        if choice == 1:
            # Execute reset machine code only
            reset_machine_id(greater_than_0_45)
            logging.info("Machine code reset completed")
            sys.exit(0)

        logging.info("Starting to initialize browser...")

        # Get user_agent
        user_agent = get_user_agent()
        if not user_agent:
            logging.error("Failed to get user agent, using default value")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Remove "HeadlessChrome" from user_agent
        user_agent = user_agent.replace("HeadlessChrome", "Chrome")

        browser_manager = BrowserManager()
        browser = browser_manager.init_browser(user_agent)

        # Get and print browser's user-agent
        user_agent = browser.latest_tab.run_js("return navigator.userAgent")

        logging.info("Starting to initialize email verification module...")
        email_handler = EmailVerificationHandler()

        logging.info("\n=== Configuration information ===")
        login_url = "https://authenticator.cursor.sh"
        sign_up_url = "https://authenticator.cursor.sh/sign-up"
        settings_url = "https://www.cursor.com/settings"
        mail_url = "https://tempmail.plus"

        logging.info("Generating random account information...")
        email_generator = EmailGenerator()
        account = email_generator.generate_email()
        password = email_generator.default_password
        first_name = email_generator.default_first_name
        last_name = email_generator.default_last_name

        logging.info(f"Generated email account: {account}")
        auto_update_cursor_auth = True

        tab = browser.latest_tab

        tab.run_js("try { turnstile.reset() } catch(e) { }")

        logging.info("\n=== Starting registration process ===")
        logging.info(f"Visiting login page: {login_url}")
        tab.get(login_url)

        if sign_up_account(browser, tab):
            logging.info("Getting session token...")
            token = get_cursor_session_token(tab)
            if token:
                logging.info("Updating authentication information...")
                update_cursor_auth(
                    email=account, access_token=token, refresh_token=token
                )

                logging.info("Resetting machine code...")
                reset_machine_id(greater_than_0_45)
                logging.info("All operations completed")
            else:
                logging.error("Failed to get session token, registration process not completed")

    except Exception as e:
        logging.error(f"Program execution error: {str(e)}")
        import traceback

        logging.error(traceback.format_exc())
    finally:
        if browser_manager:
            browser_manager.quit()
        input("\nProgram execution completed, press Enter to exit...")
