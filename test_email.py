#!/usr/bin/env python3
"""
Email Configuration Diagnostic Tool
Tests SMTP connection and email sending capability
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

print("=" * 60)
print("EMAIL CONFIGURATION DIAGNOSTIC")
print("=" * 60)

# Check if .env file exists
if ENV_FILE.exists():
    print(f"[OK] .env file found at: {ENV_FILE}")
    load_dotenv(ENV_FILE, override=True)
else:
    print(f"[ERROR] .env file NOT found at: {ENV_FILE}")
    print("[WARNING] Loading from environment variables...")
    load_dotenv(override=True)

print("\n" + "=" * 60)
print("ENVIRONMENT VARIABLES")
print("=" * 60)

smtp_server = os.getenv("SMTP_SERVER", "")
smtp_port = os.getenv("SMTP_PORT", "")
smtp_user = os.getenv("SMTP_USER", "")
smtp_password = os.getenv("SMTP_PASSWORD", "")

print(f"SMTP_SERVER: {smtp_server if smtp_server else '[NOT SET]'}")
print(f"SMTP_PORT: {smtp_port if smtp_port else '[NOT SET]'}")
print(f"SMTP_USER: {smtp_user if smtp_user else '[NOT SET]'}")
print(f"SMTP_PASSWORD: {'*' * len(smtp_password) if smtp_password else '[NOT SET]'}")

if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
    print("\n[CRITICAL ERROR] Missing SMTP configuration!")
    print("Emails will NOT be sent in production.")
    exit(1)

print("\n" + "=" * 60)
print("TESTING SMTP CONNECTION")
print("=" * 60)

try:
    print(f"Connecting to {smtp_server}:{smtp_port}...")
    server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=10)
    print("[OK] Connection established")
    
    print("Starting TLS...")
    server.starttls()
    print("[OK] TLS started")
    
    print(f"Logging in as {smtp_user}...")
    server.login(smtp_user, smtp_password)
    print("[OK] Login successful")
    
    server.quit()
    print("[OK] Connection closed")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED - EMAIL IS CONFIGURED CORRECTLY")
    print("=" * 60)
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n[ERROR] AUTHENTICATION FAILED: {e}")
    print("Check your SMTP_USER and SMTP_PASSWORD")
except smtplib.SMTPException as e:
    print(f"\n[ERROR] SMTP ERROR: {e}")
except Exception as e:
    print(f"\n[ERROR] CONNECTION FAILED: {e}")
    print("Check your SMTP_SERVER and SMTP_PORT")

print("\n" + "=" * 60)
print("RECOMMENDATIONS FOR PRODUCTION")
print("=" * 60)
print("1. Ensure .env file exists on production server")
print("2. Copy .env.production to .env on server:")
print("   cp .env.production .env")
print("3. Restart the application after copying .env")
print("4. Check application logs for email errors")
print("=" * 60)
