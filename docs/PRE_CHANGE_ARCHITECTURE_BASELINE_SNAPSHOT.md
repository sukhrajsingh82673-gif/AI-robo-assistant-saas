# ZONATA / URA Universal AI Company Operating System
## Pre-Change Architecture Baseline Snapshot & Compatibility Freeze

> **Snapshot Timestamp:** `2026-10-05T04:17:00Z`  
> **Git Commit Hash:** `f0ba68d`  
> **Active Branch:** `main`  
> **Working Tree Status:** Clean (`nothing to commit, working tree clean`)  
> **Operating Environment:** Linux (Multi-core x86_64 / aarch64 container runtime)  
> **Python Version:** 3.14.3  
> **Discovered Unit & Integration Tests:** 823 tests across 57 test files in `tests/`  
> **Database State:** SQLite (`storage/roboassistant.db`) with 191 normalized relational tables  
> **Active Merkle Ledger:** Verified chain in `storage/evidence/audit_ledger.jsonl`  
> **Active Daemon:** `api_server.py 8080` (Multi-threaded HTTP/REST API server)

---

### 1. Existing System Architecture Freeze

The existing sovereign authority hierarchy is frozen and will remain strictly immutable:

```
HOST / SOVEREIGN AUTHORITY (Human Owner / Sovereign Keys)
       ↓
ZONATA COMPANY KERNEL (Physical Truth, Merkle Ledger, Invariants)
       ↓
AI CEO EXECUTIVE OPERATING LAYER (Gemma 4 Governed Cognition, Strategy, Reflection)
       ↓
AGENCY SWARM (Department Chiefs, Coworkers, Dynamic Teams)
       ↓
MISSION & STRATEGIC PRIORITIES (Executive Planning DAG, Attention Queue)
       ↓
TASKMAKER (Task Decomposition, Idempotency, Compensation Plans)
       ↓
WORKFLOW / DURABLE EXECUTION RUNTIME (Temporal, State Machine, Outbox)
       ↓
AGENTS & COWORKERS (Hermes, OpenClaw, Letta Stateful Memory, OpenHands)
       ↓
TOOLS / EXTERNAL SYSTEMS (Universal Terminal, Browser Use, MCP, A2A, HAL, Connectors)
       ↓
EVIDENCE LEDGER & OUTCOME (Cryptographic Receipts, Merkle Proofs, Physical Verification)
```

---

### 2. Frozen Core Subsystems & Components

The following 26 foundational subsystems are validated, active, and strictly frozen against architectural regression or replacement:

1. **ZONATA Kernel** (`core/control_kernel.py`): Sovereign execution invariants, zero-mock gatekeeper.
2. **PolicyEngine** (`core/policy_engine.py`, `core/policy_engine_v2.py`): Deterministic constitutional governance.
3. **ApprovalEngine** (`core/approvals.py`, `core/decision_center.py`): Multi-tier human-in-the-loop (HITL) authorization.
4. **AuthorityGateway** (`core/authority_gateway.py`): Capability != Authority gateway.
5. **EvidenceLedger** (`core/evidence_ledger.py`): Cryptographic SHA-256 / Merkle tree audit logging with `fcntl.flock` and crash-safe `fsync`.
6. **KillSwitchMatrix** (`core/killswitch_matrix.py`): Immediate, out-of-band operational containment.
7. **AI CEO Operating Layer** (`core/ai_ceo_v8.py`, `core/ceo_conversation_engine.py`): Governed Google Gemma 4 executive cognitive engine.
8. **Agency Swarm** (`core/workforce.py`, `core/team_catalog.py`): Departmental workforce and dynamic coworker provisioning.
9. **Letta Stateful Agent Memory** (`core/stateful_agent_runtime.py`): Hierarchical conversational and archival memory.
10. **LangGraph Workflows** (`core/workflow_engine.py`): Graph-based agent execution DAGs.
11. **A2A Communication Protocol** (`core/a2a_runtime.py`): Agent-to-Agent authenticated messaging and task handoffs.
12. **MCP Interoperability Runtime** (`core/mcp_interoperability_runtime.py`): Model Context Protocol bridge for enterprise tools.
13. **OpenHands Execution Runtime** (`core/openhands_execution_runtime.py`): Sandboxed software engineering and terminal execution.
14. **Browser Use Runtime** (`core/browser_runtime.py`): Headless Chromium browser automation with DOM grounding.
15. **HAL Multimodal Runtime** (`core/hal_runtime.py`, `core/multimodal_capability_runtime.py`): Audio/visual/document cognitive processing.
16. **Universal Linux Terminal Execution Fabric** (`core/universal_terminal/`): Sandboxed bash execution with PTY, snapshot rollback, and Honest Hardware Degradation.
17. **Temporal Durable Execution Runtime** (`core/temporal_durable_execution_runtime.py`): Workflows, activities, compensation sagas, and retries.
18. **NATS JetStream Event Fabric** (`core/nats_jetstream.py`): Multi-tenant streaming, deduplication, and at-least-once message delivery.
19. **HashiCorp Vault Client** (`core/vault_client.py`): Dynamic secrets, lease management, and tenant key isolation.
20. **Keycloak OIDC IdP** (`core/keycloak_idp.py`): OpenID Connect authentication, JWT parsing, and session revocation.
21. **OpenFGA Authorization Engine** (`core/openfga_engine.py`): Fine-grained relationship-based access control (ReBAC).
22. **MinIO / S3 Object Storage** (`core/object_storage.py`): Multi-bucket tenant artifact and document storage.
23. **OpenTelemetry Engine** (`core/opentelemetry_engine.py`): Distributed W3C context tracing and metrics collection.
24. **Langfuse LLM Observability** (`core/langfuse_engine.py`): Prompt tracing, token accounting, and cost tracking.
25. **SaaS Billing & Subscriptions** (`core/saas_billing.py`): Idempotent customer charging and usage metering.
26. **PostHog Analytics** (`core/posthog_analytics.py`): Product analytics, funnels, and feature flag management.

---

### 3. Frozen Technology Boundaries

- **Secret Management:** HashiCorp Vault is ACTIVE. **DO NOT** integrate OpenBao alongside Vault.
- **Identity Provider:** Keycloak OIDC is ACTIVE. **DO NOT** integrate ZITADEL alongside Keycloak.
- **Agent Frameworks:** Agency Swarm, Letta, OpenHands, and A2A are ACTIVE. **DO NOT** add CrewAI, AutoGen, or parallel frameworks.
- **Workflow Engines:** Temporal is ACTIVE. **DO NOT** add another workflow engine.
- **Message Bus:** NATS JetStream is ACTIVE. **DO NOT** add Kafka or RabbitMQ.

---

### 4. Baseline Metrics & Configuration

| Metric / Property | Baseline Value |
| :--- | :--- |
| **Total Passing Tests** | 823 tests across 57 test modules |
| **Database Schema** | 191 tables in `storage/roboassistant.db` |
| **Active Port** | 8080 (REST API & Web Workspace) |
| **API Endpoints** | 191 route handlers in `core/production_api.py` & `core/v8_api_handler.py` |
| **Merkle Evidence Ledger** | `storage/evidence/audit_ledger.jsonl` (Integrity Verified) |
| **Current Git Commit** | `f0ba68d` |

---

### 5. Architectural Non-Regression Commitment

Any infrastructure, deployment orchestration, network isolation, edge security, or disaster recovery capabilities added during this phase will remain strictly subordinate to the ZONATA sovereign kernel and must not induce any regression across the 823 existing tests.
