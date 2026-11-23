# ADR 0009: Temporal Cluster Topology and Persistence Architecture

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4C — Durable execution backbone  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
ZONATA requires an enterprise durable execution engine to orchestrate multi-day company builds, executive goal cadences, human approval workflows, and SOP instances with guaranteed determinism, retries, and crash recovery.

Standing Rules 33–40 dictate that:
- Temporal is an execution reliability layer, NOT an authority system.
- Workflows must never execute untracked side effects or bypass the ActionGateway.
- Payloads must be encrypted with per-tenant data keys through `KeyPort`.
- Noisy tenants must not starve other tenants.

## 2. Alternatives Considered

### Option 1: Managed Temporal Cloud
- **Pros:** Managed SLAs, auto-scaling frontend and persistence.
- **Cons:** Outbound data sovereignty exposure, per-action pricing, external network dependency, lacks zero-trust on-prem/sovereign enclave deployment option.

### Option 2: Self-Hosted Temporal Cluster with Dedicated Persistence Database (Chosen)
- **Licence:** Python SDK is MIT (per GitHub/README); Temporal Server is MIT. Permissive and compliant with Standing Rule 5.
- **Topology:**
  - Cluster deployed via container orchestration (Docker Compose / Kubernetes) with separate stateless frontend, matching, and history worker services.
  - **Dedicated Persistence Database:** Temporal state is persisted in an isolated PostgreSQL database (`temporal_persistence`), strictly decoupled from the main application datastore (`roboassistant` / `zonata_app`).
  - **Multi-Tenancy Model:** Shared production namespace (`zonata-enterprise`) with per-tenant task queues (`tenant-{tenant_id}-tasks`), tenant search attributes (`CustomTenantId`, `CustomCompanyId`), and per-tenant concurrency/rate limits.
  - **Noisy-Neighbor Isolation:** Separate worker pools and priority queue throttling to prevent one tenant from consuming all matching slots.
  - **Data Protection:** Upstream Python SDK Payload Codec plugin (`KeyPortPayloadCodec`) encrypts all activity/workflow payloads client-side before transmission across the Temporal gRPC wire. The Temporal web UI and server store only encrypted blobs.

### Option 3: Namespace Per Tenant
- **Rejected Reasons:** Temporal namespaces carry significant operational overhead (memory, connection pools, search index limits) and do not scale gracefully to thousands of multi-tenant SaaS organizations.

## 3. Decision
We adopt **Option 2 (Self-Hosted Temporal Cluster with Dedicated Persistence Database)**, using the official `temporalio` Python SDK (MIT).
