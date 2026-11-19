-- Phase 11: Governance, Economic Command & Cryptographic Approvals Schema Migration
-- Authoritative schema update for AI CEO, Swarm, Budget Ceilings, Nonces, and Vector Clock Memory

ALTER TABLE enterprise_budgets ADD COLUMN IF NOT EXISTS reserved_usd REAL NOT NULL DEFAULT 0.0;
ALTER TABLE enterprise_budgets ADD COLUMN IF NOT EXISTS allocated_tokens BIGINT NOT NULL DEFAULT 0;
ALTER TABLE enterprise_budgets ADD COLUMN IF NOT EXISTS spent_tokens BIGINT NOT NULL DEFAULT 0;
ALTER TABLE enterprise_budgets ADD COLUMN IF NOT EXISTS reserved_tokens BIGINT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS enterprise_budget_reservations (
    reservation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    reserved_usd REAL NOT NULL DEFAULT 0.0,
    reserved_tokens BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'RESERVED',
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    settled_at REAL,
    actual_usd REAL DEFAULT 0.0,
    actual_tokens BIGINT DEFAULT 0,
    metadata JSONB,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_budget_res_tenant ON enterprise_budget_reservations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_budget_res_entity ON enterprise_budget_reservations(entity_id);
CREATE INDEX IF NOT EXISTS idx_budget_res_status ON enterprise_budget_reservations(status);

CREATE TABLE IF NOT EXISTS action_approval_nonces (
    nonce TEXT PRIMARY KEY,
    approval_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    action_digest TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    approver_role TEXT NOT NULL,
    signature TEXT NOT NULL,
    risk_class TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    consumed_at REAL,
    consumed_by_action_id TEXT,
    metadata JSONB,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_appr_nonce_tenant ON action_approval_nonces(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appr_nonce_status ON action_approval_nonces(status);
CREATE INDEX IF NOT EXISTS idx_appr_nonce_digest ON action_approval_nonces(action_digest);
