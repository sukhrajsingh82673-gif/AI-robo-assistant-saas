# ZONATA / URA — Enterprise Integration Architecture

## 1. Constitutional Architecture Invariant

ZONATA enforces strict hierarchical sovereign authority. No external connector, model router, or workflow engine may bypass this governing execution chain:

```
HOST / SOVEREIGN AUTHORITY
   └── ZONATA COMPANY KERNEL
         └── AI CEO (Executive Missions)
               └── AGENCY SWARM
                     └── MISSION
                           └── TASKMAKER
                                 └── EXISTING WORKFLOW / EXECUTION RUNTIME (UCK / Fabric)
                                       └── SPECIALIZED AGENTS
                                             └── GOVERNED CONNECTORS & EXTERNAL SYSTEMS
                                                   └── EVIDENCE LEDGER (Merkle Trees)
                                                         └── BUSINESS-OUTCOME VERIFICATION
```

The ZONATA Kernel remains the **sole authority** for execution authorization, policy decisions, approvals, tenant isolation, evidence acceptance, risk controls, kill switches, and business verification.

---

## 2. Governed Integration Contract

Every enterprise connector adheres to a unified specification implemented in [`core/automation_fabric/contracts.py`](../../core/automation_fabric/contracts.py) and [`core/automation_fabric/enterprise_connectors.py`](../../core/automation_fabric/enterprise_connectors.py):

1. **Unique Connector ID & Version:** Pinned semantic version and unique identifier.
2. **Capability Declarations:** Explicit list of supported operations.
3. **Input & Output JSON Schemas:** Validated prior to external invocation.
4. **Authentication Requirements:** Mediated exclusively via [`SecretManager`](../../core/secrets.py) and HashiCorp Vault. Zero raw secrets in prompts or logs.
5. **Multi-Tenant Isolation:** Mandatory `tenant_id` scoping on every call; cross-tenant operations fail closed with `403 TenantIsolationViolation`.
6. **Risk Classification:**
   - `SAFE`: Read-only, idempotent query (e.g. document retrieval, KPI query).
   - `CONFIRM`: Reversible mutation with state change (e.g. CRM lead creation).
   - `DANGEROUS`: External integration promotion or infrastructure modification.
   - `CRITICAL`: Financial, credential, destructive, or irreversible (e.g. ERP purchase order > $1,000).
7. **SSRF Defense:** Prohibits cloud metadata (`169.254.169.254`), loopback (`127.0.0.1`, `localhost`), and unvetted CIDR ranges.
8. **Token-Bucket Rate Limiter:** Per-connector configurable RPM capacity.
9. **Circuit Breakers:** Per-connector state machine (`CLOSED` -> `OPEN` -> `HALF_OPEN`) halting requests on consecutive faults.
10. **Crash-Window Idempotency:** Durable SQLite table `automation_connector_idempotency` preventing duplicate execution across worker crashes.

---

## 3. The 15 Open-Source Enterprise Capabilities

| Area | Capability | Primary Open-Source Project | License | Connector ID |
| :--- | :--- | :--- | :--- | :--- |
| **A** | Enterprise Integration & Messaging | Apache Camel | Apache-2.0 | `conn_apache_camel` |
| **B** | AI Model Gateway & Local Inference | LiteLLM / vLLM | MIT / Apache-2.0 | `conn_litellm_gateway` |
| **C** | Document Extraction & OCR | Apache Tika / Tesseract OCR | Apache-2.0 | `conn_apache_tika_ocr` |
| **D** | Enterprise Hybrid Search & Vector | OpenSearch / Qdrant | Apache-2.0 | `conn_opensearch_qdrant` |
| **E** | ERP & Operational Business Records | ERPNext / Frappe Framework | MIT / GPL-3.0 | `conn_erpnext_records` |
| **F** | CRM & Sales Operations | SuiteCRM | Apache-2.0 API Client | `conn_suitecrm_sales` |
| **G** | Support & ITSM Tickets | Zammad / GLPI | Apache-2.0 API Client | `conn_zammad_glpi_support` |
| **H** | Collaboration & Open Protocols | Nextcloud Server (WebDAV, CalDAV, SMTP) | Apache-2.0 Client | `conn_nextcloud_collaboration` |
| **I** | Business Intelligence & Analytics | Apache Superset / dbt Core | Apache-2.0 | `conn_superset_dbt_analytics` |
| **J** | Data Ingestion & Sync | Meltano | MIT | `conn_meltano_sync` |
| **K** | Runtime Threat Detection | Falco / Wazuh | Apache-2.0 | `conn_falco_wazuh_security` |
| **L** | GitOps & Controlled Delivery | Argo CD | Apache-2.0 | `conn_argocd_gitops` |
| **M** | Adversarial AI Evaluation | promptfoo | MIT | `conn_promptfoo_eval` |
| **N** | Multi-Tenant Communications | Matrix Synapse | Apache-2.0 Client | `conn_matrix_synapse_comms` |
| **O** | Feature Rollouts & Flags | OpenFeature | Apache-2.0 | `conn_openfeature_flags` |

---

## 4. Governed Execution Lifecycle

Every business operation passes through the standard 9-stage authority gate:

```
[User / AI CEO Request]
          │
          ▼
   1. Strict Tenant Authentication (api_server.py)
          │
          ▼
   2. PolicyEngine V2 Evaluation (core/policy_engine_v2.py)
          │
          ▼
   3. Approval Gate Check (Sensitive write actions pause for executive approval)
          │
          ▼
   4. HMAC-SHA256 Execution Lease Generation (fabric.py)
          │
          ▼
   5. SSRF & Schema Validation (connector_registry.py)
          │
          ▼
   6. Connector Dispatch via Token-Bucket & Circuit Breaker
          │
          ▼
   7. External Outcome Read-Back & State Verification
          │
          ▼
   8. Merkle Audit Digest Sealing (EvidenceLedger)
          │
          ▼
   9. User-Accessible Verified Result
```
