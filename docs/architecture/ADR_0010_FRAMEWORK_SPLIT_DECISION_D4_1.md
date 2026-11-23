# ADR 0010: Framework Split and Responsibility Allocation (Decision D4-1)

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4B — Architectural boundary between Temporal, LangGraph, ADK, and ZONATA Gateway  
**Deciders:** ZONATA Systems Architecture (Owner-Approved)  

---

## 1. Context and Problem Statement
To build a resilient enterprise AI system, orchestration responsibilities must be cleanly divided among specialized runtimes without overlap, circular dependencies, or authority leakage.

Standing Rule 33 states: **Frameworks are replaceable runtime adapters.** They hold execution state only, never authority, budgets, policies, or approvals.

## 2. Decision D4-1 Role Matrix

| Layer | Owns | Does NOT Own |
|:---|:---|:---|
| **Temporal** | Durability across minutes to days: company builds, approval chains, goal cadences, SOP instances, SLA timers, schedules, retries, cancellation (kill switch), signals. | Reasoning, LLM prompt engineering, tool execution logic. |
| **LangGraph** | One position's controllable reasoning graph inside a bounded step: employee task graph, maker-checker graph, CEO planning graph with owner interrupts. | Cross-day durability, multi-agent team coordination, long-term state. |
| **Google ADK** | **Multi-agent teams** requiring hierarchy, delegation, parallel fan-out, and critic loops: Agent Factory department teams and Step 3 research teams. | Durable backbone, single-employee graphs, authority decisions. |
| **ZONATA Gateway** | Every decision about whether something may happen, authority profile checks, budgets, kill switches, and immutable evidence ledger recording. | Nothing is delegated away from it. |

## 3. Strict Nesting & Independence Rules
1. **Zero Cross-Framework Imports:** LangGraph and Google ADK code must never import each other or Temporal SDKs.
2. **Activity Invocation Pattern:** When a LangGraph node requires a multi-agent team, it calls `AgentRuntimePort.run(team=...)`, which Temporal runs as a separate, bounded activity.
3. **Internal Gateway Routing:** Inside the platform, all agent and framework communication routes through typed ZONATA ports (`LLMGateway`, `ToolRegistry` $\rightarrow$ `ActionGateway`). A2A is reserved strictly for external third-party agent interop.
