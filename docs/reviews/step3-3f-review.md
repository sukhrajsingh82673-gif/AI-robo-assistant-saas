# Sub-Step 3F Review: Anti-Evasion Policy & Dependency Deny-List (Rule 25)

**Sub-Step:** 3F  
**Branch:** `step3-hands`  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  
**Verdict:** **PASS**  

---

## 1. Audit Against Acceptance Criteria

| Criteria | Required Invariant | Audit Findings | Result |
| :--- | :--- | :--- | :--- |
| **Banned Package Deny-List** | Deny stealth plugins (`playwright-stealth`) and solver SDKs (`2captcha`, `anticaptcha`). | `BANNED_PACKAGES` defined in `core/security/anti_evasion.py` and checked across requirements, pyproject, and package.json. Verified in `test_01` & `test_03`. | **PASS** |
| **AST Stealth Pattern Check** | Flag AST code attempting webdriver manipulation or solver endpoints. | `AntiEvasionASTVisitor` flags solver endpoints and `navigator.webdriver` tampering. Verified in `test_02`. | **PASS** |
| **CI Automated Verification** | Standalone script executed in CI supply chain audit job. | `scripts/anti_evasion_linter.py` added to CI workflow under Supply Chain audit job. Verified locally and integrated. | **PASS** |
| **Challenge Halting & Routes** | Challenges halt task, set `BLOCKED`, and suggest official routes (APIs, exports). | `ChallengePolicyEngine.evaluate_challenge` transitions task to `BLOCKED` with official route suggestions. Verified in `test_04`. | **PASS** |
| **Governed Backoff (Rule 25)** | Exponential jittered backoff; strictly zero IP rotation. | `GovernedRateLimiter` applies jittered backoff; `request_proxy_rotation` raises `AntiEvasionViolationError`. Verified in `test_05`. | **PASS** |
| **Repository Rule 25 Hygiene** | Entire codebase clean of Rule 25 violations. | `scan_repository_anti_evasion` confirms zero violations. Verified in `test_06`. | **PASS** |

---

## 2. Reviewer Verdict

**STATUS: PASS (Pending CI Verification).**  
Sub-Step 3F satisfies all Rule 25 anti-evasion requirements, AST/dependency deny-list scanning, challenge routing, and jittered rate limiting without proxy rotation. Ready to commit and push for GitHub Actions CI verification.
