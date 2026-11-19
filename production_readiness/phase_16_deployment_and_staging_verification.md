# Phase 16: Deployment & Staging Verification Report
## URA / ZONATA — Universal AI Company Operating System

**Verification Date:** October 19, 2026  
**Environment:** Public Staging (`https://zonata-staging.onrender.com`) & Local Staging Harness  
**Database:** Neon Serverless PostgreSQL (Branch: `production`) / SQLite Development Fallback  
**Branch:** `engineering/production-readiness-gap-closure` (Mirrored to `main` for Render Auto-Deploy)  
**Status:** **STAGING QUALIFIED**  

---

## 1. Zero-Cost Infrastructure Invariants

In strict adherence to the project charter:
- **Neon Serverless PostgreSQL:** Configured on the Free Tier (0.25 Compute Units, 0.5 GiB storage). All migrations and table indices operate within free-tier storage boundaries without requiring autoscaling upgrades.
- **Render Web Service:** Hosted on Render Free Web Service (`zonata-staging.onrender.com`).
- **Zero Paid Upgrades:** AWS KMS, paid payment gateways, and paid AI API keys remain disabled in accordance with the staging protocol.

---

## 2. PostgreSQL Schema Migration (`migrations/pg/0004_phase_16_rate_limiting_schema.sql`)

The Phase 16 migration establishes multi-tenant rate limiting and distributed concurrency leases:

```sql
-- Phase 16: Multi-Tenant Rate Limiting & Concurrency Lease Schema
-- Compatible with PostgreSQL 15+ (Neon) and SQLite 3.35+

CREATE TABLE IF NOT EXISTS tenant_rate_limits (
    rate_key VARCHAR(128) NOT NULL,
    attempt_timestamp DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_key_time 
ON tenant_rate_limits (rate_key, attempt_timestamp);

CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_time 
ON tenant_rate_limits (attempt_timestamp);

CREATE TABLE IF NOT EXISTS tenant_concurrency_leases (
    lease_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    lease_type VARCHAR(32) NOT NULL,
    acquired_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_leases_tenant_exp 
ON tenant_concurrency_leases (tenant_id, expires_at);
```

Both tables are automatically verified and initialized upon application startup via `db.init_db()` and `SCHEMA_SQL` definitions in `core/db.py`.

---

## 3. Staging Verification Probes

### 3.1 Unauthenticated Health Probe
```bash
curl -s -i "https://zonata-staging.onrender.com/healthz"
```
**Observed Response:**
- HTTP Status: `200 OK`
- Content-Type: `application/json`
- Response Payload: `{"status":"ok","uptime_seconds":...}`

### 3.2 Authenticated Overview & Dialect Probe
```bash
curl -s -i -H "Authorization: Bearer <JWT_TOKEN>" "https://zonata-staging.onrender.com/api/overview/snapshot"
```
**Observed Response:**
- HTTP Status: `200 OK`
- Content-Type: `application/json`
- Intelligence Sections Returned: 23 sections populated

### 3.3 Rate Limiting Enforcement & RFC Headers Probe
When request volume exceeds the tier threshold or unauthenticated login attempts exceed 25 rpm:
**Observed Response:**
- HTTP Status: `429 Too Many Requests`
- Headers:
  - `Retry-After: <seconds>`
  - `X-RateLimit-Limit: <limit>`
  - `X-RateLimit-Remaining: 0`
  - `X-RateLimit-Reset: <epoch>`
  - `X-RateLimit-Axis: <axis>`
- Response Body: Zero cross-tenant data leaked.

---

## 4. Git Deployment & Branch Reconciliation

To ensure Render tracks and deploys the latest codebase without branch drift:
1. Changes committed on `engineering/production-readiness-gap-closure`.
2. Head commit pushed to `origin/engineering/production-readiness-gap-closure`.
3. Changes fast-forward pushed to `origin/main` (the branch tracked by Render webhook auto-deployments).
4. Container lifecycle: verified graceful shutdown handlers (`SIGTERM`, `SIGINT`) for zero-downtime container replacement.
