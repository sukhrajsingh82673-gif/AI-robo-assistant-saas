# ADR 0014: Agent-to-Agent (A2A) Protocol Evaluation & Scope

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4F — External agent interoperability  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
Agent-to-Agent (A2A) protocol enables communication between independent external AI agents. The repository contains a 1,488-line custom simulation (`core/a2a_interoperability_runtime.py`).

Step 4 mandates:
- Evaluating upstream A2A SDK maturity.
- Enforcing Decision D4-1: Platform agents communicate strictly through ZONATA ports (`LLMGateway`, `ToolRegistry` $\rightarrow$ `ActionGateway`), not via peer-to-peer A2A, so the ActionGateway has complete visibility and authority.
- Evaluating whether external A2A interop should be adopted or designated `NOT_ADOPTED`.

## 2. Evaluation of Upstream A2A SDK
- Upstream Python SDK (`a2a-sdk`) is currently pre-v0.4 and undergoing rapid specification shifts without stable backward compatibility guarantees.
- Internal platform orchestration does not need A2A: ZONATA's sovereign port architecture, Temporal workflows, and Google ADK team coordinators provide far superior governance, cryptographic non-repudiation, and spend enforcement.

## 3. Decision
1. **Internal Orchestration:** A2A is strictly excluded from internal agent-to-agent communication.
2. **External Interoperability:** A2A is evaluated exclusively as an external bridge (`ExternalAgentPort`). Due to SDK volatility, external A2A integration is designated **`NOT_ADOPTED`** for production platform operations in Step 4, pending upstream standardization and security hardening.
3. **Adoption Register:** In accordance with Standing Rule 37, A2A will be recorded as `NOT_ADOPTED` in `docs/reports/ADOPTION_STATUS.md`.
