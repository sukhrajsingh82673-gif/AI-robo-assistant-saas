-- ============================================================================
-- ZONATA Company Setup — Stage 3 schema (additive, Neon Postgres safe)
--
-- Adds the optional create-new-company fields and stores the workflow run id on
-- the build row. No column is dropped or rewritten. The reverse migration lives
-- in migrations/rollback/pg/0009_company_build_workflow_rollback.sql and is
-- never applied automatically.
-- ============================================================================

ALTER TABLE companies ADD COLUMN IF NOT EXISTS target_customers TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS budget_amount REAL;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS budget_currency TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS timeline TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS setup_notes TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS assets JSON;

ALTER TABLE company_build_runs ADD COLUMN IF NOT EXISTS workflow_run_id TEXT;
