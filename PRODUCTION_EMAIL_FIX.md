# PRODUCTION EMAIL FIX - DEPLOYMENT GUIDE

## Issue Identified
OTPs are being saved to the database but emails are NOT being sent in production.

## Root Cause
The production server is missing the `.env` file with SMTP credentials.

## Local Testing Results
✅ Email configuration is CORRECT locally
✅ SMTP connection successful (smtp.gmail.com:587)
✅ Authentication successful (bindushreegd490@gmail.com)
✅ All email tests passed

## Production Deployment Steps

### Step 1: Connect to Production Server
```bash
ssh root@your-production-server-ip
```

### Step 2: Navigate to Application Directory
```bash
cd /root/client_backend
# OR
cd /var/www/client_backend
```

### Step 3: Check Current .env Status
```bash
ls -la .env
cat .env  # Check if file exists and has SMTP config
```

### Step 4: Create/Update .env File
```bash
# Create .env file with SMTP credentials
cat > .env << 'EOF'
DATABASE_URL=postgresql+psycopg2://dbadmin:p%25%258N2n%5EdY6R%257rU@public-primary-pg-inmumbaizone2-189645-1657841.db.onutho.com:5432/packers
SECRET_KEY=your-secret-key-change-in-production
ADMIN_EMAIL=bindushreegd490@gmail.com

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=bindushreegd490@gmail.com
SMTP_PASSWORD=sqvr icdg hstg tukj

# Utho Object Storage
UTHO_ACCESS_KEY=twMDcBefWv3mlIC5QZphKTiuxgNXRkor6GE7
UTHO_SECRET_KEY=MytpownPzqx1CYTdbgaZsQ9UXehARf45lOFS
UTHO_BUCKET_NAME=mybucket-moveaway-mhr
UTHO_ENDPOINT_URL=https://innoida.utho.io
UTHO_REGION=ap-south-1
EOF
```

### Step 5: Verify .env File
```bash
cat .env | grep SMTP
# Should show:
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=bindushreegd490@gmail.com
# SMTP_PASSWORD=sqvr icdg hstg tukj
```

### Step 6: Test Email Configuration (Optional)
```bash
# Upload test_email.py to server
python3 test_email.py
# Should show: [SUCCESS] ALL TESTS PASSED
```

### Step 7: Restart Application
```bash
# If using PM2
pm2 restart client_backend

# If using systemd
systemctl restart client_backend

# If using uvicorn directly
pkill -f "uvicorn main:app"
nohup python3 main.py &
```

### Step 8: Verify Application Logs
```bash
# PM2 logs
pm2 logs client_backend --lines 50

# Systemd logs
journalctl -u client_backend -n 50 -f

# Check for email-related errors
tail -f /var/log/client_backend.log | grep -i "email\|smtp\|otp"
```

### Step 9: Test Registration Flow
1. Go to: https://voidworksgroup.co.uk/register
2. Register a new client with email OTP
3. Check email inbox for OTP
4. Check database: `SELECT email, otp, is_verified FROM clients ORDER BY created_at DESC LIMIT 5;`

## Verification Checklist
- [ ] .env file exists on production server
- [ ] SMTP credentials are correct in .env
- [ ] Application restarted after .env update
- [ ] No SMTP errors in application logs
- [ ] Test registration sends OTP email successfully
- [ ] OTP email arrives in inbox within 30 seconds

## Common Issues & Solutions

### Issue 1: .env file not loaded
**Symptom**: Logs show "Email not configured. Skipping OTP email."
**Solution**: Ensure .env file is in the same directory as main.py

### Issue 2: Gmail blocking login
**Symptom**: "SMTP Authentication Error"
**Solution**: 
- Verify app password is correct: `sqvr icdg hstg tukj`
- Check if 2FA is enabled on Gmail account
- Generate new app password if needed

### Issue 3: Firewall blocking SMTP
**Symptom**: "Connection timeout" or "Connection refused"
**Solution**: 
```bash
# Allow outbound SMTP
sudo ufw allow out 587/tcp
sudo iptables -A OUTPUT -p tcp --dport 587 -j ACCEPT
```

### Issue 4: Background thread not executing
**Symptom**: Registration succeeds but no email sent
**Solution**: Check ThreadPoolExecutor is working:
```python
# Add logging in auth.py
print(f"Background OTP send started for {client.email}")
```

## Production Server Locations
Based on previous deployments:
- Client Backend: `/root/client_backend` or `/var/www/client_backend`
- Crew Admin Backend: `/var/www/packers-movers-admin`

## Quick Fix Command (One-liner)
```bash
ssh root@server-ip "cd /root/client_backend && cat > .env << 'EOF'
DATABASE_URL=postgresql+psycopg2://dbadmin:p%25%258N2n%5EdY6R%257rU@public-primary-pg-inmumbaizone2-189645-1657841.db.onutho.com:5432/packers
SECRET_KEY=your-secret-key-change-in-production
ADMIN_EMAIL=bindushreegd490@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=bindushreegd490@gmail.com
SMTP_PASSWORD=sqvr icdg hstg tukj
UTHO_ACCESS_KEY=twMDcBefWv3mlIC5QZphKTiuxgNXRkor6GE7
UTHO_SECRET_KEY=MytpownPzqx1CYTdbgaZsQ9UXehARf45lOFS
UTHO_BUCKET_NAME=mybucket-moveaway-mhr
UTHO_ENDPOINT_URL=https://innoida.utho.io
UTHO_REGION=ap-south-1
EOF
&& pm2 restart client_backend"
```

## Expected Behavior After Fix
1. User registers with email
2. OTP saved to database (already working ✅)
3. Email sent in background thread (will be fixed ✅)
4. User receives OTP email within 10-30 seconds
5. User verifies OTP and logs in

## Support
If issues persist after deployment:
1. Check application logs for errors
2. Verify .env file permissions: `chmod 600 .env`
3. Test SMTP connection manually using test_email.py
4. Check Gmail account for security alerts
