# Sub-Step 3H Handoff: Research Hand & Search Provider

**Sub-Step:** 3H  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml        |   4 +-
 core/capability_probe.py        |   6 +-
 core/ports/__init__.py          |  15 +++
 core/ports/search.py            | 243 ++++++++++++++++++++++++++++++++++++++++
 core/research/__init__.py       |   7 ++
 core/research/engine.py         |  51 +++++++++
 docs/reports/STEP3_REPORT.md    |  22 +++
 docs/reviews/step3-3g-review.md |   7 +-
 tests/test_step3_research.py    | 109 ++++++++++++++++++
 9 files changed, 460 insertions(+), 5 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run unit tests for Sub-Step 3H
python -m unittest tests/test_step3_research.py

# 2. Run all Step 3 test suites together
pytest tests/test_step3_*.py tests/test_truth_linter.py -v
```

---

## 3. Claims Made & Verified

1. **Port Architecture Compliance:** `SearchPort` implemented behind standard `Port` abstraction, supporting `SearXNGSearchProvider`, `SandboxSearchProvider`, and `NotConfiguredSearchProvider`. Verified in `test_01`.
2. **Untrusted Search Content Boundary (Rule 26):** Search results and snippets enclosed in `<<<SEARCH_RESULTS>>> ... <<<END_SEARCH_RESULTS>>>`. Verified in `test_02`.
3. **Prompt Injection Neutralization (Rule 26):** Malicious instructions inside web snippets remain passive data and cannot hijack agent tool execution. Verified in `test_03`.
4. **SearXNG Error Resilience:** Offline endpoints return `FAILED` with explicit error, zero unhandled exceptions. Verified in `test_04`.
5. **Capability Truth Table Integration (Rule 30):** `probe_search()` reports accurate provider status in the capability truth table. Verified in `test_05`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3H delivers the research hand and search provider.
- Sub-Step 3I will deliver terminal governance and safety controls.
