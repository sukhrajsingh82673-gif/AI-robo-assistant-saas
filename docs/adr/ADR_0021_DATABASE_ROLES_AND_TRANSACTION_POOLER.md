# ADR 0021: Database Role Hierarchy, Transaction-Mode Pooling, and Transaction-Scoped RLS Context

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 42 (Least privilege and default deny), Rule 43 (Tenant context is transaction-scoped)

---

## 1. Context and Problem Statement
Multi-tenant isolation in ZONATA relies on PostgreSQL Row-Level Security (RLS). However, two critical vulnerabilities threaten tenant isolation:
1. **Superuser / Table Owner Bypass:** If the application connects as a superuser or the role that owns the database tables, PostgreSQL by default bypasses RLS policies entirely unless `FORCE ROW LEVEL SECURITY` is set on every table.
2. **Transaction Pooler Session Bleed:** In modern cloud deployments (e.g., Neon serverless pooling, PgBouncer in `pool_mode = transaction`), multiple transactions from different tenants share the same backend PostgreSQL connection. Setting session-level variables (`set_config(..., false)`) causes tenant state to persist onto subsequent transactions of other tenants.

## 2. Decision

### 2.1 Least-Privilege Role Hierarchy
The database must be accessed strictly through differentiated, non-superuser roles:
1. `zonata_migrator`: Owns schemas and tables; holds DDL (`CREATE`, `ALTER`, `DROP`); used solely by migration runners during deployment; **never connects at application runtime**.
2. `zonata_app`: Non-owner role holding DML only (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on tenant tables; subject to RLS enforcement.
3. `zonata_worker`: DML on background queues and ledger ingestion; cannot alter schema.
4. `zonata_backup`: Read-only + `REPLICATION` grant for physical streaming backups.

### 2.2 Transaction-Scoped RLS Context (Rule 43)
1. **Transaction-Scoped `set_config`:**
   Every database query touching tenant data must execute within an explicit transaction where the tenant context is set using the 3rd argument `is_local = true`:
   ```sql
   SELECT set_config('zonata.tenant_id', $1, true),
          set_config('zonata.company_id', $2, true);
   ```
   Setting `is_local = true` makes the setting strictly local to the current transaction (equivalent to `SET LOCAL`). When the transaction issues `COMMIT` or `ROLLBACK`, the tenant context is automatically wiped, ensuring zero tenant leakage across transactions sharing the pooled connection.
2. **Fail-Closed Missing Context:**
   If a query runs without an active tenant context, `zonata.tenant_id` evaluates to empty string or NULL, and RLS policies fail closed (returning 0 rows on `SELECT` and raising an exception on `INSERT`/`UPDATE`).
3. **Mandatory `FORCE ROW LEVEL SECURITY`:**
   All tenant-scoped tables must execute `ALTER TABLE <table> FORCE ROW LEVEL SECURITY;` so that even administrative maintenance operations cannot inadvertently bypass isolation.

## 3. Consequences
- **Positive:** Immune to cross-tenant connection pooling leaks; compatible with Neon transaction pooler, AWS RDS Proxy, and PgBouncer; least-privilege roles prevent accidental DDL at runtime.
- **Negative:** Requires all multi-statement operations to be wrapped in explicit transactions; autocommit single queries must execute the `set_config` in the same transaction block.
