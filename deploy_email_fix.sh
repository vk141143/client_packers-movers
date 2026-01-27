#!/bin/bash

# Production Email Fix Deployment Script
# This script deploys the .env file to production and restarts the application

set -e  # Exit on error

echo "=========================================="
echo "PRODUCTION EMAIL FIX DEPLOYMENT"
echo "=========================================="
echo ""

# Configuration
PRODUCTION_SERVER="root@your-server-ip"  # UPDATE THIS
APP_DIR="/root/client_backend"           # UPDATE THIS IF DIFFERENT

echo "Target Server: $PRODUCTION_SERVER"
echo "Application Directory: $APP_DIR"
echo ""

# Check if .env.production exists locally
if [ ! -f ".env.production" ]; then
    echo "ERROR: .env.production file not found!"
    echo "Please ensure .env.production exists in the current directory"
    exit 1
fi

echo "[1/5] Checking SSH connection..."
if ssh -o ConnectTimeout=5 $PRODUCTION_SERVER "echo 'Connected'" 2>/dev/null; then
    echo "✓ SSH connection successful"
else
    echo "✗ SSH connection failed"
    echo "Please check your server IP and SSH credentials"
    exit 1
fi

echo ""
echo "[2/5] Backing up existing .env (if exists)..."
ssh $PRODUCTION_SERVER "cd $APP_DIR && [ -f .env ] && cp .env .env.backup.$(date +%Y%m%d_%H%M%S) || echo 'No existing .env to backup'"

echo ""
echo "[3/5] Uploading .env file to production..."
scp .env.production $PRODUCTION_SERVER:$APP_DIR/.env
echo "✓ .env file uploaded"

echo ""
echo "[4/5] Verifying .env file on server..."
ssh $PRODUCTION_SERVER "cd $APP_DIR && cat .env | grep -q 'SMTP_SERVER' && echo '✓ SMTP_SERVER found' || echo '✗ SMTP_SERVER missing'"
ssh $PRODUCTION_SERVER "cd $APP_DIR && cat .env | grep -q 'SMTP_USER' && echo '✓ SMTP_USER found' || echo '✗ SMTP_USER missing'"
ssh $PRODUCTION_SERVER "cd $APP_DIR && cat .env | grep -q 'SMTP_PASSWORD' && echo '✓ SMTP_PASSWORD found' || echo '✗ SMTP_PASSWORD missing'"

echo ""
echo "[5/5] Restarting application..."
ssh $PRODUCTION_SERVER "cd $APP_DIR && pm2 restart client_backend || systemctl restart client_backend || echo 'Please restart manually'"

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Test registration at: https://voidworksgroup.co.uk/register"
echo "2. Check email inbox for OTP"
echo "3. Monitor logs: ssh $PRODUCTION_SERVER 'pm2 logs client_backend'"
echo ""
echo "If emails still don't arrive:"
echo "1. Check application logs for errors"
echo "2. Run test_email.py on production server"
echo "3. Verify Gmail account security settings"
echo ""
