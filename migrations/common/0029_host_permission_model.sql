-- Common SQLite/PostgreSQL Migration 0029: Host Permission Model and Device Grants
-- OpenCode Step 3B: devices, host_grants, grant_events (append-only), host_sessions

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
    pairing_code_expires_at REAL,
    last_seen_at REAL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_devices_tenant ON devices(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_devices_owner ON devices(owner_id);

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
    valid_from REAL NOT NULL,
    valid_until REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    revoked_at REAL,
    revoked_by_principal_id TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_host_grants_dev ON host_grants(device_id, status);
CREATE INDEX IF NOT EXISTS idx_host_grants_tenant ON host_grants(tenant_id, company_id);

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
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_grant_events_dev ON grant_events(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_grant_events_tenant ON grant_events(tenant_id, timestamp);

CREATE TABLE IF NOT EXISTS host_sessions (
    session_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_sequence_no INTEGER NOT NULL DEFAULT 0,
    last_heartbeat_at REAL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_host_sessions_dev ON host_sessions(device_id, status);
CREATE INDEX IF NOT EXISTS idx_host_sessions_tenant ON host_sessions(tenant_id, company_id);
