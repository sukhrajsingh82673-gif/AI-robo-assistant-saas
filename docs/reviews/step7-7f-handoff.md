# Sub-Step 7F Handoff Dossier: Human Resources & Workforce Operations

**Date:** 2026-11-24  
**Author:** Antigravity Architect  
**Reviewer:** OpenCode Arbiter  
**Scope:** Inclusive job description linter, salary transparency, Rule 63 counterfactual fairness disparity testing across 100 demographic slices, employee onboarding lifecycle, deterministic statutory payroll, and 60-second credential offboarding.

---

## 1. Files Changed & Added (`git diff --stat`)
```
core/hr/__init__.py                |   1 +
core/hr/fairness.py                | 125 ++++++++++++++++++++++
core/hr/lifecycle.py               |  78 +++++++++++++++
core/hr/offboarding.py             |  84 +++++++++++++++
core/hr/payroll.py                 |  98 ++++++++++++++++++
core/hr/recruiting.py              |  85 ++++++++++++++++
docs/reports/STEP7_REPORT.md       |  30 ++++++
docs/reviews/step7-7f-handoff.md   |  38 +++++++
docs/reviews/step7-7f-review.md    |  34 +++++++
packs/regions/india/payroll_rules.json | 20 ++++
tests/test_step7f_hr.py            | 188 +++++++++++++++++++++++++++++++++
11 files changed, 791 insertions(+)
```

## 2. Commands to Re-run
```bash
pytest -v tests/test_step7f_hr.py
pytest -q tests/test_step7_preflight.py tests/test_preservation_step7.py tests/test_step7b_platform.py tests/test_step7c_finance.py tests/test_step7d_sales_support.py tests/test_step7e_marketing.py tests/test_step7f_hr.py
```

## 3. Claims & Invariants Verified
1. **Inclusive Recruiting & Salary Transparency:** Job postings strictly require non-zero salary ranges; masculine/exclusionary terms are flagged.
2. **Rule 63 Counterfactual Fairness:** Audits 100 demographic permutations across names, gender markers, and age; disparity ratios strictly bounded within $[0.95, 1.05]$. Biased models raise `CounterfactualFairnessViolation` and halt.
3. **Employee Lifecycle & Rule 62:** Onboarding steps tracked; compensation increases mandate human gateway authorization.
4. **Deterministic Payroll (Rule 61):** Calculates EPF, ESIC, PT, and TDS according to statutory pack parameters.
5. **Offboarding SLA & SHA256 Receipt:** Comprehensive revocation across sessions, OpenBao leases, and DB roles runs in under 60 seconds with SHA256 cryptographic audit receipt.

## 4. Known Gaps / Next Sub-Step
- Sub-Step 7G will implement Operations & Production Depth (BOM explosion, OEE calculation, inspection lot quarantine holds, maintenance schedules).
