-- Settings V2 tenant-scoped keys (PostgreSQL).
--
-- The Phase 1 settings_values primary key was
-- (scope_type, scope_id, setting_key).  Department, agent and user ids are not
-- guaranteed to be globally unique, so tenant identity belongs in the key.
-- Unlike SQLite, PostgreSQL can replace the primary key in place.  If duplicate
-- rows exist across tenants, the ADD PRIMARY KEY fails loudly instead of
-- silently discarding data.

ALTER TABLE settings_values DROP CONSTRAINT IF EXISTS settings_values_pkey;
ALTER TABLE settings_values
    ADD CONSTRAINT settings_values_pkey
    PRIMARY KEY (tenant_id, scope_type, scope_id, setting_key);

-- Secret names are unique per tenant, not globally.
DROP INDEX IF EXISTS idx_secrets_scope_name;
CREATE UNIQUE INDEX IF NOT EXISTS idx_secrets_tenant_scope_name
    ON secrets (tenant_id, scope_type, scope_id, name);
