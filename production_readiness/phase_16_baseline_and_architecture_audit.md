# Phase 16: Baseline and Architecture Audit Report
## URA / ZONATA — Universal AI Company Operating System
### Multi-Tenant Rate Limiting, Abuse Prevention & Tenant Fairness

**Audit Date:** October 19, 2026  
**Auditor:** Autonomous Senior Principal Systems Architect & Cryptographic Security Lead  
**Evaluation Scope:** Baseline Review, Threat Modeling, Architecture Invariants & Multi-Instance Consistency  
**Branch:** `engineering/production-readiness-gap-closure`  
**Base Commit:** `ec1eb567a49998c7960808a59fb7dd93168e5959`  

---

## 1. Executive Summary

Phase 16 addresses the critical production readiness domain of **Rate Limiting, Abuse Prevention & Tenant Fairness**. In multi-tenant enterprise software-as-a-service (SaaS) environments, unconstrained resource consumption by a single aggressive tenant, rogue agent, or external adversary poses systemic risks: noisy-neighbor starvation, resource exhaustion, elevated hosting costs, cascading database connection pool depletion, and denial-of-service (DoS).

Prior to Phase 16, ZONATA relied primarily on coarse IP-based perimeter checks and application-layer budget checks without granular, multi-dimensional rate limiting, per-tier quota enforcement, or distributed concurrency leases.

This audit establishes the baseline threat landscape, formalizes the 4-layer hierarchical rate-limiting architecture, defines distributed lease mechanics, and verifies adherence to the platform's constitutional invariants.

---

## 2. Threat Modeling & Abuse Scenarios

The architecture is designed to withstand five primary attack and degradation vectors:

| Threat ID | Threat Vector | Mechanism of Abuse | Systemic Impact Mitigated by Phase 16 |
|:---|:---|:---|:---|
| **THR-16-01** | **Noisy Neighbor Starvation** | Tenant A issues massive parallel queries across overview and portfolio endpoints. | Tenant A is bounded by its commercial tier quota (Free: 60 rpm; Starter: 300 rpm; Pro: 1200 rpm; Enterprise: 3600 rpm). Tenant B experiences zero latency degradation or quota impact. |
| **THR-16-02** | **Credential Stuffing & Brute Force** | Adversary rapidly issues auth token/login requests from distributed or rotating IPs. | Dedicated IP authentication perimeter limits (`25 rpm` on `/api/auth/token`, `10 rpm` on `/api/auth/register`) strictly rate-limit authentication abuse. |
| **THR-16-03** | **Long-Running Job / Agent Concurrency Exhaustion** | A tenant triggers dozens of asynchronous multi-agent missions or workflow executions simultaneously. | Distributed concurrency lease manager enforces tenant concurrency ceilings (Free: 1 concurrent; Starter: 3; Pro: 10; Enterprise: 50). Additional jobs are rejected with HTTP 429 and `Retry-After`. |
| **THR-16-04** | **Cross-Tenant Information Leakage via Headers** | Adversary probes rate-limit responses to infer neighbor tenant activity or quota limits. | RFC-compliant rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`) expose only the requesting tenant's scoped limits with zero neighbor metadata or shared pool exposure. |
| **THR-16-05** | **Tenant Identity Spoofing** | Adversary injects `X-Tenant-ID: <victim_tenant>` headers in requests to consume a victim's quota. | Tenant context is extracted strictly from cryptographically validated Bearer JWT tokens (`UserManager.verify_token`). Header spoofing mismatches trigger immediate `AuthExceptions.TenantIsolationViolation` (HTTP 403 Forbidden). |

---

## 3. Four-Tier Architectural Hierarchy

Rate limiting in ZONATA is structured across four orthogonal, defense-in-depth evaluation axes:

```
+-------------------------------------------------------------------------+
| Layer 1: Anonymous & IP Perimeter Gate                                 |
| - Global IP Ceiling: 1,200 req/min                                      |
| - Sensitive Auth Login: 25 req/min                                      |
| - Sensitive Auth Register: 10 req/min                                   |
+------------------------------------+------------------------------------+
                                     | (Passes Perimeter)
                                     v
