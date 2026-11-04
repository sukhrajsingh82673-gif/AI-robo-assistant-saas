# Stage 1 — Internal Simulation: Northstar Business Systems
## Evidence-based capability and gap report

**Date:** 2026-11-03 (post-enterprise multi-company + skill-arena revision)
**Repo:** `/root/roboassistant` @ `ed059eb` (`hardening/real-llm-tenant-isolation`) + uncommitted skill/arena batch listed below
**Instance:** SQLite `ZONATA_DB_PATH=/tmp/opencode/ns1/storage/ns1.db`, server on `127.0.0.1:8101`, `APP_ENV=development`
**Company:** Northstar Business Systems (`comp_994fc2`) inside tenant `tnt_primary`
**Control tenant:** `tnt_beta` / `comp_beta` (isolation probes)
**Evidence directory:** `/tmp/opencode/ns1/evidence/`
**Data:** 100% synthetic (`.test` email domains, fabricated customers, no real PII, no real money)

---

## 1. Verdict

Stage 1 is **partially successful**, and materially more honest after the P0 pass.

A complete, data-grounded business loop exists and can be demonstrated:
company onboarding → CRM/records/finance writes → AI CEO grounded analysis → mission with a real LLM → SHA-256/ed25519 evidence seal → tenant isolation.

Three product claims that were **false at first measurement are now fixed and re-verified** (see §4 and `evidence/p0_verification.json`):

1. **Browser navigation is real.** `navigate` performs an HTTP fetch (example.com: HTTP 200, 577 bytes, real title "Example Domain", 6.4 s). The fabricated `ORD-…` / `₹45,00,000` DOM is gone; a test-only fixture is gated behind `ZONATA_TEST_MODE=1`. Click/type/submit now return `ACTION_NOT_IMPLEMENTED` outside tests instead of pretending to succeed, and `EXTRACT` returns only parsed page text.
2. **Workflow verification is no longer tautological.** It reports `verification_scope: STATE_INTEGRITY_ONLY` and `business_outcome_verified: false`, honours the caller's input, and the approval workflow explicitly states that no funds were transferred.
3. **Truncated deliverables are refused.** A deliverable cut off at the model token limit ends `UNCERTAIN` with `VERIFICATION_REFUSED` and **no** evidence seal. Verified by `tests/test_mission_truncation_guard.py`.

One **release-blocking security defect was found and fixed**: the terminal agent could read live `DATABASE_URL` credentials out of `.env.local` (and would have read private keys). Two **cross-tenant leaks were found and fixed**. The **global kill switch is now authoritative on every execution surface**: terminal, missions, browser, MCP, workflows, workloads, A2A, OpenHands, finance and workforce all return `403` while engaged (15/15 probes).

The enterprise multi-company batch closed the largest functional gaps: a real expense-approval workflow with a posted-and-re-read GL outcome, role-gated approvals, per-claim/department/company budgets with segregation of duties, deterministic CEO metrics, live MCP resources, per-tenant workflow runtimes, and company-scoped evidence verification.

The skill-arena batch adds a governed decision layer rather than a pretend one: 12 skills are executable contracts, and corporate decisions are scored by four independent deterministic lenses with explicit `CONSENSUS` / `MAJORITY` / `CONTESTED` / `INSUFFICIENT_EVIDENCE` outcomes, authority tiers, real approvals and sealed evidence. Disagreement is never averaged away and missing evidence is never answered confidently.

The workforce batch turns the previously empty 25-table corporate schema into a working company: an organization is provisioned from an industry blueprint (15 industries), with 13 C-suite executives, multi-level reporting, configurable departments and positions, authority profiles, SOP versioning, KRA/KPI with anti-gaming, explainable performance reviews, a shared agent-capability factory with isolated per-employee instances, and governed cross-department collaboration. Live proof: 17 departments, 13 executives, cycle rejection, quota rejection, cross-employee isolation, a refused unevidenced measurement and a `109.8/EXCEEDING` explainable review — all over authenticated HTTP with retained evidence. Building it also exposed and closed two real defects: `organizations` had no `company_id` (a same-tenant cross-company read leak) and a company could be provisioned twice.

The product is still **not** a fully operating AI company: there is no real browser interaction engine, mission delegation is limited to terminal filesystem/environment facts, blueprint/employee budgets are not enforced at execution time, SOP versions are not yet executed by the agent runtime, and onboarding/billing/partner capability pages are missing.

Recommendation: **do not start Stage 2 (design-partner pilot)** until the owner revokes the compromised PAT, rotates the Neon credential, and the browser/delegation/partner-page gaps in §6 are resolved or hidden from partner UI. Paid infrastructure is not justified by the current evidence.

---

## 2. Method

- Every write went through the same authenticated HTTP API a UI client uses (no direct DB seeding for business data).
- Every claim below maps to a retained raw response in `/tmp/opencode/ns1/evidence/`.
- Capabilities were exercised, not inferred from tests. Test-suite results are reported separately in §5 and are **not** treated as proof of end-to-end behaviour.
- Where a capability failed or is simulated, the status says so; nothing was re-labelled to make a milestone pass.

---

## 3. Capability matrix

Legend: **VERIFIED** = ran end-to-end with retained evidence · **PARTIAL** = some real behaviour, some gap · **UNVERIFIED** = implemented but not proven · **BLOCKED** = cannot run in this environment · **NOT IMPLEMENTED** = surface exists but does nothing real · **FAILED** = ran and produced a wrong result.

