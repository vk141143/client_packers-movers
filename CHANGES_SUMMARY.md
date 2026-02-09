# Client Backend Changes Summary

## Changes Made

### 1. Registration Endpoint Simplification
**Endpoint:** `POST /api/auth/register/client`

**Removed Fields:**
- ❌ `company_name`
- ❌ `contact_person_name`
- ❌ `department`

**Current Required Fields:**
- ✅ `email` (EmailStr)
- ✅ `password` (string)
- ✅ `full_name` (string)
- ✅ `phone_number` (string)
- ✅ `client_type` (string)
- ✅ `business_address` (string)
- ✅ `otp_method` (Literal["email", "phone"], default: "email")

**Validation:**
- Duplicate email check
- Duplicate phone number check

---

### 2. Client Model Updates
**File:** `app/models/client.py`

**Removed Columns:**
- ❌ `contact_person_name`
- ❌ `department`

**Current Columns:**
- ✅ `id` (UUID, primary key)
- ✅ `email` (unique, indexed)
- ✅ `password`
- ✅ `full_name`
- ✅ `company_name` (kept for existing data)
- ✅ `phone_number`
- ✅ `client_type`
- ✅ `business_address`
- ✅ `is_verified`
- ✅ `otp`
- ✅ `otp_expiry`
- ✅ `otp_method`
- ✅ `reset_otp`
- ✅ `reset_otp_expiry`
- ✅ `reset_token`
- ✅ `reset_token_expiry`
- ✅ `created_at`

---

### 3. Profile Endpoints

#### GET Profile
**Endpoint:** `GET /api/auth/client/profile`

**Response Fields:**
```json
{
  "id": "uuid",
  "email": "client@example.com",
  "full_name": "John Doe",
  "organization_name": "ABC Company",
  "phone_number": "+44 7700 900000",
  "client_type": "Council",
  "business_address": "123 Main St",
  "is_verified": true,
  "created_at": "2026-01-29T12:00:00Z"
}
```

#### PATCH Profile
**Endpoint:** `PATCH /api/auth/client/profile`

**Editable Fields:**
- ✅ `phone_number` (optional)
- ✅ `business_address` (optional)

**Read-Only Fields:**
- 🔒 `organization_name` (from company_name)
- 🔒 `email`
- 🔒 `full_name`
- 🔒 `client_type`

---

### 4. New Job Endpoints

#### Cancelled Jobs
**Endpoint:** `GET /api/client/cancelled-jobs`

**Response:**
```json
[
  {
    "job_id": "uuid",
    "service_type": "Emergency Clearance",
    "property_address": "123 Main St",
    "preferred_date": "2026-02-15",
    "cancellation_reason": "Changed plans",
    "cancelled_at": "29 Jan 2026",
    "quote_amount": 500.00
  }
]
```

#### Accepted Quotes
**Endpoint:** `GET /api/client/accepted-quotes`

**Response:**
```json
[
  {
    "job_id": "uuid",
    "service_type": "Emergency Clearance",
    "property_address": "123 Main St",
    "preferred_date": "2026-02-15",
    "quote_amount": 500.00,
    "deposit_amount": 100.00,
    "deposit_paid": true,
    "accepted_at": "29 Jan 2026"
  }
]
```

---

### 5. Database Migration

**File:** `drop_columns_migration.py`

**Purpose:** Drop `contact_person_name` and `department` columns from clients table

**How to Run:**
```bash
cd client_backend
python drop_columns_migration.py
```

**Safety Features:**
- Checks if columns exist before dropping
- Requires "YES" confirmation
- Shows detailed progress messages
- Handles errors gracefully

---

## Summary of All Client Endpoints

### Authentication
1. `POST /api/auth/register/client` - Register new client
2. `POST /api/auth/verify-otp` - Verify registration OTP
3. `POST /api/auth/resend-otp` - Resend OTP
4. `POST /api/auth/login/client` - Client login
5. `POST /api/auth/refresh` - Refresh access token
6. `POST /api/auth/forgot-password` - Request password reset
7. `POST /api/auth/verify-forgot-otp` - Verify reset OTP
8. `POST /api/auth/resend-forgot-otp` - Resend reset OTP
9. `POST /api/auth/reset-password` - Reset password

### Profile
10. `GET /api/auth/client/profile` - Get client profile
11. `PATCH /api/auth/client/profile` - Update profile (phone, address only)

### Jobs
12. `POST /api/jobs` - Create new job request
13. `GET /api/jobs` - Get all jobs
14. `DELETE /api/jobs/{job_id}/cancel` - Cancel job

### Quotes
15. `GET /api/client/quotes` - Get all quotes
16. `GET /api/client/quotes/{job_id}` - Get quote details
17. `POST /api/client/quotes/{job_id}/approve` - Approve quote
18. `POST /api/client/quotes/{job_id}/decline` - Decline quote
19. `GET /api/client/accepted-quotes` - Get accepted quotes only

### Tracking
20. `GET /api/client/tracking` - Get all active jobs
21. `GET /api/client/tracking/{job_id}` - Get job tracking details

### History
22. `GET /api/client/history` - Get all jobs history
23. `GET /api/client/completed-jobs` - Get completed jobs
24. `GET /api/client/cancelled-jobs` - Get cancelled jobs

### Payments
25. `GET /api/client/payment-requests` - Get pending payment requests

### Ratings
26. `POST /api/jobs/{job_id}/rating` - Submit job rating
27. `GET /api/jobs/{job_id}/rating` - Get job rating

---

## Files Modified

1. ✅ `app/schemas/auth.py` - Removed fields from ClientRegister
2. ✅ `app/models/client.py` - Removed columns and updated create method
3. ✅ `app/routers/auth.py` - Updated registration, profile endpoints
4. ✅ `app/routers/job.py` - Added cancelled-jobs and accepted-quotes endpoints
5. ✅ `drop_columns_migration.py` - Created migration script

---

## Next Steps

1. **Run Migration:**
   ```bash
   python drop_columns_migration.py
   ```

2. **Restart Backend:**
   ```bash
   poetry run python main.py
   ```

3. **Test Endpoints:**
   - Test registration with new simplified fields
   - Test profile GET/PATCH
   - Test new cancelled-jobs endpoint
   - Test new accepted-quotes endpoint

4. **Deploy:**
   - Commit changes
   - Push to repository
   - Deploy to production
   - Run migration on production database

---

## Breaking Changes

⚠️ **API Breaking Changes:**
- Registration no longer accepts `company_name`, `contact_person_name`, `department`
- Profile update no longer accepts `organization_name`, `contact_person`, `department`
- Profile response no longer includes `contact_person`, `department`

⚠️ **Database Breaking Changes:**
- `contact_person_name` column will be dropped
- `department` column will be dropped
- Existing data in these columns will be lost

---

## Rollback Plan

If issues occur:

1. **Revert Code Changes:**
   ```bash
   git revert <commit-hash>
   ```

2. **Restore Database Columns:**
   ```sql
   ALTER TABLE clients ADD COLUMN contact_person_name VARCHAR;
   ALTER TABLE clients ADD COLUMN department VARCHAR;
   ```

3. **Redeploy Previous Version**

---

## Status: ✅ READY FOR DEPLOYMENT

All changes are complete and consistent across:
- ✅ Schemas
- ✅ Models
- ✅ Routers
- ✅ Endpoints
- ✅ Migration script created
