-- ============================================================================
-- Migration 0015 (Common / SQLite): Sovereign Folio Backbone
-- ============================================================================

CREATE TABLE IF NOT EXISTS folios (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    folio_type TEXT NOT NULL,
    title TEXT NOT NULL,
    subject_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    retention_policy_id TEXT,
    retention_until REAL,
    merkle_root TEXT NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
    created_by TEXT NOT NULL,
    closed_at REAL,
    archived_at REAL,
    expunged_at REAL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_folios_tenant_comp ON folios (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_folios_status ON folios (status);
CREATE INDEX IF NOT EXISTS idx_folios_type ON folios (folio_type);

CREATE TABLE IF NOT EXISTS folio_entries (
    id TEXT PRIMARY KEY,
    folio_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    title TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    author_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    entry_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    CONSTRAINT uq_folio_seq UNIQUE (folio_id, sequence_number),
    FOREIGN KEY (folio_id) REFERENCES folios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_folio_entries_folio ON folio_entries (folio_id);
CREATE INDEX IF NOT EXISTS idx_folio_entries_ref ON folio_entries (reference_id);
