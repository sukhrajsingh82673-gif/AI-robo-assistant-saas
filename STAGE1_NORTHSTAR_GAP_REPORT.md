# Stage 1 — Internal Simulation: Northstar Business Systems
## Evidence-based capability and gap report

**Date:** 2026-11-01 (post-P0 revision)
**Repo:** `/root/roboassistant` @ `7084a57` (`hardening/real-llm-tenant-isolation`) + uncommitted fixes listed below
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

One **release-blocking security defect was found and fixed**: the terminal agent could read live `DATABASE_URL` credentials out of `.env.local` (and would have read private keys). Two **cross-tenant leaks were found and fixed**. The **global kill switch is now authoritative** for terminal, missions and browser (all return `403`).

The product is still **not** an operating AI company: there is no real browser interaction engine, no mission→agent→tool delegation, and no spending-limit/SoD enforcement on expenses.

Recommendation: **do not start Stage 2 (design-partner pilot)** until the remaining P0 items in §6 are resolved. Paid infrastructure is not justified by the current evidence.

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
| 5 | Finance — expense → GL posting | PARTIAL | ₹12,000 approval posted to GL 6020 with journal `tx_ce738566`, `reference_no`, evidence ref; **no policy/threshold/separation-of-duties gate** — any owner token can post any amount | `finance_lifecycle.json` |
| 6 | AI CEO chat grounded in company data | PARTIAL | After fix: correct 5 customers, ₹41,995 MRR, 40% onboarding, ₹28,000 pending, ₹12,000 posted, ₹80,000 budget; **weighted pipeline arithmetic wrong** (₹29,997 vs ₹31,897). Before fix it answered "pre-launch, zero data" | `ceo_chat_baseline.json`, `ceo_chat_grounded.json` |
| 7 | AI CEO tenant isolation | VERIFIED | `tnt_beta` context has 0 customers/pipeline/expenses and no company name | `ceo_context_isolation.json` |
| 8 | Mission runtime (NS-001) | PARTIAL | Real `embedded_free/openai-fast` plan (26.4 s) + grounded deliverable. Truncation is now detected: `finish_reason=length` → `UNCERTAIN` + `VERIFICATION_REFUSED`, no seal (guard test). Still no delegation to specialist agents, no tool calls | `mission_run.json`, `tests/test_mission_truncation_guard.py` |
| 9 | Evidence ledger (mission) | VERIFIED | `EV-7DCECE5B`, ed25519 signature, merkle index 2127, SHA-256 `ff6df601…` matches file; beta sees 0 records | `mission_run.json` |
| 10 | Evidence "verification" semantics | PARTIAL | Verification = file exists + hash matches + not truncated. It still does not verify the content is correct or complete beyond the truncation marker | `mission_run.json`, `p0_verification.json` |
| 11 | Governed terminal — execution | VERIFIED | Real commands, exit codes, evidence ids, snapshot ids; write/read file works; `rm -rf /` denied | `terminal.json` |
| 12 | Governed terminal — secret protection | VERIFIED (after fix) | **Before:** read live Neon `DATABASE_URL` from `.env.local`. **After:** `.env*`, `id_rsa`, `*.pem`, `.git-credentials`, `.netrc`, `.aws/credentials`, `.npmrc`, credentials JSON, `enterprise_settings.json`, `/etc/shadow` denied; outputs scrubbed | `terminal_secret_probe.json`, `terminal_secret_probe_after_fix.json` |
| 13 | MCP — server registration/trust | VERIFIED | Real local JSON-RPC server on `127.0.0.1:8123` registered → validated → trusted | `mcp_register.json` |
| 14 | MCP — tool discovery | VERIFIED (after fix) | `refresh` now performs a live JSON-RPC `tools/list` against the trusted server and registers returned tools: `discovery: LIVE_TOOLS_LIST`, 2 tools discovered. Failures report `FAILED`; untrusted servers `SKIPPED_UNTRUSTED` | `p0_verification.json` |
| 15 | MCP — read-only tool invocation | VERIFIED | `get_onboarding_summary` executed against the real server, returned real data, `VERIFIED`, evidence `EV-B1C70902`, SHA-256 sealed | `mcp_invoke.json` |
| 16 | MCP — financial tool approval gate | VERIFIED (after fix) | Call suspends (`APPROVAL_REQUIRED`, `apr_*`); approval resumes through every gate and the real server recorded the refund (`VERIFIED`, `EV-8687FA1E`); rejection closes the suspended execution as `REJECTED`. A forged `pre_approved_id` is denied `POLICY_DENIED` | `p0_verification.json` |
| 17 | MCP — execution listing API | VERIFIED | `GET /api/mcp/executions` returns full rows including `execution_status` and `verification_status`. The earlier claim that these were omitted was incorrect | `p0_verification.json` |
| 18 | Browser — session creation | VERIFIED | Session created with domain allow-list, SSRF/domain policy evaluated | `browser.json` |
| 19 | Browser — navigation | VERIFIED (after fix) | Real `urllib` fetch: `https://example.com` → HTTP 200, 577 bytes, title "Example Domain", `REAL_HTTP_FETCH`, 6.4 s. Non-allowlisted host → `403`. Unreachable host → `NAVIGATION_FAILED`, no invented content. Test fixture only under `ZONATA_TEST_MODE=1` | `browser_after_fix.json` |
| 19a | Browser — data extraction | VERIFIED (after fix) | `EXTRACT` returns parsed page text, title, status and selector matches; unmatched selector → `ELEMENT_NOT_FOUND`; fabricated records/KPI removed | `browser_after_fix.json` |
| 19b | Browser — click / type / submit | NOT IMPLEMENTED | No browser engine installed; actions return `ACTION_NOT_IMPLEMENTED` instead of a fake success. Financial selectors still intercept first with `APPROVAL_REQUIRED` | `browser_after_fix.json` |
| 20 | Agent Factory — blueprint synthesis | PARTIAL | Blueprint created per tenant with budget ₹30,000 and tool list, but output is template-based (role fixed to "Operations Specialist", generic responsibilities), not LLM-designed from the prompt | `agent_factory.json` |
| 21 | Employee creation | PARTIAL | Employee persisted with scoped tools/budget, but there is no API to execute work *as* that employee; generated tools (`python3`, `jq`, `tar`) are not what an onboarding specialist needs | `agent_factory.json` |
| 22 | Workflows — run lifecycle | PARTIAL | State machine runs, checkpoints, lease, evidence. Caller input is now honoured (`objective`/`task` fallback). The canonical node performs no external action; it advances state only | `p0_verification.json` |
| 23 | Workflows — verification | PARTIAL (after fix) | Now reports `verification_scope: STATE_INTEGRITY_ONLY`, `business_outcome_verified: false`, and states that no external action occurred. The approval workflow reports `disbursed: false` (no payment connector). Self-consistency is no longer presented as business proof | `p0_verification.json`, `zonata/langgraph_adapter.py` |
| 24 | Kill switch — workflows | VERIFIED | Engaged via API → workflow start blocked with `KILLSWITCH_ENGAGED`; disengage restores | `killswitch.json` |
| 25 | Kill switch — automation | VERIFIED (after fix) | Global gate checked at execution time: terminal, mission submit/step, and browser session/execution/navigate/action all return `403` while engaged; disengage restores | `p0_verification.json` |
| 26 | Kill switch — browser/terminal | VERIFIED (after fix) | Covered by the authoritative global automation gate; browser scoped kill switches also exist | `p0_verification.json` |
| 27 | Restart persistence | VERIFIED | After kill -9 + restart: 5 customers, 6 deals, 12 records, 5 employees, blueprint, MCP server + 2 tools, finance (₹12,000 posted / ₹28,000 pending), workflow run, mission `COMPLETED` | `restart_persistence.json` |
| 28 | Tenant isolation — records/files/agent-factory | VERIFIED (after fix) | Before fix `tnt_beta` read `tnt_primary` agent blueprints; after per-tenant engines both tenants see only their own (0 vs 0 for beta, own only for Northstar) | `tenant_isolation_after_fixes.json` |
| 29 | Tenant isolation — MCP | VERIFIED | `tnt_beta` invoking Northstar's server → `403 Cross-tenant access prohibited` | `tenant_isolation_after_fixes.json` |
| 30 | Tenant isolation — workflow runs | VERIFIED (after fix) | Before fix beta saw Northstar's run; after fix beta sees 0 runs, `404` on run state, `404` on pause | `tenant_isolation_after_fixes.json` |
| 31 | Tenant isolation — missions/evidence | VERIFIED | beta gets `404` on mission, 0 evidence rows | `mission_run.json` |
| 32 | Tenant isolation — finance | VERIFIED | beta approval of Northstar expense → `400 not found`; beta sees 0 customers, ₹0 balances | `finance_lifecycle.json` |
| 33 | Approval pipeline (human-in-the-loop) | PARTIAL (after fix) | MCP approvals now validate the approval, resume the exact suspended execution, and record evidence; forged ids are denied; rejection closes the execution. Expenses still bypass approvals entirely (#5) | `p0_verification.json` |
| 34 | Budget / spending limits | UNVERIFIED | Blueprint/employee budgets exist as fields; no execution path was found that enforces them. Not proven either way | `agent_factory.json` |
| 35 | Default LLM (free, owner-configurable) | VERIFIED | `embedded_free` (Pollinations `openai-fast` → gpt-oss-20b) answered keyless; owner-configurable provider list present; failures degrade honestly with `degraded=true` | `ceo_chat_grounded.json` |
| 36 | LLM availability under rate limits | PARTIAL | Free tier ≈1 req/30 s; retries/cooldown added, but runs still occasionally end `BLOCKED — no language model provider is available` | `mission_submit2.json` |
| 37 | Browser E2E in CI | BLOCKED | No Playwright, no Chromium, no Docker in this sandbox; the JS E2E scripts were not executed | environment check |
| 38 | Live Postgres | BLOCKED | `psycopg2` importable but no server reachable; all evidence is SQLite | environment check |
| 39 | GitHub push / CI | BLOCKED | Embedded PAT invalid (401), `gh` not logged in, no SSH key; commit `7084a57` and the Stage-1 fixes are local only | `git status` |

---

## 4. Findings that invalidate product claims

### F1 — Browser was fabricated (severity: high, honesty — fixed)
`BrowserUseExecutionProvider.navigate()` originally never opened a socket; it built fixed markup and returned `success: true`. It now performs a real HTTP fetch and reports the true title/status/size (`browser_after_fix.json`). Interaction actions (click/type/submit) are explicitly `ACTION_NOT_IMPLEMENTED` because no browser engine exists. The test fixture is gated behind `ZONATA_TEST_MODE=1`.
**Residual:** no headless engine means no form submission, screenshots or JS execution; screenshot artifacts are `NOT_CAPTURED`.
**Evidence:** `evidence/browser.json` (pre-fix), `evidence/browser_after_fix.json` (post-fix).

### F2 — Workflow verification proved nothing (severity: high, honesty — fixed)
`zonata/langgraph_adapter.py` previously compared a hash to itself and labelled it verified. It now returns `verification_scope: STATE_INTEGRITY_ONLY` and `business_outcome_verified: false`, explicitly stating that no external action occurred. The approval workflow no longer claims `disbursed: true`.
**Residual:** workflows still perform no external action; they exercise orchestration/checkpointing/evidence only.
**Evidence:** `evidence/workflow.json` (pre-fix), `evidence/p0_verification.json` (post-fix).

### F3 — Terminal could read production secrets (severity: critical, fixed)
`head -c 120 /root/roboassistant/.env.local` returned `DATABASE_URL=postgresql://Postgres_owner:npg_…@ep-broad-sky…`. Fixed via deny-lists and output scrubbing; re-probe returns `POLICY_DENIED`.
**Residual:** the credential is still live in `.env.local` and must be **rotated**; the embedded PAT in `origin` must also be **revoked**.

### F4 — Cross-tenant leaks (severity: critical, fixed)
- Agent Factory / Records / Files were module-level singletons bound to `tnt_primary`; `tnt_beta` read `tnt_primary` blueprints.
- `GET /api/workflows/runs` returned runs for all tenants because the runtime is a process-wide singleton; run mutation endpoints were unguarded.
Both fixed and re-tested.

### F5 — Truncated deliverable accepted as verified (severity: medium — fixed)
NS-001's deliverable originally ended mid-table (3,636 bytes) at the token limit but was marked `COMPLETED`. The dispatcher now records `finish_reason`, writes a `DELIVERABLE_TRUNCATED` marker, and refuses verification: status `UNCERTAIN`, timeline `VERIFICATION_REFUSED`, `evidence_id` empty. Verified deterministically by `tests/test_mission_truncation_guard.py`.
**Residual:** the mission deliverable call hard-codes `max_tokens=1800`, so the owner's `llm_max_tokens` setting does not govern mission output length.

### F6 — Kill switch was not authoritative (severity: high — fixed)
The automation kill switch previously let terminal execution and new missions proceed. It is now checked at execution time in terminal, mission submit/step and every browser entry point; each returns `403` while engaged (`p0_verification.json`).

### F7 — MCP approval dead-end (severity: high — fixed)
Approved MCP operations were never resumed. `resume_approved_execution()` now runs on approval, re-checks the approval (APPROVED, same tenant/company), re-invokes the real tool and records evidence (`VERIFIED`, `EV-8687FA1E`; the local server's state file recorded the refund). Rejection marks the suspended execution `REJECTED`. A client-supplied `pre_approved_id` is validated and forged ids are `POLICY_DENIED`.

### F8 — No MCP discovery (severity: medium — fixed)
`refresh` now calls the live `tools/list` and registers returned tools (`LIVE_TOOLS_LIST`); failures and untrusted servers are reported distinctly. Remaining gap: `test_server_connection` still returns a hard-coded `latency_ms: 12.4` without an RPC round-trip.

### F9 — API/handler signature drift (severity: medium, fixed where found)
Three endpoints crashed on first use: `POST /api/mcp/servers` (`auth_token`), `POST /api/browser/executions` (`task_id`), `POST /api/browser/action` (`human_intent`). This means these paths had never been exercised in the current branch.

### F10 — CEO miscomputed weighted pipeline (severity: low)
Grounded context is correct; the model's arithmetic is not. Any CEO number that matters must be computed in code, not by the model.

### F11 — Browser provider sessions are in-memory only (severity: low)
Session rows persist in the DB, but the provider's session/DOM state does not. After a restart, `navigate` re-initialises silently and `action` returns `Session … not found`. Combined with F1, no browser state can be trusted across restarts.

---

## 5. Test suite results (after fixes)

Run against an isolated pytest DB (`tests/conftest.py`), on the patched tree, on 2026-11-01:

| Suite | Result |
|---|---|
| `tests/test_browser_use_execution.py` | 27 passed |
| `tests/test_mission_truncation_guard.py` | 1 passed |
| `tests/test_mcp_interoperability.py` | 36 passed |
| `tests/test_public_ga_integrity_and_finance.py` | 2 passed |
| `tests/test_crm_persistence.py` | 4 passed |
| `tests/test_universal_terminal_master_qualification.py` | 18 passed |
| `tests/test_direct_object_access_and_tenant_security.py` + `tests/test_governed_terminal_runtime.py` + terminal master | 41 passed |
| `tests/test_durable_workflow.py` | 55 passed |
| `tests/test_assistant_coworker_compound_mission.py` | 6 passed |

**Caveat:** browser tests exercise the deterministic test fixture under `ZONATA_TEST_MODE=1`; they prove governance and parsing logic, not a real browser engine. Real-network behaviour is evidenced separately (`browser_after_fix.json`). Green tests are not treated as proof of end-to-end capability.

**Still not runnable here:** Playwright/Chromium E2E, Docker/container suites, live-Postgres suite.

---

## 6. Prioritised remediation before Stage 2

**P0 — must fix before any design partner sees the product**
1. ~~Remove or gate browser "verified" claims.~~ **Done:** real HTTP navigation, honest failures, no fabricated DOM, interactions refused. Remaining: a real headless engine (Playwright) is still absent, so form submission is `NOT IMPLEMENTED`.
2. ~~Replace tautological workflow verification.~~ **Done:** `STATE_INTEGRITY_ONLY`, `business_outcome_verified: false`, honest disbursement flag. Remaining: workflows have no real external action to verify.
3. ~~Make the kill switch authoritative.~~ **Done and verified:** terminal, missions and browser return `403` while engaged.
4. ~~Resume or explicitly fail approved MCP operations.~~ **Done and verified:** resume re-invokes the real tool, rejection closes the execution, forged approvals are denied.
5. ~~Add truncation detection to mission verification.~~ **Done and verified:** `UNCERTAIN` + `VERIFICATION_REFUSED`, no seal.
6. **Rotate** the Neon `DATABASE_URL` password and **revoke** the embedded GitHub PAT; scrub `.env.local` and the git remote. *(Still open — owner action.)*

**P1 — required for a credible pilot**
7. Policy/threshold/SoD on expense approval; company-coded revenue postings; department creation API; first-class product/project entities.
8. ~~Real MCP `tools/list` discovery.~~ **Done.** Remaining: `test_server_connection` must measure real latency instead of returning `12.4` ms.
9. Enforce blueprint/employee budgets at execution time, or delete the fields.
10. Compute financial metrics in code and give the model the computed values (do not let it do arithmetic). The CEO pipeline error (F10) is still open.
11. Wire agent delegation: mission → specialist agent → scoped tool call → evidence; today a mission is one model call plus a file write.
12. Make mission output length honour `llm_max_tokens` (currently hard-coded to 1800 in the deliverable call).

**P2 — operational**
13. Real browser E2E in CI (needs Playwright + Chromium), live-Postgres suite, container suite; the current sandbox cannot run them.
14. Valid GitHub credentials so the hardening branch and these fixes can be pushed and reviewed.
15. Convert module-level singletons to tenant-scoped factories everywhere (audit remaining `= SomeEngine()` globals).

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
| `storage/evidence/audit_ledger.jsonl` | Ledger entries written by the real runs |

---

## 8. Stage-2 entry criteria

Stage 2 (design-partner pilot) may start only when:
- the owner has rotated the Neon `DATABASE_URL` and revoked the embedded PAT (P0-6);
- P1-7 (expense threshold/SoD) and P1-11 (real mission→agent→tool delegation) are closed, because both are visible in the demo flow;
- the capability matrix contains no `NOT IMPLEMENTED` or `FAILED` entry that a partner would touch — browser click/type/submit must either work with a real engine or be hidden from the partner UI;
- tenant isolation has an automated regression test for every engine that is still a singleton;
- a partner-facing page lists capabilities with the same statuses used here.

### Post-fix evidence index (retained raw responses)

| Evidence file | Proves |
|---|---|
| `browser_after_fix.json` | Real navigation (title/HTTP 200/577 bytes/`REAL_HTTP_FETCH`), allow-list denial, `ACTION_NOT_IMPLEMENTED`, financial approval interception |
| `p0_verification.json` | Kill switch `403` on terminal/mission/browser; MCP executions include `execution_status`; forged approval `POLICY_DENIED`; suspend→approve→real resume `VERIFIED` with server-side refund recorded; rejection → `REJECTED`; `LIVE_TOOLS_LIST` discovery; honest workflow outputs |
| `tests/test_mission_truncation_guard.py` | Truncated deliverable → `UNCERTAIN`, `VERIFICATION_REFUSED`, no evidence id, marker retained on disk |

### Known remaining gaps (do not hide these in a demo)

- Browser click/type/submit have no execution engine (`ACTION_NOT_IMPLEMENTED`); screenshots are `NOT_CAPTURED`.
- Browser provider session/DOM state is in-memory; it is lost on restart (F11).
- Workflows execute state transitions only; `business_outcome_verified` is always `false`.
- Missions are a single plan+deliverable model call; no specialist delegation or scoped tool use.
- Expense approval has no threshold or separation-of-duties enforcement.
- CEO weighted-pipeline arithmetic is still model-generated and wrong (₹29,997 vs ₹31,897).
- `test_server_connection` reports a hard-coded `latency_ms: 12.4`.
- Free LLM tier is rate-limited and intermittently unavailable; missions correctly end `BLOCKED` instead of fabricating.
- All evidence is SQLite; live Postgres, Playwright E2E and container suites remain unexecuted here.

Paid hosting, public signup, and payment processing remain unjustified by current evidence.
