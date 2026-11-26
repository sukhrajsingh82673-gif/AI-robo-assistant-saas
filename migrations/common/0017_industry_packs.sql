-- Common SQLite/PostgreSQL Migration 0017: Industry Pack Framework Tables

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
    UNIQUE (tenant_id, company_id, pack_id)
);

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
    UNIQUE (tenant_id, company_id, folio_type)
);