| # | Capability | Status | What actually happened | Evidence |
|---|---|---|---|---|
| 1 | Company onboarding (tenant-scoped) | VERIFIED | `POST /api/onboard` created `comp_994fc2`, 5 departments, 2 seeded employees; no cross-tenant visibility | `onboard_northstar.json` |
| 2 | CRM customers / deals | VERIFIED | 5 customers, 6 deals created; MRR ₹41,995, weighted pipeline ₹31,897.20/mo recomputed from rows | `populate.json` |
| 3 | Business records (products, projects, onboarding, charter) | PARTIAL | 12 records created through `/api/records`; no first-class product/project/onboarding entities, so they are opaque `record_type` rows | `populate.json` |
| 4 | Finance — chart of accounts | VERIFIED | Per-company CoA provisioned (12 accounts, ids `comp_994fc2_acc_*`) | `finance_lifecycle.json` |
| 5 | Finance — expense → GL posting | VERIFIED | ₹12,000 approval posted to GL 6020 with journal `tx_ce738566`. Policy now enforced: client `APPROVED` ignored (enters `SUBMITTED`), per-claim cap, department/company budgets at intake *and* approval, claimant ≠ approver, duplicate/cross-company approval rejected. Workflow proof: ₹4,321.75 → `tx_6c3241ab`, GL 6020 `12000.00 → 16321.75`, `business_outcome_verified: true` | `finance_lifecycle.json`, `p1_live_api_part1.json`, `p1_live_api_part2.json` |
| 6 | AI CEO chat grounded in company data | VERIFIED | Deterministic `computed_metrics` injected and returned: 5 customers, MRR ₹41,995, ARR ₹503,940, weighted pipeline ₹31,897.2, pending ₹29,350, posted ₹21,697. Live CEO answer quoted the computed values; `comp_beta` returned zeros under its own `company_id`. Degraded responses still include the metrics | `ceo_chat_grounded.json`, `p1_live_api_ceo_metrics.json` |
| 7 | AI CEO tenant isolation | VERIFIED | `tnt_beta` context has 0 customers/pipeline/expenses and no company name | `ceo_context_isolation.json` |
| 8 | Mission runtime (NS-001) | PARTIAL | Real `embedded_free/openai-fast` plan + grounded deliverable. Truncation is detected (`UNCERTAIN` + `VERIFICATION_REFUSED`, no seal); `llm_max_tokens` now governs output with a bounded continuation loop. Delegation is real but limited to `TerminalProvider` filesystem/environment inspection with per-capability timeline events and a delegation digest; no general specialist-agent routing | `mission_run.json`, `tests/test_mission_truncation_guard.py` |
| 9 | Evidence ledger (mission) | VERIFIED | `EV-7DCECE5B`, ed25519 signature, merkle index 2127, SHA-256 `ff6df601…` matches file; beta sees 0 records | `mission_run.json` |
| 10 | Evidence "verification" semantics | PARTIAL (after fix) | `GET /api/evidence/<id>/verify` recomputes the payload digest, re-verifies every link in the record's epoch, re-hashes physical file artifacts, and reports DB postconditions as `REQUIRES_EXECUTION_CONTEXT`. Live: `VERIFIED`, `chain_scope: ACTIVE_EPOCH`, 37 historical forks recorded. Content correctness still depends on the originating execution context | `p1_live_api_evidence.json` |
| 11 | Governed terminal — execution | VERIFIED | Real commands, exit codes, evidence ids, snapshot ids; write/read file works; `rm -rf /` denied | `terminal.json` |
| 12 | Governed terminal — secret protection | VERIFIED (after fix) | **Before:** read live Neon `DATABASE_URL` from `.env.local`. **After:** `.env*`, `id_rsa`, `*.pem`, `.git-credentials`, `.netrc`, `.aws/credentials`, `.npmrc`, credentials JSON, `enterprise_settings.json`, `/etc/shadow` denied; outputs scrubbed | `terminal_secret_probe.json`, `terminal_secret_probe_after_fix.json` |
| 13 | MCP — server registration/trust | VERIFIED | Real local JSON-RPC server on `127.0.0.1:8123` registered → validated → trusted | `mcp_register.json` |
| 14 | MCP — discovery + resources | VERIFIED (after fix) | `refresh` performs live `tools/list` (`LIVE_TOOLS_LIST`, 2 tools) and `resources/list` (`LIVE_RESOURCES_LIST`, 1 resource); `resources/read` returns live content (`LIVE_RESOURCES_READ`, `read_verified: true`). `test` measures real `initialize` latency (11.4 ms), or `UNREACHABLE`; failures are reported, untrusted servers `SKIPPED_UNTRUSTED` | `p0_verification.json`, `p1_live_api_mcp.json` |
| 15 | MCP — read-only tool invocation | VERIFIED | `get_onboarding_summary` executed against the real server, returned real data, `VERIFIED`, evidence `EV-B1C70902`, SHA-256 sealed | `mcp_invoke.json` |
| 16 | MCP — financial tool approval gate | VERIFIED (after fix) | Call suspends (`APPROVAL_REQUIRED`, `apr_*`); approval resumes through every gate and the real server recorded the refund (`VERIFIED`, `EV-8687FA1E`); rejection closes the suspended execution as `REJECTED`. A forged `pre_approved_id` is denied `POLICY_DENIED` | `p0_verification.json` |
| 17 | MCP — execution listing API | VERIFIED | `GET /api/mcp/executions` returns full rows including `execution_status` and `verification_status`. The earlier claim that these were omitted was incorrect | `p0_verification.json` |
| 18 | Browser — session creation | VERIFIED | Session created with domain allow-list, SSRF/domain policy evaluated | `browser.json` |
| 19 | Browser — navigation | VERIFIED (after fix) | Real `urllib` fetch: `https://example.com` → HTTP 200, 577 bytes, title "Example Domain", `REAL_HTTP_FETCH`, 6.4 s. Non-allowlisted host → `403`. Unreachable host → `NAVIGATION_FAILED`, no invented content. Test fixture only under `ZONATA_TEST_MODE=1` | `browser_after_fix.json` |
| 19a | Browser — data extraction | VERIFIED (after fix) | `EXTRACT` returns parsed page text, title, status and selector matches; unmatched selector → `ELEMENT_NOT_FOUND`; fabricated records/KPI removed | `browser_after_fix.json` |
| 19b | Browser — click / type / submit | NOT IMPLEMENTED | No browser engine installed; actions return `ACTION_NOT_IMPLEMENTED` instead of a fake success. Financial selectors still intercept first with `APPROVAL_REQUIRED` | `browser_after_fix.json` |
| 20 | Agent Factory — blueprint synthesis | PARTIAL | Blueprint created per tenant with budget ₹30,000 and tool list, but output is template-based (role fixed to "Operations Specialist", generic responsibilities), not LLM-designed from the prompt | `agent_factory.json` |
| 21 | Employee creation | PARTIAL | Employee persisted with scoped tools/budget, but there is no API to execute work *as* that employee; generated tools (`python3`, `jq`, `tar`) are not what an onboarding specialist needs | `agent_factory.json` |
| 22 | Workflows — run lifecycle + isolation | VERIFIED | State machine runs, checkpoints, lease, evidence. Per-tenant runtimes (no shared state/checkpoints) and token-derived tenant/company; reserved `__*` keys stripped. Caller input is honoured | `p0_verification.json`, `p1_live_api_part2.json` |
| 23 | Workflows — verification | VERIFIED | Canonical demo workflows honestly report `STATE_INTEGRITY_ONLY` / `business_outcome_verified: false`. `wf_company_expense_approval` goes further: role-gated approval → real GL post → independent DB re-read of expense row, matching transaction and balance delta; only then `business_outcome_verified: true` | `p1_live_api_part2.json`, `zonata/langgraph_adapter.py` |
| 24 | Kill switch — workflows | VERIFIED | Engaged via API → workflow start blocked with `KILLSWITCH_ENGAGED`; disengage restores | `killswitch.json` |
| 25 | Kill switch — automation | VERIFIED (after fix) | Global gate checked at execution time on 15/15 surfaces: terminal, mission submit/step, browser sessions/executions, MCP invoke, workflow run/resume/recover, workload launcher, A2A delegation, OpenHands create/command, finance create/approve, workforce execute. Non-governance roles cannot toggle it; disengage restores real execution | `p0_verification.json`, `p1_live_api_killswitch.json`, `p1_live_api_killswitch2.json` |
| 26 | Kill switch — browser/terminal | VERIFIED (after fix) | Covered by the authoritative global automation gate; browser scoped kill switches also exist | `p0_verification.json` |
| 27 | Restart persistence | VERIFIED | After kill -9 + restart: 5 customers, 6 deals, 12 records, 5 employees, blueprint, MCP server + 2 tools, finance (₹12,000 posted / ₹28,000 pending), workflow run, mission `COMPLETED` | `restart_persistence.json` |
| 28 | Tenant isolation — records/files/agent-factory | VERIFIED (after fix) | Before fix `tnt_beta` read `tnt_primary` agent blueprints; after per-tenant engines both tenants see only their own (0 vs 0 for beta, own only for Northstar) | `tenant_isolation_after_fixes.json` |
| 29 | Tenant isolation — MCP | VERIFIED | `tnt_beta` invoking Northstar's server → `403 Cross-tenant access prohibited` | `tenant_isolation_after_fixes.json` |
| 30 | Tenant isolation — workflow runs | VERIFIED (after fix) | Before fix beta saw Northstar's run; after fix beta sees 0 runs, `404` on run state, `404` on pause | `tenant_isolation_after_fixes.json` |
| 31 | Tenant isolation — missions/evidence | VERIFIED | beta gets `404` on mission, 0 evidence rows | `mission_run.json` |
| 32 | Tenant isolation — finance | VERIFIED | beta approval of Northstar expense → `400 not found`; beta sees 0 customers, ₹0 balances | `finance_lifecycle.json` |
| 33 | Approval pipeline (human-in-the-loop) | VERIFIED (after fix) | MCP approvals validate and resume the exact suspended execution; forged ids denied; rejection closes it. Workflow and finance approvals are role-gated (OWNER/EXECUTIVE/GLOBAL_ADMIN), company-scoped, identity derived from the token, and double/duplicate decisions rejected. Live: OBSERVER/MANAGER `403`, EXECUTIVE approval posts to GL | `p0_verification.json`, `p1_live_api_part2.json` |
| 34 | Budget / spending limits | PARTIAL | Department and company monthly budgets are enforced at expense intake *and* approval; per-claim hard limit is configurable. Blueprint/employee budgets remain fields with no proven execution-time enforcement | `agent_factory.json`, `p1_live_api_part1.json` |
| 35 | Default LLM (free, owner-configurable) | VERIFIED | `embedded_free` (Pollinations `openai-fast` → gpt-oss-20b) answered keyless; owner-configurable provider list present; failures degrade honestly with `degraded=true` | `ceo_chat_grounded.json` |
| 36 | LLM availability under rate limits | PARTIAL | Free tier ≈1 req/30 s; retries/cooldown added, but runs still occasionally end `BLOCKED — no language model provider is available` | `mission_submit2.json` |
| 37 | Browser E2E in CI | BLOCKED | No Playwright, no Chromium, no Docker in this sandbox; the JS E2E scripts were not executed | environment check |
| 38 | Live Postgres | BLOCKED | `psycopg2` importable but no server reachable; all evidence is SQLite | environment check |
| 39 | GitHub push / CI | BLOCKED | The pasted PAT is compromised and must be revoked; no fresh token, `gh` not logged in, no SSH key. Commit `e2d04c7` and the enterprise fixes are local only | `git status` |
| 40 | Department management | VERIFIED | `POST /api/departments` role-gated (OBSERVER `403`), duplicate `409`, numeric validation, token-derived tenant/company; `GET` returns only the token's company | `p1_live_api_part1.json` |
| 41 | Evidence isolation | VERIFIED | New records carry `tenant_id`/`company_id`; another company or tenant gets `404 EVIDENCE_NOT_FOUND`; `GET /api/evidence` filters both. Legacy records lack company metadata and remain readable within the tenant | `p1_live_api_evidence_scope.json` |
| 42 | Deterministic company metrics | VERIFIED | ARR/MRR/weighted pipeline/expenses/finance computed in code from tenant+company rows with CI-safe divisions; injected into CEO context and returned on degradation | `p1_live_api_ceo_metrics.json` |
| 43 | Multi-company controls regression | VERIFIED | 16-test suite covers tenant/company isolation, finance policy, budgets, approval roles, workflow scoping, metrics, evidence | `tests/test_enterprise_multi_company_controls.py` |
| 44 | Executable skill contracts | VERIFIED | 12 skills, each an enforced contract: minimum authority tier, risk class, required inputs, checks, hard limits and protocol source. A run evaluates the contract, persists it in `skill_runs`, seals evidence, and the run history is readable company-scoped at `GET /api/arena/skill-runs`. Live: owner `verified-delivery` → `SATISFIED`, `EV-A940E802`; operator `board-reporting` → `ESCALATED` (requires `EXECUTIVE`) | `p2_skill_arena_live.json`, `tests/test_skill_arena.py` |
| 45 | Multi-judge decision arena | VERIFIED (deterministic) | 2–8 options scored by 4 independent lenses (FINANCE/RISK/OPERATIONS/COMPLIANCE) with Borda + aggregate ranking. Disagreement surfaces as `CONTESTED`; missing evidence produces `NEEDS_EVIDENCE`; policy denial produces `DENIED`; high-risk/contested/low-authority outcomes create a real approval. Live low-risk: `DECIDED`/`CONSENSUS`, winner `vendor_a`, `EV-14D45C00`; live high-risk as MANAGER: `ESCALATED`, approval `apr_fa15d6e1` | `p2_skill_arena_live.json`, `tests/test_skill_arena.py` |
| 46 | Decision authority tiers + isolation | VERIFIED | Role→tier mapping (EMPLOYEE/MANAGER/EXECUTIVE/OWNER); risk and policy can only raise the required tier. Decision retrieval is company-scoped: beta token → `404`, decision list not shared. Kill switch blocks both arena evaluation and skill execution (`403`) | `p2_skill_arena_live.json` |
| 47 | Arena approval decision identity | VERIFIED (after fix) | `POST /api/approvals/<id>/decide` previously decided as a hardcoded OWNER. It now derives user/role from the token and enforces company scope: OBSERVER `403`, OWNER `200 APPROVED` with signed grant hash | `p2_skill_arena_live.json` |
| 48 | Organization + department + position provisioning | VERIFIED | `POST /api/workforce/organization` builds a whole company from a data-driven industry blueprint. Live: 17 departments, 13 executives, 40+ employees, every mutation sealed (`EV-5537CD9C`). Departments, positions and hires are separately addressable endpoints | `p3_workforce_live.json` |
| 49 | Dynamic multi-level hierarchy | VERIFIED | Executive → director → manager → specialist chains are created and stored in `employee_reporting_relationships`; `reporting_chain()` walks real rows. Live CEO chain returned through the API; a G8 specialist sits ≥3 levels below the CEO | `p3_workforce_live.json`, `tests/test_workforce_architecture.py` |
| 50 | Reporting-cycle and grade guards | VERIFIED | Making the CEO report to the COO is rejected (`400`, "cycle"); self-management is rejected; a senior position cannot report to a junior one; cross-company managers are refused | `p3_workforce_live.json` |
| 51 | One enterprise root per company | VERIFIED (after fix) | A second `POST /api/workforce/organization` for the same company is rejected instead of colliding on department codes. `organizations` now carries `company_id`, closing a same-tenant cross-company read leak found while testing | `p3_workforce_live.json` |
| 52 | Industry coverage of the C-suite | VERIFIED | 15 industry blueprints. Marketing/Sales/Product/Customer-Success are base departments, so **every** industry provisions all 13 chiefs; sector blueprints override them with specialised roles. Live financial services: 13/13 executives | `p3_workforce_live.json`, `tests/test_workforce_architecture.py` |
| 53 | Authority profiles and spend limits | VERIFIED (mapped, not enforced at execution) | G1–G9 map to OWNER/EXECUTIVE/MANAGER/EMPLOYEE tiers with single/monthly spend limits, hire/delegate/SOP rights, data classifications and a signature hash. These are **stored and returned**, not yet consulted by the finance or agent runtimes | `tests/test_workforce_architecture.py` |
| 54 | Employee identity and lifecycle | VERIFIED | Employees get a code, internal `.test` work email, position, department, authority profile, knowledge clearance. Deactivation requires OWNER authority, sets the kill switch, releases the seat and keeps history (no hard delete) | `tests/test_workforce_architecture.py` |
| 55 | SOP definition and immutable versioning | VERIFIED | `POST /api/workforce/sops` + `/versions`. Versions are content-hashed; republishing the same semver is refused; only `APPROVED` versions can be assigned; assignment supersedes the previous one | `tests/test_workforce_architecture.py` |
| 56 | KRA/KPI with anti-gaming | VERIFIED | KRA weights capped at 100%. KPI definitions support polarity, thresholds, paired counter-metrics. A measurement without an evidence reference is refused; a paired counter-metric is mandatory when defined | `p3_workforce_live.json` |
| 57 | Explainable performance evaluation | VERIFIED | 4-factor composite (KPI 0.55, SOP 0.20, anti-gaming 0.10, collaboration 0.15) with the formula and per-KPI weights stored. Refuses to score without measurements (`409 INSUFFICIENT_MEASUREMENTS`) or without KRAs (`400`); blocked external KPIs are excluded and named, never penalised. Live: `109.8` / `EXCEEDING` with `EV-D2F9320F` | `p3_workforce_live.json` |
| 58 | Shared agent capabilities, isolated instances | VERIFIED | Capabilities and signed templates are shared per tenant; each provisioning creates its own instance, lease, execution session, memory scope and session token. Quota default 4/employee; live third instance → `400`; another employee cannot terminate the instance (`400`); unregistered capability refused | `p3_workforce_live.json` |
| 59 | Governed cross-department collaboration | VERIFIED | Requires a real mission, two distinct departments, an accountable deliverable, positive SLA and a valid escalation executive. Lifecycle `REQUESTED → ACCEPTED → FULFILLED` is enforced; fulfilling before acceptance → `400` | `p3_workforce_live.json` |
| 60 | Workforce API authority gating | VERIFIED | Reads require report authority (OPERATOR/OBSERVER `403`); writes require OWNER/EXECUTIVE; deactivation requires OWNER. Company is resolved from the token and verified against the tenant. Every POST is behind the global kill switch | `p3_workforce_live.json`, `tests/test_workforce_api.py` |
| 61 | Legacy-schema self-healing | VERIFIED (after fix) | A pilot DB whose `employee_kras` came from the V7 KPI engine lacked `weight_percentage`/`position_id`; the service now probes the exact columns it writes and runs the additive migrations once per database. `organizations.company_id` is added the same way | `p3_workforce_live.json` |

