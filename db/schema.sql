-- Enable the UUID extension if we want to use UUIDs (good practice)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table to store every single raw event
CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(100), -- Using VARCHAR for flexibility (could be email, ID, etc.)
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    data_payload JSONB -- Use JSONB for efficient querying of nested data
);

-- Table to store the aggregated analytics
CREATE TABLE IF NOT EXISTS daily_user_metrics (
    metric_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    metric_date DATE NOT NULL,
    event_count INT DEFAULT 0,
    -- This constraint ensures we only have one row per user per day
    CONSTRAINT unique_user_date UNIQUE (user_id, metric_date)
);