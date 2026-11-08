-- Settings V2 canonical schema (portable SQLite/PostgreSQL subset).
-- The migration runner executes this file statement by statement.  Keep each
-- statement free of dialect-specific procedural bodies; append-only triggers
-- and rules live in migrations/sqlite and migrations/pg.

CREATE TABLE IF NOT EXISTS settings_values (
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    locked INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (scope_type, scope_id, setting_key)
);

CREATE INDEX IF NOT EXISTS idx_settings_values_tenant ON settings_values (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_settings_values_key ON settings_values (setting_key);
CREATE INDEX IF NOT EXISTS idx_settings_values_scope ON settings_values (scope_type, scope_id);

CREATE TABLE IF NOT EXISTS settings_audit (
    audit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    actor TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'human',
    reason TEXT,
    request_id TEXT,
    ip_address TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'APPROVED',
    previous_hash TEXT,
    entry_hash TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_settings_audit_tenant_time ON settings_audit (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_settings_audit_company_time ON settings_audit (tenant_id, company_id, created_at);
CREATE INDEX IF NOT EXISTS idx_settings_audit_key ON settings_audit (tenant_id, setting_key);

CREATE TABLE IF NOT EXISTS secrets (
    secret_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    name TEXT NOT NULL,
    ciphertext TEXT NOT NULL,
    nonce TEXT NOT NULL,
    key_id TEXT NOT NULL,
    last4 TEXT NOT NULL DEFAULT '',
    created_by TEXT,
    created_at REAL NOT NULL,
    rotated_at REAL,
    last_used_at REAL,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_secrets_scope_name ON secrets (scope_type, scope_id, name);
CREATE INDEX IF NOT EXISTS idx_secrets_tenant ON secrets (tenant_id, company_id);

CREATE TABLE IF NOT EXISTS settings_presets (
    preset_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    values_json TEXT NOT NULL,
    created_by TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_settings_presets_tenant ON settings_presets (tenant_id, name);

CREATE TABLE IF NOT EXISTS roles (
    role_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id TEXT PRIMARY KEY,
    description TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_company_roles (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (user_id, company_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_company_roles_company ON user_company_roles (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_user_company_roles_user ON user_company_roles (tenant_id, user_id);

CREATE TABLE IF NOT EXISTS settings_approvals (
    approval_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    proposed_value TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'human',
    risk TEXT NOT NULL DEFAULT 'MEDIUM',
    status TEXT NOT NULL DEFAULT 'PENDING',
    required_approvals INTEGER NOT NULL DEFAULT 1,
    approvals_json TEXT NOT NULL DEFAULT '[]',
    reason TEXT,
    decision_reason TEXT,
    created_at REAL NOT NULL,
    expires_at REAL,
    resolved_at REAL,
    resolved_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_settings_approvals_tenant_status ON settings_approvals (tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_settings_approvals_key ON settings_approvals (tenant_id, setting_key);

CREATE TABLE IF NOT EXISTS settings_environments (
    environment TEXT PRIMARY KEY,
    description TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS settings_revision (
    tenant_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
);
