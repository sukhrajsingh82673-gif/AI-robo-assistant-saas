# ADR 0044: Regional Cellular Architecture and Sovereign Data Residency

**Status:** APPROVED  
**Date:** 2026-11-24  
**Author:** Antigravity Systems Architect  
**Reviewer:** OpenCode Arbiter  
**Governing Rules:** Rule 41 (Secrets and Encryption), Rule 67 (Preservation Extension), Rule 73 (Global by Construction)

---

## 1. Context & Problem Statement
Sovereign privacy regulations (EU GDPR Chapter V, India DPDP Act 2023, Saudi PDPL, China PIPL) impose stringent legal restrictions on cross-border transfers of personal data, financial transactions, and health records. Many enterprise customers contractually mandate that:
- Customer data, backups, and encryption keys must never leave a designated geographic boundary (e.g., `eu-central-1` in Frankfurt or `ap-south-1` in Mumbai).
- Machine learning models processing local tenant data must run inside the sovereign region.
- Cross-region data aggregation must be strictly prevented or explicitly consented and audited.

A monolithic deployment with a global database or shared caching layer fails these legal constraints.

---

## 2. Decision: Sovereign Regional Cells with Hard Cross-Region Boundary Gates

We implement a **Cellular Architecture**:

```
                       ┌─────────────────────────┐
                       │  Global Edge / Geo DNS  │
                       │  (Tenant Region Router) │
                       └────────────┬────────────┘
                                    │
             ┌──────────────────────┴──────────────────────┐
             │ Route by tenant.home_region                 │
             ▼                                             ▼
┌─────────────────────────┐                   ┌─────────────────────────┐
│     Region Cell EU      │                   │     Region Cell IN      │
│  (e.g., Frankfurt)      │                   │  (e.g., Mumbai)         │
│                         │                   │                         │
│ - PostgreSQL (EU Data)  │                   │ - PostgreSQL (IN Data)  │
│ - OpenBao (EU Transit)  │                   │ - OpenBao (IN Transit)  │
│ - Object Store (S3 EU)  │                   │ - Object Store (S3 IN)  │
│ - Temporal Worker Pool  │                   │ - Temporal Worker Pool  │
│ - Regional LLM Gateway  │                   │ - Regional LLM Gateway  │
└─────────────────────────┘                   └─────────────────────────┘
```

1. **Autonomous Regional Cells:**
   - Each region operates an isolated, complete instance of the data and compute plane:
     - Local PostgreSQL 16 cluster with isolated `tenant_id` namespaces.
     - Local OpenBao cluster holding cell-specific encryption keys.
     - Local S3-compatible object storage for documents, backups, and artifacts.
     - Local Temporal cluster and worker pool.
     - Local Model Gateway enforcing region-pinned LLM provider endpoints.
2. **Deterministic Tenant Home Region Assignment:**
   - Each tenant record specifies an immutable `home_region` (e.g., `eu-west-1`, `us-east-1`, `in-south-1`).
   - Tenant requests are routed exclusively to the tenant's assigned regional cell.
3. **Hard Cross-Region Call Refusal (Rule 73):**
   - The networking layer and RPC dispatchers enforce a strict cell boundary check:
     ```python
     if request.target_region != current_cell.region_id:
         logger.critical("Cross-region access prohibited: %s -> %s", current_cell.region_id, request.target_region)
         raise CrossRegionOperationRefusedError(
             f"Data transfer from {current_cell.region_id} to {request.target_region} violates sovereign residency"
         )
     ```
   - Any unauthenticated or unpermitted cross-region database or storage call is refused and logged as a high-severity security audit event.
4. **Regional Model Gateway Routing:**
   - Inferences for an EU tenant are routed strictly to EU-located endpoints (e.g., Anthropic EU on AWS Frankfurt or Vertex AI EU on GCP Belgium).
   - Sending EU or Indian tenant personal identifiers to a non-sovereign model endpoint raises `SovereignAIBoundaryViolationError`.

---

## 3. License, Boundary & Security Notes
- All intra-cell communication is mTLS-encrypted.
- Regional keys in OpenBao are backed by local HSM / KMS root keys with non-exportable private material.
- CI tests include explicit negative tests attempting cross-region reads and model invocations, verifying that every cross-region attempt is refused.
