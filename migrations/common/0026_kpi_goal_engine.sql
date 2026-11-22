-- Common SQLite/PostgreSQL Migration 0026: KPI Engine, Goal Trees, and Kaizen Loop
-- OpenCode Step 2I: Deterministic arithmetic KPI trees, snapshots with computation proofs, and Kaizen defect clustering

-- 1. KPI Tree Definitions Table (Hierarchical Tree)
CREATE TABLE IF NOT EXISTS kpi_tree_definitions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    scope_level TEXT NOT NULL,
    scope_id TEXT,
    metric_type TEXT NOT NULL,
    target_value REAL NOT NULL,
    warning_threshold REAL NOT NULL,
    critical_threshold REAL NOT NULL,
    direction TEXT NOT NULL DEFAULT 'HIGHER_IS_BETTER',
    unit TEXT NOT NULL DEFAULT 'COUNT',
    cadence TEXT NOT NULL DEFAULT 'DAILY',
    parent_kpi_id TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_kpi_id) REFERENCES kpi_tree_definitions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_kpi_tree_tenant_comp ON kpi_tree_definitions(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_kpi_tree_scope ON kpi_tree_definitions(scope_level, scope_id);
CREATE INDEX IF NOT EXISTS idx_kpi_tree_parent ON kpi_tree_definitions(parent_kpi_id);

-- 2. KPI Snapshots Table (Historical Scores & Mathematical Proofs)
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kpi_id TEXT NOT NULL,
    scope_level TEXT NOT NULL,
    scope_id TEXT,
    current_value REAL NOT NULL,
    target_value REAL NOT NULL,
    warning_threshold REAL NOT NULL,
    critical_threshold REAL NOT NULL,
    status TEXT NOT NULL,
    computation_proof JSON NOT NULL,
    inputs_hash TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    computed_at REAL NOT NULL,
    FOREIGN KEY (kpi_id) REFERENCES kpi_tree_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_kpi ON kpi_snapshots(kpi_id, computed_at);
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_tenant_comp ON kpi_snapshots(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_status ON kpi_snapshots(status);

-- 3. KPI Alerts Table (Breach Notifications & Playbook Triggers)
CREATE TABLE IF NOT EXISTS kpi_alerts (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kpi_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    observed_value REAL NOT NULL,
    threshold_value REAL NOT NULL,
    escalated_to_role TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    playbook_triggered TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (kpi_id) REFERENCES kpi_tree_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES kpi_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kpi_alerts_kpi ON kpi_alerts(kpi_id);
CREATE INDEX IF NOT EXISTS idx_kpi_alerts_status ON kpi_alerts(status);

-- 4. Kaizen Defect Records Table
CREATE TABLE IF NOT EXISTS kaizen_defect_records (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    position_id TEXT,
    employee_id TEXT,
    sop_id TEXT,
    defect_type TEXT NOT NULL,
    details JSON,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES work_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kaizen_defects_pos ON kaizen_defect_records(position_id, defect_type);
CREATE INDEX IF NOT EXISTS idx_kaizen_defects_sop ON kaizen_defect_records(sop_id, defect_type);

-- 5. Kaizen Proposals Table
CREATE TABLE IF NOT EXISTS kaizen_proposals (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    proposal_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    cluster_defect_type TEXT NOT NULL,
    cluster_count INTEGER NOT NULL,
    title TEXT NOT NULL,
    content JSON NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kaizen_proposals_target ON kaizen_proposals(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_kaizen_proposals_status ON kaizen_proposals(status);
