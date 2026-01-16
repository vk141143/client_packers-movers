-- Add missing columns to jobs table if they don't exist

-- Add property_size if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='property_size') THEN
        ALTER TABLE jobs ADD COLUMN property_size VARCHAR;
    END IF;
END $$;

-- Add van_loads if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='van_loads') THEN
        ALTER TABLE jobs ADD COLUMN van_loads INTEGER;
    END IF;
END $$;

-- Add waste_types if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='waste_types') THEN
        ALTER TABLE jobs ADD COLUMN waste_types VARCHAR;
    END IF;
END $$;

-- Add furniture_items if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='furniture_items') THEN
        ALTER TABLE jobs ADD COLUMN furniture_items INTEGER;
    END IF;
END $$;

-- Add assigned_crew_id if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='assigned_crew_id') THEN
        ALTER TABLE jobs ADD COLUMN assigned_crew_id VARCHAR;
    END IF;
END $$;

-- Add rating if missing
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='rating') THEN
        ALTER TABLE jobs ADD COLUMN rating FLOAT;
    END IF;
END $$;

-- Add access difficulty columns
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='ground_floor') THEN
        ALTER TABLE jobs ADD COLUMN ground_floor BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='stairs_no_lift') THEN
        ALTER TABLE jobs ADD COLUMN stairs_no_lift BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='restricted_parking') THEN
        ALTER TABLE jobs ADD COLUMN restricted_parking BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='long_carry_distance') THEN
        ALTER TABLE jobs ADD COLUMN long_carry_distance BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Add compliance add-ons columns
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='photo_report') THEN
        ALTER TABLE jobs ADD COLUMN photo_report BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='council_compliance_pack') THEN
        ALTER TABLE jobs ADD COLUMN council_compliance_pack BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='jobs' AND column_name='deep_sanitation') THEN
        ALTER TABLE jobs ADD COLUMN deep_sanitation BOOLEAN DEFAULT FALSE;
    END IF;
END $$;
