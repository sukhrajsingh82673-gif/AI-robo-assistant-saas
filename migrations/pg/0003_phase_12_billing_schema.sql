-- Phase 12: Commercial SaaS Lifecycle, Entitlements & Multi-Gateway Billing Schema Migration
-- Neon Serverless PostgreSQL 16 Migration for Subscription State Machine, Webhook Ledger, and Invoices

CREATE TABLE IF NOT EXISTS tenant_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'STARTER',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    current_period_start REAL NOT NULL,
    current_period_end REAL NOT NULL,
    grace_period_end REAL,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    payment_provider TEXT NOT NULL DEFAULT 'internal',
    provider_customer_id TEXT,
    provider_subscription_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata JSONB,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tenant_sub_tenant ON tenant_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_sub_status ON tenant_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_tenant_sub_tier ON tenant_subscriptions(tier);

CREATE TABLE IF NOT EXISTS billing_webhook_events (
    event_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB,
    processed_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROCESSED',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_bwh_provider_event ON billing_webhook_events(provider, event_id);
CREATE INDEX IF NOT EXISTS idx_bwh_status ON billing_webhook_events(status);

CREATE TABLE IF NOT EXISTS tenant_invoices (
    invoice_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subscription_id TEXT,
    amount_due_usd REAL NOT NULL,
    amount_paid_usd REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'PAID',
    period_start REAL NOT NULL,
    period_end REAL NOT NULL,
    line_items JSONB,
    created_at REAL NOT NULL,
    paid_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoice_tenant ON tenant_invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON tenant_invoices(status);
