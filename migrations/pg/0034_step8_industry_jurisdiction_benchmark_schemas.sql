-- Migration 0034: Step 8 Industry Depth, Jurisdiction Packs, and Benchmark Schemas
-- Additive migration creating isolated schemas: industries, jurisdictions, benchmarks.
-- Implements RLS and tenant/company isolation per Rules 41, 67, 74.

CREATE SCHEMA IF NOT EXISTS industries;
CREATE SCHEMA IF NOT EXISTS jurisdictions;
CREATE SCHEMA IF NOT EXISTS benchmarks;

-- ============================================================================
-- 1. INDUSTRIES SCHEMA
-- ============================================================================
CREATE TABLE IF NOT EXISTS industries.industry_overlays (
    industry_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    tier VARCHAR(8) NOT NULL DEFAULT 'T0',
    content_digest VARCHAR(64) NOT NULL,
    overlay_data JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE industries.industry_overlays ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_industry_overlays ON industries.industry_overlays
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS industries.overlay_expert_reviews (
    review_id VARCHAR(64) PRIMARY KEY,
    industry_id VARCHAR(64) NOT NULL REFERENCES industries.industry_overlays(industry_id) ON DELETE CASCADE,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    reviewer_id VARCHAR(64) NOT NULL,
    reviewer_name TEXT NOT NULL,
    stated_credentials TEXT NOT NULL,
    checklist_json JSONB NOT NULL,
    conflict_declaration TEXT NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE industries.overlay_expert_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_overlay_reviews ON industries.overlay_expert_reviews
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- 2. JURISDICTIONS SCHEMA
-- ============================================================================
CREATE TABLE IF NOT EXISTS jurisdictions.jurisdiction_packs (
    jurisdiction_code VARCHAR(32) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    country_name TEXT NOT NULL,
    regime_type VARCHAR(32) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    pack_data JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE jurisdictions.jurisdiction_packs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_jurisdiction_packs ON jurisdictions.jurisdiction_packs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- 3. BENCHMARKS SCHEMA (Vault & Claims)
-- ============================================================================
CREATE TABLE IF NOT EXISTS benchmarks.benchmark_vault (
    task_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    department VARCHAR(64) NOT NULL,
    sector_overlay VARCHAR(64),
    jurisdiction VARCHAR(32),
    encrypted_task_prompt TEXT NOT NULL,
    encrypted_reference_truth TEXT NOT NULL,
    encrypted_grader_key TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE benchmarks.benchmark_vault ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_benchmark_vault ON benchmarks.benchmark_vault
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS benchmarks.benchmark_claims (
    claim_id VARCHAR(64) PRIMARY KEY,
    task_type VARCHAR(64) NOT NULL,
    configuration VARCHAR(16) NOT NULL,
    comparison_status VARCHAR(32) NOT NULL,
    effect_size NUMERIC(8, 4),
    confidence_interval_low NUMERIC(8, 4),
    confidence_interval_high NUMERIC(8, 4),
    critical_error_count INT NOT NULL DEFAULT 0,
    policy_violation_count INT NOT NULL DEFAULT 0,
    model_id VARCHAR(64) NOT NULL,
    prompt_spec_hash VARCHAR(64) NOT NULL,
    pre_registration_seal VARCHAR(64) NOT NULL,
    measured_date DATE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE benchmarks.benchmark_claims ENABLE ROW LEVEL SECURITY;

-- Claims are public/read-only for certified statements
CREATE POLICY public_read_benchmark_claims ON benchmarks.benchmark_claims
    FOR SELECT USING (true);
