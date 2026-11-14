-- Manual rollback for 0009_company_build_workflow.sql (never auto-applied).
-- Dropping these columns discards optional create-new fields and the workflow
-- run id. Take a backup first.

ALTER TABLE company_build_runs DROP COLUMN IF EXISTS workflow_run_id;

ALTER TABLE companies DROP COLUMN IF EXISTS assets;
ALTER TABLE companies DROP COLUMN IF EXISTS setup_notes;
ALTER TABLE companies DROP COLUMN IF EXISTS timeline;
ALTER TABLE companies DROP COLUMN IF EXISTS budget_currency;
ALTER TABLE companies DROP COLUMN IF EXISTS budget_amount;
ALTER TABLE companies DROP COLUMN IF EXISTS target_customers;
