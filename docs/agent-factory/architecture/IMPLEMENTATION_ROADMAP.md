# IMPLEMENTATION_ROADMAP

**Method:** ten phases, each ends at a **human decision gate** (D1…D10). OpenCode stops at each gate and reports evidence. Effort figures assume one builder working with a coding agent and are **estimates with wide uncertainty** (±40 %); total ≈ 19–21 weeks before restricted-pilot readiness. Principle: *reuse before build; preserve existing behaviour; no phase merges without the existing test baseline still green (AT-22).*

| Phase | Weeks | Outcome |
|---|---|---|
| 1 Audit & baseline | 0.5–1 | Verified inventory, port map, test baseline, licence gate |
| 2 Foundation & governance | 2 | Schema, ports, API skeleton, evidence-before-success |
| 3 Templates & requirement engine | 2 | Spec/validator/calculator, ARS, template library v0 |
| 4 Single-agent manufacturing | 2 | One agent end-to-end into *staging* |
| 5 Batch & multi-agent | 2 | DAG, parallel workers, quotas, team manifest |
| 6 Capabilities & tools | 2 | MCP/A2A/knowledge/memory/browser bindings; sandbox + import (flag-gated) |
| 7 QA & certification | 3 | Independent QA, scanners, gates, signing |
| 8 Registry & provisioning | 1.5 | Release approval, atomic publish, assignment, marketplace UI |
| 9 Monitoring & lifecycle | 2 | SLOs, incidents, upgrades, rollback, Command Centre |
| 10 Enterprise acceptance | 2 | Full AT suite, security review, DR drill, readiness report |

---

## Phase 1 — Repository audit and architecture baseline (read-only)

| Item | Detail |
|---|---|
| Modules | none (documentation only) |
| Dependencies | repo access |
| Files to create | `docs/agent-factory/audit/{INVENTORY.md, PORT_MAP.md, audit_scan.json, baseline_tests.txt, API_CONVENTIONS.md, LICENCE_GATE.md}`; copy `architecture/` into `docs/agent-factory/architecture/` |
| Database | none |
| APIs | none (record conventions) |
| Tests | Run entire existing suite; save output |
| Security checks | Secrets scan of repo history (gitleaks) — report only; list prod credentials exposure |
| Acceptance | Every claimed component classified with evidence; 8 reuse questions answered; port map complete; baseline recorded; **licence gate** (every dependency the plan will add: exact licence/version/maintenance, re-verifying all `[KNOWLEDGE]` rows) |
| Risks | Audit reveals governance components are stubs (G-01..G-04) |
| Rollback | n/a (docs) |
| **Gate D1** | Human approves audit + any architecture adjustments |

## Phase 2 — Factory foundation and governance integration

| Item | Detail |
|---|---|
| Modules | `agent_factory/{domain,ports,adapters/zonata,api,migrations}`; feature flag; error/idempotency/rate-limit middleware; lifecycle-event writer; kill-switch checks |
| Dependencies | D1 |
| Files | per module layout; `migrations/001_agent_factory_core.sql` (adapted), `002_fks`; `adapters/zonata/{governance,identity,secrets,model_gateway,tools,mcp,memory,workforce,runtime,artifacts,orchestrator_*,telemetry}.py` + `fakes/`; router registration (single line in app factory) |
| Database | `001` + `002` |
| APIs | routes 1, 2, 12, 36, 37, 38, 39 (requests, jobs, kill, quotas, evidence, health) |
| Tests | Unit with fakes; DB tests: `001_verify.sql` equivalent; AT-10 (DB layer), AT-12 (RLS part), AT-14, AT-22 |
| Security checks | RLS under non-owner role; tenant only from principal; 404-not-403; evidence-before-success property test |
| Acceptance | Request can be created, authorised through the real AuthorityGateway, recorded in the real ledger, listed; all `001_verify` checks pass on the repo's DB; existing suite unchanged |
| Risks | Ports cannot be bound (governance stub) → stop-the-line |
| Rollback | `AF_ENABLED=0`; drop `af_*` (down migration) |
| **Gate D2** | Governance integration demo + test evidence |

