# INDEPENDENT VERIFICATION — Agent Factory Phase 1 Audit

Date: 2026-11-20 · Branch: `zonata/stage-9-pilot` @ `f59156c`
Host: Android/Termux aarch64 · Python 3.14.10 · SQLite
Supersedes: audit of `6003d16` (2026-11-19) — this pass re-executes against the current branch.

## Verdict

**PHASE 1 AUDIT: COMPLETE.**
**Critical path: PASS.** Agent Factory is present and green (`84/84`), governance and tenant isolation are green (`50/50`), and dependency/secret/licence checks are clean apart from the findings below. No blocking defect was found. Gate D1 decisions (D1.1 DB queue, D1.2 T0, D1.3 strangler) are already implemented on this branch.

## 1. Test evidence

Full suite (fresh, on this branch, `ZONATA_DB_DIALECT=sqlite`):

```
2051 passed, 50 failed, 26 skipped, 3 errors, 8 subtests passed in 767.87s
```

Every failure is triaged in `FAILURE_TRIAGE.md`:

| Class | Count | Meaning |
|---|---|---|
| Environment-only (Termux/Android) | 41 | hardcoded `/tmp`, `/root`, X display, `/proc` metrics, no host CLI |
| Flaky under full contended run | 5 | pass in isolation (`flaky_rerun.txt`) |
| Stale settings assertions | 5 | expects 45/202; registry has 46/214 |
| `INSERT OR REPLACE` invariant | 1 | source-level rule; PG normalizer covers runtime |
| Undeclared test dep (`python-dotenv`) | 1 | installing it makes 18/18 tests pass |

Targeted re-runs:

- `tests/agent_factory` → **84 passed** (9.70s)
- `test_audit_remediation_security.py` + `test_direct_object_access_and_tenant_security.py` + `tests/agent_factory` → **134 passed** (21.32s)
- `test_cross_process_concurrency_coordination.py`, `test_phase_14_cross_process_governance.py`, `test_independent_enterprise_pilot_e2e.py` → **18 passed** (53.90s) after installing `python-dotenv`

## 2. Findings

### F1 — Five upserts still use SQLite-only `INSERT OR REPLACE` (LOW, non-blocking)
`core/accountable_owner.py:91`, `core/ura_router.py:208,768`, `core/process_packs/loader.py:169`, `core/process_packs/engine.py:296`.
`core/db.py:4623-4670` rewrites `INSERT OR REPLACE` to `ON CONFLICT (...) DO UPDATE` for PostgreSQL, so runtime is safe; the source-level invariant test (`test_postgresql_dialect_compatibility`) still fails. **Action:** convert to `ON CONFLICT`, or explicitly exempt `af_*` tables in the test.

### F2 — Settings test drift: 45/202 expected vs 46/214 actual (LOW, non-blocking)
`core/settings/registry.py` (last touched `cbff16b`, 2026-11-13) and `definitions.py` (`c6254fa`, 2026-11-15) define **46 categories** and 214 settings; the five assertions were last updated 2026-10-30/11-07. Registry is authoritative. **Action:** update the five assertions (or confirm the intended count if 45/202 is the contract).

### F3 — `python-dotenv` missing from `requirements.txt` (INFO — fixed during audit)
Tests import it at module scope; `core/coworker/db_store_v2.py:287` imports it lazily. After `pip install python-dotenv`, the affected files pass. **Action:** add `python-dotenv` to the manifest (runtime optional, test required).

### F4 — Gate D1 process drift (PROCESS)
`SUMMARY.md` still ends with “STOPPING … awaiting human approval” and D1.1–D1.4 unchecked, although Phases 2–10 and Stage 9 are merged and pushed on this branch. **Action:** record the human approval/retrospective sign-off in `SUMMARY.md` so the audit trail matches the code.

### F5 — Live credentials outside the repository (SECURITY)
`.bashrc` contains a Gemini API key and `~/.config/gh/hosts.yml` contains a GitHub PAT in plaintext. In-repo gitleaks hits are all synthetic/placeholder and the live PAT does **not** appear in git history. **Action:** rotate both credentials and load them from a secret store or environment.

### F6 — Hardcoded `/tmp` blocks 41 tests on this host (ENVIRONMENT)
`/tmp` is read-only on Termux. Tests and some runtime helpers write there directly. **Action:** route temp paths through `tempfile`/`TMPDIR` (or `$PREFIX/tmp`) so the suite is portable.

## 3. Security hygiene

