# Sub-Step 3I Handoff: Terminal Governance & Safety Controls

**Sub-Step:** 3I  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml        |   4 +-
 core/capability_probe.py        |   6 ++
 core/ports/__init__.py          |  10 ++
 core/ports/terminal.py          | 202 ++++++++++++++++++++++++++++++++++++++++
 core/terminal/__init__.py       |  21 +++++
 core/terminal/classifier.py     |  80 ++++++++++++++++
 core/terminal/types.py          |  56 +++++++++++
 docs/reports/STEP3_REPORT.md    |  23 ++++
 docs/reviews/step3-3h-review.md |   7 +-
 tests/test_step3_terminal.py    | 126 +++++++++++++++++++++++++
 10 files changed, 531 insertions(+), 4 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run unit tests for Sub-Step 3I
python -m unittest tests/test_step3_terminal.py

# 2. Run all Step 3 test suites together
pytest tests/test_step3_*.py tests/test_truth_linter.py -v
```

---

## 3. Claims Made & Verified

1. **Terminal Default Disabled:** When `TERMINAL_ENABLED="0"`, commands fail closed with `TerminalDisabledError` and probe returns `NOT_CONFIGURED`. Verified in `test_01`.
2. **Forbidden Command Blocking (Rule 3):** `sudo`, `curl | sh`, and destructive `rm` commands are blocked with `DangerousCommandForbiddenError`. Verified in `test_02`.
3. **High-Impact Command Gating (Rule 27):** Destructive commands require `is_human_approved=True`. Verified in `test_03`.
4. **Untrusted Output Boundary (Rule 26):** Terminal stdout and stderr are enclosed within `<<<TERMINAL_OUTPUT>>>` tags. Verified in `test_04`.
5. **Process Supervision & Kill Signal:** Unresponsive commands exceeding timeouts are terminated with `killed_by_signal=True`. Verified in `test_05`.
6. **Capability Truth Table Integration (Rule 30):** Terminal probe complies with reality truth table invariants. Verified in `test_06`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3I delivers terminal governance, safety classification, and process supervision.
- Sub-Step 3J will deliver the Agent Factory Import lane & untrusted code sandboxing.
