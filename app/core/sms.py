import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio not installed. SMS OTP will be disabled. Install with: pip install twilio")

def send_otp_sms(phone_number: str, otp: str = None):
    """Send OTP via Twilio Verify API
    If otp is provided, it's ignored (Twilio generates OTP automatically)
    """
    if not TWILIO_AVAILABLE:
        print(f"SMS OTP requested but Twilio not installed. OTP: {otp}")
        return False
    
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_SID:
        print(f"Twilio not configured. OTP: {otp}")
        return False
    
    try:
        # Format phone number to E.164 format if not already
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Use Twilio Verify API - let Twilio generate the OTP
        verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=phone_number,
            channel='sms'
        )
        
        print(f"SMS OTP sent successfully. Status: {verification.status}")
        return True
    except Exception as e:
        print(f"Failed to send SMS OTP: {e}")
        return False

def verify_otp_sms(phone_number: str, otp: str):
    """Verify OTP via Twilio Verify API"""
    if not TWILIO_AVAILABLE:
        return False
    
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_SID:
        return False
    
    try:
        # Format phone number to E.164 format if not already
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Verify the OTP
        verification_check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone_number,
            code=otp
        )
        
        print(f"OTP verification status: {verification_check.status}")
        return verification_check.status == "approved"
    except Exception as e:
        print(f"Failed to verify OTP: {e}")
        return False
