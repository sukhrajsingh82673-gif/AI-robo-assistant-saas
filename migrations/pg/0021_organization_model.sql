-- PostgreSQL 16 Migration 0021: Organization Model (Board to Agent)
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. Departments Table (Additive columns if missing)
CREATE TABLE IF NOT EXISTS departments (
    department_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    lead_position_id TEXT,
    manager_agent_id TEXT,
    budget_limit REAL NOT NULL DEFAULT 0.0,
    spending_limit REAL NOT NULL DEFAULT 0.0,
    budget_minor_units BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_departments_tenant_company ON departments(tenant_id, company_id);

ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'departments' AND policyname = 'tenant_isolation_departments'
    ) THEN
        CREATE POLICY tenant_isolation_departments ON departments
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 2. Positions Table
CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    department_id TEXT,
    title TEXT NOT NULL,
    level TEXT NOT NULL,
    job_description_doc_id TEXT,
    authority_profile_id TEXT,
    kra_kpi_set TEXT NOT NULL DEFAULT '[]',
    sop_set TEXT NOT NULL DEFAULT '[]',
    allowed_tools TEXT NOT NULL DEFAULT '[]',
    spend_limit_minor_units BIGINT NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(department_id) REFERENCES departments(department_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_positions_tenant_company ON positions(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_positions_level ON positions(level);
CREATE INDEX IF NOT EXISTS idx_positions_dept ON positions(department_id);

ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'positions' AND policyname = 'tenant_isolation_positions'
    ) THEN
        CREATE POLICY tenant_isolation_positions ON positions
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 3. Position Assignments Table
CREATE TABLE IF NOT EXISTS position_assignments (
    assignment_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    occupant_type TEXT NOT NULL,
    occupant_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(position_id) REFERENCES positions(position_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pos_assign_tenant_company ON position_assignments(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_pos_assign_position ON position_assignments(position_id);
CREATE INDEX IF NOT EXISTS idx_pos_assign_occupant ON position_assignments(occupant_id);
CREATE INDEX IF NOT EXISTS idx_pos_assign_status ON position_assignments(status);

ALTER TABLE position_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_assignments FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'position_assignments' AND policyname = 'tenant_isolation_position_assignments'
    ) THEN
        CREATE POLICY tenant_isolation_position_assignments ON position_assignments
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 4. Reporting Lines Table
CREATE TABLE IF NOT EXISTS reporting_lines (
    reporting_line_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    reports_to_position_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(position_id) REFERENCES positions(position_id) ON DELETE CASCADE,
    FOREIGN KEY(reports_to_position_id) REFERENCES positions(position_id) ON DELETE CASCADE,
    UNIQUE(tenant_id, company_id, position_id)
);

CREATE INDEX IF NOT EXISTS idx_reporting_lines_tenant_company ON reporting_lines(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_reporting_lines_reports_to ON reporting_lines(reports_to_position_id);

ALTER TABLE reporting_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE reporting_lines FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'reporting_lines' AND policyname = 'tenant_isolation_reporting_lines'
    ) THEN
        CREATE POLICY tenant_isolation_reporting_lines ON reporting_lines
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 5. Board Principals Table
CREATE TABLE IF NOT EXISTS board_principals (
    principal_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    voting_shares_basis_points INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_board_principals_tenant_company ON board_principals(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_board_principals_user ON board_principals(user_id);

ALTER TABLE board_principals ENABLE ROW LEVEL SECURITY;
ALTER TABLE board_principals FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'board_principals' AND policyname = 'tenant_isolation_board_principals'
    ) THEN
        CREATE POLICY tenant_isolation_board_principals ON board_principals
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 6. Handover Packs Table
CREATE TABLE IF NOT EXISTS handover_packs (
    pack_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    previous_occupant_type TEXT NOT NULL,
    previous_occupant_id TEXT NOT NULL,
    successor_occupant_type TEXT,
    successor_occupant_id TEXT,
    open_tasks TEXT NOT NULL DEFAULT '[]',
    context_documents TEXT NOT NULL DEFAULT '[]',
    decisions TEXT NOT NULL DEFAULT '[]',
    pending_approvals TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'GENERATED',
    evidence_id TEXT,
    generated_at REAL NOT NULL,
    acknowledged_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(position_id) REFERENCES positions(position_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_handover_packs_tenant_company ON handover_packs(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_handover_packs_position ON handover_packs(position_id);
CREATE INDEX IF NOT EXISTS idx_handover_packs_prev_occupant ON handover_packs(previous_occupant_id);

ALTER TABLE handover_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE handover_packs FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'handover_packs' AND policyname = 'tenant_isolation_handover_packs'
    ) THEN
        CREATE POLICY tenant_isolation_handover_packs ON handover_packs
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- Rule 15 Principal Separation: Revoke Mutation Privileges from Agents
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE ALL PRIVILEGES ON positions, position_assignments, reporting_lines, board_principals, departments, handover_packs FROM zonata_agent_role;
        GRANT SELECT ON positions, position_assignments, reporting_lines, departments, handover_packs TO zonata_agent_role;
    END IF;
END $$;
