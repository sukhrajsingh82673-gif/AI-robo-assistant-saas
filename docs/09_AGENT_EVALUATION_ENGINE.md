# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Agent Evaluation Engine Specification

---

### 1. Mandatory 13-Vector Evaluation Matrix
The `AgentEvaluationEngine` (`core/agent_evaluation_engine.py`) enforces strict certification criteria. AI agents are constitutionally prohibited from self-certifying.

| Vector | Target Scope | Minimum Passing Score | Failure Mitigation |
| :--- | :--- | :---: | :--- |
| **SECURITY** | Tool injection & host escape prevention | 100% | Immediate package rejection |
| **RELIABILITY** | Crash recovery & state checkpointing | 85% | Re-test with fault injection |
| **POLICY_COMPLIANCE**| Self-modification & authority bounds | 100% | Blocked permanently |
| **TOOL_USE** | Parameter validation & typing | 90% | Schema refinement |
| **REASONING_BEHAVIOR**| Goal convergence without oscillation | 85% | Prompt graph tuning |
| **LOOP_DETECTION** | Infinite delegation & recursion stops | 100% | Max depth 4 enforced |
| **COST** | Token budget compliance | 90% | Admission quota reduction |
| **LATENCY** | P95 step latency < 2,500ms | 80% | Model tier adjustment |
| **DATA_LEAKAGE** | Cross-tenant memory isolation | 100% | Immediate quarantine |
| **PROMPT_INJECTION** | Neutralization of adversarial jailbreaks | 90% | Guardrail escalation |
| **FAILURE_RECOVERY** | UNKNOWN_OUTCOME reconciliation protocol | 95% | Retrying prohibited |
| **OUTCOME_VERIFICATION**| Evidence-backed commercial verification | 95% | Human review required |
| **TENANT_ISOLATION** | Cryptographic token tenant scoping | 100% | Immediate rejection |
