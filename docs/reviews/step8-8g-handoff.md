# Sub-Step 8G Handoff: Pilot Kit & Readiness Gate

## 1. Files Changed
```text
 core/pilot/__init__.py
 core/pilot/exit.py
 core/pilot/kill_switch.py
 core/pilot/shadow_runner.py
 docs/pilot/PILOT_CHARTER_TEMPLATE.md
 docs/reports/PILOT_READINESS_REPORT.md
 scripts/pilot_readiness.py
 tests/test_step8g_pilot_readiness.py
 docs/reports/STEP8_REPORT.md
```

## 2. Commands to Re-run
```bash
PYTHONPATH=. pytest -v tests/test_step8g_pilot_readiness.py tests/test_preservation_step8.py
```

## 3. Claims & Evidence
1. **Passive Shadow Mode & Zero Writes:** Intercepts live workflows; spy confirms 0 external mutations (`test_01`).
2. **Shadow Write Blocker:** Unauthorized mutation raises `ShadowModeWriteBlockedError` (`test_02`).
3. **Emergency Kill-Switch Sub-Second Latency:** Isolation drill verifies shutdown in < 1000 ms (`test_03`).
4. **Execution Block on Isolated Tenant:** Tripped switch raises `PermissionError: TENANT_ISOLATED` (`test_04`).
5. **Clean Exit & Cryptographic Erasure:** Generates self-contained JSON archive and sealed erasure receipt (`test_05`).
6. **Standardized Pilot Charter:** `docs/pilot/PILOT_CHARTER_TEMPLATE.md` specifies 30-day term, scope, and human DPO gatekeeper roles (`test_06`).
7. **Readiness Qualification Invariant:** `scripts/pilot_readiness.py` evaluates 12 criteria and outputs strictly `READY_FOR_HUMAN_GO_DECISION` (never automated "GO") (`test_07`).
8. **Preservation Invariant:** All 2,137 Step 1–7 baseline files remain cryptographically untouched (`test_preservation_step8.py`).

## 4. Known Gaps
- None. Real pilot deployment requires counterparty executive signoff on the bilateral charter.
