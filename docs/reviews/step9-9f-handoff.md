# OpenCode Handoff: Sub-Step 9F

## 1. Summary of Changes
- Created `core/onboarding/wizard.py` implementing guided onboarding state machine.
- Created `core/onboarding/demo_company.py` seeding synthetic demo companies with clean reset mechanics.
- Created `core/onboarding/importer.py` implementing CSV data ingestion with dry-run verification and atomic rollback.
- Created `core/compliance/data_act_export.py` generating EU Data Act (Regulation EU 2023/2854) compliant portable tenant archives with zero exit fees.
- Created `tests/test_step9f_onboarding.py`.

## 2. Verification Commands
```bash
pytest -v tests/test_step9f_onboarding.py
```

## 3. Claims and Invariants
- Onboarding wizard enforces all required fields and step transitions.
- CSV imports rollback completely if any row fails validation in batch.
- EU Data Act export bundles all customer entities with zero exit fees recorded in metadata.
- Step 1–8 baseline files (including existing `core/compliance/__init__.py`) remain strictly untouched.
