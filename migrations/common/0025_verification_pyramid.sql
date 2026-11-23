-- Common SQLite/PostgreSQL Migration 0025: Verification Pyramid
-- OpenCode Step 2H: Five-layer verification engine, layer results, and spot checks

-- 1. Task Verifications Table
CREATE TABLE IF NOT EXISTS task_verifications (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    overall_status TEXT NOT NULL DEFAULT 'PENDING',
    required_layers JSON NOT NULL,
    current_layer TEXT,
    is_spot_check INTEGER NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    failing_layer TEXT,
    created_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES work_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_verifications_tenant_comp ON task_verifications(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_task_verifications_task ON task_verifications(task_id);
CREATE INDEX IF NOT EXISTS idx_task_verifications_status ON task_verifications(overall_status);

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
    scorecard JSON,
    evidence_pointers JSON,
    error_message TEXT,
    evaluated_at REAL NOT NULL,
    FOREIGN KEY (verification_id) REFERENCES task_verifications(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES work_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_verification_layer_results_ver ON verification_layer_results(verification_id, layer);
CREATE INDEX IF NOT EXISTS idx_verification_layer_results_task ON verification_layer_results(task_id);
CREATE INDEX IF NOT EXISTS idx_verification_layer_results_status ON verification_layer_results(status);
