# Sub-step 6G Handoff Dossier — Open-Source Agent and Tool Intake ("Agent Zoo")

## 1. Summary of Changes
- Implemented `core/evolution/intake.py`:
  - `IntakeState` state machine governing the discovery, quarantine, evaluation, sandboxing, certification, and human promotion of external agents.
  - License classification engine adhering to Rule 5 allow-list, separating permissive licenses from `BOUNDARY` (AGPL/GPL) and prohibited licenses.
  - Static security and AST scanner rejecting `curl | sh` installers (Rule 32), unpinned dependencies, missing cryptographic hash locks, dangerous `eval`/`exec` calls, and direct environment secret access.
  - Untrusted documentation sanitizer detecting prompt-injection attempts in README content.
  - Monitored `BehavioralSandbox` verifying capability declarations against observed syscall traces (network egress, filesystem writes, subprocess execution).
  - `HermesEvaluator` generating reference evaluation report for Nous Research Hermes Agent (MIT).
- Added comprehensive unit and integration tests in `tests/test_step6_intake.py` (8 tests).
- Updated `.github/workflows/ci-evolution.yml` to include `tests/test_step6_intake.py`.
- Updated `docs/reports/STEP6_REPORT.md` with complete Sub-step 6G results.

## 2. Git Diff Stat
```text
 .github/workflows/ci-evolution.yml |   4 +-
 docs/reports/STEP6_REPORT.md       |  25 ++++
 core/evolution/intake.py           | 475 +++++++++++++++++++++++++++++++++++++
 tests/test_step6_intake.py         | 185 +++++++++++++++++++++++++++
 4 files changed, 687 insertions(+), 2 deletions(-)
```

## 3. Commands to Re-run
```bash
python -m pytest tests/test_step6_intake.py -v
python -m pytest tests/test_step6_preservation_contract.py -v
```

## 4. Claims and Verification
1. **Rule 5 Allow-list & Boundary Isolation:** Permissive licenses accepted, AGPL-3.0 flagged as `BOUNDARY` requiring container isolation. Verified in `test_04_static_scanner_flags_agpl_as_boundary`.
2. **Rule 32 Pipe-to-Shell Ban:** Installers matching `curl | sh` or `wget | bash` detected as BLOCKER. Verified in `test_02_static_scanner_rejects_curl_pipe_sh_installer`.
3. **Dependency Pinning & Hash Locks:** Missing cryptographic hashes or unpinned ranges rejected. Verified in `test_03_static_scanner_rejects_unpinned_or_unhashed_dependency`.
4. **Human-Only Promotion (Rule 53, Rule 57):** AI principal promotion to `ACTIVE` rejected with `HumanApprovalRequiredError`. Human principal succeeds. Verified in `test_07_promotion_to_active_strictly_requires_human_principal`.
5. **Sandbox Isolation & Capability Reconciliation:** Egress to unauthorized hosts and filesystem directory traversal blocked. Verified in `test_06_sandbox_blocks_unauthorized_egress_and_fs_escape`.
6. **Documentation Sanitization:** Prompt injections in untrusted READMEs flagged. Verified in `test_08_mutation_check_readme_prompt_injection_flagged`.
7. **Preservation Contract (Rule 49):** Working tree integrity verified against `STEP1-5_BASELINE.json`. Zero legacy files touched.

## 5. Mutation Checks Performed
- Manifest with unpinned dependencies and missing hashes rejected.
- Malicious agent attempting unauthorized network egress and write to `/etc/shadow` caught by sandbox.
- Automated agent attempting promotion to `ACTIVE` blocked.
- README prompt injection caught by scanner.

## 6. Known Gaps
- None. Fully self-contained, no external network dependencies, 100% passing tests.