| Check | Result | Evidence |
|---|---|---|
| Secret scan (git history, 304 commits / 25.02 MB) | 758 findings, all triaged synthetic; live PAT absent | `gitleaks_console.txt`, `gitleaks_report.json` |
| Python dependency audit | 43 installed packages, **0 known vulnerabilities** | `pip_audit_local.json` |
| npm audit | **0 vulnerabilities** (info/low/moderate/high/critical) | `npm_audit.json` |
| Governance suite | **84/84** AF tests (AT-01…AT-22: approvals, self-grant prevention, tenant isolation, evidence ledger, signed artifacts, quotas, import quarantine, migrations, worker) | `governance_security.txt` |
| Tenant isolation negatives | **50/50** passed | `governance_security.txt` |

gitleaks breakdown: 739 `generic-api-key` (test/doc fixtures), 10 `stripe-access-token` (test values), 5 `github-pat` (fixtures, not the live token), 1 `private-key` (documentation table), 1 `jwt`, 2 `curl-auth-header`. Nothing requires revocation.

## 4. Licence gate (re-verified upstream, 2026-11-20T12:47Z)

Raw data: `licence_verification.json`.

### Adopted Python dependencies

| Package | Version | SPDX |
|---|---|---|
| pydantic | 2.14.4 | MIT |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| langgraph | 1.2.24 | MIT |
| opentelemetry-api | 1.45.2 | Apache-2.0 |
| jsonschema | 4.26.0 | MIT |
| bandit | 1.9.4 | Apache-2.0 |
| pip-audit | 2.10.1 | Apache-2.0 |
| langfuse | 5.2.0 | MIT (repo reports NOASSERTION — mixed OSS/EE tree) |
| deepeval | 4.3.4 | Apache-2.0 |
| ragas | 0.4.4 | Apache-2.0 |
| garak | 0.17.1 | Apache-2.0 |
| pyrit | 1.2.1 | MIT |
| semgrep | 1.186.0 | **LGPL-2.1-or-later** (tool-only, not linked) |
| mcp | 2.3.0 | MIT |
| a2a-sdk | 1.3.1 | Apache-2.0 |
| pg8000 | 1.31.6 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| numpy | 2.5.5 | 0BSD / BSD-3 / CC0 / MIT / Zlib |
| pandas | 3.1.1 | BSD-3-Clause |
| python-dateutil | 4.0.0 | BSD-3-Clause |

### Infrastructure

| Component | SPDX | State | Decision |
|---|---|---|---|
| MinIO | **AGPL-3.0** | **archived** | **Do not adopt**; use S3/R2 or local disk |
| HashiCorp Vault | **BSL-1.1** (NOASSERTION) | active | **Avoid**; use OpenBao |
| OpenBao | MPL-2.0 | active | Approved for secrets/transit |
| Temporal | MIT | active | Approved (still disabled — no daemon) |
| Keycloak / OpenFGA / NATS | Apache-2.0 | active | Approved |
| OTel Collector | Apache-2.0 | active | Approved |
| pgvector / Qdrant | PostgreSQL / Apache-2.0 | active | Approved |
| gVisor / Firecracker / Kata | Apache-2.0 | active | Approved but unavailable on Termux |
| cosign / Syft / OSV-Scanner | Apache-2.0 | active | Approved |
| promptfoo | MIT | active | Optional adapter only |
| bagalsharad/agent_factory | Apache-2.0 | active | Approved as adapt |
| CrewAI / Google ADK | MIT / Apache-2.0 | active | Rejected (duplicate authority) |

## 5. Gate D1 status

- **D1.1 Orchestration — CONFIRMED:** `DbQueueOrchestrator` / DB-queue worker; no Temporal dependency.
- **D1.2 Sandbox tier — CONFIRMED:** T0 (declarative compilation, no untrusted host execution, import lane quarantined).
- **D1.3 Legacy factories — CONFIRMED:** legacy builders behind `AgentBuildPort` (strangler mapping).
- **D1.4 Phase 2 go-ahead — EFFECTIVELY EXECUTED:** Phases 2–10 and Stages 0–9 are on this branch; record sign-off (F4).

## 6. Residual risk

- No live PostgreSQL/RLS, container runtime, Temporal, or external SaaS was exercised; verification is T0/SQLite on Termux.
- Android resource limits make concurrency/benchmark tests non-representative; five tests are flaky under full-run contention only.
- Licence data is point-in-time; re-check `semgrep` (LGPL) and `MinIO` (archived) before any change of use.

## 7. Evidence files

`baseline_tests.txt`, `FAILURE_TRIAGE.md`, `failures_detail.txt`, `flaky_rerun.txt`, `governance_security.txt`, `gitleaks_console.txt`, `gitleaks_report.json`, `pip_audit_local.json`, `pip_audit_local_console.txt`, `npm_audit.json`, `licence_verification.json`.

**Sign-off: Phase 1 audit closed on `f59156c`. Go for Phase 2 review / pilot, subject to F1–F6 actions.**
