from DrissionPage import ChromiumOptions, Chromium
import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()


class BrowserManager:
    def __init__(self):
        self.browser = None

    def init_browser(self, user_agent=None):
        """Initialize browser"""
        co = self._get_browser_options(user_agent)
        self.browser = Chromium(co)
        return self.browser

    def _get_browser_options(self, user_agent=None):
        """Get browser configuration"""
        co = ChromiumOptions()
        try:
            extension_path = self._get_extension_path("turnstilePatch")
            co.add_extension(extension_path)
        except FileNotFoundError as e:
            logging.warning(f"Warning: {e}")

        browser_path = os.getenv("BROWSER_PATH")
        if browser_path:
            co.set_paths(browser_path=browser_path)

        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")
        proxy = os.getenv("BROWSER_PROXY")
        if proxy:
            co.set_proxy(proxy)

        co.auto_port()
        if user_agent:
            co.set_user_agent(user_agent)

        co.headless(
            os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        )  # Use headless mode in production environment

        # Special handling for Mac systems
        if sys.platform == "darwin":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-gpu")

        return co

    def _get_extension_path(self, exname='turnstilePatch'):
        """Get extension path"""
        root_dir = os.getcwd()
        extension_path = os.path.join(root_dir, exname)

        if hasattr(sys, "_MEIPASS"):
            extension_path = os.path.join(sys._MEIPASS, exname)

        if not os.path.exists(extension_path):
            raise FileNotFoundError(f"Extension does not exist: {extension_path}")

        return extension_path

    def quit(self):
        """Close browser"""
        if self.browser:
            try:
                self.browser.quit()
            except:
                pass
