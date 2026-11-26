-- Common SQLite/PostgreSQL Migration 0024: SOP Executor
-- OpenCode Step 2G: Executable SOPs, Instance Runs, Step Records, and Compensations

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
    compliance_score REAL NOT NULL DEFAULT 0.0,
    context_inputs JSON,
    context_outputs JSON,
    error_reason TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (sop_id) REFERENCES sop_definitions(sop_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES sop_versions(version_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_sop_instances_tenant_company ON sop_instances(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_sop_instances_status ON sop_instances(status);
CREATE INDEX IF NOT EXISTS idx_sop_instances_sop_ver ON sop_instances(sop_id, version_id);

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
    inputs JSON,
    outputs JSON,
    preconditions_passed INTEGER NOT NULL DEFAULT 1,
    postconditions_passed INTEGER NOT NULL DEFAULT 1,
    start_time REAL NOT NULL,
    finish_time REAL NOT NULL,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    reversibility TEXT NOT NULL DEFAULT 'IDEMPOTENT',
    error TEXT,
    evidence_event_id TEXT,
    execution_timestamp REAL NOT NULL,
    FOREIGN KEY (instance_id) REFERENCES sop_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sop_step_records_instance ON sop_step_records(instance_id, step_number);
CREATE INDEX IF NOT EXISTS idx_sop_step_records_tenant_company ON sop_step_records(tenant_id, company_id);

-- 3. SOP Compensations Table
CREATE TABLE IF NOT EXISTS sop_compensations (
    id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    compensation_step_name TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    action_details JSON,
    compensated_at REAL NOT NULL,
    evidence_event_id TEXT,
    FOREIGN KEY (instance_id) REFERENCES sop_instances(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sop_compensations_instance ON sop_compensations(instance_id);
