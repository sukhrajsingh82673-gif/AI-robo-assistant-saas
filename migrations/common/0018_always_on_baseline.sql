-- Common SQLite/PostgreSQL Migration 0018: Always-On Baseline

CREATE TABLE IF NOT EXISTS outbox_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'DISPATCHED', 'FAILED', 'DEAD_LETTER')),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_error TEXT,
    next_retry_at REAL NOT NULL,
    locked_by TEXT,
    locked_until REAL,
    dispatched_at REAL,
    created_at REAL NOT NULL,
    CONSTRAINT uq_outbox_tenant_idempotency UNIQUE (tenant_id, company_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_outbox_drain ON outbox_events(status, next_retry_at, locked_until);
CREATE INDEX IF NOT EXISTS idx_outbox_tenant_company ON outbox_events(tenant_id, company_id);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    job_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    cron_or_interval_seconds INTEGER NOT NULL,
    next_run_at REAL NOT NULL,
    last_run_at REAL,
    max_run_seconds INTEGER NOT NULL DEFAULT 300,
    catchup_policy TEXT NOT NULL DEFAULT 'RUN_ONCE' CHECK (catchup_policy IN ('RUN_ONCE', 'SKIP_MISSED')),
    lease_owner TEXT,
    lease_heartbeat_at REAL,
    lease_expires_at REAL,
    status TEXT NOT NULL DEFAULT 'IDLE' CHECK (status IN ('IDLE', 'RUNNING', 'FAILED', 'PAUSED')),
    created_at REAL NOT NULL,
    CONSTRAINT uq_scheduled_jobs_tenant_name UNIQUE (tenant_id, company_id, name)
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_next_run ON scheduled_jobs(status, next_run_at, lease_expires_at);

CREATE TABLE IF NOT EXISTS scheduler_leader_leases (
    lease_key TEXT PRIMARY KEY,
    leader_node_id TEXT NOT NULL,
    heartbeat_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
