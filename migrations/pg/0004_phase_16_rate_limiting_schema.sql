-- ==============================================================================
-- Migration: 0004_phase_16_rate_limiting_schema.sql
-- Description: PostgreSQL multi-tenant rate limits, fairness windows, and distributed concurrency leases
-- Phase: 16 (Rate Limiting, Abuse Prevention & Tenant Fairness)
-- ==============================================================================

-- 1. Distributed Tenant Rate Limits & Sliding Windows
CREATE TABLE IF NOT EXISTS tenant_rate_limits (
    rate_key TEXT NOT NULL,
    attempt_timestamp DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_key ON tenant_rate_limits(rate_key, attempt_timestamp);
CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_ts ON tenant_rate_limits(attempt_timestamp);

-- 2. Distributed Tenant Concurrency Leases
CREATE TABLE IF NOT EXISTS tenant_concurrency_leases (
    lease_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    lease_type TEXT NOT NULL, -- WORKFLOW, AGENT_MISSION, AI_GENERATION
    acquired_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_leases_tenant ON tenant_concurrency_leases(tenant_id, expires_at);