## Phase 3 — Template library and requirement engine

| Item | Detail |
|---|---|
| Modules | `spec/` (schema, validator, permission calculator, compiler skeleton), `templates/` (loader, resolver, 6 starter templates: research, document-reporting, data-analysis, support-triage, supervisor, executive-advisor), `capabilities/` catalogue v0, `roles/requirement_analyst` (LangGraph graph + prompt files) |
| Dependencies | Phase 2; vendored modules from bagalsharad/agent_factory **after review** (record file list, commit hash, licence/NOTICE) |
| Files | per layout; `NOTICE` additions |
| Database | seed `003_seed_templates` (global rows) |
| APIs | 3, 4, 5, 13, 14, 15, 16 |
| Tests | Schema (positive + negative incl. agents-may-use-employees), calculator property tests (⊆ inputs, idempotent, monotone), template compat tests, ARS golden tests with recorded model responses + live smoke |
| Security checks | No credential-like strings pass validator (fuzz); template signature verification |
| Acceptance | NL request → valid ARS (≤5 clarifying questions); template resolution deterministic; AT-02 up to spec-render |
| Risks | LLM ARS quality; vendored code quality |
| Rollback | Disable analyze route; templates are data |
| **Gate D3** | Review ARS samples with owner |

## Phase 4 — Single-agent manufacturing

| Item | Detail |
|---|---|
| Modules | `control/director` (DB-queue first), `roles/{agent_architect,agent_developer,integration_engineer}`, `build/{pipeline,stages,workers}`, `registry/{agents,versions}`, signer, `spec/compiler` + `GovernedCall` runtime wrapper, staging runtime deploy |
| Dependencies | Phase 3 |
| Files | per layout |
| Database | none new |
| APIs | 9 (start), 18 (builds), 26 (read), version read |
| Tests | AT-01 (mock model for plumbing + one real-model run), AT-08, AT-11 (partial), compiler tests (every external node wrapped), signature tests |
| Security checks | Frozen `permission_profile`; secrets never in spec; staged agent can't call ungranted tool |
| Acceptance | Request → BUILT agent version in staging, signed package, ledger entries per stage |
| Risks | Compiler gaps vs. LangGraph features |
| Rollback | Disable build start; staging only |
| **Gate D4** | Demo one agent running under governance |

## Phase 5 — Batch and multi-agent manufacturing

| Item | Detail |
|---|---|
| Modules | `control/{planner,quota,budget,estimator}` (lift `batch_scheduler.py`), orchestrator adapters (Temporal if available, DB-queue), team manifest, team compile (supervisor/hierarchical), shared knowledge ACL |
| Dependencies | Phase 4 |
| Database | none new |
| APIs | 7, 8, 10, 11 |
| Tests | AT-04, 05, 06, 07, 19, 20; planner unit tests (15 existing checks ported) |
| Security checks | Delegation = min(); cycle rejection; per-tenant quota atomicity (race test) |
| Acceptance | Marketing team of 7 builds in waves with correct concurrency; failure of one item blocks dependants; cost cap enforced |
| Risks | Concurrency bugs; free-tier single worker (document) |
| Rollback | Limit `agent_count` to 1 via policy |
| **Gate D5** | |

## Phase 6 — Capability and tool integration

