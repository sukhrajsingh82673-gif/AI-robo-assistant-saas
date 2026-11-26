-- PostgreSQL 16 Migration 0025: Verification Pyramid
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. Task Verifications Table
CREATE TABLE IF NOT EXISTS task_verifications (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    overall_status TEXT NOT NULL DEFAULT 'PENDING',
    required_layers JSONB NOT NULL,
    current_layer TEXT,
    is_spot_check INTEGER NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    failing_layer TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    completed_at DOUBLE PRECISION,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES work_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_verifications_tenant_comp ON task_verifications(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_task_verifications_task ON task_verifications(task_id);
CREATE INDEX IF NOT EXISTS idx_task_verifications_status ON task_verifications(overall_status);

ALTER TABLE task_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_verifications FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'task_verifications' AND policyname = 'tenant_isolation_task_verifications'
    ) THEN
        CREATE POLICY tenant_isolation_task_verifications ON task_verifications
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 2. Verification Layer Results Table
CREATE TABLE IF NOT EXISTS verification_layer_results (
    id TEXT PRIMARY KEY,
    verification_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    layer TEXT NOT NULL,
    invoker_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PASSED',
    rule_name TEXT,
    observed_value TEXT,
    expected_value TEXT,
    scorecard JSONB,
    evidence_pointers JSONB,
    error_message TEXT,
    evaluated_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (verification_id) REFERENCES task_verifications(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES work_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_verification_layer_results_ver ON verification_layer_results(verification_id, layer);
CREATE INDEX IF NOT EXISTS idx_verification_layer_results_task ON verification_layer_results(task_id);
CREATE INDEX IF NOT EXISTS idx_verification_layer_results_status ON verification_layer_results(status);

ALTER TABLE verification_layer_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_layer_results FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'verification_layer_results' AND policyname = 'tenant_isolation_verification_layer_results'
    ) THEN
        CREATE POLICY tenant_isolation_verification_layer_results ON verification_layer_results
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- Rule 15: Agent Role Protections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE INSERT, UPDATE, DELETE ON task_verifications FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON verification_layer_results FROM zonata_agent_role;
    END IF;
END $$;
