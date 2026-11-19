# ZONATA V3 — Supply Chain & Open-Source License Audit

## 1. Open-Source Component Inventory & Licensing Analysis
| Subsystem / Project | Upstream Library / Tool | Upstream License | ZONATA Architectural Implementation | Commercial / SaaS Compliance Verdict |
|---|---|---|---|---|
| **01 — Agency Swarm** | Agency Swarm | MIT | Internal Workforce Planner & Swarm Orchestrator | **COMPLIANT** (Permissive commercial use) |
| **02 — Mem0** | Mem0 | Apache-2.0 | Stateful Organizational Memory Gateway | **COMPLIANT** (Permissive commercial use) |
| **03 — HAL** | HAL Multimodal | MIT | Hardware Abstraction Layer & Desktop Observer | **COMPLIANT** (Permissive commercial use) |
| **04 — LangGraph** | LangGraph | MIT | Durable Multi-Agent DAG State Machine | **COMPLIANT** (Permissive commercial use) |
| **05 — A2A** | Agent-to-Agent Mesh | Apache-2.0 | Governed Interoperability Protocol & Escrow | **COMPLIANT** (Permissive commercial use) |
| **06 — MCP** | Model Context Protocol | MIT | Centralized MCP Server & Tool Gateway | **COMPLIANT** (Permissive commercial use) |
| **07 — OpenHands** | OpenHands | MIT | Sandboxed Agent Software Engineering Runtime | **COMPLIANT** (Permissive commercial use) |
| **08 — Browser Use** | Browser Use | MIT | Governed Autonomous Browser Gateway | **COMPLIANT** (Permissive commercial use) |
| **09 — Temporal** | Temporal IO | MIT | Durable Workflow & Long-Running Reliability | **COMPLIANT** (Permissive commercial use) |
| **10 — Nango** | Nango | **Elastic License 2.0 (ELv2)** | Internal Infrastructure Dependency / Adapter | **COMPLIANT UNDER STRICT POLICY** |

---

## 2. Elastic License 2.0 Governance Notice
> [!IMPORTANT]
> Nango is licensed under Elastic License 2.0. ELv2 strictly prohibits providing Nango directly as a managed service or SaaS to third parties.
> 
> **Enforced Governance:** ZONATA integrates Nango exclusively as an internal infrastructure adapter/dependency for internal enterprise SaaS operations. ZONATA does NOT resell, rehost, or offer Nango API access to external developers.

---

## 3. Dependency Pinning & Supply Chain Controls
- All Python dependencies adhere to pure standard library implementations or verified MIT/Apache packages.
- Docker multi-stage builds employ deterministic Debian stable base images with pinned packages.
- Zero untrusted dynamic code execution or unverified third-party binaries.
