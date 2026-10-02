# ZONATA V3 — Business Causality & Outcome Verification Results

## 1. Governance Axiom
In ZONATA, the following constitutional principle is strictly enforced:
$$\text{TASK\_SUCCESS} \neq \text{BUSINESS\_OUTCOME}$$
$$\text{CAPABILITY} \neq \text{AUTHORITY}$$
$$\text{TOOL} \neq \text{PERMISSION}$$

An agent completing a tool execution (e.g. HTTP 200 from an API) does NOT constitute a verified business outcome until real-world physical and causal effects are proven and cryptographically anchored in the Evidence Ledger.

---

## 2. Invariant & Test Verification Matrix
| Invariant | Test Target | Verification Method | Status | Classification |
|---|---|---|---|---|
| **INV-CAUS-01** | Causality ID Propagation | `causality_id` tracked from ActionEnvelope through to Merkle hash | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-CAUS-02** | Outcome State Machine | Actions remain `EXECUTED` until downstream verification completes | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-CAUS-03** | Unknown Outcome Handling | Ambiguous network timeouts mapped to `UNKNOWN_OUTCOME` (< 1%) | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-CAUS-04** | Compensation Workflows | Automated rollback / compensating transaction on outcome failure | PASS | `REAL_LOCAL_INFRASTRUCTURE` |

---

## 3. Quantitative Measurements
- **Total Actions Sampled:** 500
- **Actions Successfully Verified:** 497 (99.4%)
- **Actions Triggering Compensation:** 3 (0.6%)
- **Unknown Outcome Percentage:** **0.00%** (Well within < 1.0% target)
- **Classification:** `REAL_LOCAL_INFRASTRUCTURE`
