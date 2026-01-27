#test
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
else:
    load_dotenv(override=True)

def send_otp_email(email: str, otp: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    print(f"[EMAIL DEBUG] SMTP_SERVER: {smtp_server}")
    print(f"[EMAIL DEBUG] SMTP_PORT: {smtp_port}")
    print(f"[EMAIL DEBUG] SMTP_USER: {smtp_user}")
    print(f"[EMAIL DEBUG] SMTP_PASSWORD: {'SET' if smtp_password else 'NOT SET'}")
    print(f"[EMAIL DEBUG] Target email: {email}")
    print(f"[EMAIL DEBUG] OTP: {otp}")
    
    if not smtp_user or not smtp_password:
        print("[EMAIL ERROR] Email not configured. Skipping OTP email.")
        print(f"[EMAIL ERROR] SMTP_USER empty: {not smtp_user}")
        print(f"[EMAIL ERROR] SMTP_PASSWORD empty: {not smtp_password}")
        return
    
    subject = "Verify Your Email - OTP"
    body = f"""
    Welcome to Emergency Property Clearance!
    
    Your OTP for email verification is: {otp}
    
    This OTP will expire in 10 minutes.
    
    Please enter this OTP to verify your account and access the dashboard.
    """
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        print(f"[EMAIL DEBUG] Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        print(f"[EMAIL DEBUG] Connected successfully")
        
        print(f"[EMAIL DEBUG] Starting TLS...")
        server.starttls()
        print(f"[EMAIL DEBUG] TLS started")
        
        print(f"[EMAIL DEBUG] Logging in as {smtp_user}...")
        server.login(smtp_user, smtp_password)
        print(f"[EMAIL DEBUG] Login successful")
        
        print(f"[EMAIL DEBUG] Sending message...")
        server.send_message(msg)
        print(f"[EMAIL DEBUG] Message sent")
        
        server.quit()
        print(f"[EMAIL SUCCESS] OTP sent to {email}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL ERROR] SMTP Authentication failed: {e}")
        raise
    except smtplib.SMTPException as e:
        print(f"[EMAIL ERROR] SMTP error: {e}")
        raise
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send OTP email: {e}")
        import traceback
        traceback.print_exc()
        raise

def send_password_reset_email(email: str, reset_token: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if not smtp_user or not smtp_password:
        print("Email not configured. Skipping password reset email.")
        return
    
    reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
    
    subject = "Reset your password"
    body = f"""
    Hi,
    
    You requested to reset your password for Emergency Property Clearance.
    
    Click the link below to reset your password:
    {reset_link}
    
    This link will expire in 1 hour and can only be used once.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    Emergency Property Clearance Team
    """
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Password reset email sent to {email}")
    except Exception as e:
        print(f"Failed to send password reset email: {e}")

def send_job_assignment_email(crew_email: str, crew_name: str, job_id: str, address: str, scheduled_date: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if not smtp_user or not smtp_password:
        return
    
    subject = "New Job Assigned"
    body = f"""Hi {crew_name},

You have been assigned to a new job:

Job ID: {job_id}
Address: {address}
Scheduled: {scheduled_date}

Please log in to view details.

Best regards,
Emergency Property Clearance Team"""
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = crew_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except:
        pass
