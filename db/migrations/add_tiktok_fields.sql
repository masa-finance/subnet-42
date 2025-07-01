-- Migration to add TikTok telemetry fields
-- This script can be run on both SQLite and PostgreSQL

-- Add new TikTok telemetry fields to the telemetry table
ALTER TABLE telemetry ADD COLUMN tiktok_transcription_success INTEGER DEFAULT 0;
ALTER TABLE telemetry ADD COLUMN tiktok_transcription_errors INTEGER DEFAULT 0;

-- Create indexes for the new fields for better query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_tiktok_success ON telemetry(tiktok_transcription_success);
CREATE INDEX IF NOT EXISTS idx_telemetry_tiktok_errors ON telemetry(tiktok_transcription_errors); 