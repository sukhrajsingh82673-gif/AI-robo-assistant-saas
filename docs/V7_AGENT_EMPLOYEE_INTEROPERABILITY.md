# ZONATA V7 — Agent + Employee Interoperability & Colleague Teams
**Document ID:** ZONATA-V7-INTEROP-008  
**Classification:** INTEROPERABILITY & MISSION TEAM SPECIFICATION  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. Colleague Collaboration Model

ZONATA V7 proves that pre-built specialist agents and template-built employees are not mutually exclusive. They form synergistic mission teams:

```
[Mission: Q4 Jaipur Resort Digital Campaign & Direct Revenue Expansion]
                                |
                                v
               [Mission Team Leader (Template AI Employee)]
               - Role: Hotel Revenue Optimization Specialist
               - Context: Royal Hotel Jaipur SOPs, pricing floor, ADR targets
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
[Pre-Built Specialist]  [Pre-Built Specialist]  [Pre-Built Specialist]
Research Specialist     Browser Robot           Data Analyst
(Competitive scraping) (OTA portal verification)(Lead conversion model)
```

### Collaboration Roles
- **Mission Lead (Template Employee):** Holds company-specific context, sets pricing limits, and validates that outputs conform to corporate SOPs.
- **Specialist Colleagues (Pre-Built Agents):** Execute specialized tasks (e.g. web browsing, deep research, code execution) without needing to understand broad company policy.

---

## 2. Deterministic Conflict Resolution (Zero LLM Guesswork)

When team members disagree (e.g., Sales Specialist advocates a 25% discount to close a deal fast, while the Revenue Employee allows a maximum 15% discount per SOP):

```
                       [Disagreement Detected]
                                  |
                                  v
              [Prohibit Resolution by Model Confidence]
             (LLM self-confidence is strictly non-binding)
                                  |
                                  v
                [Policy & Evidence Hierarchy Check]
                1. Inspect corporate pricing policy in DB
                2. Check CEO & Human Owner rule ceilings
                3. Check historical KPI achievement data
                                  |
                                  v
                 [Chief Officer Ruling & Evidence Seal]
                "Revenue policy caps maximum unapproved discount
                 at 15%. Ruling in favor of Revenue Employee."
```

- **Result:** Conflicts are resolved with 100% determinism based on corporate authority, preserving financial safety.
