# Phase 16: Rate Limiting & Abuse Prevention Design Specification
## URA / ZONATA — Universal AI Company Operating System

**Document Version:** 1.0  
**Phase:** Phase 16 (Rate Limiting, Abuse Prevention & Tenant Fairness)  
**Status:** **APPROVED & IMPLEMENTED**  
**Component Module:** `core/tenant_fairness.py` & `api_server.py`  

---

## 1. Architectural Strategy & Design Rationale

Modern SaaS platforms serving high-value autonomous enterprise agent workflows require deterministic rate-limiting guarantees. Simple fixed-window counters suffer from burst spikes at window boundaries (the "two-times burst" boundary defect). Token bucket algorithms require frequent atomic reads and writes of balance counters with complex concurrency coordination.

ZONATA adopts a **Sliding Window Log** algorithm backed by a high-performance relational table (`tenant_rate_limits`) with microsecond timestamp granularity. This provides:
1. **Mathematical Smoothness:** Rejections are calculated precisely against the trailing 60.0-second rolling window; no boundary bursts are possible.
2. **Multi-Instance Synchronization:** Shared across all web and worker instances connecting to the same Neon PostgreSQL database.
3. **Stateless Scalability:** Web workers maintain no sticky sessions; any node can evaluate any request with complete consistency.
4. **Resilient Fallback:** Seamless in-memory fallback ensures high-availability during database network blips.

---

## 2. Database Schema Design

### 2.1 Table: `tenant_rate_limits`
Stores individual request arrival timestamps indexed by composite lookup keys:

```sql
CREATE TABLE IF NOT EXISTS tenant_rate_limits (
    rate_key VARCHAR(128) NOT NULL,
    attempt_timestamp DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_key_time 
ON tenant_rate_limits (rate_key, attempt_timestamp);

CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_time 
ON tenant_rate_limits (attempt_timestamp);
```

### 2.2 Table: `tenant_concurrency_leases`
Coordinates distributed locks for long-running workflows, agent missions, and asynchronous processing:

```sql
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

---

## 3. Tier Matrix & Quota Specification

| Commercial Plan Tier | Requests Per Minute (RPM) | Max Concurrent Leases | Expensive AI RPM | Mutating RPM | Identity (Per-User) RPM |
|:---|:---:|:---:|:---:|:---:|:---:|
| **FREE** | 60 | 1 | 10 | 30 | 60 |
| **STARTER** | 300 | 3 | 30 | 120 | 120 |
| **PRO** | 1,200 | 10 | 60 | 300 | 300 |
| **ENTERPRISE** | 3,600 | 50 | 180 | 600 | 600 |

### 3.1 Endpoint Categorization
- **Exempt Endpoints:** Static assets (`/assets/*`, `.css`, `.js`, `.ico`), health check (`/healthz`, `/api/healthz`), readiness check (`/readyz`), metrics (`/metrics`).
- **Auth Perimeter Endpoints:**
  - Token Issuance / Login: `/api/auth/token`, `/api/auth/login` (25 req/min per IP)
  - User Registration: `/api/auth/register` (10 req/min per IP)
- **Expensive AI / Analytic Endpoints:**
  - `/api/overview/explain-variance`
  - `/api/portfolio/forecast`
  - `/api/company/simulate-workload`
  - `/api/universal-terminal/exec`
  - `/api/orchestration/step`
- **Mutating Endpoints:**
  - Any HTTP method in `["POST", "PUT", "DELETE", "PATCH"]` targeting stateful resources (e.g., `/api/departments/update`, `/api/budget/reserve`, `/api/settings/update`).

---

## 4. RFC-Compliant HTTP Response & Header Specification

When a request exceeds its allocated quota on any axis, the API server responds with **HTTP 429 Too Many Requests** and supplies standard rate-limiting headers:

| Header Name | Type | Description |
|:---|:---|:---|
| `Retry-After` | Integer (Seconds) | Time in seconds until the oldest request in the window falls outside the 60-second horizon. |
| `X-RateLimit-Limit` | Integer | Total request ceiling allocated for the violated rate-limiting axis. |
| `X-RateLimit-Remaining` | Integer | Number of requests remaining in the current window (0 on 429). |
| `X-RateLimit-Reset` | Integer (Unix Epoch) | Absolute Unix epoch timestamp when the current window fully resets. |
| `X-RateLimit-Axis` | String | Axis of violation (`IP`, `TENANT`, `IDENTITY`, `ENDPOINT`, `CONCURRENCY`). |

### 4.1 Security Invariant: Zero Cross-Tenant Leakage
Under no circumstances do HTTP 429 responses disclose neighbor tenant IDs, overall system traffic, or shared tenant resource allocations. The response payload conforms strictly to:

```json
{
  "error": "Too Many Requests",
  "detail": "Rate limit exceeded for tenant quota (60 requests/min). Try again in 14s.",
  "retry_after": 14,
  "axis": "TENANT",
  "limit": 60,
  "remaining": 0
}
```

---

## 5. Telemetry & SRE Observability

In accordance with Phase 8 SRE specifications, rate-limiting violations are recorded in Prometheus metrics exposed at `/metrics`:

```prometheus
# HELP zonata_rate_limit_exceeded_total Total rate limit rejections by axis and tenant tier
# TYPE zonata_rate_limit_exceeded_total counter
zonata_rate_limit_exceeded_total{axis="TENANT",tier="FREE"} 42
zonata_rate_limit_exceeded_total{axis="IP",tier="ANONYMOUS"} 8
zonata_rate_limit_exceeded_total{axis="ENDPOINT",tier="PRO"} 2
```

This telemetry enables alerting rules (e.g., alerting when rate-limiting rejections spike beyond baseline thresholds, indicating an ongoing DDoS attack or a misconfigured customer webhook loop).
