-- Migration 0035: Step 9 Product Readiness Schemas
-- Additive migration creating isolated schemas: product, billing, marketplace.
-- Implements RLS, tenant isolation, and cryptographic chaining per Rules 77, 78, 79, 81.

CREATE SCHEMA IF NOT EXISTS product;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS marketplace;

-- ============================================================================
-- 1. BILLING SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS billing.plans (
    plan_id VARCHAR(64) PRIMARY KEY,
    code VARCHAR(64) UNIQUE NOT NULL,
    name TEXT NOT NULL,
    tier VARCHAR(32) NOT NULL DEFAULT 'starter', -- free, starter, team, enterprise
    base_fee_cents BIGINT NOT NULL DEFAULT 0,
    included_tokens BIGINT NOT NULL DEFAULT 0,
    overage_rate_cents_per_million BIGINT NOT NULL DEFAULT 0,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing.subscriptions (
    subscription_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    plan_id VARCHAR(64) NOT NULL REFERENCES billing.plans(plan_id),
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- active, past_due, canceled, paused
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    grace_period_until TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE billing.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_subscriptions ON billing.subscriptions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS billing.usage_ledger (
    entry_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    subscription_id VARCHAR(64) NOT NULL REFERENCES billing.subscriptions(subscription_id),
    metric VARCHAR(64) NOT NULL, -- ai_tokens, api_calls, storage_mb, active_seats
    quantity BIGINT NOT NULL,
    unit VARCHAR(32) NOT NULL,
    amount_cents BIGINT NOT NULL DEFAULT 0,
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    prev_hash VARCHAR(64) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE billing.usage_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_usage_ledger ON billing.usage_ledger
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS billing.invoices (
    invoice_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    subscription_id VARCHAR(64) NOT NULL REFERENCES billing.subscriptions(subscription_id),
    invoice_number VARCHAR(64) UNIQUE NOT NULL,
    subtotal_cents BIGINT NOT NULL,
    tax_cents BIGINT NOT NULL DEFAULT 0,
    total_cents BIGINT NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL DEFAULT 'draft', -- draft, open, paid, void, uncollectible
    pdf_url TEXT,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_at TIMESTAMPTZ NOT NULL,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE billing.invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_invoices ON billing.invoices
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS billing.cost_caps (
    cap_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) UNIQUE NOT NULL,
    hard_cap_cents BIGINT NOT NULL DEFAULT 100000, -- default $1000.00
    soft_cap_cents BIGINT NOT NULL DEFAULT 80000,  -- default $800.00 (80%)
    current_spend_cents BIGINT NOT NULL DEFAULT 0,
    period VARCHAR(32) NOT NULL DEFAULT 'monthly',
    notification_email TEXT,
    auto_halt_active BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE billing.cost_caps ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_cost_caps ON billing.cost_caps
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- 2. PRODUCT SCHEMA (Platform Core & Configuration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS product.tenants_extended (
    tenant_id VARCHAR(64) PRIMARY KEY,
    slug VARCHAR(64) UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    data_residency_region VARCHAR(32) NOT NULL DEFAULT 'eu-central-1',
    onboarding_status VARCHAR(32) NOT NULL DEFAULT 'pending', -- pending, in_progress, completed
    switching_status VARCHAR(32) NOT NULL DEFAULT 'standard', -- standard, exporting, transferred
    telemetry_opt_in BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product.feature_flags (
    flag_id VARCHAR(64) PRIMARY KEY,
    flag_key VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64), -- NULL indicates global platform default
    enabled BOOLEAN NOT NULL DEFAULT false,
    variant TEXT,
    targeting_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_kill_switched BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_flag_tenant UNIQUE (flag_key, tenant_id)
);

CREATE TABLE IF NOT EXISTS product.api_keys (
    key_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    name TEXT NOT NULL,
    key_prefix VARCHAR(16) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    rate_limit_rps INTEGER NOT NULL DEFAULT 50,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE product.api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_api_keys ON product.api_keys
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS product.webhooks (
    webhook_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    url TEXT NOT NULL,
    event_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    secret_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- active, disabled, failing
    failure_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE product.webhooks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_webhooks ON product.webhooks
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- 3. MARKETPLACE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS marketplace.packages (
    package_id VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    publisher TEXT NOT NULL,
    manifest_json JSONB NOT NULL,
    capabilities_declared JSONB NOT NULL DEFAULT '[]'::jsonb,
    review_status VARCHAR(32) NOT NULL DEFAULT 'pending', -- pending, approved, rejected, revoked
    is_active BOOLEAN NOT NULL DEFAULT true,
    installed_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (package_id, version)
);

CREATE TABLE IF NOT EXISTS marketplace.installations (
    installation_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    package_id VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    capabilities_granted JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'installed', -- installed, paused, revoked
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT fk_package FOREIGN KEY (package_id, version) REFERENCES marketplace.packages(package_id, version)
);

ALTER TABLE marketplace.installations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_installations ON marketplace.installations
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- Seed canonical plans
INSERT INTO billing.plans (plan_id, code, name, tier, base_fee_cents, included_tokens, overage_rate_cents_per_million, currency, features)
VALUES 
    ('plan_free_v1', 'community', 'Community Free', 'free', 0, 100000, 0, 'USD', '{"api_rate_limit_rps": 5, "custom_webhooks": false, "marketplace_install": true}'::jsonb),
    ('plan_team_v1', 'team', 'Team Standard', 'team', 9900, 5000000, 300, 'USD', '{"api_rate_limit_rps": 50, "custom_webhooks": true, "marketplace_install": true}'::jsonb),
    ('plan_enterprise_v1', 'enterprise', 'Enterprise Tier', 'enterprise', 49900, 50000000, 150, 'USD', '{"api_rate_limit_rps": 500, "custom_webhooks": true, "marketplace_install": true, "sso": true}'::jsonb)
ON CONFLICT (plan_id) DO NOTHING;