+-------------------------------------------------------------------------+
| Layer 2: Tenant-Level Commercial Tier Quota                             |
| - FREE: 60 req/min, 1 concurrency lease                                 |
| - STARTER: 300 req/min, 3 concurrency leases                            |
| - PRO: 1,200 req/min, 10 concurrency leases                             |
| - ENTERPRISE: 3,600 req/min, 50 concurrency leases                      |
+------------------------------------+------------------------------------+
                                     | (Within Tenant Allowance)
                                     v
+-------------------------------------------------------------------------+
| Layer 3: Identity-Level Fairness (Per User Within Tenant)               |
| - Sub-allocates tenant capacity to prevent single user dominating tenant|
| - Free: 60 rpm | Starter: 120 rpm | Pro: 300 rpm | Enterprise: 600 rpm  |
+------------------------------------+------------------------------------+
                                     | (Within User Allowance)
                                     v
+-------------------------------------------------------------------------+
| Layer 4: Endpoint-Specific Throttling                                   |
| - Expensive Operations (e.g. LLM reasoning, explain-variance): 10-180 rpm|
| - Mutating Operations (e.g. POST, PUT, DELETE state updates): 30-600 rpm|
+-------------------------------------------------------------------------+
```

---

## 4. Multi-Instance Consistency & Storage Engine

Because ZONATA operates in production environments across potentially multiple web container instances (e.g., Render autoscaled services or canary deployments), rate limiting and concurrency leases cannot rely exclusively on single-process memory counters.

### 4.1 Persistence Model
1. **Primary Shared State:** Backed by PostgreSQL (or SQLite in local environments) via two dedicated tables:
   - `tenant_rate_limits`: Stores sliding-window attempt timestamps indexed by `(rate_key, attempt_timestamp)`.
   - `tenant_concurrency_leases`: Stores active concurrency leases with explicit lease IDs, tenant IDs, lease types, and expiry timestamps (`expires_at`).
2. **Atomic Window Evaluation:** Sliding window pruning and counter evaluation occur within database transactions (`BEGIN IMMEDIATE` / serialized commits).
3. **Probabilistic Table Pruning:** To maintain lightweight storage overhead within Neon serverless free-tier storage boundaries, 1 out of every 50 evaluations probabilistically purges records older than 1 hour (`DELETE FROM tenant_rate_limits WHERE attempt_timestamp < now - 3600.0`).
4. **Thread-Safe In-Memory Fallback:** If the database connection is interrupted or partitioned, the engine transparently falls back to an in-memory sliding window protected by threading locks, ensuring continuous operational availability without crashing request pipelines.

---

## 5. Constitutional Invariant Verification

Before any code modifications for Phase 16 were executed, the platform's three protected constitutional assets were forensically verified:

| Protected Asset | Verification Method | Expected Value | Baseline Value | Status |
|:---|:---:|:---|:---|:---:|
| `storage/roboassistant.db` | SHA-256 | `ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4` | `ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4` | **MATCH** |
| `storage/evidence/audit_ledger.jsonl` | SHA-256 | `ca8181ec9314f281acad3512a34d32323fc195e6eed9f6412d7262e1e6dd0996` | `ca8181ec9314f281acad3512a34d32323fc195e6eed9f6412d7262e1e6dd0996` | **MATCH** |
| `web/workflow_workspace.js` | Git Blob SHA-1 | `198d57ec6bda875cd2a6825fe2ef8929b7ba30bd` | `198d57ec6bda875cd2a6825fe2ef8929b7ba30bd` | **MATCH** |

All tests and qualification runs strictly utilize isolated temporary SQLite databases (`configure_isolated_test_db()`), preserving production asset files untouched.
