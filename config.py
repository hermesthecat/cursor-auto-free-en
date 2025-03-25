from dotenv import load_dotenv
import os
import sys
from logger import logging
from language import get_translation


class Config:
    def __init__(self):
        # Get the root directory path of the application
        if getattr(sys, "frozen", False):
            # If it's a packaged executable
            application_path = os.path.dirname(sys.executable)
        else:
            # If it's in development environment
            application_path = os.path.dirname(os.path.abspath(__file__))

        # Specify the path to the .env file
        dotenv_path = os.path.join(application_path, ".env")

        if not os.path.exists(dotenv_path):
            raise FileNotFoundError(get_translation("file_not_exists", path=dotenv_path))

        # Load .env file
        load_dotenv(dotenv_path)

        self.imap = False
        self.temp_mail = os.getenv("TEMP_MAIL", "").strip().split("@")[0]
        self.temp_mail_epin = os.getenv("TEMP_MAIL_EPIN", "").strip()
        self.temp_mail_ext = os.getenv("TEMP_MAIL_EXT", "").strip()
        self.domain = os.getenv("DOMAIN", "").strip()

        # If temporary email is null, load IMAP
        if self.temp_mail == "null":
            self.imap = True
            self.imap_server = os.getenv("IMAP_SERVER", "").strip()
            self.imap_port = os.getenv("IMAP_PORT", "").strip()
            self.imap_user = os.getenv("IMAP_USER", "").strip()
            self.imap_pass = os.getenv("IMAP_PASS", "").strip()
            self.imap_dir = os.getenv("IMAP_DIR", "inbox").strip()

        self.check_config()

    def get_temp_mail(self):
        return self.temp_mail

    def get_temp_mail_epin(self):
        return self.temp_mail_epin

    def get_temp_mail_ext(self):
        return self.temp_mail_ext

    def get_imap(self):
        if not self.imap:
            return False
        return {
            "imap_server": self.imap_server,
            "imap_port": self.imap_port,
            "imap_user": self.imap_user,
            "imap_pass": self.imap_pass,
            "imap_dir": self.imap_dir,
        }

    def get_domain(self):
        return self.domain

    def get_protocol(self):
        """Get email protocol type
        
        Returns:
            str: 'IMAP' or 'POP3'
        """
        return os.getenv('IMAP_PROTOCOL', 'POP3')

    def check_config(self):
        """Check if configuration items are valid

        Check rules:
        1. If using tempmail.plus, TEMP_MAIL and DOMAIN need to be configured
        2. If using IMAP, IMAP_SERVER, IMAP_PORT, IMAP_USER, IMAP_PASS need to be configured
        3. IMAP_DIR is optional
        """
        # Basic configuration check
        required_configs = {
            "domain": "domain_not_configured",
        }

        # Check basic configurations
        for key, error_key in required_configs.items():
            if not self.check_is_valid(getattr(self, key)):
                raise ValueError(get_translation(error_key))

        # Check email configuration
        if self.temp_mail != "null":
            # tempmail.plus mode
            if not self.check_is_valid(self.temp_mail):
                raise ValueError(get_translation("temp_mail_not_configured"))
        else:
            # IMAP mode
            imap_configs = {
                "imap_server": "imap_server_not_configured",
                "imap_port": "imap_port_not_configured",
                "imap_user": "imap_user_not_configured",
                "imap_pass": "imap_pass_not_configured",
            }

            for key, error_key in imap_configs.items():
                value = getattr(self, key)
                if value == "null" or not self.check_is_valid(value):
                    raise ValueError(get_translation(error_key))

            # IMAP_DIR is optional, check its validity if set
            if self.imap_dir != "null" and not self.check_is_valid(self.imap_dir):
                raise ValueError(get_translation("imap_dir_invalid"))

    def check_is_valid(self, value):
        """Check if a configuration item is valid

        Args:
            value: The value of the configuration item

        Returns:
            bool: Whether the configuration item is valid
        """
        return isinstance(value, str) and len(str(value).strip()) > 0

    def print_config(self):
        if self.imap:
            logging.info(get_translation("imap_server", server=self.imap_server))
            logging.info(get_translation("imap_port", port=self.imap_port))
            logging.info(get_translation("imap_username", username=self.imap_user))
            logging.info(get_translation("imap_password", password='*' * len(self.imap_pass)))
            logging.info(get_translation("imap_inbox_dir", dir=self.imap_dir))
        if self.temp_mail != "null":
            logging.info(get_translation("temp_mail", mail=f"{self.temp_mail}{self.temp_mail_ext}"))
        logging.info(get_translation("domain", domain=self.domain))


# Usage example
if __name__ == "__main__":
    try:
        config = Config()
        print(get_translation("env_variables_loaded"))
        config.print_config()
    except ValueError as e:
        print(get_translation("error_prefix", error=e))
