-- ============================================================================
-- Migration 0014: Sovereign Document, File, Blob, and Retention Backbone
-- OpenCode Step 1E: Universal Governed Multi-Tenant Document System
-- ============================================================================

-- 1. Documents Root Table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    folio_id VARCHAR(64),
    name VARCHAR(255) NOT NULL,
    current_version_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
    sensitivity_level VARCHAR(32) NOT NULL DEFAULT 'INTERNAL',
    regime_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    retention_policy_id VARCHAR(64),
    retention_until TIMESTAMPTZ,
    disposed_at TIMESTAMPTZ,
    tombstone BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_tenant_comp ON documents (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_folio ON documents (folio_id);

-- 2. Deduplicated Content-Addressed Blobs (Deduplicated per tenant)
CREATE TABLE IF NOT EXISTS blobs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    byte_size BIGINT NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    storage_provider VARCHAR(64) NOT NULL,
    encrypted BOOLEAN NOT NULL DEFAULT TRUE,
    dek_wrapped TEXT,
    encryption_iv VARCHAR(64),
    ref_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenant_blob_sha UNIQUE (tenant_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_blobs_sha256 ON blobs (sha256);

-- 3. Immutable Document Versions
CREATE TABLE IF NOT EXISTS document_versions (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    blob_id VARCHAR(64) NOT NULL REFERENCES blobs(id),
    author_id VARCHAR(64) NOT NULL,
    change_reason TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    evidence_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_doc_version UNIQUE (document_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_doc ON document_versions (document_id);

-- 4. Append-Only Document Events
CREATE TABLE IF NOT EXISTS document_events (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor_id VARCHAR(64) NOT NULL,
    evidence_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doc_events_doc ON document_events (document_id);
CREATE INDEX IF NOT EXISTS idx_doc_events_tenant ON document_events (tenant_id, company_id);

-- 5. Classifications
CREATE TABLE IF NOT EXISTS classifications (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_type VARCHAR(64) NOT NULL,
    method VARCHAR(32) NOT NULL,
    confidence REAL NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    classified_by VARCHAR(64) NOT NULL,
    review_status VARCHAR(32) NOT NULL DEFAULT 'APPROVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_classifications_doc ON classifications (document_id);

-- 6. Extractions (with trust: UNTRUSTED, DLP labels, provenance)
CREATE TABLE IF NOT EXISTS extractions (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    raw_text TEXT,
    trust VARCHAR(32) NOT NULL DEFAULT 'UNTRUSTED',
    dlp_labels JSONB NOT NULL DEFAULT '[]'::jsonb,
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_extractions_doc ON extractions (document_id);
CREATE INDEX IF NOT EXISTS idx_extractions_fts ON extractions USING GIN (to_tsvector('english', coalesce(raw_text, '')));

-- 7. Retention Policies
CREATE TABLE IF NOT EXISTS retention_policies (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    document_type VARCHAR(64) NOT NULL,
    retention_days INTEGER NOT NULL,
    trigger_event VARCHAR(64) NOT NULL DEFAULT 'CREATED',
    jurisdiction VARCHAR(32) NOT NULL DEFAULT 'GLOBAL',
    worm_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_retention_tenant ON retention_policies (tenant_id, company_id);

-- 8. Legal Holds
CREATE TABLE IF NOT EXISTS legal_holds (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    matter_id VARCHAR(64),
    applied_by VARCHAR(64) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ,
    released_by VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_legal_holds_doc ON legal_holds (document_id);
CREATE INDEX IF NOT EXISTS idx_legal_holds_tenant ON legal_holds (tenant_id, company_id);

-- 9. Access Grants
CREATE TABLE IF NOT EXISTS access_grants (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    grantee_type VARCHAR(32) NOT NULL,
    grantee_id VARCHAR(64) NOT NULL,
    permission VARCHAR(32) NOT NULL DEFAULT 'READ',
    granted_by VARCHAR(64) NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_access_grants_doc ON access_grants (document_id);
CREATE INDEX IF NOT EXISTS idx_access_grants_tenant ON access_grants (tenant_id, grantee_id);

-- 10. Share Links
CREATE TABLE IF NOT EXISTS share_links (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    revoked_at TIMESTAMPTZ,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_share_links_hash ON share_links (token_hash);
CREATE INDEX IF NOT EXISTS idx_share_links_doc ON share_links (document_id);

-- ============================================================================
-- Row-Level Security (PostgreSQL 16)
-- Rule 13: Multi-tenant by default. Cross-tenant and cross-company reads and
-- writes are strictly prohibited by kernel RLS policies.
-- ============================================================================
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'documents', 'blobs', 'document_events', 'retention_policies',
    'legal_holds', 'access_grants', 'share_links'
  ] LOOP
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

  -- Child tables isolated via document_id join to documents
  FOREACH t IN ARRAY ARRAY['document_versions', 'classifications', 'extractions'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t||'_tenant_isolation', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (' ||
      '  EXISTS (SELECT 1 FROM documents d WHERE d.id = %I.document_id AND (' ||
      '    (d.tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), '''') OR current_setting(''zonata.tenant_id'', true) IS NULL)' ||
      '    AND (d.company_id = NULLIF(current_setting(''zonata.company_id'', true), '''') OR current_setting(''zonata.company_id'', true) IS NULL)' ||
      '  ))' ||
      ') WITH CHECK (' ||
      '  EXISTS (SELECT 1 FROM documents d WHERE d.id = %I.document_id AND (' ||
      '    (d.tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), '''') OR current_setting(''zonata.tenant_id'', true) IS NULL)' ||
      '    AND (d.company_id = NULLIF(current_setting(''zonata.company_id'', true), '''') OR current_setting(''zonata.company_id'', true) IS NULL)' ||
      '  ))' ||
      ')', t||'_tenant_isolation', t, t, t
    );
  END LOOP;
END $$;
