-- Migration: Create attack_embeddings table and similarity search function
-- Purpose: Store known prompt injection attack embeddings for Layer 2 detection

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for storing attack embeddings
CREATE TABLE IF NOT EXISTS attack_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attack_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- text-embedding-3-small dimensions
    category TEXT NOT NULL,
    subcategory TEXT,
    severity FLOAT NOT NULL DEFAULT 0.9,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create IVFFlat index for fast cosine similarity search
-- Lists=100 is a good balance for ~1000 vectors; adjust if dataset grows
CREATE INDEX IF NOT EXISTS attack_embeddings_embedding_idx
ON attack_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for filtering by category and active status
CREATE INDEX IF NOT EXISTS attack_embeddings_category_idx ON attack_embeddings (category);
CREATE INDEX IF NOT EXISTS attack_embeddings_active_idx ON attack_embeddings (is_active) WHERE is_active = TRUE;

-- RPC function for similarity search
-- Returns attacks with similarity above threshold, ordered by similarity
CREATE OR REPLACE FUNCTION match_attack_embeddings(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.85,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    attack_text TEXT,
    category TEXT,
    subcategory TEXT,
    severity FLOAT,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        ae.id,
        ae.attack_text,
        ae.category,
        ae.subcategory,
        ae.severity,
        1 - (ae.embedding <=> query_embedding) AS similarity
    FROM attack_embeddings ae
    WHERE ae.is_active = TRUE
        AND 1 - (ae.embedding <=> query_embedding) > match_threshold
    ORDER BY ae.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Add comment to the table
COMMENT ON TABLE attack_embeddings IS 'Known prompt injection attacks with embeddings for similarity-based detection';
COMMENT ON FUNCTION match_attack_embeddings IS 'Find similar attack embeddings using cosine similarity with pgvector';
