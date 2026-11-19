# ZONATA V7 — Employee Performance Review & Continuous Feedback Loop
**Document ID:** ZONATA-V7-PERF-012  
**Classification:** PERFORMANCE GOVERNANCE & OBSERVABILITY SPECIFICATION  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. Continuous Performance Evaluation Loop

ZONATA V7 does not evaluate employees based on subjective opinions. Performance is calculated continuously via measurable KPI outcomes and operational vitals:

```
[Completed Missions]
          |
          v
[KPI Measurements + Verification Proofs]
          |
          v
[Aggregate Performance Engine]
  - Target Met Rate (%)
  - Variance (%)
  - Policy Breaches Count
  - Spend Efficiency (Cost vs Outcome)
          |
          v
[Performance Health Rating]
  - PERFORMING (Score >= 85%, 0 Breaches)
  - DEGRADED (Score 75-84%)
  - REVIEW_REQUIRED (Score 50-74%, or 2+ Warnings)
  - UNDERPERFORMING (Score < 50%, or 3+ Breaches)
          |
          v
[CEO Executive Review & Action]
  - Retain & Reward
  - Initiate Retraining
  - Propose Template Version Upgrade
  - Quarantine / Retire & Replace
```

---

## 2. Measurable Performance Report Artifact

```json
{
  "employee_id": "emp_ai_revenue_specialist_01",
  "total_measurements": 14,
  "targets_met": 12,
  "warnings": 2,
  "breaches": 0,
  "score": 92.8,
  "health": "PERFORMING",
  "summary": "PERFORMING: 12/14 targets met, 0 breaches, score 92.8%",
  "evaluated_at": 1790962145.21
}
```