| Item | Detail |
|---|---|
| Modules | Capability implementations: MCP (gateway, hash pinning), A2A (peers, narrowing), knowledge/memory scopes (Letta/pgvector via existing layers), browser (allowlist, SSRF guard), DB views, reporting; `build/sandbox_client`; Import lane; OpenHands Tool Smith (flag) |
| Dependencies | Phase 5; sandbox host if T1/T2 desired |
| APIs | 27 |
| Tests | AT-13; SB-01..06 (only when sandbox enabled); browser SSRF; tool-poisoning |
| Security checks | Egress policy tests; no secrets in sandbox; scanner gates |
| Acceptance | Agents use only granted tools; ungranted blocked + evidenced; if sandbox disabled, `/ready` says so and code-bearing requests are rejected with `AF-SANDBOX-UNAVAILABLE` |
| Risks | Sandbox infra unavailable (expected on free tier) |
| Rollback | `AF_SANDBOX_TIERS=""` |
| **Gate D6** | |

## Phase 7 — Automated QA and certification

| Item | Detail |
|---|---|
| Modules | `qa/{datasets,runners,scanners,redteam,scoring}`, `cert/{gates,bundle,signer,verifier}`, QA Director, Security/Functional/Performance services, Langfuse dataset integration |
| Dependencies | Phase 6 (tools to test), real model profile and budget |
| APIs | 19, 20, 21, 22 |
| Tests | AT-09, AT-15, AT-21; gate evaluator tests ported; calibration with a known-good and known-bad agent per dataset; flakiness measurement |
| Security checks | Held-out isolation (FGA deny for builder roles); judge separation; evaluator-independence trigger |
| Acceptance | A good agent certifies; a deliberately flawed one is rejected for the right gate; bundle verifies offline; **first real measured thresholds reviewed** (D7 may adjust policy v1.0.0 → v1.1.0 via the formal change path) |
| Risks | Dataset quality; LLM cost; judge bias |
| Rollback | Certification disabled ⇒ nothing can be released |
| **Gate D7** | Owner reviews measured pass rates and policy |

## Phase 8 — Agent registry and provisioning

| Item | Detail |
|---|---|
| Modules | `registry/{release,assignment,lifecycle}`, Release Manager, ApprovalEngine integration, atomic team publish, runtime channels (staging/canary/prod), WorkforcePort assignment; **Marketplace UI M1–M6** |
| APIs | 23, 24, 25, 26, 28, 29, 32 |
| Tests | AT-10, 16, 17, 05 (atomic publish incl. failure injection), UI contract tests |
| Security checks | Approval bound to certification hash; approver disjointness; unsigned package refused by runtime |
| Acceptance | Approved agent appears for the assigned employee; rollback works; partial team publication impossible |
| Rollback | Revoke release; pointer back |
| **Gate D8** | |

## Phase 9 — Monitoring, upgrades and lifecycle management

| Item | Detail |
|---|---|
| Modules | `monitor/{collector,slo,incidents}`, Monitoring Engineer analyst, upgrade lane (G10), suspend/resume/retire, feedback, canary evals, **Command Centre C1–C15** |
| APIs | 30, 31, 33, 34, 35 |
| Tests | AT-03, 18; incident-rule tests (zero-tolerance ⇒ suspend ≤5 s); upgrade regression tests |
| Security checks | No self-modification path exists (route/DB audit); retire revokes principal/tokens/bindings |
| Acceptance | Degradation detected on seeded fault; rollback one-click; upgrade requires re-certification |
| **Gate D9** | |

## Phase 10 — Enterprise acceptance and restricted-pilot readiness

| Item | Detail |
|---|---|
| Work | Run AT-01…22 + SB on target infra; independent security review (internal red-team + external if budget); load/soak where infra allows; DR drill; runbooks; documentation; **Readiness report** (validated / not validated matrix) |
| Acceptance | All 22 AT pass with evidence; no open critical/high; baseline suite green; pilot exit criteria and kill criteria defined |
| Risks | Unvalidated scale claims |
| **Gate D10** | Go / no-go for restricted pilot |

## Cross-phase rules

Small commits, one concern each; migrations additive; every phase updates `docs/agent-factory/STATUS.md` (what is verified, what is not); no phase may weaken a gate to pass; CI blocks merging if AT-22 baseline diverges.
