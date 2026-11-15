-- ============================================================================
-- ZONATA Company Setup — Stage 1 schema (additive, Neon Postgres safe)
--
-- Every statement is idempotent. No existing column is dropped or rewritten;
-- the only data change normalises the legacy ATTENTION status and backfills
-- updated_at. The reverse migration lives in
-- migrations/rollback/pg/0008_company_setup_rollback.sql and is never applied
-- automatically.
-- ============================================================================

-- 1. Company record fields -------------------------------------------------
ALTER TABLE companies ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS owner_name TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS owner_email TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS owner_role TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS created_by TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS updated_at REAL;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS website TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS business_model TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS revenue_amount REAL;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS revenue_currency TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS revenue_period TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS readiness_score REAL;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS deleted_at REAL;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS deleted_by TEXT;

UPDATE companies SET updated_at = created_at WHERE updated_at IS NULL;
UPDATE companies SET status = 'NEEDS_ATTENTION' WHERE status = 'ATTENTION';

CREATE INDEX IF NOT EXISTS idx_companies_tenant_status ON companies(tenant_id, status);

-- 2. Build / onboarding runs ----------------------------------------------
CREATE TABLE IF NOT EXISTS company_build_runs (
    build_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    run_type TEXT NOT NULL DEFAULT 'BUILD',
    workflow_id TEXT,
    phase TEXT NOT NULL DEFAULT 'INTAKE',
    phase_state TEXT NOT NULL DEFAULT 'PENDING',
    progress REAL NOT NULL DEFAULT 0.0,
    estimate_min_days INTEGER NOT NULL DEFAULT 1,
    estimate_max_days INTEGER NOT NULL DEFAULT 3,
    started_at REAL,
    finished_at REAL,
    failure_reason TEXT,
    log JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_company_build_runs_company ON company_build_runs(company_id);

-- 3. Files, legal pack ----------------------------------------------------
CREATE TABLE IF NOT EXISTS company_files (
    file_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'DOCUMENT',
    filename TEXT NOT NULL,
    mime TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    storage_key TEXT,
    sha256 TEXT,
    scan_status TEXT NOT NULL DEFAULT 'UNSCANNED',
    uploaded_by TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_company_files_company ON company_files(company_id);

CREATE TABLE IF NOT EXISTS company_legal_items (
    item_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    authority TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    instructions TEXT,
    draft_disclaimer TEXT NOT NULL DEFAULT 'Draft: verify with a qualified professional',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_company_legal_items_company ON company_legal_items(company_id);

-- 4. Drafts and per-company admin allow-list ------------------------------
CREATE TABLE IF NOT EXISTS company_drafts (
    draft_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    user_id TEXT NOT NULL,
    company_type TEXT,
    payload JSON NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_company_drafts_tenant ON company_drafts(tenant_id, user_id);

CREATE TABLE IF NOT EXISTS company_admin_grants (
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (tenant_id, company_id, user_id)
);

-- 5. Protected deletion ---------------------------------------------------
CREATE TABLE IF NOT EXISTS company_deletion_requests (
    request_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'AWAITING_CONFIRMATION',
    steps_done JSON,
    removal_summary JSON,
    export_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    export_parts INTEGER NOT NULL DEFAULT 0,
    export_ref TEXT,
    email_status TEXT NOT NULL DEFAULT 'NOT_SENT',
    download_confirmed_at REAL,
    purge_after REAL,
    requested_by TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_company_deletion_requests_company ON company_deletion_requests(company_id);

-- 6. Audit trail ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_audit_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    detail JSON,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_company_audit_events_company ON company_audit_events(company_id, created_at);
CREATE INDEX IF NOT EXISTS idx_company_audit_events_tenant ON company_audit_events(tenant_id, created_at);

-- 7. Connection metadata (columns on the existing table) ------------------
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS provider_id TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS scope JSON;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS last_check_at REAL;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS secret_ref TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS verified_at REAL;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS verification_method TEXT;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS skipped INTEGER DEFAULT 0;
ALTER TABLE external_connections ADD COLUMN IF NOT EXISTS skip_reason TEXT;
