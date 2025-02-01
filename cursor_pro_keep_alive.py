import os

from exit_cursor import ExitCursor
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


def handle_turnstile(tab):
    logging.info("Checking Turnstile verification...")
    try:
        while True:
            try:
                challengeCheck = (
                    tab.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )

                if challengeCheck:
                    logging.info("Turnstile verification detected, processing...")
                    time.sleep(random.uniform(1, 3))
                    challengeCheck.click()
                    time.sleep(2)
                    logging.info("Turnstile verification passed")
                    return True
            except:
                pass

            if tab.ele("@name=password"):
                logging.info("Verification successful - Reached password input page")
                break
            if tab.ele("@data-index=0"):
                logging.info("Verification successful - Reached verification code input page")
                break
            if tab.ele("Account Settings"):
                logging.info("Verification successful - Reached account settings page")
                break

            time.sleep(random.uniform(1, 2))
    except Exception as e:
        logging.error(f"Turnstile verification failed: {str(e)}")
        return False


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
    logging.info("=== Starting Account Registration Process ===")
    logging.info(f"Visiting registration page: {sign_up_url}")
    tab.get(sign_up_url)

    try:
        if tab.ele("@name=first_name"):
            logging.info("Filling personal information...")
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
        logging.error(f"Failed to access registration page: {str(e)}")
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            logging.info("Setting password...")
            tab.ele("@name=password").input(password)
            time.sleep(random.uniform(1, 3))

            logging.info("Submitting password...")
            tab.ele("@type=submit").click()
            logging.info("Password set, waiting for system response...")

    except Exception as e:
        logging.error(f"Failed to set password: {str(e)}")
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
                logging.info("Entering verification code...")
                i = 0
                for digit in code:
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                    i += 1
                logging.info("Verification code entered")
                break
        except Exception as e:
            logging.error(f"Error during verification code process: {str(e)}")

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
            logging.info(f"Account usage limit: {total_usage}")
    except Exception as e:
        logging.error(f"Failed to get account usage information: {str(e)}")

    logging.info("\n=== Registration Complete ===")
    account_info = f"Cursor Account Information:\nEmail: {account}\nPassword: {password}"
    logging.info(account_info)
    time.sleep(5)
    return True


def generate_turkish_first_name():
    """Generate random Turkish first name"""
    turkish_names = [
        "Ahmet", "Mehmet", "Ali", "Mustafa", "Hüseyin", "Hasan", "Murat",
        "Yusuf", "Osman", "Kemal", "Orhan", "Halil", "Cem", "Burak",
        "Ayşe", "Fatma", "Emine", "Hatice", "Zeynep", "Elif", "Meryem",
        "Zehra", "Sevgi", "Esra", "Derya", "Merve", "Ebru", "Gül", "Seda",
        "Can", "Deniz", "Ege", "Kaya", "Yağız", "Toprak", "Çınar", "Yiğit", "Alp",
        "Berk", "Doruk", "Kutay", "Tan", "Efe", "Mert", "Onur", "Tolga", "Umut"
    ]
    return random.choice(turkish_names)


def generate_turkish_last_name():
    """Generate random Turkish last name"""
    turkish_surnames = [
        "Yılmaz", "Kaya", "Demir", "Yıldız", "Yıldırım",
        "Aydın", "Arslan", "Doğan", "Kılıç", "Aslan", "Erdoğan",
        "Koç", "Kurt", "Polat", "Korkmaz", "Aktaş", "Karahan",
        "Türk", "Kocaman", "Güler", "Yalçın", "Turan", "Güneş", "Bulut", "Tekin",
        "Yavuz", "Aksoy", "Avcı", "Ateş", "Taş", "Alp", "Yüksel", "Demirci",
        "Kalkan", "Toprak", "Dağ", "Deniz", "Akın", "Sarı", "Bilgin"
    ]
    return random.choice(turkish_surnames)


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
        
        # Generate name and surname once during initialization
        self.turkish_name = generate_turkish_first_name()
        self.turkish_surname = generate_turkish_last_name()
        
        # Convert Turkish characters to their ASCII equivalents once
        tr_to_en = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgioscCGIOSU")
        self.ascii_name = self.turkish_name.lower().translate(tr_to_en)
        self.ascii_surname = self.turkish_surname.lower().translate(tr_to_en)

    def generate_email(self):
        """Generate email address in format: turkish_name.turkish_surname.random_3_digits@domain"""
        random_digits = "".join(random.choices("0123456789", k=3))
        return f"{self.ascii_name}.{self.ascii_surname}.{random_digits}@{self.domain}"

    def get_account_info(self):
        """Get complete account information"""
        return {
            "email": self.generate_email(),
            "password": self.default_password,
            "first_name": self.turkish_name,
            "last_name": self.turkish_surname,
        }


if __name__ == "__main__":
    print_logo()
    browser_manager = None
    try:
        logging.info("\n=== Initializing Program ===")
        ExitCursor()
        logging.info("Initializing browser...")
        browser_manager = BrowserManager()
        browser = browser_manager.init_browser()

        logging.info("Initializing email verification module...")
        email_handler = EmailVerificationHandler()

        logging.info("\n=== Configuration Information ===")
        login_url = "https://authenticator.cursor.sh"
        sign_up_url = "https://authenticator.cursor.sh/sign-up"
        settings_url = "https://www.cursor.com/settings"
        mail_url = "https://tempmail.plus"

        logging.info("Generating random account information...")
        email_generator = EmailGenerator()
        account = email_generator.generate_email()
        password = email_generator.default_password
        first_name = email_generator.turkish_name
        last_name = email_generator.turkish_surname

        logging.info(f"Generated email account: {account}")
        auto_update_cursor_auth = True

        tab = browser.latest_tab
        tab.run_js("try { turnstile.reset() } catch(e) { }")

        logging.info("\n=== Starting Registration Process ===")
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

                logging.info("Resetting machine ID...")
                MachineIDResetter().reset_machine_ids()
                logging.info("All operations completed")
            else:
                logging.error("Failed to get session token, registration process incomplete")

    except Exception as e:
        logging.error(f"Program execution error: {str(e)}")
        import traceback

        logging.error(traceback.format_exc())
    finally:
        if browser_manager:
            browser_manager.quit()
        input("\nProgram execution completed, press Enter to exit...")
