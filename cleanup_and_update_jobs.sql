-- Drop job_drafts table if exists
DROP TABLE IF EXISTS job_drafts CASCADE;

-- Update jobs table to allow null client_id
ALTER TABLE jobs 
ALTER COLUMN client_id DROP NOT NULL;

-- Add columns if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='jobs' AND column_name='vehicle_type') THEN
        ALTER TABLE jobs ADD COLUMN vehicle_type VARCHAR(100);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='jobs' AND column_name='property_photos') THEN
        ALTER TABLE jobs ADD COLUMN property_photos TEXT[];
    END IF;
END $$;
