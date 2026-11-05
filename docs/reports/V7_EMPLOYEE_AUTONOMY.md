# ZONATA V7 — Employee Autonomy Governance (Levels 0–5)
**Document ID:** ZONATA-V7-AUTONOMY-010  
**Classification:** RISK BOUNDING & ACTION AUTHORIZATION SPECIFICATION  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. Formal Autonomy Tiers (Levels 0 to 5)

Every Template-built employee is configured with an explicit operational autonomy ceiling:

| Level | Designation | Permitted Actions | Spend Limit | Human Approval Trigger | Delegation Permitted |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | `MANUAL` | Suggestions / drafts | $0.00 | Every tool call | NO |
| **1** | `ASSISTIVE` | `READ_ONLY` tools | $0.00 | Any mutation | NO |
| **2** | `CONDITIONAL` | `READ_ONLY`, `LOW_RISK_MUTATING` | $50.00 | Any action > $50 or Mutating | YES (Level $\le 1$) |
| **3** | `BOUNDED` | Standard domain mutations | $500.00 | Exceeding budget or risk ceiling | YES (Level $\le 3$) |
| **4** | `HIGH_AUTONOMY` | Cross-system mutations | $2,500.00 | Financial > $2,500 or Destructive | YES (Level $\le 4$) |
| **5** | `FULL_AUTONOMY` | Strategic autonomous missions | $10,000.00 | Core sovereignty breach only | YES (Level $\le 5$) |

---

## 2. Delegation Containment (`CHILD ⊆ PARENT`)

When an employee with delegation rights spawns a child worker:
1. `Child.AutonomyLevel <= Parent.AutonomyLevel`
2. `Child.DelegatedBudget <= Parent.RemainingBudget`
3. `Child.AllowedTools` $\subseteq$ `Parent.AllowedTools`
4. `Child.AllowedDataDomains` $\subseteq$ `Parent.AllowedDataDomains`
5. `Child.RiskClass <= Parent.RiskClass`

- **Enforcement:** Attempting to spawn a child with broader permissions or excessive budget raises `DelegationViolationError` and halts execution.