---

## 4. Findings that invalidate product claims

### F1 — Browser was fabricated (severity: high, honesty — fixed)
`BrowserUseExecutionProvider.navigate()` originally never opened a socket; it built fixed markup and returned `success: true`. It now performs a real HTTP fetch and reports the true title/status/size (`browser_after_fix.json`). Interaction actions (click/type/submit) are explicitly `ACTION_NOT_IMPLEMENTED` because no browser engine exists. The test fixture is gated behind `ZONATA_TEST_MODE=1`.
**Residual:** no headless engine means no form submission, screenshots or JS execution; screenshot artifacts are `NOT_CAPTURED`.
**Evidence:** `evidence/browser.json` (pre-fix), `evidence/browser_after_fix.json` (post-fix).

### F2 — Workflow verification proved nothing (severity: high, honesty — fixed)
`zonata/langgraph_adapter.py` previously compared a hash to itself and labelled it verified. It now returns `verification_scope: STATE_INTEGRITY_ONLY` and `business_outcome_verified: false`, explicitly stating that no external action occurred. The approval workflow no longer claims `disbursed: true`.
**Residual:** only the canonical demo workflows remain state-transition-only. The new `wf_company_expense_approval` performs a real, independent business outcome: it validates a SUBMITTED claim, pauses for a role-gated approval, posts to the general ledger, then re-reads the expense row, matching transaction and account balance delta. Live API proof: expense `4321.75` → `tx_6c3241ab` → GL 6020 balance `12000.00 → 16321.75`, `business_outcome_verified: true`, sealed as `EV-6A27866C`.
**Evidence:** `evidence/workflow.json` (pre-fix), `evidence/p0_verification.json`, `evidence/p1_live_api_part2.json` (post-fix).

