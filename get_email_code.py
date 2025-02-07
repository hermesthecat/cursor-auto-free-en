import logging
import time
import re
from config import Config
import requests
import email
import imaplib


class EmailVerificationHandler:
    def __init__(self):
        self.imap = Config().get_imap()
        self.username = Config().get_temp_mail()
        self.epin = Config().get_temp_mail_epin()
        self.session = requests.Session()
        self.emailExtension = Config().get_temp_mail_ext()

    def get_verification_code(self):
        code = None

        try:
            print("Processing...")

            if self.imap is False:
                # Wait and get latest email
                code, first_id = self._get_latest_mail_code()
                # Clean up email
                self._cleanup_mail(first_id)
            else:
                code = self._get_mail_code_by_imap()

        except Exception as e:
            print(f"Failed to get verification code: {str(e)}")

        return code

    # Get email using IMAP
    def _get_mail_code_by_imap(self, retry = 0):
        if retry > 0:
            time.sleep(3)
        if retry >= 20:
            raise Exception("Verification code retrieval timeout")
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap['imap_server'], self.imap['imap_port'])
            mail.login(self.imap['imap_user'], self.imap['imap_pass'])
            mail.select(self.imap['imap_dir'])

            status, messages = mail.search(None, 'FROM', '"no-reply@cursor.sh"')
            if status != 'OK':
                return None

            mail_ids = messages[0].split()
            if not mail_ids:
                # If no email received, try again
                return self._get_mail_code_by_imap(retry=retry + 1)

            latest_mail_id = mail_ids[-1]

            # Get email content
            status, msg_data = mail.fetch(latest_mail_id, '(RFC822)')
            if status != 'OK':
                return None

            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract email body
            body = self._extract_imap_body(email_message)
            if body:
                # Use regex to find 6-digit verification code
                code_match = re.search(r"\b\d{6}\b", body)
                if code_match:
                    code = code_match.group()
                    # Delete email
                    mail.store(latest_mail_id, '+FLAGS', '\\Deleted')
                    mail.expunge()
                    mail.logout()
                    # print(f"Found verification code: {code}")
                    return code
            # print("Verification code not found")
            mail.logout()
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def _extract_imap_body(self, email_message):
        # Extract email body
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        return body
                    except Exception as e:
                        logging.error(f"Failed to decode email body: {e}")
        else:
            content_type = email_message.get_content_type()
            if content_type == "text/plain":
                charset = email_message.get_content_charset() or 'utf-8'
                try:
                    body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
                    return body
                except Exception as e:
                    logging.error(f"Failed to decode email body: {e}")
        return ""

    # Manual verification code input
    def _get_latest_mail_code(self):
        # Get email list
        mail_list_url = f"https://tempmail.plus/api/mails?email={self.username}{self.emailExtension}&limit=20&epin={self.epin}"
        mail_list_response = self.session.get(mail_list_url)
        mail_list_data = mail_list_response.json()
        time.sleep(0.5)
        if not mail_list_data.get("result"):
            return None, None

        # Get latest email ID
        first_id = mail_list_data.get("first_id")
        if not first_id:
            return None, None

        # Get specific email content
        mail_detail_url = f"https://tempmail.plus/api/mails/{first_id}?email={self.username}{self.emailExtension}&epin={self.epin}"
        mail_detail_response = self.session.get(mail_detail_url)
        mail_detail_data = mail_detail_response.json()
        time.sleep(0.5)
        if not mail_detail_data.get("result"):
            return None, None

        # Extract 6-digit verification code from email text
        mail_text = mail_detail_data.get("text", "")
        # Modify regex to ensure 6 digits are not preceded by letters or domain-related symbols
        code_match = re.search(r"(?<![a-zA-Z@.])\b\d{6}\b", mail_text)

        if code_match:
            return code_match.group(), first_id
        return None, None

    def _cleanup_mail(self, first_id):
        # Construct delete request URL and data
        delete_url = "https://tempmail.plus/api/mails/"
        payload = {
            "email": f"{self.username}{self.emailExtension}",
            "first_id": first_id,
            "epin": f"{self.epin}",
        }

        # Try up to 5 times
        for _ in range(5):
            response = self.session.delete(delete_url, data=payload)
            try:
                result = response.json().get("result")
                if result is True:
                    return True
            except:
                pass

            # If failed, wait 0.5 seconds and retry
            time.sleep(0.5)

        return False


if __name__ == "__main__":
    email_handler = EmailVerificationHandler()
    code = email_handler.get_verification_code()
    print(code)
