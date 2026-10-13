# URA / ZONATA SaaS — PostgreSQL Runtime Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Subsystems**: `core/db.py`, `docker-compose.prod.yml`, `PRODUCTION_DEPLOYMENT_RUNBOOK.md`  
**Formal Verdict**: **BLOCKED PENDING STAGING RUNTIME PROOF**

---

## 1. Executive Summary & Verdict Rationale

This qualification report audits the database engine implementation, dialect abstractions, and operational readiness for PostgreSQL 16 support in URA / ZONATA Enterprise SaaS.

### Verdict: BLOCKED PENDING STAGING RUNTIME PROOF
- **Code-Level Implementation (Audited & Ready)**: The application code in `core/db.py` contains a complete dual-engine database abstraction layer supporting both `DatabaseDialect.SQLITE` and `DatabaseDialect.POSTGRESQL`. Parameter translation (`?` to `%s`), transactional wrappers (`PostgresConnectionWrapper`), row factory parity (`RealDictCursor`), and dialect detection logic have been fully implemented and verified in the test harness.
- **Physical Staging / Managed PostgreSQL Execution (BLOCKED)**: In the present host execution environment (Linux aarch64 PRoot container), the Docker daemon is unavailable, and no live PostgreSQL 16 network server or managed cloud database instance is currently connected.
- **Strict Anti-Fabrication Standard**: In accordance with sovereign qualification integrity, **we do not fabricate live PostgreSQL execution**. The runtime execution gate remains explicitly **BLOCKED** until verified against an authorized, running PostgreSQL 16 staging instance.

---

## 2. Infrastructure Qualification Criteria: Managed vs. Self-Hosted

A physically owned hardware server is **not** required. A properly configured, isolated, and secured managed PostgreSQL service satisfies all staging and production database requirements:

| Database Option | Qualification Feasibility | Security & Isolation Requirement |
|---|---|---|
| **Managed Cloud RDS / Cloud SQL** | **ACCEPTED** (Recommended) | Dedicated VPC / Private Subnet, TLS encryption in transit (`sslmode=verify-full`), automated snapshots, minimum 2 vCPU / 4 GB RAM. |
| **Managed Serverless (Aurora / Neon)** | **ACCEPTED** | Connection pooler (PgBouncer) configured to handle connection bursts; transaction isolation level `READ COMMITTED`. |
| **Self-Hosted Container (Docker / K8s)** | **ACCEPTED** | Dedicated internal bridge network, persistent volume mount, non-root container process, memory limit >= 2GB. |
| **Direct Host Installation** | **ACCEPTED** | Local Unix domain socket or loopback binding, dedicated system user `postgres`, WAL archiving configured. |

---

## 3. Staging Verification Acceptance Matrix (Required Proof)

To transition this gate from `BLOCKED` to `PASS`, the following evidence must be captured from a live, running PostgreSQL 16 instance:

```
[ API Server ] ---> (DATABASE_URL=postgresql://user:pass@host:5432/zonata_staging)
                          |
                          v
         [ PostgreSQL 16 Staging Database ]
```

| Verification Item | Acceptance Criteria | Target Evidence | Status |
|---|---|---|---|
| **1. Genuine PostgreSQL Connection** | Running API connects to PostgreSQL and does not fall back to SQLite | `SELECT version()` returns PostgreSQL 16.x in API startup logs | **BLOCKED** |
| **2. Fresh Migration Execution** | Schema tables (`users`, `crm_customers`, `crm_deals`, `auth_credentials`, `system_settings`) created cleanly on empty database | Information schema table inventory; zero migration errors | **BLOCKED** |
| **3. Core Persistence** | User registration, authentication, CRM accounts, and settings persist and reload | Records queried directly via `psql` and returned by API | **BLOCKED** |
| **4. Tenant Isolation Enforcement** | Cross-tenant queries return empty sets; cross-tenant updates/deletes return 404 | SQL logs confirming `tenant_id` scoping on all executed queries | **BLOCKED** |
| **5. Concurrency & Transactions** | Concurrent writes succeed; transaction rollbacks clean up uncommitted rows | Zero deadlocks; rollback leaves no orphaned rows | **BLOCKED** |
| **6. Reconnection & Restart** | Application survives database restart and reconnects automatically without crashing | Connection pool re-establishes socket connection | **BLOCKED** |
| **7. Backup & Restore Rehearsal** | `pg_dump` snapshot archive restored to disposable verification database | Zero data loss; row counts and foreign keys intact | **BLOCKED** |

---

## 4. Concise Infrastructure Prerequisite Checklist

To execute Section 3 proof, the operator or infrastructure team must provide:

1. **PostgreSQL 16 Instance**:
   - Host / Connection endpoint (e.g. `postgres-staging.internal` or Cloud RDS endpoint).
   - Port (default `5432`).
   - Database name (`zonata_staging`).
   - Dedicated service user and strong password.
2. **Network Routing**:
   - Outbound network egress from the application runtime to port 5432 on the database host.
3. **Python PostgreSQL Driver**:
   - `psycopg2-binary` or `asyncpg` installed in the application container environment (already included in `docker/Dockerfile.api`).
4. **Environment Variables Configured**:
   ```bash
   export DATABASE_URL="postgresql://zonata_staging_user:StrongSecret123!@postgres-staging.internal:5432/zonata_staging?sslmode=require"
   export APP_ENV="staging"
   export ZONATA_STRICT_AUTH="1"
   ```

---

## 5. Formal Decision

| Evaluation Area | Verdict | Summary |
|---|---|---|
| **PostgreSQL Runtime Execution** | **BLOCKED PENDING STAGING RUNTIME PROOF** | Code-level abstractions and compose manifests are validated. Runtime operation remains blocked until an authorized PostgreSQL 16 instance is connected. |
