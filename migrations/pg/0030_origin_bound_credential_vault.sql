-- PostgreSQL 16 Schema for Origin-Bound Enterprise Secret Vault (OpenCode Step 3D)

CREATE TABLE IF NOT EXISTS enterprise_secret_vault (
    secret_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    origin TEXT NOT NULL,
    username_ciphertext TEXT,
    secret_ciphertext TEXT NOT NULL,
    secret_type TEXT NOT NULL,
    privilege_level TEXT NOT NULL DEFAULT 'STANDARD',
    allowed_agent_ids TEXT NOT NULL DEFAULT '[]',
    allowed_roles TEXT NOT NULL DEFAULT '[]',
    created_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION,
    last_used_at DOUBLE PRECISION,
    revoked_at DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_esv_tenant_company ON enterprise_secret_vault(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_esv_origin ON enterprise_secret_vault(origin);

ALTER TABLE enterprise_secret_vault ENABLE ROW LEVEL SECURITY;
ALTER TABLE enterprise_secret_vault FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS esv_tenant_isolation ON enterprise_secret_vault;
CREATE POLICY esv_tenant_isolation ON enterprise_secret_vault
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    )
    WITH CHECK (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    );

CREATE TABLE IF NOT EXISTS enterprise_ephemeral_cookies (
    cookie_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    origin TEXT NOT NULL,
    cookie_ciphertext TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL,
    purged_at DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_eec_session ON enterprise_ephemeral_cookies(session_id, origin);

ALTER TABLE enterprise_ephemeral_cookies ENABLE ROW LEVEL SECURITY;
ALTER TABLE enterprise_ephemeral_cookies FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS eec_tenant_isolation ON enterprise_ephemeral_cookies;
CREATE POLICY eec_tenant_isolation ON enterprise_ephemeral_cookies
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    )
    WITH CHECK (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    );
