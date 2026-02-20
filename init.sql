-- FDA Offline Database Schema
-- PostgreSQL 15+ with pgcrypto for encryption and JSONB for flexible querying
-- Supports 7 OpenFDA endpoints + audit trail for 21 CFR Part 11 compliance

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- Column-level encryption
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Fuzzy text search

-- ==============================================================================
-- 510(k) CLEARANCES TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_510k (
    id SERIAL PRIMARY KEY,
    k_number VARCHAR(20) UNIQUE NOT NULL,
    product_code VARCHAR(10) NOT NULL,
    device_name TEXT,  -- Encrypted with pgcrypto if sensitive
    applicant TEXT,    -- Encrypted if sensitive
    decision_date DATE,
    decision_description TEXT,
    openfda_json JSONB NOT NULL,  -- Full OpenFDA response as JSONB
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64),  -- HMAC-SHA256 for integrity
    updated_at TIMESTAMPTZ,
    CONSTRAINT fk_510k_product_code FOREIGN KEY (product_code) 
        REFERENCES fda_classification(product_code) ON DELETE CASCADE
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_510k_product_code ON fda_510k(product_code);
CREATE INDEX IF NOT EXISTS idx_510k_decision_date ON fda_510k(decision_date DESC);
CREATE INDEX IF NOT EXISTS idx_510k_cached_at ON fda_510k(cached_at);
CREATE INDEX IF NOT EXISTS idx_510k_k_number ON fda_510k(k_number);
-- GIN index for JSONB containment queries (@>, @<, ?, ?&, ?|)
CREATE INDEX IF NOT EXISTS idx_510k_openfda_gin ON fda_510k USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- 510(k) SUMMARY SECTIONS TABLE (for future graph traversal)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_510k_sections (
    section_id SERIAL PRIMARY KEY,
    k_number VARCHAR(20) NOT NULL,
    section_type VARCHAR(50) NOT NULL,  -- 'indications', 'testing', 'materials', etc.
    section_content JSONB NOT NULL,     -- Structured section data
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_sections_k_number FOREIGN KEY (k_number) 
        REFERENCES fda_510k(k_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sections_k_number ON fda_510k_sections(k_number);
CREATE INDEX IF NOT EXISTS idx_sections_type ON fda_510k_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_sections_content_gin ON fda_510k_sections USING GIN (section_content jsonb_path_ops);
-- Trigram index for fuzzy text search (similarity, %)
CREATE INDEX IF NOT EXISTS idx_sections_trgm ON fda_510k_sections USING GIN ((section_content::text) gin_trgm_ops);

-- ==============================================================================
-- DEVICE CLASSIFICATION TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_classification (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(10) UNIQUE NOT NULL,
    device_name TEXT,
    device_class VARCHAR(5),  -- 'I', 'II', 'III', 'U' (unclassified)
    regulation_number VARCHAR(50),
    review_panel VARCHAR(5),  -- 'CV', 'CH', 'HE', etc.
    openfda_json JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_classification_product_code ON fda_classification(product_code);
CREATE INDEX IF NOT EXISTS idx_classification_device_class ON fda_classification(device_class);
CREATE INDEX IF NOT EXISTS idx_classification_review_panel ON fda_classification(review_panel);
CREATE INDEX IF NOT EXISTS idx_classification_openfda_gin ON fda_classification USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- MAUDE ADVERSE EVENTS TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_maude_events (
    id SERIAL PRIMARY KEY,
    event_key VARCHAR(50) UNIQUE NOT NULL,  -- mdr_report_key
    product_code VARCHAR(10),
    event_type VARCHAR(100),
    date_received DATE,
    adverse_event_flag VARCHAR(1),  -- 'Y' or 'N'
    openfda_json JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_maude_event_key ON fda_maude_events(event_key);
CREATE INDEX IF NOT EXISTS idx_maude_product_code ON fda_maude_events(product_code);
CREATE INDEX IF NOT EXISTS idx_maude_date_received ON fda_maude_events(date_received DESC);
CREATE INDEX IF NOT EXISTS idx_maude_openfda_gin ON fda_maude_events USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- RECALLS TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_recalls (
    id SERIAL PRIMARY KEY,
    recall_number VARCHAR(20) UNIQUE NOT NULL,
    product_code VARCHAR(10),
    classification VARCHAR(20),  -- 'Class I', 'Class II', 'Class III'
    recalling_firm TEXT,
    event_date_initiated DATE,
    openfda_json JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_recalls_recall_number ON fda_recalls(recall_number);
CREATE INDEX IF NOT EXISTS idx_recalls_product_code ON fda_recalls(product_code);
CREATE INDEX IF NOT EXISTS idx_recalls_classification ON fda_recalls(classification);
CREATE INDEX IF NOT EXISTS idx_recalls_event_date ON fda_recalls(event_date_initiated DESC);
CREATE INDEX IF NOT EXISTS idx_recalls_openfda_gin ON fda_recalls USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- PMA APPROVALS TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_pma (
    id SERIAL PRIMARY KEY,
    pma_number VARCHAR(20) UNIQUE NOT NULL,
    product_code VARCHAR(10),
    device_name TEXT,
    applicant TEXT,  -- Encrypted if sensitive
    decision_date DATE,
    openfda_json JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_pma_pma_number ON fda_pma(pma_number);
CREATE INDEX IF NOT EXISTS idx_pma_product_code ON fda_pma(product_code);
CREATE INDEX IF NOT EXISTS idx_pma_decision_date ON fda_pma(decision_date DESC);
CREATE INDEX IF NOT EXISTS idx_pma_openfda_gin ON fda_pma USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- UDI (UNIQUE DEVICE IDENTIFICATION) TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_udi (
    id SERIAL PRIMARY KEY,
    di VARCHAR(100) UNIQUE NOT NULL,  -- Device Identifier
    product_code VARCHAR(10),
    brand_name TEXT,
    company_name TEXT,
    openfda_json JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_udi_di ON fda_udi(di);
CREATE INDEX IF NOT EXISTS idx_udi_product_code ON fda_udi(product_code);
CREATE INDEX IF NOT EXISTS idx_udi_brand_name ON fda_udi(brand_name);
CREATE INDEX IF NOT EXISTS idx_udi_openfda_gin ON fda_udi USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- ENFORCEMENT ACTIONS TABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS fda_enforcement (
    id SERIAL PRIMARY KEY,
    recall_number VARCHAR(20) UNIQUE NOT NULL,
    product_code VARCHAR(10),
    classification VARCHAR(20),
    status VARCHAR(50),
    center_classification_date DATE,
    openfda_json JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_enforcement_recall_number ON fda_enforcement(recall_number);
CREATE INDEX IF NOT EXISTS idx_enforcement_product_code ON fda_enforcement(product_code);
CREATE INDEX IF NOT EXISTS idx_enforcement_classification ON fda_enforcement(classification);
CREATE INDEX IF NOT EXISTS idx_enforcement_openfda_gin ON fda_enforcement USING GIN (openfda_json jsonb_path_ops);

-- ==============================================================================
-- AUDIT TRAIL (21 CFR Part 11 Compliance)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    event_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence_number BIGSERIAL UNIQUE,  -- Monotonic counter, immune to clock manipulation
    event_type VARCHAR(20) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE', 'QUERY'
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100),
    user_id VARCHAR(100) NOT NULL,
    signature VARCHAR(128),  -- HMAC for non-repudiation
    metadata JSONB  -- Before/after snapshots, reason codes
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);

-- ==============================================================================
-- REFRESH METADATA (Track data freshness and TTL)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS refresh_metadata (
    endpoint VARCHAR(50) PRIMARY KEY,
    last_refresh TIMESTAMPTZ NOT NULL,
    next_refresh TIMESTAMPTZ,
    ttl_hours INTEGER,
    record_count INTEGER,
    status VARCHAR(20) DEFAULT 'current',  -- 'current', 'stale', 'refreshing'
    error_message TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- DELTA CHECKSUMS (Track changes for incremental updates)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS delta_checksums (
    endpoint VARCHAR(50),
    record_id VARCHAR(100),
    checksum VARCHAR(64),
    last_verified TIMESTAMPTZ,
    PRIMARY KEY (endpoint, record_id)
);

CREATE INDEX IF NOT EXISTS idx_delta_endpoint ON delta_checksums(endpoint);
CREATE INDEX IF NOT EXISTS idx_delta_last_verified ON delta_checksums(last_verified);

-- ==============================================================================
-- FUNCTIONS AND TRIGGERS
-- ==============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for fda_510k table
CREATE TRIGGER update_fda_510k_updated_at
    BEFORE UPDATE ON fda_510k
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to log audit events
CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    event_type_val VARCHAR(20);
    record_id_val VARCHAR(100);
    metadata_val JSONB;
BEGIN
    -- Determine event type
    IF TG_OP = 'INSERT' THEN
        event_type_val := 'INSERT';
        record_id_val := NEW.id::TEXT;
        metadata_val := jsonb_build_object('new_record', row_to_json(NEW));
    ELSIF TG_OP = 'UPDATE' THEN
        event_type_val := 'UPDATE';
        record_id_val := NEW.id::TEXT;
        metadata_val := jsonb_build_object(
            'old_record', row_to_json(OLD),
            'new_record', row_to_json(NEW)
        );
    ELSIF TG_OP = 'DELETE' THEN
        event_type_val := 'DELETE';
        record_id_val := OLD.id::TEXT;
        metadata_val := jsonb_build_object('deleted_record', row_to_json(OLD));
    END IF;

    -- Insert audit log entry
    INSERT INTO audit_log (
        event_type,
        table_name,
        record_id,
        user_id,
        metadata
    ) VALUES (
        event_type_val,
        TG_TABLE_NAME,
        record_id_val,
        COALESCE(current_setting('app.user_id', TRUE), 'system'),
        metadata_val
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to all data tables
CREATE TRIGGER audit_fda_510k
    AFTER INSERT OR UPDATE OR DELETE ON fda_510k
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_fda_classification
    AFTER INSERT OR UPDATE OR DELETE ON fda_classification
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_fda_maude_events
    AFTER INSERT OR UPDATE OR DELETE ON fda_maude_events
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_fda_recalls
    AFTER INSERT OR UPDATE OR DELETE ON fda_recalls
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_fda_pma
    AFTER INSERT OR UPDATE OR DELETE ON fda_pma
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_fda_udi
    AFTER INSERT OR UPDATE OR DELETE ON fda_udi
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_fda_enforcement
    AFTER INSERT OR UPDATE OR DELETE ON fda_enforcement
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

-- ==============================================================================
-- INITIAL METADATA SETUP
-- ==============================================================================
INSERT INTO refresh_metadata (endpoint, last_refresh, ttl_hours, record_count, status)
VALUES 
    ('510k', NOW(), 168, 0, 'current'),  -- 7 days TTL
    ('classification', NOW(), NULL, 0, 'current'),  -- Static, never expires
    ('maude', NOW(), 24, 0, 'current'),  -- 1 day TTL (safety-critical)
    ('recalls', NOW(), 24, 0, 'current'),  -- 1 day TTL
    ('pma', NOW(), 168, 0, 'current'),  -- 7 days TTL
    ('udi', NOW(), 168, 0, 'current'),  -- 7 days TTL
    ('enforcement', NOW(), 24, 0, 'current')  -- 1 day TTL
ON CONFLICT (endpoint) DO NOTHING;

-- ==============================================================================
-- SAMPLE VERIFICATION QUERIES
-- ==============================================================================

-- Query 1: Find 510(k)s with specific regulation number using JSONB containment
-- SELECT k_number, openfda_json->'device_name' AS device
-- FROM fda_510k
-- WHERE openfda_json @> '{"openfda": {"regulation_number": ["870.3610"]}}';

-- Query 2: Full-text search across all sections
-- SELECT k.k_number, s.section_type, s.section_content
-- FROM fda_510k k
-- JOIN fda_510k_sections s ON k.k_number = s.k_number
-- WHERE s.section_content::text ILIKE '%titanium%';

-- Query 3: Find recent Class I recalls
-- SELECT recall_number, recalling_firm, event_date_initiated
-- FROM fda_recalls
-- WHERE classification = 'Class I'
-- AND event_date_initiated > NOW() - INTERVAL '1 year'
-- ORDER BY event_date_initiated DESC;

-- Query 4: Audit trail for specific K-number
-- SELECT timestamp, event_type, user_id, metadata
-- FROM audit_log
-- WHERE table_name = 'fda_510k'
-- AND record_id IN (SELECT id::TEXT FROM fda_510k WHERE k_number = 'K123456')
-- ORDER BY timestamp DESC;
