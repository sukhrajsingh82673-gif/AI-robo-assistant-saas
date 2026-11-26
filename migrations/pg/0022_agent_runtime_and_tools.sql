-- PostgreSQL 16 Migration 0022: Agent Runtime and Tools
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. Agent Runs Table
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    current_step INTEGER NOT NULL DEFAULT 0,
    max_steps INTEGER NOT NULL DEFAULT 10,
    timeout_seconds REAL NOT NULL DEFAULT 120.0,
    budget_micro_units BIGINT NOT NULL DEFAULT 500000,
    spent_micro_units BIGINT NOT NULL DEFAULT 0,
    autonomy_level TEXT NOT NULL DEFAULT 'SHADOW',
    error_reason TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    metadata JSONB,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant_company ON agent_runs(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);

ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'agent_runs' AND policyname = 'tenant_isolation_agent_runs'
    ) THEN
        CREATE POLICY tenant_isolation_agent_runs ON agent_runs
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 2. Agent Run Steps Table
CREATE TABLE IF NOT EXISTS agent_run_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,
    status TEXT NOT NULL DEFAULT 'PENDING',
    idempotency_key TEXT,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    evidence_id TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(run_id) REFERENCES agent_runs(id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_run_steps_run_step ON agent_run_steps(run_id, step_number);
CREATE INDEX IF NOT EXISTS idx_agent_run_steps_idempotency ON agent_run_steps(idempotency_key);

ALTER TABLE agent_run_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_run_steps FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'agent_run_steps' AND policyname = 'tenant_isolation_agent_run_steps'
    ) THEN
        CREATE POLICY tenant_isolation_agent_run_steps ON agent_run_steps
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 3. Agent Certifications Table
CREATE TABLE IF NOT EXISTS agent_certifications (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    certification_status TEXT NOT NULL DEFAULT 'UNCERTIFIED',
    qualification_task_id TEXT,
    test_records JSONB NOT NULL DEFAULT '[]'::jsonb,
    certified_at REAL,
    certified_by TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_certifications_agent_tenant ON agent_certifications(agent_id, tenant_id);

ALTER TABLE agent_certifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_certifications FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'agent_certifications' AND policyname = 'tenant_isolation_agent_certifications'
    ) THEN
        CREATE POLICY tenant_isolation_agent_certifications ON agent_certifications
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 4. Calendar Events Table
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    uid TEXT NOT NULL,
    summary TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CONFIRMED',
    ical_data TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_tenant_company ON calendar_events(tenant_id, company_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_events_uid ON calendar_events(tenant_id, company_id, uid);

ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'calendar_events' AND policyname = 'tenant_isolation_calendar_events'
    ) THEN
        CREATE POLICY tenant_isolation_calendar_events ON calendar_events
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- Rule 15: Agent Role Protections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE INSERT, UPDATE, DELETE ON agent_certifications FROM zonata_agent_role;
    END IF;
END $$;