### F3 — Terminal could read production secrets (severity: critical, fixed)
`head -c 120 /root/roboassistant/.env.local` returned a live `DATABASE_URL=postgresql://<user>:<secret>@<host>/<db>` credential. Fixed via deny-lists and output scrubbing; re-probe returns `POLICY_DENIED`.
**Residual:** the credential is still live in `.env.local` and must be **rotated**; the embedded PAT in `origin` must also be **revoked**.

### F4 — Cross-tenant leaks (severity: critical, fixed)
- Agent Factory / Records / Files were module-level singletons bound to `tnt_primary`; `tnt_beta` read `tnt_primary` blueprints.
- `GET /api/workflows/runs` returned runs for all tenants because the runtime is a process-wide singleton; run mutation endpoints were unguarded.
Both fixed and re-tested.

### F5 — Truncated deliverable accepted as verified (severity: medium — fixed)
NS-001's deliverable originally ended mid-table (3,636 bytes) at the token limit but was marked `COMPLETED`. The dispatcher now records `finish_reason`, writes a `DELIVERABLE_TRUNCATED` marker, and refuses verification: status `UNCERTAIN`, timeline `VERIFICATION_REFUSED`, `evidence_id` empty. Verified deterministically by `tests/test_mission_truncation_guard.py`.
**Residual:** the continuation loop is bounded (default 2, cap 5) because the free tier is rate-limited; a deliverable that still exceeds the budget is marked truncated rather than silently accepted.

