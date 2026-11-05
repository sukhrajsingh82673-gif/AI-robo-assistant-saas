# POSTGRESQL MIGRATION ARCHITECTURE & RUNBOOK
**ZONATA Universal AI Company Operating System**  
*Classification: PRODUCTION DATABASE ROADMAP*  
*Timestamp: 2026-10-02T11:15:00Z*

---

## 1. Migration Rationale

While SQLite with WAL mode and 60-second busy timeout supports single-node deployments and fast local testing (benchmarked at 49.3 agents/sec across 500 simulated agents), an enterprise multi-tenant SaaS serving hundreds of concurrent enterprises requires:
- Multi-master / replica concurrency
- Row-level locking instead of database-level writer locks
- Native JSONB indexing for agent states, workflow payloads, and Merkle packages
- Distributed connection pooling via `pgbouncer`
- Point-in-time recovery (PITR) via Write-Ahead Logging replication.

---

## 2. Schema Compatibility & Data Types

The 121 normalized SQLite tables are designed with SQL-92 standards to allow direct translation to PostgreSQL 16+:

| SQLite 3 Type | PostgreSQL 16+ Type | Notes |
| :--- | :--- | :--- |
| `TEXT` | `VARCHAR` / `TEXT` | Primary keys (`tenant_id`, `company_id`, `agent_id`) map to `VARCHAR(64)` |
| `REAL` (timestamps) | `DOUBLE PRECISION` or `TIMESTAMPTZ` | Unix epoch timestamps map cleanly |
| `INTEGER` | `INTEGER` / `BIGINT` | Counters, flags (`0`/`1` to `BOOLEAN`) |
| `JSON` | `JSONB` | Enables GIN indexing on payloads, metadata, and audit records |

---

## 3. Database Abstraction Layer Architecture

In `core/db.py`, replace raw `sqlite3.connect` with a database engine abstraction:

```python
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

class Database:
    def __init__(self):
        self.is_postgres = bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))
        if self.is_postgres:
            import psycopg2
            from psycopg2.pool import ThreadedConnectionPool
            self.pool = ThreadedConnectionPool(minconn=5, maxconn=50, dsn=DATABASE_URL)
        else:
            self.db_path = DB_PATH

    def get_connection(self):
        if self.is_postgres:
            return self.pool.getconn()
        else:
            # SQLite fallback for local development & testing
            return sqlite3.connect(self.db_path, timeout=60.0)
```

---

## 4. Migration Execution Steps

1. **Step 1: Dump SQLite Tables to CSV/JSON**:
   Use `sqlite3 storage/roboassistant.db .dump` or custom Python exporter.
2. **Step 2: Execute DDL in PostgreSQL**:
   Run generated `schema_postgres.sql` with `CASCADE` foreign keys and GIN indexes.
3. **Step 3: Load Data via COPY**:
   Stream CSV records into PostgreSQL tables within a single transaction.
4. **Step 4: Verify Row Counts & Foreign Key Integrity**:
   Run consistency validation scripts comparing SQLite record counts against PostgreSQL.
5. **Step 5: Cut Over Traffic**:
   Update `DATABASE_URL` in `/etc/zonata/zonata.env` and restart `zonata-api` and `zonata-daemon`.
