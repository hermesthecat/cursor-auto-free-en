import os
from dotenv import load_dotenv
from get_email_code import EmailVerificationHandler
import logging

def test_temp_mail():
    """Test temporary email method"""
    handler = EmailVerificationHandler()
    print("\n=== Testing temporary email mode ===")
    print(f"Temporary email: {os.getenv('TEMP_MAIL')}@mailto.plus")
    code = handler.get_verification_code()
    if code:
        print(f"Successfully obtained verification code: {code}")
    else:
        print("Could not obtain verification code")

def test_email_server():
    """Test email server method (POP3/IMAP)"""
    handler = EmailVerificationHandler()
    protocol = os.getenv('IMAP_PROTOCOL', 'POP3')
    print(f"\n=== Testing {protocol} mode ===")
    print(f"Email server: {os.getenv('IMAP_SERVER')}")
    print(f"Email account: {os.getenv('IMAP_USER')}")
    code = handler.get_verification_code()
    if code:
        print(f"Successfully obtained verification code: {code}")
    else:
        print("Could not obtain verification code")

def print_config():
    """Print current configuration"""
    print("\nCurrent environment variable configuration:")
    print(f"TEMP_MAIL: {os.getenv('TEMP_MAIL')}")
    if os.getenv('TEMP_MAIL') == 'null':
        print(f"IMAP_SERVER: {os.getenv('IMAP_SERVER')}")
        print(f"IMAP_PORT: {os.getenv('IMAP_PORT')}")
        print(f"IMAP_USER: {os.getenv('IMAP_USER')}")
        print(f"IMAP_PROTOCOL: {os.getenv('IMAP_PROTOCOL', 'POP3')}")
    print(f"DOMAIN: {os.getenv('DOMAIN')}")

def main():
    # Load environment variables
    load_dotenv()
    
    # Print initial configuration
    print_config()
    
    try:
        # Decide which mode to test based on configuration
        if os.getenv('TEMP_MAIL') != 'null':
            test_temp_mail()
        else:
            test_email_server()
    except Exception as e:
        print(f"Error occurred during testing: {str(e)}")

if __name__ == "__main__":
    main() 