# Sub-Step 6C Handoff Dossier — Failure Intelligence & Governed Diagnosis

- **Date:** 2026-11-24
- **Builder:** Antigravity Systems Architect & Builder
- **Reviewer:** OpenCode Security Arbiter & Red Team
- **Target Branch:** `step6-evolution`

---

## 1. Files Changed & Created (git diff --stat)
```
 .github/workflows/ci-evolution.yml          |   4 +-
 core/evolution/__init__.py                  |  17 ++
 core/evolution/failure_intelligence.py      | 263 ++++++++++++++++++++++++
 docs/reports/STEP6_REPORT.md                |  22 ++
 tests/test_step6_failure_intelligence.py    | 145 +++++++++++++
 5 files changed, 449 insertions(+), 2 deletions(-)
```
*Note: Rule 49 (Preservation Contract) strictly preserved. Zero Step 1-5 files modified.*

---

## 2. Commands to Re-run
```bash
cd /data/data/com.termux/files/home/AI-robo-assistant-saas
python3 -m pytest tests/test_step6_failure_intelligence.py -v
python3 -m pytest tests/test_truth_linter.py -q
```

---

## 3. Claims & Evidence
1. **6-Class Taxonomy:** Ingestion verified across `EXECUTION_ERROR`, `VERIFICATION_FAILURE`, `POLICY_DENIAL`, `REGRESSION`, `HALLUCINATION`, and `AMBIGUOUS_SPEC`.
2. **Deduplication:** 10 repeated failures collapse into 1 incident with `count = 10`.
3. **Analyst Graph Routing:** Diagnoses failure context and routes to `PLAYBOOK_CANDIDATE`, `OPTIMIZER_CANDIDATE`, `OWNER_HELP_REQUEST`, or `GITHUB_TRIAGE`.
4. **PII/Secret Scrubbing:** Eliminates JWTs, email addresses, passwords, and credit card numbers from traces.
5. **Scorecards:** Calculates MTTF, MTTR, regression rate, and class breakdowns.

---

## 4. Mutation Checks
- Passing an unclassified failure (e.g. `"BIZARRE_CUSTOM_FAILURE_CLASS"`) defaults to `FailureClass.UNKNOWN`, confidence `0.20`, human escalation `True`, and routes to `GITHUB_TRIAGE`.

---

## 5. Known Gaps
- None. Ready for OpenCode review and git commit.
