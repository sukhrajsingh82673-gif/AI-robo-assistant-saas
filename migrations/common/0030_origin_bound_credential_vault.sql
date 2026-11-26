-- SQLite / Common Schema for Origin-Bound Enterprise Secret Vault (OpenCode Step 3D)

CREATE TABLE IF NOT EXISTS enterprise_secret_vault (
    secret_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    origin TEXT NOT NULL,
    username_ciphertext TEXT,
    secret_ciphertext TEXT NOT NULL,
    secret_type TEXT NOT NULL, -- PASSWORD, API_KEY, COOKIE_JAR, OAUTH_TOKEN, SSH_KEY
    privilege_level TEXT NOT NULL DEFAULT 'STANDARD', -- STANDARD, HIGH_PRIVILEGE
    allowed_agent_ids TEXT NOT NULL DEFAULT '[]', -- JSON Array
    allowed_roles TEXT NOT NULL DEFAULT '[]', -- JSON Array
    created_at REAL NOT NULL,
    expires_at REAL,
    last_used_at REAL,
    revoked_at REAL
);

CREATE INDEX IF NOT EXISTS idx_esv_tenant_company ON enterprise_secret_vault(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_esv_origin ON enterprise_secret_vault(origin);

CREATE TABLE IF NOT EXISTS enterprise_ephemeral_cookies (
    cookie_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    origin TEXT NOT NULL,
    cookie_ciphertext TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    purged_at REAL
);

CREATE INDEX IF NOT EXISTS idx_eec_session ON enterprise_ephemeral_cookies(session_id, origin);
