-- PostgreSQL 16 Migration 0026: KPI Engine, Goal Trees, and Kaizen Loop
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. KPI Tree Definitions Table
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
    target_value DOUBLE PRECISION NOT NULL,
    warning_threshold DOUBLE PRECISION NOT NULL,
    critical_threshold DOUBLE PRECISION NOT NULL,
    direction TEXT NOT NULL DEFAULT 'HIGHER_IS_BETTER',
    unit TEXT NOT NULL DEFAULT 'COUNT',
    cadence TEXT NOT NULL DEFAULT 'DAILY',
    parent_kpi_id TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_kpi_id) REFERENCES kpi_tree_definitions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_kpi_tree_tenant_comp ON kpi_tree_definitions(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_kpi_tree_scope ON kpi_tree_definitions(scope_level, scope_id);

ALTER TABLE kpi_tree_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_tree_definitions FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kpi_tree_definitions' AND policyname = 'tenant_isolation_kpi_tree_definitions') THEN
        CREATE POLICY tenant_isolation_kpi_tree_definitions ON kpi_tree_definitions
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 2. KPI Snapshots Table
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kpi_id TEXT NOT NULL,
    scope_level TEXT NOT NULL,
    scope_id TEXT,
    current_value DOUBLE PRECISION NOT NULL,
    target_value DOUBLE PRECISION NOT NULL,
    warning_threshold DOUBLE PRECISION NOT NULL,
    critical_threshold DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,
    computation_proof JSONB NOT NULL,
    inputs_hash TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    computed_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (kpi_id) REFERENCES kpi_tree_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_kpi ON kpi_snapshots(kpi_id, computed_at);
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_tenant_comp ON kpi_snapshots(tenant_id, company_id);

ALTER TABLE kpi_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_snapshots FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kpi_snapshots' AND policyname = 'tenant_isolation_kpi_snapshots') THEN
        CREATE POLICY tenant_isolation_kpi_snapshots ON kpi_snapshots
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- 3. KPI Alerts Table
CREATE TABLE IF NOT EXISTS kpi_alerts (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kpi_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    observed_value DOUBLE PRECISION NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    escalated_to_role TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    playbook_triggered TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (kpi_id) REFERENCES kpi_tree_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES kpi_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kpi_alerts_kpi ON kpi_alerts(kpi_id);
CREATE INDEX IF NOT EXISTS idx_kpi_alerts_status ON kpi_alerts(status);

ALTER TABLE kpi_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_alerts FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kpi_alerts' AND policyname = 'tenant_isolation_kpi_alerts') THEN
        CREATE POLICY tenant_isolation_kpi_alerts ON kpi_alerts
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

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
    details JSONB,
    recorded_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES work_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kaizen_defects_pos ON kaizen_defect_records(position_id, defect_type);
CREATE INDEX IF NOT EXISTS idx_kaizen_defects_sop ON kaizen_defect_records(sop_id, defect_type);

ALTER TABLE kaizen_defect_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE kaizen_defect_records FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kaizen_defect_records' AND policyname = 'tenant_isolation_kaizen_defect_records') THEN
        CREATE POLICY tenant_isolation_kaizen_defect_records ON kaizen_defect_records
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

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
    content JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kaizen_proposals_target ON kaizen_proposals(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_kaizen_proposals_status ON kaizen_proposals(status);

ALTER TABLE kaizen_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE kaizen_proposals FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kaizen_proposals' AND policyname = 'tenant_isolation_kaizen_proposals') THEN
        CREATE POLICY tenant_isolation_kaizen_proposals ON kaizen_proposals
            FOR ALL USING (tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

-- Rule 15: Agent Role Protections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE INSERT, UPDATE, DELETE ON kpi_tree_definitions FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON kpi_snapshots FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON kpi_alerts FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON kaizen_defect_records FROM zonata_agent_role;
        REVOKE INSERT, UPDATE, DELETE ON kaizen_proposals FROM zonata_agent_role;
    END IF;
END $$;
