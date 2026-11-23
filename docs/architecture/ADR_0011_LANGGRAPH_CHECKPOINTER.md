# ADR 0011: Tenant-Safe LangGraph PostgreSQL Checkpointer Architecture

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4E — Single-position reasoning graph state persistence  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
LangGraph provides cyclic graph control for single-position reasoning loops (`EmployeeTaskGraph`, `CheckerGraph`, `CEOPlanningGraph`). To ensure resilience across process crashes, LangGraph relies on checkpointers.

Standing Rule 5, Rule 24, Rule 35, and Rule 36 mandate that:
- Multi-tenant isolation must be enforced at the database level with Row Level Security (RLS).
- Checkpoints must not store plaintext credentials, secrets, or unbounded documents.
- Thread IDs must be cryptographically partitioned by tenant and company.
- Checkpoints must support interrupt/resume workflows with action digest verification.

## 2. Alternatives Considered

### Option 1: Official `langgraph-checkpoint-postgres` directly
- **Pros:** Maintained upstream package.
- **Cons:** Assumes single-tenant or global database connections without native PostgreSQL RLS context (`zonata.tenant_id`) or envelope encryption of checkpoint state blobs.

### Option 2: ZONATA Sovereign Tenant-Safe Checkpointer (`ZonataPostgresSaver`) (Chosen)
- **Licence:** MIT (compatible with LangGraph's MIT license and Rule 5).
- **Architecture:**
  - Implements the official LangGraph `BaseCheckpointSaver` interface.
  - Table `langgraph_checkpoints` carries `tenant_id`, `company_id`, `thread_id`, `checkpoint_ns`, `checkpoint_id`, `parent_checkpoint_id`, and `payload_blob`.
  - Enforces PostgreSQL 16 Row Level Security (RLS) fail-closed policies.
  - **Envelope Encryption:** State payloads are encrypted using tenant-specific data encryption keys via `KeyPort`. Raw checkpoints never contain plaintext canary strings.
  - **Interrupts & Human Resumption:** When a node calls `interrupt()`, the payload contains an ActionGateway approval digest. Resuming via `Command(resume=...)` verifies that the resumed action matches the exact digest approved by the human principal.

## 3. Decision
We implement `ZonataPostgresSaver` in `core/langgraph/checkpointer.py`, conforming to LangGraph checkpoint semantics while guaranteeing multi-tenant RLS isolation and envelope encryption.
