# Stage 1 — Internal Simulation: Northstar Business Systems
## Evidence-based capability and gap report

**Date:** 2026-11-03 (post-enterprise multi-company revision)
**Repo:** `/root/roboassistant` @ `e2d04c7` (`hardening/real-llm-tenant-isolation`) + uncommitted enterprise fixes listed below
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

The product is still **not** a fully operating AI company: there is no real browser interaction engine, mission delegation is limited to terminal filesystem/environment facts, blueprint/employee budgets are not enforced at execution time, and onboarding/billing/partner capability pages are missing.

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

Run against an isolated pytest DB (`tests/conftest.py`), on the patched tree, on 2026-11-03 (after the enterprise multi-company batch):

| Suite | Result |
|---|---|
| `tests/test_browser_use_execution.py` + `tests/test_mission_truncation_guard.py` | 28 passed |
| `tests/test_mcp_interoperability.py` | 38 passed |
| `tests/test_durable_workflow.py` | 55 passed |
| `tests/test_enterprise_multi_company_controls.py` (new) | 16 passed |
| `tests/test_public_ga_integrity_and_finance.py` + `test_phase_16_tenant_fairness.py` + `test_direct_object_access_and_tenant_security.py` + `test_governed_terminal_runtime.py` | 37 passed |
| `tests/test_step2_operational_validation.py` | 10 passed |
| `tests/test_crm_persistence.py` | 4 passed |

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
| `storage/evidence/audit_ledger.jsonl` | Ledger entries written by the real runs |

---

## 8. Stage-2 entry criteria

Stage 2 (design-partner pilot) may start only when:
- the owner has revoked the embedded GitHub PAT and rotated the Neon `DATABASE_URL` (P0-6) — **still open, owner action**;
- **P1-7 is closed** (expense threshold/SoD + department API). **P1-11 is partially done:** real terminal delegation exists; specialist routing beyond the terminal provider remains limited;
- the capability matrix contains no `NOT IMPLEMENTED` or `FAILED` entry that a partner would touch — browser click/type/submit must either work with a real engine or be hidden from the partner UI (**still open: no engine**);
- tenant isolation has an automated regression test for every engine that is still a singleton (**new 16-test control suite covers workflow/finance/departments/evidence; a remaining-singleton audit is still required**);
- a partner-facing page lists capabilities with the same statuses used here.

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
| `tests/test_mission_truncation_guard.py` | Truncated deliverable → `UNCERTAIN`, `VERIFICATION_REFUSED`, no evidence id, marker retained on disk |

### Known remaining gaps (do not hide these in a demo)

- Browser click/type/submit have no execution engine (`ACTION_NOT_IMPLEMENTED`); screenshots are `NOT_CAPTURED`.
- Browser provider session/DOM state is in-memory; it is lost on restart (F11).
- Canonical demo workflows remain state-transition-only; `business_outcome_verified` is `true` only for `wf_company_expense_approval`, which posts and independently re-reads the GL.
- Mission delegation is real but limited to `TerminalProvider` filesystem/environment inspection; specialist-agent routing and broader scoped tool calls are still missing.
- Blueprint/employee budgets are not yet enforced at execution time (department/company expense budgets are).
- Evidence records written before this batch have no `company_id` metadata, so same-tenant company filtering cannot retroactively scope them. New records are scoped; the legacy ledger is recorded, not hidden.
- Organisation/company onboarding, billing and partner-facing capability pages are not yet built.
- Free LLM tier is rate-limited and intermittently unavailable; missions correctly end `BLOCKED` instead of fabricating.
- All evidence is SQLite; live Postgres, Playwright E2E and container suites remain unexecuted here.
- The GitHub PAT pasted earlier is compromised and must be revoked; pushing these commits requires a fresh token.

Paid hosting, public signup, and payment processing remain unjustified by current evidence.
