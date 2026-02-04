-- Migration: Fix API keys table for dashboard compatibility
-- Adds user_id, key_prefix, status columns and proper RLS policies

-- =============================================================================
-- ADD MISSING COLUMNS
-- =============================================================================

-- Add user_id column to link API keys to users
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Add key_prefix column for display (first 12 chars of key)
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS key_prefix TEXT;

-- Add status column (active/revoked) for easier querying
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active' CHECK (status IN ('active', 'revoked'));

-- Sync status with is_active for existing rows
UPDATE api_keys SET status = CASE WHEN is_active THEN 'active' ELSE 'revoked' END WHERE status IS NULL;

-- Index for user queries
CREATE INDEX IF NOT EXISTS api_keys_user_id_idx ON api_keys (user_id);


-- =============================================================================
-- RLS POLICIES FOR AUTHENTICATED USERS
-- =============================================================================

-- Drop existing restrictive policies if they exist
DROP POLICY IF EXISTS "Users can view own api_keys" ON api_keys;
DROP POLICY IF EXISTS "Users can insert own api_keys" ON api_keys;
DROP POLICY IF EXISTS "Users can update own api_keys" ON api_keys;

-- Allow authenticated users to view their own keys
CREATE POLICY "Users can view own api_keys"
    ON api_keys
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- Allow authenticated users to insert their own keys
CREATE POLICY "Users can insert own api_keys"
    ON api_keys
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Allow authenticated users to update their own keys
CREATE POLICY "Users can update own api_keys"
    ON api_keys
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());


-- =============================================================================
-- RLS POLICIES FOR REQUEST_LOGS
-- =============================================================================

DROP POLICY IF EXISTS "Users can view own request_logs" ON request_logs;

-- Allow users to view request logs for their own API keys
CREATE POLICY "Users can view own request_logs"
    ON request_logs
    FOR SELECT
    TO authenticated
    USING (
        api_key_id IN (
            SELECT id FROM api_keys WHERE user_id = auth.uid()
        )
    );


-- =============================================================================
-- CREATE API KEY FUNCTION
-- =============================================================================

-- Function to create a new API key and return the full key (only time it's shown)
CREATE OR REPLACE FUNCTION create_api_key(
    p_name TEXT,
    p_rate_limit INT DEFAULT 1000
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_key TEXT;
    v_key_hash TEXT;
    v_key_prefix TEXT;
    v_user_id UUID;
BEGIN
    -- Get current user
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Not authenticated';
    END IF;

    -- Generate a random API key: sk-argus-<32 random chars>
    v_key := 'sk-argus-' || encode(gen_random_bytes(24), 'base64');
    -- Remove any non-alphanumeric chars from base64
    v_key := regexp_replace(v_key, '[^a-zA-Z0-9-]', '', 'g');

    -- Hash for storage
    v_key_hash := encode(sha256(v_key::bytea), 'hex');

    -- Prefix for display (first 12 chars)
    v_key_prefix := substring(v_key from 1 for 12);

    -- Insert the key
    INSERT INTO api_keys (user_id, key_hash, key_prefix, name, daily_limit, is_active, status)
    VALUES (v_user_id, v_key_hash, v_key_prefix, p_name, p_rate_limit, TRUE, 'active');

    -- Return the full key (only time user will see it)
    RETURN v_key;
END;
$$;

COMMENT ON FUNCTION create_api_key IS 'Create a new API key for the current user. Returns the full key (only shown once).';


-- =============================================================================
-- ADD INPUT_HASH TO REQUEST_LOGS (for History page)
-- =============================================================================

ALTER TABLE request_logs
ADD COLUMN IF NOT EXISTS input_hash TEXT;

-- Rename layer_reached to layer_detected for frontend compatibility
-- (Can't easily rename, so add alias column)
ALTER TABLE request_logs
ADD COLUMN IF NOT EXISTS layer_detected INT;

-- Sync existing data
UPDATE request_logs SET layer_detected = layer_reached WHERE layer_detected IS NULL;
