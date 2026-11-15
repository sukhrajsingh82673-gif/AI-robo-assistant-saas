-- ============================================================================
-- ZONATA Company Setup — Stage 5 schema (additive, Neon Postgres safe)
--
-- Records the state needed to restore a company during its recovery window and
-- to download or re-send the export that was produced before deletion.
-- No column is dropped or rewritten.
--
-- The reverse migration lives in
-- migrations/rollback/pg/0011_company_deletion_export_rollback.sql and is never
-- applied automatically.
-- ============================================================================

ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS previous_status TEXT;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS export_ready_at REAL;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS export_sha256 TEXT;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS export_size_bytes INTEGER;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS export_content_type TEXT;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS recovery_days INTEGER;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS email_recipient TEXT;
ALTER TABLE company_deletion_requests ADD COLUMN IF NOT EXISTS purge_blocked_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_company_deletion_requests_purge
    ON company_deletion_requests(status, purge_after);