### F6 — Kill switch was not authoritative (severity: high — fixed)
The automation kill switch previously let terminal execution and new missions proceed. It is now checked at execution time on every execution surface: terminal, mission submit/step, browser sessions/executions, MCP invoke, workflow run/resume/recover, workload launcher, A2A delegation, OpenHands create/command, finance create/approve and workforce execute. Live proof: 15/15 surfaces returned `403` while engaged; non-governance roles could not toggle it; disengaging restored a real terminal command (`exit_code: 0`). (`p0_verification.json`, `p1_live_api_killswitch.json`, `p1_live_api_killswitch2.json`.)

### F7 — MCP approval dead-end (severity: high — fixed)
Approved MCP operations were never resumed. `resume_approved_execution()` now runs on approval, re-checks the approval (APPROVED, same tenant/company), re-invokes the real tool and records evidence (`VERIFIED`, `EV-8687FA1E`; the local server's state file recorded the refund). Rejection marks the suspended execution `REJECTED`. A client-supplied `pre_approved_id` is validated and forged ids are `POLICY_DENIED`.

### F8 — No MCP discovery (severity: medium — fixed)
`refresh` calls the live `tools/list` and registers returned tools (`LIVE_TOOLS_LIST`); `resources/list` discovers real resources (`LIVE_RESOURCES_LIST`) and `resources/read` returns live content under trust + kill-switch checks (`LIVE_RESOURCES_READ`). `test_server_connection` now performs a real `initialize` RPC and reports measured latency (11.4 ms live), or `UNREACHABLE` on failure — the hard-coded `12.4` ms value is gone. Live proof: `p1_live_api_mcp.json`.

### F9 — API/handler signature drift (severity: medium, fixed where found)
Three endpoints crashed on first use: `POST /api/mcp/servers` (`auth_token`), `POST /api/browser/executions` (`task_id`), `POST /api/browser/action` (`human_intent`). This means these paths had never been exercised in the current branch.

### F10 — CEO miscomputed weighted pipeline (severity: low — fixed)
Grounded context was correct; the model's arithmetic was not. Financial metrics are now computed in `core/company_metrics.py` from tenant+company-scoped SQL and injected as `computed_metrics` / `metric_brief`; the CEO is instructed to quote them exactly. Live proof: MRR ₹41,995, ARR ₹503,940, weighted pipeline ₹31,897.2; `comp_beta` returned zeros under its own `company_id` (`p1_live_api_ceo_metrics.json`).

### F11 — Browser provider sessions are in-memory only (severity: low)
Session rows persist in the DB, but the provider's session/DOM state does not. After a restart, `navigate` re-initialises silently and `action` returns `Session … not found`. Combined with F1, no browser state can be trusted across restarts.

---

## 5. Test suite results (after fixes)

Run against an isolated pytest DB (`tests/conftest.py`), on the patched tree, on 2026-11-03 (after the enterprise multi-company and skill-arena batches):

| Suite | Result |
|---|---|
| `tests/test_skill_arena.py` + `tests/test_enterprise_multi_company_controls.py` | 30 passed |
| `tests/test_workforce_architecture.py` (new) | 45 passed |
| `tests/test_workforce_api.py` (new) | 12 passed |
| `tests/test_v7_employee_template_and_factory.py` + `tests/test_v7_ceo_workforce_and_collaboration.py` + `tests/test_enterprise_workforce.py` + `tests/test_workforce_orchestrator.py` + `tests/test_aic_organization_layer.py` | 55 passed |
| `tests/test_durable_workflow.py` + `tests/test_mcp_interoperability.py` + `tests/test_browser_use_execution.py` + `tests/test_mission_truncation_guard.py` | 121 passed |
| `tests/test_public_ga_integrity_and_finance.py` + `test_phase_16_tenant_fairness.py` + `test_direct_object_access_and_tenant_security.py` + `test_tenant_concurrency_and_instance_persistence.py` | 33 passed |
| `tests/test_governed_terminal_runtime.py` + `test_universal_linux_terminal_fabric.py` + `tests/test_step2_operational_validation.py` | 47 passed |

**Caveat:** browser tests exercise the deterministic test fixture under `ZONATA_TEST_MODE=1`; they prove governance and parsing logic, not a real browser engine. Real-network behaviour is evidenced separately (`browser_after_fix.json`). Green tests are not treated as proof of end-to-end capability.

**Still not runnable here:** Playwright/Chromium E2E, Docker/container suites, live-Postgres suite.

---

## 6. Prioritised remediation before Stage 2

**P0 — must fix before any design partner sees the product**
1. ~~Remove or gate browser "verified" claims.~~ **Done:** real HTTP navigation, honest failures, no fabricated DOM, interactions refused. Remaining: a real headless engine (Playwright) is still absent, so form submission is `NOT IMPLEMENTED`.
2. ~~Replace tautological workflow verification.~~ **Done:** canonical demo workflows report `STATE_INTEGRITY_ONLY` / `business_outcome_verified: false` with an honest disbursement flag; `wf_company_expense_approval` proves a real GL outcome by independent re-read.
3. ~~Make the kill switch authoritative.~~ **Done and verified on every execution surface:** terminal, missions, browser sessions/executions, MCP invoke, workflow run/resume/recover, workload launcher, A2A delegation, OpenHands create/command, finance create/approve and workforce execute all return `403` while engaged; only OWNER/EXECUTIVE/GLOBAL_ADMIN may toggle it. Disengaging restores real terminal execution (`exit_code: 0`).
4. ~~Resume or explicitly fail approved MCP operations.~~ **Done and verified:** resume re-invokes the real tool, rejection closes the execution, forged approvals are denied.
5. ~~Add truncation detection to mission verification.~~ **Done and verified:** `UNCERTAIN` + `VERIFICATION_REFUSED`, no seal.
6. **Rotate** the Neon `DATABASE_URL` password and **revoke** the embedded GitHub PAT; scrub `.env.local` and the git remote. *(Still open — owner action.)*

**P1 — required for a credible pilot**
7. ~~Policy/threshold/SoD on expense approval; department creation API.~~ **Done:** client-asserted status is ignored (`SUBMITTED` only), amount/per-claim hard limit, department + company monthly budgets at intake *and* approval, claimant ≠ approver SoD, duplicate/cross-company approval rejection, `approved_by`/`approved_at` recorded, no GL post before approval. `POST /api/departments` is role-gated and company-scoped. **Still open:** first-class product/project entities.
8. ~~Real MCP discovery and real connection latency.~~ **Done and verified live:** `initialize` measures true latency (11.4 ms), `resources/list` discovers a real resource, `resources/read` returns live content (`LIVE_RESOURCES_READ`, `read_verified: true`). No hard-coded latency or simulated discovery on the live path.
9. **Partially done:** department and company budgets are enforced at expense intake and approval; blueprint/employee budget enforcement is still not exercised at execution time.
10. ~~Compute financial metrics in code and give the model the computed values.~~ **Done and verified:** `core/company_metrics.py` computes ARR/MRR/weighted pipeline/expenses/finance from tenant+company-scoped SQL; the CEO chat injects `computed_metrics` + `metric_brief` and returns them even when the LLM is degraded. Live CEO answer quoted MRR ₹41,995 and weighted pipeline ₹31,897.2; `comp_beta` returned zeros with its own `company_id`.
11. **Partially done:** mission delegation now performs real `TerminalProvider` calls (`inspect_filesystem`, `inspect_environment`), emits per-capability timeline events and injects the tool facts into the deliverable prompt. Specialist-agent routing beyond the terminal provider is still limited.
12. ~~Make mission output honour `llm_max_tokens`.~~ **Done:** `max_tokens` follows `llm_max_tokens`; bounded continuation loop (default 2, cap 5) with timeline events; the truncation marker is only kept when the output is still truncated.

**P2 — operational**
13. Real browser E2E in CI (needs Playwright + Chromium), live-Postgres suite, container suite; the current sandbox cannot run them.
14. Valid GitHub credentials so the hardening branch and these fixes can be pushed and reviewed. **Blocked:** the pasted PAT is compromised and must be revoked by the owner before a fresh token is issued.
15. ~~Convert module-level singletons to tenant-scoped factories everywhere.~~ **Done for workflow/finance/departments/browser/CEO metrics:** per-tenant workflow runtimes, tenant/company-scoped finance and evidence, token-derived company on department and workflow APIs. Remaining singletons still need an audit.
16. ~~Tenant/company isolation for evidence verification.~~ **Done:** new evidence records carry `tenant_id`/`company_id`; another company or tenant receives `EVIDENCE_NOT_FOUND` (verified live). Legacy records without metadata remain readable inside the same tenant and are recorded as a gap.
17. ~~Governed corporate decisions instead of single-model answers.~~ **Done:** `POST /api/arena/evaluate` scores ≥2 options through 4 deterministic lenses, refuses to hide disagreement (`CONTESTED`), refuses to answer without evidence (`NEEDS_EVIDENCE`), routes high-risk/contested outcomes to a real approval, and enforces authority tiers. `POST /api/skills/<id>/run` enforces 12 executable SOP contracts; `GET /api/arena/skill-runs` exposes company-scoped run history. 14 regressions + live API proof. **Residual:** judges are deterministic scoring functions, not independent LLM agents; that is deliberate and is stated as such.
18. **P1-18 (new) — wire workforce authority to enforcement.** G1–G9 profiles (spend limits, hire/delegate/SOP rights, data classifications) are stored and returned but not yet consulted by the finance runtime, agent provisioning or PolicyEngine. Until they are, "employee authority" is descriptive, not enforcing. Also outstanding: SOP execution by the agent runtime, task-assignment API, and a mission-creation API.

---

## 7. Code changes in this stage (uncommitted)

| File | Change |
|---|---|
| `api_server.py` | Onboard `MemoryType` shadowing crash fix; per-tenant Records/Files/AgentFactory engines; company scoping on records/files/expenses; MCP `auth_token`→`credential_ref`; browser execution/action handler signatures; workflow run tenant guards; per-tenant finance scoping |
| `core/ceo_chat.py` | Grounded `build_company_context` (customers, pipeline, expenses, products, projects, onboarding, objectives, finance, rules) + stricter system prompt |
| `core/coworker/background_dispatcher.py` | Inject company context into mission plan and deliverable prompts |
| `core/llm_runtime.py` | Bounded retries + cooldown waiting for `embedded_free`; honest degradation preserved |
| `core/enterprise_finance.py` | Per-company CoA, connection-safe provisioning, expense company scoping, GL posting by account code |
| `core/universal_terminal/security_gateway.py` | Credential-path deny-list; DB-URL/secret output patterns |
| `core/coworker/providers/terminal_provider.py` | Credential-path denial (command + file parameters) and output scrubbing |
| `core/durable_workflow_runtime.py` | Tenant-scoped `list_runs` / `get_run_state` |
| `core/browser_use_execution_runtime.py` | Real `urllib` navigation with true title/status/bytes; test-only fixture behind `ZONATA_TEST_MODE=1`; honest `ACTION_NOT_IMPLEMENTED`; DOM-derived `EXTRACT`; text-based `VERIFY_POSTCONDITION`; unknown actions fail |
| `core/mcp_interoperability_runtime.py` | `pre_approved_id` validation; `resume_approved_execution()`; live `tools/list` discovery |
| `core/coworker/background_dispatcher.py` | Truncation marker + `UNCERTAIN`/`VERIFICATION_REFUSED` instead of sealing a cut-off deliverable |
| `core/llm_runtime.py` | Propagate `finish_reason` (plus retries/cooldown) |
| `zonata/langgraph_adapter.py` | Honest `STATE_INTEGRITY_ONLY` evidence; input honouring; no fabricated margin summary; approval workflow no longer claims disbursement |
| `api_server.py` (P0) | Global kill-switch gates for terminal/mission/browser; MCP approve resumes, reject closes; workflow honesty passthrough |
| `core/universal_terminal/security_agent.py`, `terminal_agent.py` | Denial results always carry `requires_approval` |
| `tests/test_mission_truncation_guard.py` | New regression test: truncated deliverable is never sealed |
| `tests/test_browser_use_execution.py` | Assertions updated to real parsed-page extraction |
| `core/enterprise_finance.py` | Expense intake/approval policy: forced `SUBMITTED`, amount cap, department/company budgets at intake + approval, claimant ≠ approver SoD, duplicate/cross-company rejection, `approved_by`/`approved_at`, no GL post on intake |
| `core/durable_workflow_runtime.py` | Per-tenant runtimes; reserved `__*` client keys stripped; approval identity written only by the runtime on authorized resume; tenant-scoped pause/resume/cancel/recover |
| `core/approvals.py` | Company-scoped `decide_request`; rejects missing/already-decided requests; records `decision_reason` |
| `core/company_metrics.py` (new) | Deterministic ARR/MRR/weighted pipeline/expenses/finance with CI-safe divisions |
| `core/ceo_chat.py` | Injects and returns `computed_metrics` + `metric_brief` in success and degraded responses |
| `core/coworker/background_dispatcher.py` | `llm_max_tokens` honoured, bounded continuation loop, real terminal delegation with per-capability timeline |
| `zonata/langgraph_adapter.py` | New `wf_company_expense_approval` with real GL post + independent DB re-read + business-outcome evidence |
| `core/evidence_ledger.py` | `verify_evidence_artifacts()`: digest, epoch-aware chain, physical artifact re-hash, DB postcondition reported as `REQUIRES_EXECUTION_CONTEXT`; tenant/company scoping |
| `api_server.py` (enterprise batch) | Kill-switch gates on all surfaces; role-gated approvals; token-derived company for departments/workflows; evidence verify/list company scoping; `/api/departments` POST; finance/department/browser/evidence endpoints |
| `core/departments.py` | Role-gated, company-scoped department create/list |
| `core/mcp_interoperability_runtime.py` | Measured `initialize` latency, live `resources/list` + `resources/read`, gated simulation |
| `core/browser_use_execution_runtime.py` | Capability inventory; all engine-dependent interactions refuse with `ACTION_NOT_IMPLEMENTED` outside test mode |
| `tests/test_enterprise_multi_company_controls.py` (new) | 16 control/isolation regressions |
| `core/operating_skills.py` | 12 skills rewritten as executable contracts (authority floor, risk class, required inputs, checks, limits, protocol source) instead of prose |
| `core/skill_arena.py` (new) | Governed skill execution + 4-lens multi-judge arena, Borda/aggregate ranking, consensus/contested/insufficient-evidence taxonomy, PolicyEngine routing, approval creation, evidence sealing, tenant/company persistence |
| `core/db.py` | `arena_decisions` and `skill_runs` tables + scope indexes (SQLite schema parity) |
| `migrations/pg/0003_skill_arena.sql` (new) | PostgreSQL DDL parity for both tables |
| `migrations/pg/0005_workforce_architecture.sql` (new) | PostgreSQL parity for `organizations.company_id` and the shared `employee_kras` columns |
| `api_server.py` (skill/arena batch) | `GET /api/skills`, `GET /api/skills/<id>`, `POST /api/skills/<id>/run`, `POST /api/arena/evaluate`, `GET /api/arena/decisions[/<id>]`, `GET /api/arena/skill-runs`; kill-switch gates; token identity for approval decisions |
| `tests/test_skill_arena.py` (new) | 14 contract/arena regressions (authority, evidence, denial, budget, decision+run isolation, reproducibility) |
| `core/workforce_architecture.py` (new) | Service/lifecycle layer over the canonical 25-table schema: 13-role executive catalog, 15 industry blueprints, G1–G9 authority, provisioning, cycle-safe reporting, employee lifecycle, immutable SOP versions, KRA/KPI with anti-gaming, explainable evaluation, capability registry + isolated agent instances with quota, governed cross-department collaboration, evidence sealing |
| `core/workforce_api.py` (new) | Role-gated, company-scoped HTTP surface (`/api/workforce/*`): 15 read routes, 18 write routes, invariant errors mapped to 400/409, no silent success |
| `api_server.py` (workforce batch) | Dispatches `GET`/`POST /api/workforce*` to the workforce handler; POST is behind the global kill switch |
| `core/db.py` | `organizations.company_id`; `employee_kras` additive columns (`responsibility`, `position_id`, `weight_percentage`, `accountability_statement`, `updated_at`, associated/authority/escalation/outcome fields); idempotent migrations for drifted pilot DBs |
| `core/kpi_kra_engine.py` | `register_kra` writes the canonical `employee_kras` shape (position, weight, accountability, `updated_at`) instead of a V7-only subset |
| `tests/test_workforce_architecture.py` (new) | 45 regressions: catalogs, provisioning, multi-level chains, cycles, headcount, SOP immutability, KRA weights, evidence-backed measurement, refusal cases, agent isolation/quota/termination, collaboration lifecycle, tenant/company isolation, deactivation history, industry C-suite coverage |
| `tests/test_workforce_api.py` (new) | 12 HTTP-surface regressions: authority gating, company scoping, honest unprovisioned state, duplicate organization, cycle surfacing, non-interception of other routes |
| `storage/evidence/audit_ledger.jsonl` | Ledger entries written by the real runs |

---

## 8. Stage-2 entry criteria

Stage 2 (design-partner pilot) may start only when:
- the owner has revoked the embedded GitHub PAT and rotated the Neon `DATABASE_URL` (P0-6) — **still open, owner action**;
- **P1-7 is closed** (expense threshold/SoD + department API). **P1-11 is partially done:** real terminal delegation exists; specialist routing beyond the terminal provider remains limited;
- the capability matrix contains no `NOT IMPLEMENTED` or `FAILED` entry that a partner would touch — browser click/type/submit must either work with a real engine or be hidden from the partner UI (**still open: no engine**);
- tenant isolation has an automated regression test for every engine that is still a singleton (**new 16-test control suite covers workflow/finance/departments/evidence; a new 14-test arena suite covers decision/skill isolation; a remaining-singleton audit is still required**);
- a partner-facing page lists capabilities with the same statuses used here;
- the workforce layer's authority profiles are enforced (P1-18) or the product stops describing them as limits.

The workforce layer may be shown to a design partner as an **organizational model and governance record** (hierarchy, roles, KPIs, review math, agent quotas), but not yet as a system where AI employees autonomously execute their SOPs within their authority.

### Post-fix evidence index (retained raw responses)

| Evidence file | Proves |
|---|---|
| `browser_after_fix.json` | Real navigation (title/HTTP 200/577 bytes/`REAL_HTTP_FETCH`), allow-list denial, `ACTION_NOT_IMPLEMENTED`, financial approval interception |
| `p0_verification.json` | Kill switch `403` on terminal/mission/browser; MCP executions include `execution_status`; forged approval `POLICY_DENIED`; suspend→approve→real resume `VERIFIED` with server-side refund recorded; rejection → `REJECTED`; `LIVE_TOOLS_LIST` discovery; honest workflow outputs |
| `p1_live_api_part1.json` | Browser capability inventory (no engine); department create/duplicate `409`/OBSERVER `403`; expense enters as `SUBMITTED` despite client `APPROVED` |
| `p1_live_api_part2.json` | Expense workflow: owner run → `WAITING_FOR_APPROVAL`; OBSERVER/MANAGER approval `403`; EXECUTIVE approval → real GL post `tx_6c3241ab`, balance `12000.00 → 16321.75`, `business_outcome_verified: true`, `EV-6A27866C`; double-approve rejected |
| `p1_live_api_evidence.json` / `p1_live_api_evidence_scope.json` | Evidence digest + epoch-aware chain `VERIFIED`; cross-company and cross-tenant verification `404 EVIDENCE_NOT_FOUND` for scoped records |
| `p1_live_api_killswitch.json` / `p1_live_api_killswitch2.json` | 15/15 execution surfaces `403` while engaged; non-governance toggle `403`; disengage restores real terminal run |
| `p1_live_api_ceo_metrics.json` | `computed_metrics` MRR ₹41,995 / ARR ₹503,940 / weighted ₹31,897.2; `comp_beta` scoped zeros |
| `p1_live_api_mcp.json` | Live `initialize` latency 11.4 ms; `LIVE_RESOURCES_LIST`; `LIVE_RESOURCES_READ` with `read_verified: true` |
| `p2_skill_arena_live.json` | 12 skills listed; owner `verified-delivery` → `SATISFIED` (`EV-A940E802`); operator `board-reporting` → `ESCALATED` requiring `EXECUTIVE`; low-risk arena → `DECIDED`/`CONSENSUS` (`vendor_a`, `EV-14D45C00`); cross-company decision `404`; high-risk arena as MANAGER → `ESCALATED` with approval `apr_fa15d6e1`; OBSERVER decide `403`; OWNER decide `APPROVED`; kill switch blocks arena and skill runs; `GET /api/arena/skill-runs` returns 2 owner-company runs and 0 for the beta tenant |
| `p3_workforce_live.json` | 34/34 live workforce checks: 17-department/13-executive provisioning (`EV-5537CD9C`), operator/observer `403`, duplicate-org `400`, cycle `400`, agent quota `400`, cross-employee termination `400`, unevidenced measurement `400`, `109.8 EXCEEDING` review (`EV-D2F9320F`), `409` without measurement, collaboration `400→200→200`, same-tenant other company returns its own empty workforce |
| `tests/test_mission_truncation_guard.py` | Truncated deliverable → `UNCERTAIN`, `VERIFICATION_REFUSED`, no evidence id, marker retained on disk |

### Known remaining gaps (do not hide these in a demo)

- Browser click/type/submit have no execution engine (`ACTION_NOT_IMPLEMENTED`); screenshots are `NOT_CAPTURED`.
- Browser provider session/DOM state is in-memory; it is lost on restart (F11).
- Arena judges are deterministic scoring functions, not independent language models. Ranking is reproducible and auditable, but it cannot read free-text rationale; an LLM may add advisory commentary elsewhere without changing the authoritative ranking.
- The arena requires caller-supplied option metadata (risk, reversibility, cost, evidence refs, confidence). It does not extract those values from documents yet.
- Skill contracts validate declared inputs and checks; they do not execute the underlying business action (e.g. `finance-control` enforces limits but the GL post still goes through the finance workflow).
- Canonical demo workflows remain state-transition-only; `business_outcome_verified` is `true` only for `wf_company_expense_approval`, which posts and independently re-reads the GL.
- Mission delegation is real but limited to `TerminalProvider` filesystem/environment inspection; specialist-agent routing and broader scoped tool calls are still missing.
- Blueprint/employee budgets are not yet enforced at execution time (department/company expense budgets are).
- Evidence records written before this batch have no `company_id` metadata, so same-tenant company filtering cannot retroactively scope them. New records are scoped; the legacy ledger is recorded, not hidden.
- Organisation/company onboarding, billing and partner-facing capability pages are not yet built.
- Workforce: SOP versions are defined, versioned and assigned but **not yet executed** by the agent runtime; execution telemetry therefore leaves SOP compliance at its default.
- Workforce: G1–G9 authority/spend profiles are stored and returned but are **not consulted** by the finance runtime or agent provisioning — they are descriptive, not enforcing, until wired to PolicyEngine.
- Workforce: agent instances are real rows with leases, sessions and isolation checks, but no model/tool call is dispatched through them yet; provisioning proves governance plumbing, not autonomous work.
- Workforce: `corporate_missions` has no creation API, so the live collaboration proof seeded one synthetic mission row directly (documented in `p3_workforce_live.json`).
- Workforce: `employee_sop_assignments` execution counters and `employee_tasks` delegation are schema-only; no task-assignment API exists yet.
- Workforce: PostgreSQL parity for the new columns ships as `migrations/pg/0005_workforce_architecture.sql`, but no PostgreSQL server was available here, so it is **unexecuted** — treat PG parity as unverified until run against a real database.
- Workforce: PostgreSQL parity for the new `organizations.company_id` and `employee_kras` columns has no migration file yet (SQLite was exercised; PG was not runnable here).
- Free LLM tier is rate-limited and intermittently unavailable; missions correctly end `BLOCKED` instead of fabricating.
- All evidence is SQLite; live Postgres, Playwright E2E and container suites remain unexecuted here.
- The GitHub PAT pasted earlier is compromised and must be revoked; pushing these commits requires a fresh token.

Paid hosting, public signup, and payment processing remain unjustified by current evidence.
