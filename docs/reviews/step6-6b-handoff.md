# Sub-Step 6B Handoff Dossier — The Preservation Contract & Regression Gate

- **Date:** 2026-11-24
- **Builder:** Antigravity Systems Architect & Builder
- **Reviewer:** OpenCode Security Arbiter & Red Team
- **Target Branch:** `step6-evolution`

---

## 1. Files Changed & Created (git diff --stat)
```
 .github/workflows/ci-evolution.yml                |   7 +
 core/evolution/__init__.py                        |   4 +
 core/evolution/preservation.py                    | 227 +++++++++++++++++++++
 docs/baselines/STEP1-5_BASELINE.json              | 1965 +++++++++++++++++++
 docs/reports/STEP6_REPORT.md                      |  28 ++
 security/protected_paths.yaml                     |  45 ++
 tests/test_step6_preservation_contract.py         | 115 +++++++++++
 7 files changed, 2391 insertions(+)
```
*Note: Rule 49 (Preservation Contract) is strictly honored. Zero Step 1-5 files modified.*

---

## 2. Commands to Re-run
```bash
cd /data/data/com.termux/files/home/AI-robo-assistant-saas
python3 -m pytest tests/test_step6_preservation_contract.py -v
python3 -m pytest tests/test_truth_linter.py -q
```

---

## 3. Claims & Evidence
1. **Annotated Tag `step5-final`:** Pinned directly to Step 5 HEAD commit `914f5331bfb7325888c0c0090e4fc6677a913681`.
2. **Cryptographic Baseline Manifest:** Generated `docs/baselines/STEP1-5_BASELINE.json` covering 1,951 files with SHA-256 and byte counts.
3. **Preservation Engine:** Implemented in `core/evolution/preservation.py` verifying file hashes, git diff status, evolution flag defaults, and migration DDL.
4. **Migration Linter:** Prevents destructive operations (DROP TABLE, DROP COLUMN, ALTER TYPE, DISABLE RLS, DROP POLICY).
5. **CI Regression Gate:** Configured `ci-evolution.yml` to run the preservation contract check on every push.

---

## 4. Mutation Checks
- Mutated `core/db.py` hash in memory: Caught immediately with `PreservationViolationError: core/db.py tampered`.
- Fed destructive SQL (`DROP TABLE`, `DROP COLUMN`, `DISABLE ROW LEVEL SECURITY`): Caught with `PreservationViolationError`.
- Tested unauthorized file path: `is_path_allowed("models/agent.py")` returned `False`.

---

## 5. Known Gaps
- None. Ready for OpenCode review and git commit.
