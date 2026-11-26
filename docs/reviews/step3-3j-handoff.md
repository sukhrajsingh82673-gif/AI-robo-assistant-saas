# Sub-Step 3J Handoff: Agent Factory Import Lane & Sandboxing

**Sub-Step:** 3J  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml            |   4 +-
 core/agent_import/__init__.py       |  29 ++++++++
 core/agent_import/license_gate.py   |  64 ++++++++++++++++++
 core/agent_import/sandbox_runner.py |  63 ++++++++++++++++++
 core/agent_import/scanner.py        |  90 +++++++++++++++++++++++++
 core/agent_import/types.py          |  75 +++++++++++++++++++++
 docs/reports/STEP3_REPORT.md        |  23 ++++
 docs/reviews/step3-3i-review.md     |   7 +-
 tests/test_step3_agent_import.py    | 128 ++++++++++++++++++++++++++++++++++++
 9 files changed, 479 insertions(+), 4 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run unit tests for Sub-Step 3J
python -m unittest tests/test_step3_agent_import.py

# 2. Run all Step 3 test suites together
pytest tests/test_step3_*.py tests/test_truth_linter.py -v
```

---

## 3. Claims Made & Verified

1. **Rule 5 Licence Gate:** Permissive licenses (`MIT`, `Apache-2.0`, `BSD`) pass; copyleft licenses (`GPL`, `AGPL`, `SSPL`, `BSL`) are rejected with `LicenseViolationError`. Verified in `test_01`.
2. **ClamAV Malware Quarantine (Rule 32):** Infected payloads detected and quarantined with `MalwareDetectedError`. Verified in `test_02`.
3. **Dangerous AST & Rule 25 Detection:** Code attempting dynamic `eval()` or importing banned stealth packages is rejected with `DangerousCodeRejectedError`. Verified in `test_03`.
4. **Execution Scratch Containment:** Sandboxed execution restricted to isolated scratch directories with automatic cleanup. Verified in `test_04`.
5. **Certified Provenance:** Clean packages certified with immutable sha256 checksums and `SkillCertificationStatus.CERTIFIED`. Verified in `test_05`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3J delivers the import lane, license gate, ClamAV scanner, and execution sandboxing.
- Sub-Step 3K will deliver the Golden Evals & Final Step 3 Qualification Scenario.
