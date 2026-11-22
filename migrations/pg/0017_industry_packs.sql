-- PostgreSQL 16 Industry Pack Backbone Migration 0017

CREATE TABLE IF NOT EXISTS installed_industry_packs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    isic_code TEXT NOT NULL,
    raw_manifest TEXT NOT NULL,
    installed_at REAL NOT NULL,
    CONSTRAINT uq_installed_pack UNIQUE (tenant_id, company_id, pack_id)
);

CREATE INDEX IF NOT EXISTS idx_installed_industry_packs_tenant_company ON installed_industry_packs(tenant_id, company_id);

CREATE TABLE IF NOT EXISTS company_folio_types (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    folio_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    config TEXT NOT NULL,
    created_at REAL NOT NULL,
    CONSTRAINT uq_company_folio_types UNIQUE (tenant_id, company_id, folio_type)
);

CREATE INDEX IF NOT EXISTS idx_company_folio_types_tenant_company ON company_folio_types(tenant_id, company_id);

-- PostgreSQL 16 Multi-Tenant Row Level Security (RLS)
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['installed_industry_packs', 'company_folio_types'] LOOP
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
