# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## PostgreSQL Production Database Architecture

---

### 1. Database Topology & High Availability
In production, ZONATA operates against an authoritative PostgreSQL 15+ cluster configured with streaming replication, automated failover (via Patroni or AWS Aurora Multi-AZ), and PgBouncer connection pooling. SQLite is reserved strictly for local development sandboxes and deterministic CI environments.

```
                          ZONATA APPLICATION PODS
                      (API, Workers, HA Supervisor)
                                   |
                +------------------+------------------+
                |                                     |
         CONTROL_PLANE POOL                       WRITE & READ POOLS
          (Min: 5, Max: 25)                       (Min: 10, Max: 50)
                |                                     |
                +------------------+------------------+
                                   |
                          PgBouncer (Port 6432)
                       (Transaction Pooling Mode)
                                   |
             +---------------------+---------------------+
             |                                           |
    PRIMARY POSTGRESQL (RW)                     READ REPLICA (RO)
   (Authoritative Mutations,                   (Heavy Analytics,
    Merkle Evidence Events)                     Audits, Reporting)
```

---

### 2. Workload Separation & Connection Pooling Architecture

To prevent high-concurrency agent execution bursts from starving critical control-plane services, ZONATA enforces strict connection separation via `DatabaseEngine` (`core/database_engine.py`):

1. **`CONTROL_PLANE` Pool**:
   - Reserved exclusively for API authentication, tenant quota validation, supervisor heartbeats, and leader election leases.
   - Pool limits: 5 minimum, 25 maximum. Timeout: 15s.
   - Admission priority: Critical (cannot be throttled by worker jobs).
2. **`WRITE` Pool**:
   - Dedicated to mutating business transactions: mission state transitions, agent spawning, workflow checkpoints, and Merkle ledger updates.
   - Pool limits: 5 minimum, 20 maximum. Timeout: 30s.
   - Statement timeout: 10,000ms. Transaction timeout: 30,000ms.
3. **`READ` Pool**:
   - Dedicated to executive dashboard queries, Letta memory searches, knowledge graph traversals, and audit verifications.
   - Pool limits: 5 minimum, 30 maximum. Timeout: 20s.

---

### 3. Concurrency & Optimistic Locking Strategy
High-contention entities (`tenants`, `companies`, `departments`, `employees`, `missions`, `governed_agents`, `temporal_workflows`, `nango_executions`) maintain an integer `version` column.

Mutations require:
```sql
UPDATE <table_name>
SET <columns>, version = version + 1
WHERE <id_column> = ? AND version = <expected_version>;
```
If `rowcount == 0`, `OptimisticLockError` is raised, forcing state reconciliation and preventing lost updates across concurrent workers.

---

### 4. Authoritative Relational Mapping & Data Types

| Entity Group | Key Tables | PostgreSQL Column Types | Constraints & Guarantees |
| :--- | :--- | :--- | :--- |
| **Tenants & IAM** | `tenants`, `users` | `VARCHAR(64)`, `JSONB`, `DOUBLE PRECISION` | Cryptographic tenant isolation, cascading deletes. |
| **Workforce & Agents** | `employees`, `governed_agents` | `VARCHAR(64)`, `INT`, `JSONB` | Strict parent-child delegation constraints (`delegation_depth <= 4`). |
| **Evidence & Audit** | `merkle_evidence_events` | `BIGSERIAL`, `VARCHAR(64)` | Immutable, sequence-checked (`UNIQUE(event_index)`), tamper-evident SHA-256 chain. |
| **Durable Execution** | `temporal_workflows`, `temporal_activity_executions` | `VARCHAR(128)`, `JSONB` | Multi-node saga coordination, state reconciliation. |
| **External Systems** | `nango_connections`, `nango_executions` | `VARCHAR(64)`, `JSONB` | JIT credential handles (`cred_...`), idempotency enforcement. |
