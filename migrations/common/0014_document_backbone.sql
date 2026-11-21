-- ============================================================================
-- Migration 0014 (Common / SQLite): Sovereign Document Backbone
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    folio_id TEXT,
    name TEXT NOT NULL,
    current_version_id TEXT,
    status TEXT NOT NULL DEFAULT 'RECEIVED',
    sensitivity_level TEXT NOT NULL DEFAULT 'INTERNAL',
    regime_tags TEXT NOT NULL DEFAULT '[]',
    legal_hold INTEGER NOT NULL DEFAULT 0,
    retention_policy_id TEXT,
    retention_until REAL,
    disposed_at REAL,
    tombstone INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_tenant_comp ON documents (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);

CREATE TABLE IF NOT EXISTS blobs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    storage_provider TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 1,
    dek_wrapped TEXT,
    encryption_iv TEXT,
    ref_count INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    CONSTRAINT uq_tenant_blob_sha UNIQUE (tenant_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_blobs_sha256 ON blobs (sha256);

CREATE TABLE IF NOT EXISTS document_versions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    blob_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    change_reason TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    evidence_id TEXT,
    created_at REAL NOT NULL,
    CONSTRAINT uq_doc_version UNIQUE (document_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_doc ON document_versions (document_id);

CREATE TABLE IF NOT EXISTS document_events (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    actor_id TEXT NOT NULL,
    evidence_id TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_doc_events_doc ON document_events (document_id);

CREATE TABLE IF NOT EXISTS classifications (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    method TEXT NOT NULL,
    confidence REAL NOT NULL,
    attributes TEXT NOT NULL DEFAULT '{}',
    classified_by TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'APPROVED',
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_classifications_doc ON classifications (document_id);

CREATE TABLE IF NOT EXISTS extractions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    raw_text TEXT,
    trust TEXT NOT NULL DEFAULT 'UNTRUSTED',
    dlp_labels TEXT NOT NULL DEFAULT '[]',
    provenance TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_extractions_doc ON extractions (document_id);

CREATE TABLE IF NOT EXISTS retention_policies (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    trigger_event TEXT NOT NULL DEFAULT 'CREATED',
    jurisdiction TEXT NOT NULL DEFAULT 'GLOBAL',
    worm_required INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS legal_holds (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    matter_id TEXT,
    applied_by TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    applied_at REAL NOT NULL,
    released_at REAL,
    released_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_legal_holds_doc ON legal_holds (document_id);

CREATE TABLE IF NOT EXISTS access_grants (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    grantee_type TEXT NOT NULL,
    grantee_id TEXT NOT NULL,
    permission TEXT NOT NULL DEFAULT 'READ',
    granted_by TEXT NOT NULL,
    granted_at REAL NOT NULL,
    revoked_at REAL
);

CREATE INDEX IF NOT EXISTS idx_access_grants_doc ON access_grants (document_id);

CREATE TABLE IF NOT EXISTS share_links (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL,
    created_by TEXT NOT NULL,
    revoked_at REAL,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_share_links_hash ON share_links (token_hash);
