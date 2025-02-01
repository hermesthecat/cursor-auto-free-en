from DrissionPage import ChromiumOptions, Chromium
from DrissionPage.common import Keys
import time
import re
import sys
import os


def get_extension_path():
    """Get extension path"""
    root_dir = os.getcwd()
    extension_path = os.path.join(root_dir, "turnstilePatch")

    if hasattr(sys, "_MEIPASS"):
        print("Running in packaged environment")
        extension_path = os.path.join(sys._MEIPASS, "turnstilePatch")

    print(f"Attempting to load extension path: {extension_path}")

    if not os.path.exists(extension_path):
        raise FileNotFoundError(
            f"Extension does not exist: {extension_path}\nPlease ensure turnstilePatch folder is in the correct location"
        )

    return extension_path


def get_browser_options():
    co = ChromiumOptions()
    try:
        extension_path = get_extension_path()
        co.add_extension(extension_path)
    except FileNotFoundError as e:
        print(f"Warning: {e}")

    co.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.92 Safari/537.36"
    )
    co.set_pref("credentials_enable_service", False)
    co.set_argument("--hide-crash-restore-bubble")
    co.auto_port()

    # Special handling for Mac systems
    if sys.platform == "darwin":
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-gpu")

    return co


def get_veri_code(username):
    # Use the same browser configuration
    co = get_browser_options()
    browser = Chromium(co)
    code = None

    try:
        # Get current tab
        tab = browser.latest_tab
        tab.run_js("try { turnstile.reset() } catch(e) { }")

        # Open temporary email website
        tab.get("https://tempmail.plus/zh")
        time.sleep(2)

        # Set email username
        while True:
            if tab.ele("@id=pre_button"):
                # Click input box
                tab.actions.click("@id=pre_button")
                time.sleep(1)
                # Delete previous content
                tab.run_js('document.getElementById("pre_button").value = ""')

                # Enter new username and press Enter
                tab.actions.input(username).key_down(Keys.ENTER).key_up(Keys.ENTER)
                break
            time.sleep(1)

        # Wait and get new email
        while True:
            new_mail = tab.ele("@class=mail")
            if new_mail:
                if new_mail.text:
                    print("Latest email:", new_mail.text)
                    tab.actions.click("@class=mail")
                    break
                else:
                    print(new_mail)
                    break
            time.sleep(1)

        # Extract verification code
        if tab.ele("@class=overflow-auto mb-20"):
            email_content = tab.ele("@class=overflow-auto mb-20").text
            verification_code = re.search(
                r"verification code is (\d{6})", email_content
            )
            if verification_code:
                code = verification_code.group(1)
                print("Verification code:", code)
            else:
                print("Verification code not found")

        # Delete email
        if tab.ele("@id=delete_mail"):
            tab.actions.click("@id=delete_mail")
            time.sleep(1)

        if tab.ele("@id=confirm_mail"):
            tab.actions.click("@id=confirm_mail")
            print("Email deleted")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        browser.quit()

    return code


# Test run
if __name__ == "__main__":
    test_username = "test_user"  # Replace with the username you want to test
    code = get_veri_code(test_username)
    print(f"Retrieved verification code: {code}")
