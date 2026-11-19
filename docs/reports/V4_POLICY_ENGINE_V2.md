# ZONATA V4 — ENTERPRISE POLICY ENGINE V2 (ABAC GOVERNANCE)
**Multi-Dimensional Context Evaluation, Decision Taxonomy, & Quorum Approvals**

## 1. Multi-Dimensional Policy Dimensions
Policy Engine V2 (`core/policy_engine_v2.py`) evaluates every operational request across 8 independent dimensions:
1. **WHO**: Requester Identity, Type (`HUMAN`, `AI_EMPLOYEE`, `SERVICE`), Roles, Departments.
2. **WHAT**: Action requested (`READ`, `MUTATE`, `EXECUTE`, `FINANCIAL_TRANSFER`, `DELETE`).
3. **WHY**: Business justification, parent mission ID.
4. **WHICH DATA**: Target data object, classification level (`PUBLIC` to `HIGHLY_RESTRICTED`), sensitivities.
5. **WHICH TOOL**: Tool identifier, tool risk class (`READ_ONLY`, `LOW_RISK`, `MUTATING`, `FINANCIAL`, `DESTRUCTIVE`).
6. **WHICH MODEL**: Model tier requested, sovereign vs cloud designation.
7. **WHICH BUDGET**: Requested spend, remaining employee budget ceiling.
8. **WHICH RISK**: Systemic blast radius and irreversibility score.

---

## 2. Decision Taxonomy
- `ALLOW`: Request unconditionally approved for execution.
- `ALLOW_WITH_RESTRICTIONS`: Request approved with mandatory audit logging, cache disabling, or data masking.
- `REQUIRE_APPROVAL`: Request halted; requires human-in-the-loop authorization (e.g., Finance Director approval).
- `DENY`: Request permanently rejected due to policy breach.
- `ESCALATE`: High-value operations (e.g., spend >= $5,000) escalated directly to Executive Council.
