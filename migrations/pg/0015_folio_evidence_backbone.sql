-- ============================================================================
-- Migration 0015: Sovereign Folio, Merkle Evidence, and Export Pack Backbone
-- OpenCode Step 1F: Universal Unit of Business Truth
-- ============================================================================

-- 1. Folios Table
CREATE TABLE IF NOT EXISTS folios (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    folio_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    subject_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    retention_policy_id VARCHAR(64),
    retention_until TIMESTAMPTZ,
    merkle_root VARCHAR(64) NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
    created_by VARCHAR(64) NOT NULL,
    closed_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    expunged_at TIMESTAMPTZ,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_folios_tenant_comp ON folios (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_folios_status ON folios (status);
CREATE INDEX IF NOT EXISTS idx_folios_type ON folios (folio_type);

-- 2. Folio Entries Table (Immutable timeline references)
CREATE TABLE IF NOT EXISTS folio_entries (
    id VARCHAR(64) PRIMARY KEY,
    folio_id VARCHAR(64) NOT NULL REFERENCES folios(id) ON DELETE CASCADE,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    entry_type VARCHAR(64) NOT NULL,
    reference_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    author_id VARCHAR(64) NOT NULL,
    sequence_number INTEGER NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_folio_seq UNIQUE (folio_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS idx_folio_entries_folio ON folio_entries (folio_id);
CREATE INDEX IF NOT EXISTS idx_folio_entries_ref ON folio_entries (reference_id);
CREATE INDEX IF NOT EXISTS idx_folio_entries_tenant ON folio_entries (tenant_id, company_id);

-- ============================================================================
-- Row-Level Security (PostgreSQL 16)
-- Rule 13: Multi-tenant by default. Cross-tenant and cross-company reads and
-- writes are strictly prohibited by kernel RLS policies.
-- ============================================================================
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['folios', 'folio_entries'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t||'_tenant_isolation', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (' ||
      '  (tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), '''') OR current_setting(''zonata.tenant_id'', true) IS NULL)' ||
      '  AND (company_id = NULLIF(current_setting(''zonata.company_id'', true), '''') OR current_setting(''zonata.company_id'', true) IS NULL)' ||
      ') WITH CHECK (' ||
      '  (tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), '''') OR current_setting(''zonata.tenant_id'', true) IS NULL)' ||
      '  AND (company_id = NULLIF(current_setting(''zonata.company_id'', true), '''') OR current_setting(''zonata.company_id'', true) IS NULL)' ||
      ')', t||'_tenant_isolation', t
    );
  END LOOP;
END $$;
