-- Manual rollback for 0011_company_deletion_export.sql (never auto-applied).
-- Dropping these columns discards the export manifest and the previous status
-- used to restore a company during its recovery window. Take a backup first.

DROP INDEX IF EXISTS idx_company_deletion_requests_purge;

ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS purge_blocked_reason;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS email_recipient;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS recovery_days;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS export_content_type;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS export_size_bytes;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS export_sha256;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS export_ready_at;
ALTER TABLE company_deletion_requests DROP COLUMN IF EXISTS previous_status;
