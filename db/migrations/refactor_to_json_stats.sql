-- Migration to refactor telemetry stats storage to JSON format
-- This migration adds a new stats_json column and removes individual stat columns

-- Add new JSON column for stats
ALTER TABLE telemetry ADD COLUMN stats_json JSONB;

-- Create index on stats_json for better query performance  
CREATE INDEX IF NOT EXISTS idx_telemetry_stats_json ON telemetry USING GIN (stats_json);

-- The individual stat columns will be dropped in a separate migration after data migration
-- For now, they remain to allow gradual migration

-- Note: This is Part 1 of the migration
-- Part 2 will involve data migration from individual columns to JSON
-- Part 3 will drop the individual columns once migration is complete

