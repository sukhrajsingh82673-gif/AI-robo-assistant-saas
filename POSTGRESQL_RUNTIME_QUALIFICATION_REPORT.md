# URA / ZONATA SaaS — PostgreSQL Runtime Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Subsystems**: `core/db.py`, `docker-compose.prod.yml`, `PRODUCTION_DEPLOYMENT_RUNBOOK.md`  
**Formal Verdict**: **BLOCKED PENDING STAGING RUNTIME PROOF**

---

## 1. Executive Summary & Verdict Rationale

This qualification report audits the database engine implementation, dialect abstractions, and operational readiness for PostgreSQL 16 support in URA / ZONATA Enterprise SaaS.

### Verdict: BLOCKED PENDING STAGING RUNTIME PROOF
- **Code-Level Implementation (Audited & Hardened)**: The application code in `core/db.py` contains a comprehensive dual-engine database abstraction layer supporting both `DatabaseDialect.SQLITE` and `DatabaseDialect.POSTGRESQL`. Parameter translation (`?` to `%s`), dialect query normalization (`INSERT OR IGNORE` -> `ON CONFLICT DO NOTHING`), pragma stripping, transactional wrappers (`PostgresConnectionWrapper`), row factory parity (`DictCursor`), and dialect detection logic have been fully implemented.
- **Production Safety Invariant (Refusal of Unintended Fallback)**: In production mode (`APP_ENV=production`), `core/db.py` strictly refuses to silently or explicitly fall back to SQLite under all environment flags. Any absence of `DATABASE_URL`, SQLite URI, or legacy override `ZONATA_ALLOW_SQLITE_IN_PRODUCTION` immediately raises `RuntimeError: Production Safety Invariant Violation: Direct SQLite fallback is prohibited in production mode...`. In addition, `sanitize_db_url()` masks connection credentials (`:***@`) in all exception strings and error logs.
- **Physical Staging / Managed PostgreSQL Execution (BLOCKED)**: In the present host execution environment (Linux aarch64 PRoot container), the Docker daemon is unavailable, and no live PostgreSQL 16 network server or managed cloud database instance is currently connected.
- **Strict Anti-Fabrication Standard**: In accordance with sovereign qualification integrity, **we do not fabricate live PostgreSQL execution or container runtime logs**. The runtime execution gate remains explicitly **BLOCKED** until verified against an authorized, running PostgreSQL 16 staging instance.

---

## 2. Infrastructure Qualification Criteria: Managed vs. Self-Hosted

A physically owned hardware server is **not** required. A properly configured, isolated, and secured managed PostgreSQL service satisfies all staging and production database requirements:

| Database Option | Qualification Feasibility | Security & Isolation Requirement |
|---|---|---|
| **Managed Cloud RDS / Cloud SQL** | **ACCEPTED** (Recommended) | Dedicated VPC / Private Subnet, TLS encryption in transit (`sslmode=verify-full`), automated snapshots, minimum 2 vCPU / 4 GB RAM. |
| **Managed Serverless (Aurora / Neon / Supabase)** | **ACCEPTED** | Connection pooler (PgBouncer) configured to handle connection bursts; transaction isolation level `READ COMMITTED`. |
| **Self-Hosted Container (Docker / K8s)** | **ACCEPTED** | Dedicated internal bridge network, persistent volume mount, non-root container process, memory limit >= 2GB. |
| **Direct Host Installation** | **ACCEPTED** | Local Unix domain socket or loopback binding, dedicated system user `postgres`, WAL archiving configured. |

---

## 3. SQL Compatibility & Dialect Layer Analysis

| Feature | SQLite Behavior | PostgreSQL Requirement | Implementation in `core/db.py` |
|---|---|---|---|
| **Parameter Placeholders** | Positional `?` | Positional `%s` | `PostgresConnectionWrapper.execute()` transforms `?` to `%s` |
| **Conflict Handling** | `INSERT OR IGNORE` | `ON CONFLICT DO NOTHING` | `PostgresConnectionWrapper._normalize_sql()` transforms syntax |
| **Pragma Statements** | `PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL` | Syntax error in Postgres | `_normalize_sql()` detects and suppresses PRAGMAs safely |
| **Row Factory Access** | `sqlite3.Row` (dict + index access) | Tuple by default | Wraps cursor with `psycopg2.extras.DictCursor` |
| **Silent Fallback Prevention** | Defaults to SQLite | Must fail closed if DB missing in prod | `Database.__init__` raises `RuntimeError` if prod has no `DATABASE_URL` |
| **Data Types** | Dynamic typing (`TEXT`, `REAL`, `JSON`) | Strict typing (`VARCHAR`, `FLOAT8`, `JSONB`) | Schema DDL maps to ANSI standard SQL types valid on PostgreSQL 16 |

---

## 4. Staging Verification Acceptance Matrix (Required Proof)

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

## 5. Concise Infrastructure Prerequisite Checklist

To execute Section 4 proof, the operator or infrastructure team must provide:

1. **Staging Connection String**:
   ```bash
   DATABASE_URL="postgresql://zonata_app:<STAGING_PASSWORD>@<STAGING_HOST>:5432/zonata_staging?sslmode=require"
   ```
2. **Access Isolation**: Dedicated disposable database (`zonata_staging`) with zero connection to production customer data.
3. **Database Version**: PostgreSQL 16.x (or compatible Aurora PostgreSQL 16).
4. **Driver Availability**: `psycopg2-binary` or `asyncpg` installed in the Python runtime environment.
5. **Backup Utilities**: `pg_dump` and `pg_restore` (or cloud snapshot trigger access) for DR qualification.
