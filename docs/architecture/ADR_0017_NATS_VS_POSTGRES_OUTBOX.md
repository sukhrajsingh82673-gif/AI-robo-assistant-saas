# ADR 0017: Messaging Architecture — PostgreSQL Outbox vs NATS

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4I — Asynchronous event messaging and fan-out  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
Docker compose manifests contain a NATS service (`nats:2.10.18-alpine`). We evaluated whether NATS is necessary or if ZONATA's transactional PostgreSQL outbox meets all architectural requirements.

## 2. Comparison

### Option 1: NATS Messaging Cluster
- **Pros:** Ultra-high throughput ($>1M$ msgs/sec), pub/sub, JetStream persistence.
- **Cons:** Dual-write consistency problem (writing to DB and publishing to NATS requires distributed 2PC or an outbox anyway), additional stateful cluster management, operational complexity.

### Option 2: Transactional PostgreSQL Outbox (`core/baseline/outbox.py`) (Chosen)
- **Licence:** Native application code over PostgreSQL (Permissive / Apache-2.0).
- **Guarantees:**
  - **Atomic Transactions:** Outbox records (`outbox_events`) are written in the exact same database transaction as the business mutation, guaranteeing zero lost events.
  - **At-Least-Once Delivery:** Polling workers deliver events to subscribers with exponential backoff and Dead Letter Queue (DLQ) after 5 failed attempts.
  - **Idempotency Keys:** Enforced by consumer handlers via `idempotency_key` (Rule 35).
  - **Throughput:** Easily handles enterprise requirements ($\sim 5,000$ events/sec per node) with low latency.

## 3. Decision
We **retain Option 2 (Transactional PostgreSQL Outbox)** as the authoritative event delivery backbone. NATS is unnecessary for ZONATA's consistency and fan-out profile, and its service definition in compose will be removed or marked deprecated to eliminate dead weight.
