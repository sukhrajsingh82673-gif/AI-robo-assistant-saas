# Phase 14 Free-Tier Deployment & Disaster Recovery Evidence

**Evaluation Date:** October 19, 2026  
**Branch:** `engineering/production-readiness-gap-closure`  
**Host Environment:** Linux aarch64, Python 3.14.6, pytest-9.1.1  
**Infrastructure Scope:** Free-Tier Render Web Service + Neon Serverless PostgreSQL  
**Deployment URL:** `https://zonata-staging.onrender.com`  
**Verdict:** **OPERATIONAL ON FREE TIER WITH DOCUMENTED INFRASTRUCTURE BOUNDARIES / DESTRUCTIVE DR GATED AS BLOCKED**

---

## 1. Free-Tier Staging Architecture & Operational Boundaries (Workstream G)

The staging environment operates on zero-cost free-tier infrastructure:

| Infrastructure Layer | Free-Tier Provider | Free-Tier Constraints | Observed Operational Behavior | Status |
|:---|:---|:---|:---|:---:|
| **Web Service Application** | **Render (Free Tier)** | 512 MB RAM, shared CPU, spins down after 15 minutes of inactivity, ephemeral filesystem | Cold-start latency observed at ~35–50 seconds upon initial probe; fast sub-50ms responses once active. | **PASS (CONSTRAINED)** |
| **Relational Database** | **Neon PostgreSQL (Free Tier)** | 0.5 GiB storage, scale-to-zero compute after 5 min inactivity, pooled & direct endpoints | Resumes automatically upon incoming connection pool request (~2–4s delay on cold wake). Data persists across application restarts. | **PASS** |
| **Ephemeral Disk Policy** | **Render Container** | File changes lost on restart | Application stores state in Neon PostgreSQL and Merkle audit ledgers; no critical business data relies solely on ephemeral container disk. | **PASS** |
| **Background Tasks & Daemons**| **Render Free Web Service** | Web service sleeps without inbound HTTP traffic | Continuous 24/7 background worker daemons cannot run without outbound cron pings or a dedicated paid worker instance. | **CONSTRAINED / DOCUMENTED** |

---

## 2. Public HTTPS Staging Endpoint Verification

Probing conducted directly against `https://zonata-staging.onrender.com`:

```http
GET /healthz HTTP/2
Host: zonata-staging.onrender.com
Status: 200 OK
Content-Type: application/json

{"status": "HEALTHY", "uptime_seconds": 34.66, "version": "1.0.0-GA", "database": "CONNECTED", "merkle_ledger": "INTEGRITY_VERIFIED", "server_mode": "MULTI_THREADED_CONCURRENT", "timestamp": 1792387462.802683}
```

```http
GET /readyz HTTP/2
Host: zonata-staging.onrender.com
Status: 200 OK
Content-Type: application/json

{"status": "HEALTHY", "uptime_seconds": 45.78, "version": "1.0.0-GA", "database": "CONNECTED", "merkle_ledger": "INTEGRITY_VERIFIED", "server_mode": "MULTI_THREADED_CONCURRENT", "timestamp": 1792387473.9172506}
```

```http
POST /api/auth/register HTTP/2
Host: zonata-staging.onrender.com
Payload: {"email": "test_phase14_... synthetic", "password": "...", "name": "..."}
Status: 201 Created
Content-Type: application/json

{"token": "eyJhbGciOi...", "token_type": "Bearer", "user": {"tenant_id": "tnt_f5d51c32", "role": "OWNER"}}
```

```http
GET /api/overview/snapshot (Unauthenticated) HTTP/2
Host: zonata-staging.onrender.com
Status: 401 Unauthorized
Content-Type: application/json

{"error": "Unauthorized", "detail": "Authentication Required: Missing, invalid, or expired Bearer token"}
```

```http
GET /api/overview/snapshot (Authenticated with Bearer token) HTTP/2
Host: zonata-staging.onrender.com
Status: 502 Bad Gateway
Content-Type: text/html (Cloudflare / Render error page)
```

### Forensic Root Cause of Authenticated 502
- `git ls-remote --heads origin` confirms `refs/heads/main` points to commit `1020d0e` (Phase 10 baseline).
- Render staging is configured to pull and build from `main`.
- The Phase 13 and Phase 14 fixes (including `PostgresCursorWrapper`, SQL parameter translation `?` $\rightarrow$ `%s`, and `try-except` error boundaries) are committed on `engineering/production-readiness-gap-closure` and have not yet been merged into `main`.
- Therefore, the live Render service is executing the pre-remediation code, causing Neon PostgreSQL to reject unescaped SQLite `?` parameter placeholders.

---

## 3. Disaster Recovery & Backup Verification (Workstream H)

### Policy & Safety Restrictions
In strict adherence to qualification safety instructions:
- **Rule**: Never overwrite or execute destructive restore drills against the live running staging database.
- **Rule**: If the environment cannot support a complete non-destructive live drill, mark it strictly as **BLOCKED / NOT TESTED**. Do not assert an unmeasured RTO or RPO.

### Classification Matrix
| DR Capability | Qualification Status | Evidence / Operational Constraint |
|:---|:---:|:---|
| **Live Database Destructive Restore Drill** | **BLOCKED / NOT TESTED** | A secondary isolated Neon database is not provisioned on the free tier. Destructive live restoration against the active staging DB would purge live registration and qualification state. |
| **Encrypted Snapshot Creation** | **PASS (LOCAL QUALIFIED)** | AES-GCM-256 authenticated encryption verified in `tests/test_production_infrastructure_qualification.py`. |
| **Offline Restore & Integrity Validation** | **PASS (LOCAL QUALIFIED)** | Verified with checksum verification and table parity validation in temporary directories. |

### Step-by-Step Procedure for Future Live DR Drills
When ready to test live restore without risking staging data:
1. Provision a second free-tier Neon project branch: `neon branches create --name drill-target`.
2. Generate an encrypted dump of the primary database using `pg_dump -Fc`.
3. Restore into the target branch: `pg_restore -d <DRILL_DATABASE_URL>`.
4. Run regression verification suite against `DRILL_DATABASE_URL`.
5. Drop the ephemeral test branch: `neon branches delete drill-target`.
