-- ============================================================================
-- ZONATA Company Setup — Stage 4 schema (additive, Neon Postgres safe)
--
-- Adds the source catalogue identity, data classification, ownership
-- verification state for connections, and the ingestion flags column.
-- No column is dropped or rewritten.
--
-- The reverse migration lives in
-- migrations/rollback/pg/0010_company_onboarding_rollback.sql and is never
-- applied automatically.
-- ============================================================================

ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS classification TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS verification_token TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS verification_requested_at REAL;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS verification_expires_at REAL;

ALTER TABLE company_files ADD COLUMN IF NOT EXISTS flags JSON;

CREATE INDEX IF NOT EXISTS idx_external_connections_source
    ON external_connections(tenant_id, company_id, source_id);

CREATE INDEX IF NOT EXISTS idx_company_files_sha
    ON company_files(tenant_id, company_id, sha256);
