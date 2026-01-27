@echo off
REM Production Email Fix Deployment Script (Windows)
REM This script deploys the .env file to production and restarts the application

echo ==========================================
echo PRODUCTION EMAIL FIX DEPLOYMENT
echo ==========================================
echo.

REM Configuration - UPDATE THESE VALUES
set PRODUCTION_SERVER=root@your-server-ip
set APP_DIR=/root/client_backend

echo Target Server: %PRODUCTION_SERVER%
echo Application Directory: %APP_DIR%
echo.

REM Check if .env.production exists
if not exist ".env.production" (
    echo ERROR: .env.production file not found!
    echo Please ensure .env.production exists in the current directory
    pause
    exit /b 1
)

echo [1/5] Uploading .env file to production...
scp .env.production %PRODUCTION_SERVER%:%APP_DIR%/.env
if errorlevel 1 (
    echo ERROR: Failed to upload .env file
    echo Please check your SSH connection and credentials
    pause
    exit /b 1
)
echo OK - .env file uploaded
echo.

echo [2/5] Verifying .env file on server...
ssh %PRODUCTION_SERVER% "cd %APP_DIR% && cat .env | grep SMTP_SERVER"
echo.

echo [3/5] Restarting application...
ssh %PRODUCTION_SERVER% "cd %APP_DIR% && pm2 restart client_backend"
echo.

echo ==========================================
echo DEPLOYMENT COMPLETE
echo ==========================================
echo.
echo Next Steps:
echo 1. Test registration at: https://voidworksgroup.co.uk/register
echo 2. Check email inbox for OTP
echo 3. Monitor logs: ssh %PRODUCTION_SERVER% "pm2 logs client_backend"
echo.
echo If emails still don't arrive:
echo 1. Check application logs for errors
echo 2. Run test_email.py on production server
echo 3. Verify Gmail account security settings
echo.
pause
