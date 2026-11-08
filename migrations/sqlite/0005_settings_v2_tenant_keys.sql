-- Settings V2 tenant-scoped keys (SQLite).
--
-- The Phase 1 settings_values primary key was
-- (scope_type, scope_id, setting_key).  Department, agent and user ids are not
-- guaranteed to be globally unique, so two tenants using the same id could
-- collide or read each other's value.  Tenant identity belongs in the key.
--
-- SQLite cannot alter a primary key in place, so the table is rebuilt once.
-- The migration runner records this file, so the rebuild runs exactly once.

CREATE TABLE IF NOT EXISTS settings_values_tenant_keys (
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
    PRIMARY KEY (tenant_id, scope_type, scope_id, setting_key)
);

INSERT OR IGNORE INTO settings_values_tenant_keys
    (tenant_id, company_id, scope_type, scope_id, setting_key,
     value_json, locked, version, updated_by, updated_at)
SELECT tenant_id, company_id, scope_type, scope_id, setting_key,
       value_json, locked, version, updated_by, updated_at
FROM settings_values;

DROP TABLE settings_values;

ALTER TABLE settings_values_tenant_keys RENAME TO settings_values;

CREATE INDEX IF NOT EXISTS idx_settings_values_tenant ON settings_values (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_settings_values_key ON settings_values (setting_key);
CREATE INDEX IF NOT EXISTS idx_settings_values_scope ON settings_values (scope_type, scope_id);

-- Secret names are unique per tenant, not globally.
DROP INDEX IF EXISTS idx_secrets_scope_name;
CREATE UNIQUE INDEX IF NOT EXISTS idx_secrets_tenant_scope_name
    ON secrets (tenant_id, scope_type, scope_id, name);
