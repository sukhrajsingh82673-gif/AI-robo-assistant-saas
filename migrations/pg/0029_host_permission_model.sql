-- PostgreSQL 16 Migration 0029: Host Permission Model and Device Grants
-- OpenCode Step 3B: Multi-Tenant RLS for devices, host_grants, grant_events, host_sessions

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    device_name TEXT NOT NULL,
    os_type TEXT NOT NULL,
    public_key TEXT NOT NULL,
    pairing_status TEXT NOT NULL DEFAULT 'PENDING',
    pairing_code_hash TEXT,
    pairing_code_expires_at DOUBLE PRECISION,
    last_seen_at DOUBLE PRECISION,
    created_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_devices_tenant ON devices(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_devices_owner ON devices(owner_id);

ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'devices' AND policyname = 'tenant_isolation_devices') THEN
        CREATE POLICY tenant_isolation_devices ON devices
            FOR ALL USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS host_grants (
    grant_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    allowed_apps TEXT NOT NULL DEFAULT '[]',
    allowed_folders TEXT NOT NULL DEFAULT '[]',
    allowed_domains TEXT NOT NULL DEFAULT '[]',
    allowed_actions TEXT NOT NULL DEFAULT '[]',
    created_by_principal_id TEXT NOT NULL,
    created_by_principal_type TEXT NOT NULL,
    valid_from DOUBLE PRECISION NOT NULL,
    valid_until DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    revoked_at DOUBLE PRECISION,
    revoked_by_principal_id TEXT,
    created_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_host_grants_dev ON host_grants(device_id, status);
CREATE INDEX IF NOT EXISTS idx_host_grants_tenant ON host_grants(tenant_id, company_id);

ALTER TABLE host_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE host_grants FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'host_grants' AND policyname = 'tenant_isolation_host_grants') THEN
        CREATE POLICY tenant_isolation_host_grants ON host_grants
            FOR ALL USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS grant_events (
    event_id TEXT PRIMARY KEY,
    grant_id TEXT,
    device_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_grant_events_dev ON grant_events(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_grant_events_tenant ON grant_events(tenant_id, timestamp);

ALTER TABLE grant_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE grant_events FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'grant_events' AND policyname = 'tenant_isolation_grant_events') THEN
        CREATE POLICY tenant_isolation_grant_events ON grant_events
            FOR ALL USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS host_sessions (
    session_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_sequence_no INTEGER NOT NULL DEFAULT 0,
    last_heartbeat_at DOUBLE PRECISION,
    created_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_host_sessions_dev ON host_sessions(device_id, status);
CREATE INDEX IF NOT EXISTS idx_host_sessions_tenant ON host_sessions(tenant_id, company_id);

ALTER TABLE host_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE host_sessions FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'host_sessions' AND policyname = 'tenant_isolation_host_sessions') THEN
        CREATE POLICY tenant_isolation_host_sessions ON host_sessions
            FOR ALL USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;
