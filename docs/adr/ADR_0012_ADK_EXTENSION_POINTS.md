# ADR 0012: Google Agent Development Kit (ADK) Extension Points & Governance

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4F — Multi-agent teams, hierarchy, and critic loops  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
Google Agent Development Kit (`google-adk`) is adopted to orchestrate multi-agent hierarchical teams (Agent Factory department squads and Step 3 research teams) featuring parallel specialists, loop critics, and workflow agents.

Standing Rules 5, 33, 34, and 40 dictate:
- ADK must operate strictly behind `AgentRuntimePort`.
- ADK agents must NEVER bypass `LLMGateway` or call external tools directly.
- ADK built-in tools (e.g. web search, code executor) must remain disabled unless wrapped.
- Upstream releases must be pinned and tested against regression suites.

## 2. Package Provenance & Licensing
- **Licence:** Apache-2.0 (Permissive; compliant with Standing Rule 5).
- **Release Cadence:** Weekly releases upstream.
- **Pinning Policy:** Pinned to exact minor/patch version in `requirements.txt` with cryptographic SHA-256 hashes. Automated dependency upgrades are gated through CI regression suites.

## 3. Decision
Google Agent Development Kit (`google-adk`) is adopted strictly as a multi-agent orchestration runtime adapter behind `AgentRuntimePort`. All model invocations, tool executions, and sessions must route through ZONATA governance ports (`LLMGateway`, `ActionGateway`, and encrypted persistence). Native un-governed tool execution or model access is strictly disabled.

## 4. Extension Points and Wrappers
1. **Model Gateway Wrapper (`ZonataADKModel`):** Implements ADK's model interface, routing every token generation request through `LLMGateway` for tier selection, budget accounting, policy checks, and evidence ledger logging.
2. **Tool Wrapper (`ZonataADKToolWrapper`):** Wraps ZONATA `ToolContract` tools into ADK-compatible tools. All executions enforce idempotency keys (Rule 35) and ActionGateway approvals.
3. **Session & Memory Service (`ZonataADKSessionService`):** Custom session store backed by PostgreSQL with RLS and `KeyPort` encryption, preventing cross-tenant leakage.
4. **Tool Confirmation Hooks:** ADK's `before_tool_callback` maps directly to ZONATA's ActionGateway approval pipeline.
5. **Team Bounds:** Enforces hard limits: maximum delegation depth ($\le 3$), maximum fan-out ($\le 8$), maximum loop iterations ($\le 5$), and spend caps in micro-units.
