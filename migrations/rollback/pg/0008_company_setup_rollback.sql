-- ============================================================================
-- ZONATA Company Setup — Stage 1 REVERSE migration
--
-- This file is NOT applied automatically (the migration manager only scans
-- migrations/common and migrations/pg|sqlite). Run it manually to roll back
-- 0008_company_setup.sql.
--
-- WARNING: dropping the tables loses company drafts, audit events and deletion
-- state. Company rows themselves are preserved; only the added columns are
-- dropped. Before running this in production, export the four tables below.
-- ============================================================================

DROP TABLE IF EXISTS company_audit_events;
DROP TABLE IF EXISTS company_deletion_requests;
DROP TABLE IF EXISTS company_admin_grants;
DROP TABLE IF EXISTS company_drafts;
DROP TABLE IF EXISTS company_legal_items;
DROP TABLE IF EXISTS company_files;
DROP TABLE IF EXISTS company_build_runs;

DROP INDEX IF EXISTS idx_companies_tenant_status;

-- Restore the legacy status value before removing the vocabulary.
UPDATE companies SET status = 'ATTENTION' WHERE status = 'NEEDS_ATTENTION';

ALTER TABLE external_connections DROP COLUMN IF EXISTS skip_reason;
ALTER TABLE external_connections DROP COLUMN IF EXISTS skipped;
ALTER TABLE external_connections DROP COLUMN IF EXISTS verification_method;
ALTER TABLE external_connections DROP COLUMN IF EXISTS verified_at;
ALTER TABLE external_connections DROP COLUMN IF EXISTS secret_ref;
ALTER TABLE external_connections DROP COLUMN IF EXISTS last_check_at;
ALTER TABLE external_connections DROP COLUMN IF EXISTS status;
ALTER TABLE external_connections DROP COLUMN IF EXISTS scope;
ALTER TABLE external_connections DROP COLUMN IF EXISTS provider_id;

ALTER TABLE companies DROP COLUMN IF EXISTS deleted_by;
ALTER TABLE companies DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE companies DROP COLUMN IF EXISTS readiness_score;
ALTER TABLE companies DROP COLUMN IF EXISTS revenue_period;
ALTER TABLE companies DROP COLUMN IF EXISTS revenue_currency;
ALTER TABLE companies DROP COLUMN IF EXISTS revenue_amount;
ALTER TABLE companies DROP COLUMN IF EXISTS business_model;
ALTER TABLE companies DROP COLUMN IF EXISTS website;
ALTER TABLE companies DROP COLUMN IF EXISTS updated_at;
ALTER TABLE companies DROP COLUMN IF EXISTS created_by;
ALTER TABLE companies DROP COLUMN IF EXISTS owner_role;
ALTER TABLE companies DROP COLUMN IF EXISTS owner_email;
ALTER TABLE companies DROP COLUMN IF EXISTS owner_name;
ALTER TABLE companies DROP COLUMN IF EXISTS description;
ALTER TABLE companies DROP COLUMN IF EXISTS title;
