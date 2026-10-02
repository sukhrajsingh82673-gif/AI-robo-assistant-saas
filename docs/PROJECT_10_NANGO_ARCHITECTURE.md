# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Governed External System Connectivity & Integration Architecture

### 1. Architectural Role & Sovereign Hierarchy

Nango is integrated into ZONATA strictly as the **Governed External System Connectivity & Integration Layer**. It serves as an infrastructure component connecting ZONATA with over 1,000+ real-world enterprise business systems (CRM, ERP, HRIS, Accounting, Marketing, Communication, Payments, Storage, Ticketing, DevOps, and E-Commerce), while remaining subordinate to ZONATA's executive cognition, policy governance, and truth verification.

```
ZONATA Universal AI Company Operating System
  └── AI CEO Brain (Cognition & 16-Stage Operating Loop)
       └── Agency Swarm (Workforce Delegation & Specialist Squads)
            └── Mission System (Enterprise Missions & OKRs)
                 └── TaskMaker (Deterministic Task Decomposition)
                      └── LangGraph (Cognitive Flow & StateGraph Orchestration)
                           └── Temporal (Durable Execution & Long-Running Reliability)
                                └── ZONATA Integration Gateway (ExternalIntegrationGateway)
                                     └── Nango Adapter (NangoAdapter)
                                          └── External Business Systems
                                               (Salesforce, HubSpot, Stripe, QuickBooks, Google, Slack, Jira, GitHub)
```

**Surrounding Governance Envelope:**
* `PolicyEngine`: Action approval policies, spending thresholds, and scope boundaries.
* `AuthorityGateway`: Epistemic checks enforcing `capability != authority`.
* `ApprovalEngine`: Human-in-the-loop escalation for `FINANCIAL`, `PRIVILEGED`, and `DESTRUCTIVE` operations.
* `CredentialVault`: Vaulted secret brokerage with opaque handles (`cred_nango_...`).
* `IntegrationKillSwitch`: Multi-scope emergency halt across 8 distinct tiers.
* `EvidenceLedger`: Cryptographic SHA-256 Merkle tree audit sealing.
* `BusinessCausalityEngine`: Lineage tracking enforcing `TASK_SUCCESS != BUSINESS_OUTCOME`.

---

### 2. Upstream Nango Alignment & Boundaries

* **Upstream Repository**: `https://github.com/NangoHQ/nango`
* **Version Baseline**: `0.64.0` / API v1
* **License**: Elastic License 2.0 (ELv2)
* **Integration Boundary**: ZONATA communicates with Nango exclusively through the abstract `ExternalIntegrationProvider` and concrete `NangoAdapter`. Nango SDK internals are never exposed to ZONATA business logic, AI CEO cognition, or agent memory blocks.
* **Replaceability**: If infrastructure requirements change, `NangoAdapter` can be replaced with direct API connectors, Composio, or custom gateways without altering ZONATA's CEO, workforce, LangGraph, or Temporal orchestrations.

---

### 3. Core Architectural Components

1. **`ExternalIntegrationGateway` (`core/nango_integration_runtime.py`)**:
   Primary ZONATA facade providing unified lifecycle management for providers, connections, actions, webhooks, and synchronizations.
2. **`NangoAdapter` (`core/nango_integration_runtime.py`)**:
   Concrete implementation of `ExternalIntegrationProvider` interfacing with the Nango engine or standard library handlers.
3. **`IntegrationSecurityBoundary` (`core/nango_integration_runtime.py`)**:
   Context Firewall enforcing regex credential scrubbing (`[REDACTED_CREDENTIAL]`, `[REDACTED_TOKEN]`), prompt injection neutralization, and opaque handle isolation.
4. **`IntegrationKillSwitch` (`core/nango_integration_runtime.py`)**:
   Multi-scope emergency halt authority (Global, Tenant, Company, Mission, Agent, Capability, Provider, Connection).
5. **`RateLimitGovernor` (`core/nango_integration_runtime.py`)**:
   Sliding window quota tracker enforcing tenant and company fairness and exponential backoff.
6. **`NangoSubsystemBridges` (`zonata/nango_adapter.py`)**:
   Bridges connecting Nango with AI CEO, Agency Swarm, LangGraph, Temporal, MCP, Browser Use, OpenHands, and A2A.
