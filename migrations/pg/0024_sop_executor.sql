-- PostgreSQL 16 Migration 0024: SOP Executor
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. SOP Instances Table
CREATE TABLE IF NOT EXISTS sop_instances (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    sop_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    executor_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    dry_run INTEGER NOT NULL DEFAULT 0,
    current_step INTEGER NOT NULL DEFAULT 0,
    total_steps INTEGER NOT NULL DEFAULT 0,
    compliance_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    context_inputs JSONB,
    context_outputs JSONB,
    error_reason TEXT,
    started_at DOUBLE PRECISION NOT NULL,
    completed_at DOUBLE PRECISION,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (sop_id) REFERENCES sop_definitions(sop_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES sop_versions(version_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_sop_instances_tenant_company ON sop_instances(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_sop_instances_status ON sop_instances(status);
CREATE INDEX IF NOT EXISTS idx_sop_instances_sop_ver ON sop_instances(sop_id, version_id);

ALTER TABLE sop_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE sop_instances FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sop_instances' AND policyname = 'tenant_isolation_sop_instances'
    ) THEN
        CREATE POLICY tenant_isolation_sop_instances ON sop_instances
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 2. SOP Step Records Table
CREATE TABLE IF NOT EXISTS sop_step_records (
    id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    step_name TEXT NOT NULL,
    step_type TEXT NOT NULL,
    tool_name TEXT,
    actor_id TEXT,
    input_hash TEXT NOT NULL,
    step_def_hash TEXT NOT NULL,
    output_hash TEXT,
    outcome TEXT NOT NULL DEFAULT 'PASSED',
    inputs JSONB,
    outputs JSONB,
    preconditions_passed INTEGER NOT NULL DEFAULT 1,
    postconditions_passed INTEGER NOT NULL DEFAULT 1,
    start_time DOUBLE PRECISION NOT NULL,
    finish_time DOUBLE PRECISION NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    reversibility TEXT NOT NULL DEFAULT 'IDEMPOTENT',
    error TEXT,
    evidence_event_id TEXT,
    execution_timestamp DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (instance_id) REFERENCES sop_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sop_step_records_instance ON sop_step_records(instance_id, step_number);
CREATE INDEX IF NOT EXISTS idx_sop_step_records_tenant_company ON sop_step_records(tenant_id, company_id);

ALTER TABLE sop_step_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE sop_step_records FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sop_step_records' AND policyname = 'tenant_isolation_sop_step_records'
    ) THEN
        CREATE POLICY tenant_isolation_sop_step_records ON sop_step_records
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 3. SOP Compensations Table
CREATE TABLE IF NOT EXISTS sop_compensations (
    id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    compensation_step_name TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    action_details JSONB,
    compensated_at DOUBLE PRECISION NOT NULL,
    evidence_event_id TEXT,
    FOREIGN KEY (instance_id) REFERENCES sop_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sop_compensations_instance ON sop_compensations(instance_id);

ALTER TABLE sop_compensations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sop_compensations FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sop_compensations' AND policyname = 'tenant_isolation_sop_compensations'
    ) THEN
        CREATE POLICY tenant_isolation_sop_compensations ON sop_compensations
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- Rule 15: Agent Role Protections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE DELETE ON sop_step_records FROM zonata_agent_role;
        REVOKE UPDATE (compliance_score) ON sop_instances FROM zonata_agent_role;
    END IF;
END $$;
