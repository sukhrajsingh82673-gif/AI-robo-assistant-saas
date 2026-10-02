# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Distributed Production Architecture Specification (V2)

---

### 1. Executive Summary & Top-Level Architecture
ZONATA V2 transitions the Universal AI Company Operating System from a hardened single-node instance into a distributed, multi-tenant, horizontally scalable cloud-native runtime. The architecture enforces strict separation between the **Control Plane** (identity, policy, authority, approvals, registries, evidence) and the **Execution Plane** (browser execution, code execution, MCP tools, A2A protocols, Nango SaaS integrations, and HAL computer control).

```
                            INTERNET / CLIENTS
                                     |
                               WAF / LB / API
                                     |
                        +------------+------------+
                        |                         |
                   API NODE 1                 API NODE N (Stateless ASGI)
                        |                         |
                        +------------+------------+
                                     |
                           ZONATA SERVICE LAYER
                                     |
            +------------------------+------------------------+
            |                        |                        |
     PostgreSQL (v15+)        Redis (v7+)               Object Storage
  (Relational Authority,   (Distributed Locks,       (S3/MinIO compliant:
   Transactions, Pooling)   Leases, Rate Limits)      Artifacts, Blobs, Packages)
            |                        |                        |
            +------------------------+------------------------+
                                     |
                          ASYNC JOB & EVENT PLANE
                        (ActionEnvelope Protocol)
                                     |
            +------------------------+------------------------+
            |                        |                        |
      Agent Workers          Supervisor Workers       Integration Workers
      (Workforce Runtime)    (HA Leader Election)     (Connectors, Webhooks)
            |                        |                        |
            +------------------------+------------------------+
                                     |
                              TEMPORAL CLUSTER
                        (Authoritative Durable Sagas)
                                     |
      +------------+-----------+------------+------------+-----------+
      |            |           |            |            |           |
     MCP          A2A        Nango       Browser      OpenHands     HAL
   Workers      Workers     Workers      Workers       Workers    Workers
      |            |           |            |            |           |
      +------------+-----------+------------+------------+-----------+
                                     |
                              EXTERNAL WORLD
                                     |
                        REALITY & EVIDENCE ENGINE
                   (Merkle Proofs, Causality Verification)
```

---

### 2. Core Architectural Planes

#### A. Control Plane (Governance & Invariants)
The Control Plane is the authoritative decision-maker and gatekeeper. No execution worker or agent can alter control-plane invariants:
* **Constitutional Policy Engine**: Evaluates 65 non-negotiable security and governance invariants.
* **Authority Gateway**: Enforces `CAPABILITY != AUTHORITY`. An agent possessing a tool contract or discovered API must obtain an authenticated, policy-cleared, signed token before execution.
* **Approval Engine**: Manages asynchronous multi-party approvals for high-risk, financial, or destructive mutations with parameter-bound cryptographic leases.
* **Evidence Ledger**: Immutable transactional ledger recording every action, state transition, and Merkle hash verification.

#### B. Data & Execution Plane (Distributed Workers)
Workers are stateless, disposable execution units operating in isolated sandboxes:
* **Agent Workforce Workers**: Execute autonomous agent decision loops, LangGraph workflows, and task decompositions.
* **Temporal Durable Workers**: Process activities, sagas, heartbeats, and retry policies underneath ZONATA governance.
* **Specialized Integration Workers**:
  - `MCP Workers`: Host and invoke Model Context Protocol tools within zero-trust boundaries.
  - `A2A Workers`: Handle agent-to-agent cryptographic messaging and task handoffs.
  - `Nango Workers`: Manage SaaS OAuth tokens, webhook ingestion, and data sync cursors.
  - `Browser Use Workers`: Run containerized Chromium instances with SSRF and DNS rebinding protections.
  - `OpenHands Workers`: Run isolated rootless container workspaces with CPU/RAM/PID quotas.
  - `HAL Workers`: Manage local computer perception and multimodal interaction.

---

### 3. Distributed Invariants & Data Flow

1. **Stateless API Ingress**:
   HTTP endpoints do not hold in-memory execution state. Incoming requests are authenticated via HMAC-SHA256 tokens, validated for tenant boundaries, assigned a `request_id`, wrapped in an `ActionEnvelope`, and dispatched asynchronously to the job plane.
2. **Authoritative Relational Persistence**:
   PostgreSQL serves as the single source of truth for all business entities, tenant quotas, approvals, schedules, and Merkle evidence metadata. Connection pooling isolates control-plane queries from high-volume agent read/write queries.
3. **Distributed Coordination & Leases**:
   Redis manages distributed locks, leader leases for the HA Supervisor, short-lived rate-limiting token buckets, and distributed killswitch propagation.
4. **Universal Asynchronous Command Envelope (`ActionEnvelope`)**:
   All inter-process execution requests adhere to the canonical envelope:
   ```json
   {
     "action_id": "act_0192a8b3c4d5",
     "tenant_id": "tenant_enterprise_prod",
     "company_id": "comp_zonata_main",
     "mission_id": "msn_growth_q4",
     "workflow_id": "wf_temp_8829",
     "agent_id": "agt_sales_rep_01",
     "parent_agent_id": "agt_ai_ceo",
     "capability_id": "nango.hubspot.create_contact",
     "target": "https://api.hubapi.com/crm/v3/objects/contacts",
     "intent": "Create verified prospect lead",
     "parameters_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "risk_class": "DATA_ENTRY",
     "authorization_contract_id": "auth_contract_7741",
     "approval_id": null,
     "credential_handle": "cred_hubspot_token",
     "idempotency_key": "idemp_lead_9921",
     "deadline": 1790999999.0,
     "parent_action_id": null,
     "causality_id": "caus_001928374",
     "created_at": 1790939000.0,
     "expires_at": 1790939300.0
   }
   ```
5. **Reality Verification & Causality Loop**:
   Every mutating action must specify an observation method. Actions transition through `PENDING -> EXECUTED -> VERIFIED`. Any ambiguous response transitions to `UNKNOWN_OUTCOME` and triggers reconciliation; blind automated retry is strictly prohibited.
