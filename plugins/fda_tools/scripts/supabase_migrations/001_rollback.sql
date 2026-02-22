-- FDA-220: Rollback for 001_pgvector_schema.sql
-- Run this to undo the migration completely.

DROP FUNCTION IF EXISTS match_k510(vector, float, int, uuid);
DROP FUNCTION IF EXISTS match_guidance(vector, float, int, uuid);

DROP TABLE IF EXISTS guidance_versions   CASCADE;
DROP TABLE IF EXISTS embedding_jobs      CASCADE;
DROP TABLE IF EXISTS project_documents   CASCADE;
DROP TABLE IF EXISTS k510_summaries      CASCADE;
DROP TABLE IF EXISTS guidance_chunks     CASCADE;
