-- Remove boolean columns from jobs table

ALTER TABLE jobs DROP COLUMN IF EXISTS ground_floor;
ALTER TABLE jobs DROP COLUMN IF EXISTS stairs_no_lift;
ALTER TABLE jobs DROP COLUMN IF EXISTS restricted_parking;
ALTER TABLE jobs DROP COLUMN IF EXISTS long_carry_distance;
ALTER TABLE jobs DROP COLUMN IF EXISTS photo_report;
ALTER TABLE jobs DROP COLUMN IF EXISTS council_compliance_pack;
ALTER TABLE jobs DROP COLUMN IF EXISTS deep_sanitation;
