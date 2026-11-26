# Sub-Step 3B Handoff: Host Permission Model and the Host Agent

**Sub-Step:** 3B  
**Branch:** `step3-hands`  
**Commit:** Pending 3B commit  
**Author:** Antigravity (Builder)  
**Reviewer:** OpenCode (Reviewer)  
**Date:** 2026-11-22  

---

## 1. Files Changed
```text
.github/workflows/ci.yml                         |   4 +-
core/capability_probe.py                         |  30 +++-
core/host/__init__.py                            |  46 ++++++
core/host/agent.py                               | 205 +++++++++++++++++++++++++
core/host/grants.py                              | 185 ++++++++++++++++++++++
core/host/pairing.py                             | 175 +++++++++++++++++++++
core/host/session.py                             | 175 +++++++++++++++++++++
core/host/types.py                               | 198 ++++++++++++++++++++++++
docs/reports/STEP3_REPORT.md                     |  31 ++++
migrations/common/0029_host_permission_model.sql |  68 ++++++++
migrations/pg/0029_host_permission_model.sql     | 108 +++++++++++++
tests/test_step3_host_agent.py                   | 344 +++++++++++++++++++++++++++++++++++++++++
12 files changed, 1561 insertions(+), 8 deletions(-)
```

---

## 2. Commands to Re-run
```bash
# Run the Step 3B host permission and host agent test suite
python -W ignore -m unittest tests/test_step3_host_agent.py

# Run both Step 3 test suites together
python -W ignore -m unittest tests/test_step3_preflight.py tests/test_step3_host_agent.py
```

---

## 3. Claims Made
1. **Host-Side Consent Enforcement (Rule 23):** Grants are verified and enforced locally by `ZonataHostAgent`. The cloud cannot widen grants, and out-of-grant commands fail locally on the host machine.
2. **One-Time Pairing with Step-Up Auth:** Pairing generates an Ed25519 keypair in local secure storage; the private key never leaves the host machine and is never stored in the database. Pairing strictly requires human step-up authentication.
3. **Cryptographic Anti-Replay & Monotonic Sequencing:** Every envelope is signed with the host's private key, carrying monotonic sequence numbers, nonces, and timestamp drift verification (< 30s). Duplicate nonces or out-of-order sequence numbers raise `ReplayDetectedError`.
4. **Principal Separation (Rule 15):** Grants can ONLY be created by an authenticated human principal (`created_by_principal_type == 'HUMAN'`). Attempts by agents, employees, or AI CEOs raise `Rule15Violation`.
5. **Deny-by-Default (Rule 23/27):** Password managers (1Password, Bitwarden, KeePass, etc.), banking portals (Chase, PayPal, etc.), and OS security settings are strictly blocked by default, requiring an explicit grant naming the application AND secondary human confirmation.
6. **Emergency Physical Kill Switch:** Triggering the host kill switch immediately halts local automation, drops cloud session (`status = HALTED`), and appends an audit event to `grant_events`.
7. **Truth Table Compliance (Rule 30):** `probe_desktop_control()` reports `NOT_CONFIGURED` without an active paired host agent.

---

## 4. Mutation Checks Done
- Verified in `test_07_principal_separation_agent_cannot_create_grant` that non-human principals (`AGENT`, `EMPLOYEE`, `AI_CEO`, `SYSTEM`) attempting grant creation fail closed with `Rule15Violation`.
- Verified in `test_08_deny_by_default_blocks_password_manager` that wildcard grants (`*`) fail to permit password managers, requiring explicit application naming and human confirmation.
- Verified in `test_03_replay_and_sequence_rejection` that replaying exact payloads or stale sequence numbers fails closed with `ReplayDetectedError`.

---

## 5. Known Gaps
- Desktop perception (accessibility tree extraction and coordinate clicking) is to be implemented in Sub-Step 3C.
- Origin-bound enterprise secret vault integration is to be implemented in Sub-Step 3D.
