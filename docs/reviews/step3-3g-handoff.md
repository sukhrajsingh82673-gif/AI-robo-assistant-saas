# Sub-Step 3G Handoff: Remote View & Human Takeover

**Sub-Step:** 3G  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml                           |   4 +-
 core/remote_view/__init__.py                       |  29 +++
 core/remote_view/streamer.py                       |  71 +++++++
 core/remote_view/takeover.py                       | 203 +++++++++++++++++++++
 core/remote_view/types.py                          |  98 ++++++++++
 docs/reports/STEP3_REPORT.md                       |  23 ++++
 docs/reviews/step3-3f-review.md                    |   7 +-
 migrations/common/0031_remote_view_and_takeover.sql       |  29 +++
 migrations/pg/0031_remote_view_and_takeover.sql    |  39 ++++
 tests/test_step3_remote_view.py                    | 150 +++++++++++++++
 10 files changed, 650 insertions(+), 4 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run unit tests for Sub-Step 3G
python -m unittest tests/test_step3_remote_view.py

# 2. Run all Step 3 test suites together
pytest tests/test_step3_*.py -v
```

---

## 3. Claims Made & Verified

1. **Bounded Viewport Capture (Rule 28):** Stream captures strictly within the granted bounding box; coordinates outside the grant are rejected. Verified in `test_01`.
2. **Pre-Transmission Masking (Rule 24 & 28):** Secret fields and challenge widgets are redacted before frame packet serialization. Verified in `test_02`.
3. **Agent Suppression during Takeover (Rule 27):** Agent commands are immediately suppressed with `AgentExecutionSuppressedError` when a human takes over. Verified in `test_03`.
4. **Structured Hand-Back Assertion:** Human releases session with explicit postcondition assertion (`CHALLENGE_SOLVED`, `MFA_COMPLETED`) recorded in audit history. Verified in `test_04`.
5. **Relational Schema & Lifecycle:** `remote_view_sessions` and `human_takeover_events` record session transitions with PostgreSQL 16 RLS policies. Verified in `test_05`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3G delivers remote view streaming and human takeover governance.
- Sub-Step 3H will deliver the research hand and search provider (`SearchPort`).
