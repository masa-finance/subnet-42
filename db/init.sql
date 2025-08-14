-- PostgreSQL Telemetry Database Initialization Script

-- Create the telemetry table with JSON stats storage
CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    hotkey VARCHAR(255) NOT NULL,
    uid VARCHAR(50),
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    boot_time BIGINT,
    last_operation_time BIGINT,
    "current_time" BIGINT,
    worker_id VARCHAR(255),
    stats_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_hotkey ON telemetry(hotkey);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry("timestamp");
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_uid ON telemetry(uid);
CREATE INDEX IF NOT EXISTS idx_telemetry_worker_id ON telemetry(worker_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_stats_json ON telemetry USING GIN (stats_json);

-- Create a composite index for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_hotkey_created_at ON telemetry(hotkey, created_at DESC); 