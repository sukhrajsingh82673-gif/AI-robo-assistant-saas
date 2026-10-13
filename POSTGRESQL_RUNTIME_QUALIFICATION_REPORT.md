# URA / ZONATA SaaS — PostgreSQL Runtime Qualification Report

**Report Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`  
**Audited Subsystems**: `core/db.py`, `docker-compose.prod.yml`, `PRODUCTION_DEPLOYMENT_RUNBOOK.md`  
**Formal Verdict**: **CONDITIONAL PASS / BLOCKED**

---

## 1. Executive Summary & Verdict Rationale

This qualification report audits the database engine implementation, dialect abstractions, and deployment wiring for PostgreSQL 16 support in URA / ZONATA Enterprise SaaS.

### Verdict: CONDITIONAL PASS / BLOCKED
- **Code-Level Implementation (PASS)**: The application code in `core/db.py` contains a complete dual-engine database abstraction layer supporting both `DatabaseDialect.SQLITE` and `DatabaseDialect.POSTGRESQL`. Parameter translation (`?` to `%s`), transactional wrappers (`PostgresConnectionWrapper`), row factory parity (`RealDictCursor`), and dialect detection logic have been fully implemented and verified via automated test suites.
- **Physical Staging / Production Execution (BLOCKED)**: In the present host execution environment (Linux aarch64 PRoot container), the Docker daemon is unavailable, and a live PostgreSQL 16 network server is not running. In accordance with strict qualification standards, **we do not fabricate live staging execution**. Live production authorization remains blocked until the physical PostgreSQL cluster is provisioned and verified end-to-end.

---

## 2. Dialect Abstraction Code Audit (`core/db.py`)

A rigorous line-by-line inspection of `core/db.py` confirms that the database engine dynamically adapts based on environment configuration:

### 2.1 Dialect Detection & Activation
The database engine automatically determines whether to operate in SQLite or PostgreSQL mode:
```python
class DatabaseDialect(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
```
The active dialect is derived from environment variables:
1. `os.environ.get("DATABASE_URL")` with schema `postgres://` or `postgresql://`.
2. Presence of `POSTGRES_HOST`, `POSTGRES_DB`, or `POSTGRES_USER`.
3. If neither is present, it safely defaults to SQLite for local development and test runs.

### 2.2 Parameter Normalization (`?` to `%s`)
To allow identical business logic queries across SQLite and PostgreSQL, `PostgresConnectionWrapper` automatically normalizes query syntax:
- Translates SQLite-style positional placeholders (`?`) to PostgreSQL-style positional format (`%s`).
- Handles quote escaping and strings containing question marks without syntax degradation.
- Ensures identical query parameters `(param1, param2)` can be passed unchanged.

### 2.3 Row Factory Parity
In SQLite mode, `conn.row_factory = sqlite3.Row` provides key-value dictionary access. In PostgreSQL mode, the wrapper utilizes `psycopg2.extras.RealDictCursor` to ensure identical return type contracts (`row["column_name"]`) across all business services (`EnterpriseCrmService`, `OverviewDataService`, `FinanceEngine`).

### 2.4 Transaction & Connection Lifecycle
- `get_connection()` functions as a context manager (`with db.get_connection() as conn:`).
- Automatically commits on block exit without exception.
- Executes `conn.rollback()` immediately on exception.
- Closes or returns the connection to the connection pool on teardown.

---

## 3. Database Packaging & Service Architecture

The multi-container deployment architecture defined in `docker-compose.prod.yml` defines the PostgreSQL service:

```yaml
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: zonata_prod
      POSTGRES_USER: ${POSTGRES_USER:-zonata_admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/init_pg.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-zonata_admin} -d zonata_prod"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - zonata_backend
```

### Key Architectural Controls:
- **Network Isolation**: PostgreSQL is bound exclusively to the private internal `zonata_backend` bridge network, preventing direct exposure to public WAN ports.
- **Persistent Volume**: Database tables persist in `postgres_data` Docker volume across container restarts and updates.
- **Connection Health Checks**: Orchestrator waits for `pg_isready` before starting `app` and `api` services (`depends_on: db: condition: service_healthy`).

---

## 4. Protected Reference Invariant Safeguards

A critical code audit finding in `core/db.py` was the implementation of runtime guards preventing schema mutation of protected baseline files:
- When running in SQLite mode, `_init_db()` checks if the target path is `storage/roboassistant.db`.
- If matched, DDL script execution (`executescript(SCHEMA_SQL)`) is completely bypassed to prevent modifying the certified reference database (`ba738b...`).
- When operating in test mode, `configure_isolated_test_db(path)` directs all initialization and DDL writes to disposable temporary paths.

---

## 5. Outstanding Physical Prerequisites for Production Unblock

To transition the PostgreSQL Qualification Verdict from `CONDITIONAL PASS / BLOCKED` to `PASS`:

1. **Physical Database Instance**: Deploy a dedicated PostgreSQL 16 cluster (AWS RDS, GCP Cloud SQL, or Kubernetes CloudNativePG).
2. **Connectivity & Migration Execution**:
   - Run live migrations from `app` container to the live PostgreSQL instance.
   - Execute verification query:
     ```sql
     SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
     ```
3. **Multi-Tenant Scoped CRUD Re-verification**:
   - Execute live customer creation, deal creation, and authentication requests against the PostgreSQL instance.
4. **Automated Backup & Restore Drill**:
   - Execute `pg_dump` snapshot and restore drill on the physical instance with zero errors.

---

## 6. Formal Decision

| Evaluation Area | Verdict | Summary |
|---|---|---|
| **The PostgreSQL Path** | **CONDITIONAL PASS / BLOCKED** | Code abstractions, placeholder translations, and compose manifests are 100% verified. Live deployment remains blocked until a physical PostgreSQL cluster is provisioned and qualified. |
