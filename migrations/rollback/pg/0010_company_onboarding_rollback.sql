-- Manual rollback for 0010_company_onboarding.sql (never auto-applied).
-- Dropping these columns discards source identity, classification, verification
-- state and ingestion flags. Take a backup first.

DROP INDEX IF EXISTS idx_company_files_sha;
DROP INDEX IF EXISTS idx_external_connections_source;

ALTER TABLE company_files DROP COLUMN IF EXISTS flags;

ALTER TABLE external_connections DROP COLUMN IF EXISTS verification_expires_at;
ALTER TABLE external_connections DROP COLUMN IF EXISTS verification_requested_at;
ALTER TABLE external_connections DROP COLUMN IF EXISTS verification_token;
ALTER TABLE external_connections DROP COLUMN IF EXISTS classification;
ALTER TABLE external_connections DROP COLUMN IF EXISTS source_id;
