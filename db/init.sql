-- PostgreSQL Telemetry Database Initialization Script

-- Create the telemetry table with all required fields
CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    hotkey VARCHAR(255) NOT NULL,
    uid VARCHAR(50),
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    boot_time BIGINT,
    last_operation_time BIGINT,
    "current_time" BIGINT,
    twitter_auth_errors INTEGER DEFAULT 0,
    twitter_errors INTEGER DEFAULT 0,
    twitter_ratelimit_errors INTEGER DEFAULT 0,
    twitter_returned_other INTEGER DEFAULT 0,
    twitter_returned_profiles INTEGER DEFAULT 0,
    twitter_returned_tweets INTEGER DEFAULT 0,
    twitter_scrapes INTEGER DEFAULT 0,
    web_errors INTEGER DEFAULT 0,
    web_success INTEGER DEFAULT 0,
    worker_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_hotkey ON telemetry(hotkey);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry("timestamp");
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_uid ON telemetry(uid);
CREATE INDEX IF NOT EXISTS idx_telemetry_worker_id ON telemetry(worker_id);

-- Create a composite index for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_hotkey_created_at ON telemetry(hotkey, created_at DESC); 