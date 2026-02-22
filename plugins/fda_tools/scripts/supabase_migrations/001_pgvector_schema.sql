-- FDA-220: pgvector schema for MDRP semantic search
-- Migration: 001_pgvector_schema.sql
-- Run order: 1 of N
--
-- Creates four tables for semantic search across guidance documents,
-- 510(k) summaries, project documents, and embedding job queue.
-- Requires: pgvector extension (available on Supabase by default)

-- ── Prerequisites ────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Guidance Chunks ──────────────────────────────────────────────────
-- FDA guidance PDF text chunks with 384-dim all-MiniLM-L6-v2 embeddings

CREATE TABLE IF NOT EXISTS guidance_chunks (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID        NOT NULL,                      -- RLS key
    doc_url       TEXT        NOT NULL,
    doc_title     TEXT        NOT NULL,
    doc_date      DATE,
    doc_etag      TEXT,                                      -- for freshness checks
    page_number   INTEGER     NOT NULL DEFAULT 1,
    chunk_index   INTEGER     NOT NULL DEFAULT 0,
    chunk_text    TEXT        NOT NULL,
    token_count   INTEGER,
    embedding     vector(384),                               -- all-MiniLM-L6-v2
    indexed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_stale      BOOLEAN     NOT NULL DEFAULT false,
    UNIQUE (tenant_id, doc_url, page_number, chunk_index)
);

-- HNSW index: ef_construction=128, m=16 — good recall/speed balance at 384 dims
CREATE INDEX IF NOT EXISTS guidance_chunks_embedding_idx
    ON guidance_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (ef_construction = 128, m = 16);

CREATE INDEX IF NOT EXISTS guidance_chunks_tenant_idx
    ON guidance_chunks (tenant_id);

CREATE INDEX IF NOT EXISTS guidance_chunks_doc_url_idx
    ON guidance_chunks (doc_url);

-- ── 510(k) Summary Embeddings ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS k510_summaries (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID        NOT NULL,
    k_number      TEXT        NOT NULL,                      -- e.g. K241234
    product_code  TEXT,
    device_name   TEXT,
    applicant     TEXT,
    decision_date DATE,
    summary_text  TEXT        NOT NULL,
    embedding     vector(384),
    indexed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, k_number)
);

CREATE INDEX IF NOT EXISTS k510_summaries_embedding_idx
    ON k510_summaries
    USING hnsw (embedding vector_cosine_ops)
    WITH (ef_construction = 128, m = 16);

CREATE INDEX IF NOT EXISTS k510_summaries_tenant_idx
    ON k510_summaries (tenant_id);

CREATE INDEX IF NOT EXISTS k510_summaries_product_code_idx
    ON k510_summaries (product_code);

-- ── Project Documents ─────────────────────────────────────────────────
-- Per-project submission sections and uploaded documents

CREATE TABLE IF NOT EXISTS project_documents (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID        NOT NULL,
    project_id    UUID        NOT NULL,
    section_code  TEXT,                                      -- e.g. SEC_02, SEC_10
    doc_type      TEXT        NOT NULL DEFAULT 'section',   -- section | upload | reference
    title         TEXT        NOT NULL,
    content_text  TEXT,
    embedding     vector(384),
    version       INTEGER     NOT NULL DEFAULT 1,
    created_by    UUID,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_confidential BOOLEAN   NOT NULL DEFAULT false         -- never synced to cloud if true
);

CREATE INDEX IF NOT EXISTS project_documents_embedding_idx
    ON project_documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (ef_construction = 128, m = 16);

CREATE INDEX IF NOT EXISTS project_documents_project_idx
    ON project_documents (project_id);

CREATE INDEX IF NOT EXISTS project_documents_tenant_idx
    ON project_documents (tenant_id);

-- ── Embedding Job Queue ───────────────────────────────────────────────
-- Tracks async embedding work so the embedder can resume on restart

