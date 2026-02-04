-- Migration: Create API keys and request logging tables
-- Purpose: Support authentication and rate limiting for the /v1/detect endpoint

-- =============================================================================
-- API KEYS TABLE
-- =============================================================================

-- Store API key hashes (never store raw keys!)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash TEXT UNIQUE NOT NULL,           -- SHA-256 hash of the API key
    name TEXT NOT NULL,                      -- Human-readable name ("User1 Production")
    daily_limit INT DEFAULT 1000,            -- Requests per day
    is_active BOOLEAN DEFAULT TRUE,          -- Can be deactivated without deletion
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::JSONB       -- Additional info (contact email, etc.)
);

-- Index for fast key lookup
CREATE INDEX IF NOT EXISTS api_keys_key_hash_idx ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS api_keys_active_idx ON api_keys (is_active) WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE api_keys IS 'API keys for authenticating /v1/detect requests';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the API key (never store raw keys)';
COMMENT ON COLUMN api_keys.daily_limit IS 'Maximum requests per day (UTC reset)';


-- =============================================================================
-- REQUEST LOGS TABLE
-- =============================================================================

-- Log every detection request for rate limiting and analytics
CREATE TABLE IF NOT EXISTS request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    is_injection BOOLEAN NOT NULL,           -- Detection result
    layer_reached INT NOT NULL DEFAULT 1,    -- Highest layer executed (1, 2, or 3)
    latency_ms FLOAT,                        -- Total processing time
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for rate limiting queries (count by key and date)
CREATE INDEX IF NOT EXISTS request_logs_key_date_idx
    ON request_logs (api_key_id, created_at DESC);

-- Index for analytics
CREATE INDEX IF NOT EXISTS request_logs_created_idx ON request_logs (created_at DESC);

-- Comments
COMMENT ON TABLE request_logs IS 'Detection request logs for rate limiting and analytics';
COMMENT ON COLUMN request_logs.layer_reached IS 'Highest detection layer that ran (1=rules, 2=embeddings, 3=LLM)';


-- =============================================================================
-- RATE LIMITING FUNCTION
-- =============================================================================

-- Function to check if an API key has exceeded its daily limit
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_api_key_id UUID,
    OUT is_allowed BOOLEAN,
    OUT request_count INT,
    OUT daily_limit INT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    day_start TIMESTAMPTZ;
BEGIN
    -- Get start of today (UTC)
    day_start := date_trunc('day', NOW() AT TIME ZONE 'UTC');

    -- Get the key's daily limit
    SELECT ak.daily_limit INTO daily_limit
    FROM api_keys ak
    WHERE ak.id = p_api_key_id AND ak.is_active = TRUE;

    IF daily_limit IS NULL THEN
        is_allowed := FALSE;
        request_count := 0;
        RETURN;
    END IF;

    -- Count requests today
    SELECT COUNT(*) INTO request_count
    FROM request_logs rl
    WHERE rl.api_key_id = p_api_key_id
      AND rl.created_at >= day_start;

    -- Check if under limit
    is_allowed := request_count < daily_limit;
END;
$$;

COMMENT ON FUNCTION check_rate_limit IS 'Check if an API key is within its daily rate limit';


-- =============================================================================
-- ANALYTICS VIEWS
-- =============================================================================

-- View for daily usage statistics per API key
CREATE OR REPLACE VIEW daily_usage_stats AS
SELECT
    ak.id AS api_key_id,
    ak.name AS api_key_name,
    DATE(rl.created_at AT TIME ZONE 'UTC') AS date,
    COUNT(*) AS total_requests,
    SUM(CASE WHEN rl.is_injection THEN 1 ELSE 0 END) AS injections_detected,
    AVG(rl.latency_ms)::NUMERIC(10, 2) AS avg_latency_ms,
    SUM(CASE WHEN rl.layer_reached = 1 THEN 1 ELSE 0 END) AS layer1_detections,
    SUM(CASE WHEN rl.layer_reached = 2 THEN 1 ELSE 0 END) AS layer2_detections,
    SUM(CASE WHEN rl.layer_reached = 3 THEN 1 ELSE 0 END) AS layer3_detections
FROM request_logs rl
JOIN api_keys ak ON rl.api_key_id = ak.id
GROUP BY ak.id, ak.name, DATE(rl.created_at AT TIME ZONE 'UTC');

COMMENT ON VIEW daily_usage_stats IS 'Daily aggregated usage statistics per API key';


-- =============================================================================
-- ROW-LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on tables
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE request_logs ENABLE ROW LEVEL SECURITY;

-- Service role can access everything (for backend operations)
CREATE POLICY "Service role full access to api_keys"
    ON api_keys
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access to request_logs"
    ON request_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Anon role has no access (all access through service role)
-- No policies needed for anon - RLS blocks by default


-- =============================================================================
-- CLEANUP FUNCTION (Optional)
-- =============================================================================

-- Function to clean up old request logs (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_request_logs()
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM request_logs
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_request_logs IS 'Remove request logs older than 30 days';
