# Sub-Step 3F Handoff: Anti-Evasion Policy & Dependency Deny-List (Rule 25)

**Sub-Step:** 3F  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml         |   8 +-
 core/browser/challenge_policy.py | 164 +++++++++++++++++++++++++
 core/browser/rate_limiter.py     | 120 ++++++++++++++++++
 core/security/anti_evasion.py    | 254 +++++++++++++++++++++++++++++++++++++++
 docs/reports/STEP3_REPORT.md     |  23 ++++
 docs/reviews/step3-3e-review.md  |   7 +-
 scripts/anti_evasion_linter.py   |  48 ++++++++
 tests/test_step3_anti_evasion.py | 146 ++++++++++++++++++++++
 8 files changed, 767 insertions(+), 4 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run anti-evasion linter
python3 scripts/anti_evasion_linter.py

# 2. Run unit tests for Sub-Step 3F
python -m unittest tests/test_step3_anti_evasion.py

# 3. Run all Step 3 test suites together
pytest tests/test_step3_*.py tests/test_truth_linter.py -v
```

---

## 3. Claims Made & Verified

1. **AST & Dependency Deny-List Enforcement (Rule 25):** Automated AST scanner in `core/security/anti_evasion.py` flags banned stealth plugins (`playwright-stealth`, `puppeteer-extra-plugin-stealth`, etc.) and captcha solvers (`2captcha`, `anticaptcha`, `deathbycaptcha`, `capmonster`). Verified in `test_01` & `test_02`.
2. **Dependency Manifest Auditing:** Scans `requirements.txt`, `pyproject.toml`, and `package.json` for prohibited packages. Verified in `test_03`.
3. **Challenge Halting & Official Alternatives:** Anti-bot challenges halt execution, set task state to `BLOCKED`, mask widget coordinates, and suggest lawful routes (APIs, allow-lists, exports). Verified in `test_04`.
4. **Governed Rate Limiting with Zero IP Rotation:** Full jitter exponential backoff on HTTP 429/503/403. Attempting proxy or IP rotation raises `AntiEvasionViolationError`. Verified in `test_05`.
5. **Clean Repository Baseline:** Full scan of repository confirms zero Rule 25 violations. Verified in `test_06`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3F establishes anti-evasion policy and dependency deny-list enforcement.
- Sub-Step 3G will deliver remote view and human takeover for supervisory control.
