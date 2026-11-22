-- PostgreSQL 16 Always-On Baseline Migration 0018

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
    next_retry_at DOUBLE PRECISION NOT NULL,
    locked_by TEXT,
    locked_until DOUBLE PRECISION,
    dispatched_at DOUBLE PRECISION,
    created_at DOUBLE PRECISION NOT NULL,
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
    next_run_at DOUBLE PRECISION NOT NULL,
    last_run_at DOUBLE PRECISION,
    max_run_seconds INTEGER NOT NULL DEFAULT 300,
    catchup_policy TEXT NOT NULL DEFAULT 'RUN_ONCE' CHECK (catchup_policy IN ('RUN_ONCE', 'SKIP_MISSED')),
    lease_owner TEXT,
    lease_heartbeat_at DOUBLE PRECISION,
    lease_expires_at DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'IDLE' CHECK (status IN ('IDLE', 'RUNNING', 'FAILED', 'PAUSED')),
    created_at DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_scheduled_jobs_tenant_name UNIQUE (tenant_id, company_id, name)
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_next_run ON scheduled_jobs(status, next_run_at, lease_expires_at);

CREATE TABLE IF NOT EXISTS scheduler_leader_leases (
    lease_key TEXT PRIMARY KEY,
    leader_node_id TEXT NOT NULL,
    heartbeat_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);

-- Upgrade existing tables from single-precision float to 64-bit double precision
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'outbox_events' AND column_name = 'next_retry_at' AND data_type = 'real'
    ) THEN
        ALTER TABLE outbox_events ALTER COLUMN next_retry_at TYPE DOUBLE PRECISION;
        ALTER TABLE outbox_events ALTER COLUMN created_at TYPE DOUBLE PRECISION;
        ALTER TABLE outbox_events ALTER COLUMN locked_until TYPE DOUBLE PRECISION;
        ALTER TABLE outbox_events ALTER COLUMN dispatched_at TYPE DOUBLE PRECISION;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'scheduled_jobs' AND column_name = 'next_run_at' AND data_type = 'real'
    ) THEN
        ALTER TABLE scheduled_jobs ALTER COLUMN next_run_at TYPE DOUBLE PRECISION;
        ALTER TABLE scheduled_jobs ALTER COLUMN last_run_at TYPE DOUBLE PRECISION;
        ALTER TABLE scheduled_jobs ALTER COLUMN created_at TYPE DOUBLE PRECISION;
    END IF;
END $$;

-- PostgreSQL 16 Multi-Tenant Row Level Security (RLS)
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['outbox_events', 'scheduled_jobs'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t||'_tenant_isolation', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (' ||
      '  (tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), ''''))' ||
      '  AND (company_id = NULLIF(current_setting(''zonata.company_id'', true), ''''))' ||
      ') WITH CHECK (' ||
      '  (tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), ''''))' ||
      '  AND (company_id = NULLIF(current_setting(''zonata.company_id'', true), ''''))' ||
      ')', t||'_tenant_isolation', t
    );
  END LOOP;
END $$;
