# Sub-step 6I Handoff Dossier — The System's Own GitHub (Governed, Public-Repo Safe)

## 1. Summary of Changes
- Implemented `core/evolution/github_client.py`:
  - `GitHubAppScope`: Enforces least privilege on GitHub App credentials; rejects tokens granting `workflows`, `administration`, or `secrets` permissions.
  - `PullRequestContract`: Enforces `ai/<class>/<id>` branch naming convention, bans writes to protected branches, enforces Rule 57 human-only merges and approvals, formats PR bodies with hashed failure-cluster IDs and metric counts (zero canary or PII leakage), and blocks any PR modifying paths listed in `security/protected_paths.yaml`.
  - `PublicInputSanitizer`: Read-only triage worker operating with zero write tools and no secrets in environment; safely detects and flags prompt injections from untrusted public issues and comments.
  - `ReleaseAttestation`: Validates SBOM, build provenance attestations, and human gateway authorization (`EXTERNAL_API_WRITE` with `DEPLOY`).
- Added comprehensive unit and integration tests in `tests/test_step6_github_automation.py` (8 tests).
- Updated `.github/workflows/ci-evolution.yml` to include `tests/test_step6_github_automation.py`.
- Updated `docs/reports/STEP6_REPORT.md` with complete Sub-step 6I verification records.

## 2. Git Diff Stat
```text
 .github/workflows/ci-evolution.yml     |   4 +-
 docs/reports/STEP6_REPORT.md           |  25 ++++
 core/evolution/github_client.py        | 210 +++++++++++++++++++++++++++++++++
 tests/test_step6_github_automation.py  | 175 +++++++++++++++++++++++++++
 4 files changed, 412 insertions(+), 2 deletions(-)
```

## 3. Commands to Re-run
```bash
python -m pytest tests/test_step6_github_automation.py -v
python -m pytest tests/test_step6_preservation_contract.py -v
```

## 4. Claims and Verification
1. **Rule 54 Least Privilege App Scoping:** Verified that tokens granting `workflows`, `administration`, or `secrets` are blocked with `ExcessivePermissionError`. Verified in `test_01_github_app_permissions_enforces_least_privilege_and_blocks_workflows`.
2. **Branch Convention & Protected Branch Guard:** Target `main`, `master`, `release` rejected; `ai/<class>/<id>` validated. Verified in `test_02_branch_naming_validator_blocks_protected_branches_and_requires_ai_prefix`.
3. **Rule 57 Human-Merge Invariant:** Automated and AI principals attempting to merge or approve PRs are rejected with `HumanMergeOnlyError` and `HumanApprovalOnlyError`. Human accounts succeed. Verified in `test_03_pr_merge_and_approval_prohibits_ai_principals_rule57` and `test_08_mutation_check_unauthenticated_or_ai_actor_cannot_force_merge`.
4. **Hashed References & Zero Canary Leakage:** PR bodies contain hashed failure IDs, evidence metrics as counts, and no tenant data or canary secrets. Verified in `test_04_pr_body_builder_hashes_failure_clusters_and_excludes_tenant_canary`.
5. **Protected Path Gate:** AI PRs touching `security/protected_paths.yaml` or `.github/workflows/` blocked. Verified in `test_05_protected_path_inspector_blocks_and_rejects_ai_prs_touching_protected_set`.
6. **Public Input Sanitization:** Prompt injection attempts quarantined with empty tool calls. Verified in `test_06_public_input_sanitizer_quarantines_prompt_injection_with_zero_tool_calls`.
7. **Release Attestation:** Release requires SBOM, provenance, and gateway deploy authorization. Verified in `test_07_release_attestation_verifies_sbom_provenance_and_gateway_approval`.
8. **Preservation Contract (Rule 49):** Working tree integrity verified against `STEP1-5_BASELINE.json`. Zero legacy files touched.

## 5. Mutation Checks Performed
- GitHub App token requesting `workflows` scope rejected.
- Bot or AI agent attempting to merge PR blocked.
- AI PR touching `security/protected_paths.yaml` raises `ProtectedPathModificationError`.
- Adversarial prompt injection in issue body safely quarantined without executing tool calls.

## 6. Known Gaps
- None. Fully self-contained, no external network dependencies, 100% passing tests.
