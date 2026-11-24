# Step 7M Handoff Dossier: Company-in-a-Box Qualification & Benchmarks

**Sub-step:** 7M  
**Branch:** `step7-departments`  
**Date:** 2026-11-24  
**Author:** Antigravity Architect  
**Reviewer:** OpenCode Arbiter  

## 1. Summary of Changes
- Created `docs/benchmarks/METHOD.md` specifying the GDPval blinded comparison methodology and TheAgentCompany 5-checkpoint deterministic verification framework (CP1 - CP5).
- Created `tests/benchmarks/test_department_benchmarks.py` implementing 250 golden tasks across all 10 departments (25 tasks each) evaluating input validation, regulatory boundaries, state mutation, Rule 59 independent re-read, and cryptographic audit seals.
- Created `scripts/step7_scenario.py` simulating 30 consecutive business days of operational lifecycle across all 10 corporate departments with zero failures.
- Created `scripts/step7_redteam.py` verifying 7 adversarial attack vectors (vendor fraud holds, sanctions evasions, liability cap redlines, rogue discounts, superhuman claims, demographic fairness, and raw SQL blocks).
- Finalized `docs/reports/STEP7_REPORT.md` certifying Step 7 completion.

## 2. Verification Commands
```bash
PYTHONPATH=. python scripts/step7_scenario.py
PYTHONPATH=. python scripts/step7_redteam.py
python -m pytest tests/test_step7*.py tests/benchmarks/test_department_benchmarks.py tests/test_preservation_step7.py -q
```

## 3. Preservation Check
Zero edits to Steps 1–6 baseline files. All 2,006 baseline files preserved with identical cryptographic hashes.
