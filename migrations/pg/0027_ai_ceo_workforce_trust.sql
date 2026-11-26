-- PostgreSQL 16 Migration 0027: AI CEO Executive Brain and Workforce Trust
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. CEO Directives Table
CREATE TABLE IF NOT EXISTS ceo_directives (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    owner_command TEXT NOT NULL,
    objective TEXT NOT NULL,
    constraints JSONB,
    deadline_ts DOUBLE PRECISION,
    budget_minor_units BIGINT NOT NULL DEFAULT 0,
    target_kpis JSONB,
    scope JSONB,
    is_ambiguous INTEGER NOT NULL DEFAULT 0,
    clarifying_question TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ceo_directives_tenant_comp ON ceo_directives(tenant_id, company_id);

ALTER TABLE ceo_directives ENABLE ROW LEVEL SECURITY;
ALTER TABLE ceo_directives FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ceo_directives' AND policyname = 'tenant_isolation_ceo_directives') THEN
        CREATE POLICY tenant_isolation_ceo_directives ON ceo_directives
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 2. CEO Decision Records Table
CREATE TABLE IF NOT EXISTS ceo_decision_records (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    directive_id TEXT,
    title TEXT NOT NULL,
    options JSONB NOT NULL,
    evidence_ids JSONB NOT NULL,
    chosen_option TEXT NOT NULL,
    reason TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    outcome_review_date TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(directive_id) REFERENCES ceo_directives(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ceo_decisions_tenant_comp ON ceo_decision_records(tenant_id, company_id);

ALTER TABLE ceo_decision_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE ceo_decision_records FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ceo_decision_records' AND policyname = 'tenant_isolation_ceo_decision_records') THEN
        CREATE POLICY tenant_isolation_ceo_decision_records ON ceo_decision_records
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 3. Company Risk Register Table
CREATE TABLE IF NOT EXISTS company_risk_register (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    details JSONB NOT NULL,
    corrective_task_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    detected_at DOUBLE PRECISION NOT NULL,
    resolved_at DOUBLE PRECISION,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(corrective_task_id) REFERENCES work_tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_register_tenant_comp ON company_risk_register(tenant_id, company_id);

ALTER TABLE company_risk_register ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_risk_register FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'company_risk_register' AND policyname = 'tenant_isolation_company_risk_register') THEN
        CREATE POLICY tenant_isolation_company_risk_register ON company_risk_register
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 4. Employee Trust Levels Table
CREATE TABLE IF NOT EXISTS employee_trust_levels (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    current_level TEXT NOT NULL DEFAULT 'SHADOW',
    tasks_completed_count INTEGER NOT NULL DEFAULT 0,
    verified_pass_rate DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    sop_compliance_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    policy_violation_count INTEGER NOT NULL DEFAULT 0,
    last_promoted_at DOUBLE PRECISION,
    is_suspended INTEGER NOT NULL DEFAULT 0,
    is_killed INTEGER NOT NULL DEFAULT 0,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    UNIQUE(tenant_id, company_id, employee_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_trust_tenant_comp ON employee_trust_levels(tenant_id, company_id);

ALTER TABLE employee_trust_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_trust_levels FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'employee_trust_levels' AND policyname = 'tenant_isolation_employee_trust_levels') THEN
        CREATE POLICY tenant_isolation_employee_trust_levels ON employee_trust_levels
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- Rule 15: Agent Role Protections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE INSERT, UPDATE, DELETE ON ceo_directives FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON ceo_decision_records FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON company_risk_register FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON employee_trust_levels FROM zonata_agent_role;
    END IF;
END $$;
