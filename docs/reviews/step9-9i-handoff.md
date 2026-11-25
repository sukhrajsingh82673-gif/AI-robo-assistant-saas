# OpenCode Handoff: Sub-Step 9I

## 1. Summary of Changes
- Created `core/marketplace/manifest.py` implementing the `zonata.marketplace-package/v1` manifest specification.
- Created `core/marketplace/registry.py` with static security review and commercial truth handling (`NOT_IMPLEMENTED` on paid installs).
- Created `core/marketplace/sandbox.py` enforcing granular capability authorization and domain-scoped network egress allowlisting.
- Created `core/marketplace/revocation.py` implementing instant (< 1s) runtime revocation.
- Created `tests/test_step9i_marketplace.py`.

## 2. Verification Commands
```bash
pytest -v tests/test_step9i_marketplace.py
```

## 3. Claims and Invariants
- Rule 81: Third-party code cannot execute unconsented operations or egress to undeclared network destinations.
- Revocation SLA (< 1 second) immediately shuts down active sandbox runtimes.
- Commercial truth: Paid marketplace listings report `NOT_IMPLEMENTED`.