CREATE TABLE IF NOT EXISTS embedding_jobs (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID        NOT NULL,
    source_table  TEXT        NOT NULL,                      -- guidance_chunks | k510_summaries | project_documents
    source_id     UUID        NOT NULL,
    status        TEXT        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending','running','done','failed')),
    attempts      INTEGER     NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS embedding_jobs_status_idx
    ON embedding_jobs (status)
    WHERE status IN ('pending', 'running');

CREATE INDEX IF NOT EXISTS embedding_jobs_tenant_idx
    ON embedding_jobs (tenant_id);

-- ── Guidance Version Tracking ─────────────────────────────────────────
-- For FDA-227: freshness checks

CREATE TABLE IF NOT EXISTS guidance_versions (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_url       TEXT        NOT NULL UNIQUE,
    doc_title     TEXT,
    etag          TEXT,
    last_modified TIMESTAMPTZ,
    content_hash  TEXT,
    indexed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    checked_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_stale      BOOLEAN     NOT NULL DEFAULT false
);

-- ── Row-Level Security ────────────────────────────────────────────────
-- Tenants can only see their own rows

ALTER TABLE guidance_chunks     ENABLE ROW LEVEL SECURITY;
ALTER TABLE k510_summaries      ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_documents   ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_jobs      ENABLE ROW LEVEL SECURITY;

-- guidance_chunks: tenant isolation
CREATE POLICY guidance_chunks_tenant_policy ON guidance_chunks
    USING (tenant_id = (current_setting('app.tenant_id', true))::uuid);

-- k510_summaries: tenant isolation
CREATE POLICY k510_summaries_tenant_policy ON k510_summaries
    USING (tenant_id = (current_setting('app.tenant_id', true))::uuid);

-- project_documents: tenant isolation
CREATE POLICY project_documents_tenant_policy ON project_documents
    USING (tenant_id = (current_setting('app.tenant_id', true))::uuid);

-- embedding_jobs: tenant isolation
CREATE POLICY embedding_jobs_tenant_policy ON embedding_jobs
    USING (tenant_id = (current_setting('app.tenant_id', true))::uuid);

-- guidance_versions: no tenant isolation (shared public data)
-- (no RLS needed — no sensitive data)

-- ── match_guidance() — cosine similarity search function ──────────────
-- Called by lib/guidance_search.py; runs entirely in the database

CREATE OR REPLACE FUNCTION match_guidance(
    query_embedding vector(384),
    match_threshold FLOAT    DEFAULT 0.7,
    match_count     INT      DEFAULT 10,
    p_tenant_id     UUID     DEFAULT NULL
)
RETURNS TABLE (
    id          UUID,
    doc_url     TEXT,
    doc_title   TEXT,
    doc_date    DATE,
    page_number INTEGER,
    chunk_index INTEGER,
    chunk_text  TEXT,
    similarity  FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        gc.id,
        gc.doc_url,
        gc.doc_title,
        gc.doc_date,
        gc.page_number,
        gc.chunk_index,
        gc.chunk_text,
        (1 - (gc.embedding <=> query_embedding))::FLOAT AS similarity
    FROM guidance_chunks gc
    WHERE
        gc.is_stale = false
        AND (p_tenant_id IS NULL OR gc.tenant_id = p_tenant_id)
        AND (1 - (gc.embedding <=> query_embedding)) >= match_threshold
    ORDER BY gc.embedding <=> query_embedding  -- ascending cosine distance
    LIMIT match_count;
END;
$$;

-- ── match_k510() — cosine similarity search over 510(k) summaries ─────

CREATE OR REPLACE FUNCTION match_k510(
    query_embedding vector(384),
    match_threshold FLOAT    DEFAULT 0.7,
    match_count     INT      DEFAULT 10,
    p_tenant_id     UUID     DEFAULT NULL
)
RETURNS TABLE (
    id            UUID,
    k_number      TEXT,
    product_code  TEXT,
    device_name   TEXT,
    applicant     TEXT,
    decision_date DATE,
    summary_text  TEXT,
    similarity    FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ks.id,
        ks.k_number,
        ks.product_code,
        ks.device_name,
        ks.applicant,
        ks.decision_date,
        ks.summary_text,
        (1 - (ks.embedding <=> query_embedding))::FLOAT AS similarity
    FROM k510_summaries ks
    WHERE
        (p_tenant_id IS NULL OR ks.tenant_id = p_tenant_id)
        AND (1 - (ks.embedding <=> query_embedding)) >= match_threshold
    ORDER BY ks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
