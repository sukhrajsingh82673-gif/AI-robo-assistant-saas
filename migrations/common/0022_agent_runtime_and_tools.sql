-- Common SQLite/PostgreSQL Migration 0022: Agent Runtime and Tools
-- OpenCode Step 2E

-- 1. Agent Runs Table (Tracks bounded execution loops and state)
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
    budget_micro_units INTEGER NOT NULL DEFAULT 500000,
    spent_micro_units INTEGER NOT NULL DEFAULT 0,
    autonomy_level TEXT NOT NULL DEFAULT 'SHADOW',
    error_reason TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant_company ON agent_runs(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);

-- 2. Agent Run Steps Table (Persists every executed or proposed step for crash recovery)
CREATE TABLE IF NOT EXISTS agent_run_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSON NOT NULL,
    result JSON,
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

-- 3. Agent Certifications Table (Certification status gate: uncertified agents cap at SHADOW)
CREATE TABLE IF NOT EXISTS agent_certifications (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    certification_status TEXT NOT NULL DEFAULT 'UNCERTIFIED',
    qualification_task_id TEXT,
    test_records JSON NOT NULL DEFAULT '[]',
    certified_at REAL,
    certified_by TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_certifications_agent_tenant ON agent_certifications(agent_id, tenant_id);

-- 4. Calendar Events Table (RFC 5545 calendar entries)
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
