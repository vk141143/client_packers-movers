# Quick Start Guide - Testing Stripe Payment Fix

## 🚀 Start the Server

```bash
cd "c:\Users\HP\Desktop\pocker and movers doc\client_backend"
poetry run python main.py
```

Expected output:
```
✅ Database connected
✅ Tables created
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## ✅ Test 1: Static File Access

Open your browser and visit:
```
http://localhost:8000/static/stripe/success.html?payment_success=true
```

**Expected Result**: You should see a beautiful success page with a green checkmark animation.

**If you see 404**: The fix didn't work. Check the console for errors.

## ✅ Test 2: Automated Test

Run the test script:
```bash
poetry run python test_static_files.py
```

**Expected Output**:
```
Testing static file access...
URL: http://localhost:8000/static/stripe/success.html
--------------------------------------------------
✅ SUCCESS: Static file is accessible!
Status Code: 200
Content Length: XXXX bytes
```

## ✅ Test 3: Full Payment Flow

### Step 1: Login as Client
```bash
POST http://localhost:8000/api/auth/login/client
Content-Type: application/json

{
  "email": "your-client@example.com",
  "password": "your-password"
}
```

Save the `access_token` from the response.

### Step 2: Create Deposit Payment
```bash
POST http://localhost:8000/api/client/jobs/{job_id}/create-deposit-payment
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Expected Response**:
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```

### Step 3: Check the URL
The `checkout_url` should redirect to Stripe. After payment, Stripe will redirect to:
```
http://localhost:8000/static/stripe/success.html?payment_success=true&session_id=cs_test_...
```

### Step 4: Confirm Payment
After seeing the success page, confirm the payment:
```bash
POST http://localhost:8000/api/client/payments/confirm-deposit
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "session_id": "cs_test_..."
}
```

## 🔍 Troubleshooting

### Issue: 404 on static file
**Solution**: 
1. Check if `static/stripe/success.html` exists
2. Restart the server
3. Check console for mount errors

### Issue: Wrong redirect URL
**Solution**:
1. Check `.env` file has `BASE_URL=http://localhost:8000`
2. Restart the server after changing .env

### Issue: Payment not confirming
**Solution**:
1. Check if payment record exists in database
2. Verify session_id matches
3. Check job status in database

## 📝 Environment Variables

Make sure your `.env` file has:
```env
BASE_URL=http://localhost:8000
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

## 🎯 Success Criteria

- ✅ Static file returns 200 (not 404)
- ✅ Success page displays with animation
- ✅ Stripe redirects to correct local URL
- ✅ Payment confirmation works
- ✅ Job status updates correctly

## 🚀 Deploy to Production

When deploying to production:

1. Update `.env.production`:
```env
BASE_URL=https://ui-packers-y8cjd.ondigitalocean.app
```

2. Deploy the updated code

3. Test the same flow in production

## 📞 Need Help?

If you're still seeing 404 errors:
1. Check server logs for errors
2. Verify static directory exists
3. Ensure no other service is using port 8000
4. Try clearing browser cache

---

**Status**: Ready to test! 🎉
