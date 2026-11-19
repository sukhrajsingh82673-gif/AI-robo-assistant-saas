-- URA / ZONATA enterprise AI corporate workforce architecture.
--
-- The canonical 25-table workforce schema ships in
-- migrations/pg/0001_postgresql_full_schema.sql. This migration only adds the
-- columns introduced by the workforce service layer so existing PostgreSQL
-- deployments converge with the SQLite schema.

-- A company owns exactly one active enterprise root, so organization rows must
-- carry the company they belong to. Before this column existed, organization
-- reads could return another company's root within the same tenant.
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS company_id TEXT;

CREATE INDEX IF NOT EXISTS idx_org_company ON organizations(tenant_id, company_id);

-- employee_kras is shared by the canonical corporate_employees registry and the
-- V7 ai_employees registry, so it intentionally has no employee/tenant foreign
-- keys: the two registries have independent lifecycles.
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS responsibility TEXT;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS associated_workflows JSON;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS associated_kpi_ids JSON;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS allowed_tools JSON;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS authority_scope JSON;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS escalation_rules JSON;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS expected_outcomes JSON;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS position_id TEXT;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS strategic_objective_id TEXT;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS weight_percentage REAL DEFAULT 25.0;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS accountability_statement TEXT;
ALTER TABLE employee_kras ADD COLUMN IF NOT EXISTS updated_at REAL;
