# ZONATA V7 — Employee Template Architecture & Dual-Workforce Generation
**Document ID:** ZONATA-V7-ARCH-001  
**Classification:** ENTERPRISE WORKFORCE SPECIFICATION  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. Executive Summary & Design Principle

ZONATA V7 introduces a second workforce generation pathway without replacing, deprecating, or modifying any pre-existing specialist agents or open-source framework integrations (Agency Swarm, Letta, HAL, LangGraph, A2A, MCP, OpenHands, Browser Use, Temporal, Nango):

> **Core Principle:** Pre-built agents provide reusable specialist capabilities; Template-built AI Employees provide company- and project-specific behavior, SOPs, KPIs, KRAs, authority scopes, and workflow alignment. The AI CEO coordinates both independently or enables them to collaborate as colleagues under a unified organizational hierarchy.

```
                      +-----------------------------+
                      |         HUMAN OWNER         |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |           AI CEO            |
                      | (Strategic Orchestrator)    |
                      +--------------+--------------+
                                     |
             +-----------------------+-----------------------+
             |                                               |
             v                                               v
+-------------------------+                     +-------------------------+
|   TYPE A: PRE-BUILT     |                     |    TYPE B / TYPE C:     |
|   SPECIALIST AGENTS     |                     | TEMPLATE AI EMPLOYEES   |
| (Sales, Research, Dev,  |                     | (Company/Project Roles, |
|  Browser, Analyst, Ops) |                     |  SOPs, KPIs, KRAs, ACL) |
+------------+------------+                     +------------+------------+
             |                                               |
             +-----------------------+-----------------------+
                                     |
                                     v
                      +-----------------------------+
                      |    COLLEAGUE COLLABORATION  |
                      |  (Mission Teams & Hierarchy)|
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    ZONATA GOVERNANCE GATE   |
                      |  (Action Gateway, DLP, WORM)|
                      +-----------------------------+
```

---

## 2. Distinction: Template vs Agent vs Employee

| Concept | Definition | Mutability | Lifecycle Persistence |
| :--- | :--- | :--- | :--- |
| **AGENT** | Capability-oriented execution specialist (e.g. Browser Robot, Research Agent, OpenHands Runner). | Pinned version | Stateless / Ephemeral task execution |
| **EMPLOYEE TEMPLATE** | Governed operational specification (role, responsibilities, SOPs, KPIs, KRAs, authority, tools, autonomy). | Immutable versioned blueprint | Specification level (blueprint) |
| **AI EMPLOYEE** | Governed persistent business-role workforce member instantiated from a template or registry. | Controlled version succession | Persistent across missions; distinct operational identity |
| **MISSION** | High-level business objective decomposed into Directed Acyclic Graph (DAG) tasks. | State tracked | Bound to causal outcome |

---

## 3. The 3 Workforce Types

1. **TYPE A — PRE-BUILT SPECIALISTS:**
   - Universal capabilities: Sales Specialist, Research Specialist, Developer, Browser Robot, Data Analyst, Customer Support, Financial Reconciler.
   - Reusable across all tenants and companies without bespoke domain retraining.
2. **TYPE B — UNIVERSAL TEMPLATE EMPLOYEES:**
   - General-purpose corporate roles: Universal Revenue Manager, General Marketing Director, Corporate Compliance Auditor.
   - Configured with standard corporate SOPs and organizational hierarchy.
3. **TYPE C — PROJECT-SPECIFIC TEMPLATE EMPLOYEES:**
   - Tailored to a single company, department, project, or temporary initiative (e.g., *Royal Hotel Jaipur — Revenue Optimization Specialist*).
   - Strictly isolated to the originating tenant and company boundaries.

---

## 4. Governance Guarantees

- **No Self-Authorization:** Neither pre-built specialists nor template employees can elevate their own autonomy, bypass budget limits, or access data outside their classification clearance.
- **Unified Action Gateway:** All external tool mutations pass through the same idempotent, DLP-scrubbed, policy-evaluated Action Gateway.
