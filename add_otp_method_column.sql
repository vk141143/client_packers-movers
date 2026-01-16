-- Add otp_method column to clients table
ALTER TABLE clients ADD COLUMN IF NOT EXISTS otp_method VARCHAR(10);
