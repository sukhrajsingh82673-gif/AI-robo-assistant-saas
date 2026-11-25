# OpenCode Handoff: Sub-Step 9G

## 1. Summary of Changes
- Created `web/pwa/manifest.json` and `web/pwa/sw.js` implementing Progressive Web App capabilities.
- Created `core/ui/mobile_approvals.py` guarding mobile approvals with offline read-only barriers and biometric WebAuthn passkey requirements on high-value actions.
- Created `core/ui/accessibility_checker.py` enforcing WCAG 2.2 AA automated compliance checks.
- Created `docs/accessibility/DRAFT_ACR_VPAT.md` certifying accessibility criteria conformance.
- Created `tests/test_step9g_mobile_accessibility.py`.

## 2. Verification Commands
```bash
pytest -v tests/test_step9g_mobile_accessibility.py
```

## 3. Claims and Invariants
- High-value transactions (>= 1,000,000 cents) require cryptographic passkey authentication.
- Offline mutations are strictly blocked; pending approvals are cached read-only.
- WCAG 2.2 AA violations (unlabelled inputs, missing alt tags, non-keyboard interactive elements) are caught automatically by CI checks.
