### API contract — `/api/{CURRENT}/agent-factory/…`

`{CURRENT}` = the highest API version already used by the ZONATA backend, **verified in Phase 1** (the brief guessed `v9`; do not use `v9` unless the repo already does). All routes below are relative to that prefix.

**Cross-cutting rules (every route)**

| Concern | Rule |
|---|---|
| Authentication | Existing ZONATA auth (Keycloak-issued JWT / session). Reject missing/expired tokens with 401. |
| Tenant context | Taken **only** from the authenticated principal, never from path/body. `X-Company-ID` header selects the company and must belong to the tenant; otherwise **404** (identical to "not found" — no existence oracle). Sets `zonata.tenant_id` on the DB transaction. |
| Authorisation | Every handler calls `GovernancePort.authorize(principal, action, resource, context)` (AuthorityGateway → PolicyEngine → OpenFGA). `deny` → 403 `AF-AUTHZ-DENIED`; `require_approval` → 202 with `approval_id`. |
| Kill switch | Handlers for mutating routes consult `KillSwitchMatrix` first (`factory`, `tenant`, `agent`, `batch` scopes) → 423 `AF-KILLED`. |
| Idempotency | All `POST` that create or transition require `Idempotency-Key` (16–128 chars). Same key + same body hash → original response replayed (`Idempotent-Replay: true`); same key + different body → 409 `AF-IDEMPOTENCY-MISMATCH`. Keys stored in `af_request.idempotency_key` / dedicated column per route family; TTL ≥ 24 h. |
| Validation | Pydantic v2 strict models; unknown fields → 422. Body ≤ 256 KiB (NL requirement ≤ 20 000 chars). |
| Rate limits | Per principal: 30 req/min mutating, 300 req/min read; per tenant: 10 manufacturing requests/hour on free tier, configurable. 429 + `Retry-After`. Global limits enforced at the proxy as well (in-process limits are per instance). |
| Errors | RFC 9457 `application/problem+json`: `{type, title, status, detail, code, correlation_id, errors[]}`. `code` is stable (`AF-…`). Never leak internal paths, SQL, or other tenants' identifiers. |
| Pagination | Cursor-based: `?limit=50&cursor=…` (max 200). Responses: `{items:[…], next_cursor}`. |
| Evidence | Every mutating route appends to the EvidenceLedger **before** returning success; the ledger id is returned in `X-Evidence-Id`. |
| Async | Long operations return **202** + `Location: /jobs/{id}`; progress via `GET /jobs/{id}` and SSE `GET /jobs/{id}/events`. |

**Routes**

| # | Method & path | Purpose | Authz action | Notes |
|---|---|---|---|---|
| 1 | `POST /requests` | Employee/assistant submits an NL request (single, multi, team, hierarchy, from_template, from_scratch, upgrade, import) | `factory.request.create` | Body: `{mode, natural_language, template_ref?, target_agent_id?, source_url?, budget_cap_usd?, release_policy?}`. Returns 202 `{request_id, status:"REQUESTED"}`. `import` mode routes to the quarantined Import lane. |
| 2 | `GET /requests`, `GET /requests/{id}` | List/inspect requests (own by default; managers see company; CEO sees all) | `factory.request.read` | Includes ARS versions, open questions, estimate. |
| 3 | `POST /requests/{id}/clarifications` | Requester answers essential questions | `factory.request.update` | Resumes analysis. |
| 4 | `POST /requests/{id}/analyze` | (Re)run requirement analysis | `factory.request.analyze` | Idempotent; produces new ARS version. |
| 5 | `GET /requests/{id}/estimate` | Estimated tokens, cost, wall-clock, sandbox seconds, quota impact | `factory.request.read` | Shown before approval of build. |
| 6 | `POST /requests/{id}/design/approve` | Approve/modify the architecture (R2+ requires it) | `factory.design.approve` | Approver ≠ requester for R2+. |
| 7 | `POST /batches` | Create batch directly (advanced; normally created by analysis) | `factory.batch.create` | Validates DAG (acyclic, ≤ 500 agents). |
| 8 | `GET /batches/{id}` | Manufacturing manifest + per-item status | `factory.batch.read` | Matches `batch_manifest.example.json`. |
| 9 | `POST /batches/{id}/start` | Begin building after estimate/budget reservation | `factory.build.start` | Reserves budget; starts workflow. |
| 10 | `POST /batches/{id}/cancel` | Cancel a batch | `factory.batch.cancel` | Cooperative; running builds drain or are killed. |
| 11 | `POST /batches/{id}/items/{key}/retry` | Retry a failed item | `factory.build.retry` | Max attempts per policy (default 3). |
| 12 | `GET /jobs/{id}`, `GET /jobs/{id}/events` | Track a job; SSE stream | `factory.job.read` | |
| 13 | `GET /templates`, `GET /templates/{name}/versions` | Browse templates | `factory.template.read` | Filters: category, risk tier, capability. |
| 14 | `POST /templates` / `POST /templates/{name}/versions` | Propose template/version | `factory.template.propose` | Creates DRAFT only. |
| 15 | `POST /templates/{name}/versions/{semver}/submit` | Submit for review | `factory.template.submit` | → IN_REVIEW; ApprovalEngine record. |
| 16 | `POST /templates/{name}/versions/{semver}/publish` | Publish approved version | `factory.template.publish` | Requires approval_id; never automatic. |
| 17 | `POST /agents/{id}/promote-to-template` | Propose template from validated agent | `factory.template.propose` | Review required. |
| 18 | `GET /agents/{id}/builds`, `GET /builds/{id}` | Inspect builds (stages, logs ref, cost) | `factory.build.read` | |
| 19 | `GET /agent-versions/{id}/evaluations`, `GET /eval-runs/{id}` | View tests and results | `factory.eval.read` | |
| 20 | `GET /agent-versions/{id}/findings` | Security findings | `factory.finding.read` | |
| 21 | `POST /findings/{id}/waive` | Waive a medium/low finding | `factory.finding.waive` | Needs security approver ≠ requester ≠ builder. Critical/high cannot be waived (409). |
| 22 | `GET /agent-versions/{id}/certification`, `GET /batches/{id}/certification` | View certification + gate results | `factory.cert.read` | Includes evidence ledger ref. |
| 23 | `POST /releases` | Release Manager submits certified package for approval | `factory.release.submit` | Body: `{agent_version_id | batch_id, channel}`. Creates ApprovalEngine request. |
| 24 | `POST /releases/{id}/decision` | Approve/reject (human or AI CEO per approval matrix) | `factory.release.decide` | DB trigger + service forbid requester/director self-approval. |
| 25 | `POST /releases/{id}/publish` | Publish approved release to the registry | `factory.agent.publish` | Atomic for teams. |
| 26 | `GET /agents`, `GET /agents/{id}`, `GET /agents/{id}/versions` | Registry search/filter/inspect | `factory.agent.read` | Filters: category, status, capability, assignee, risk. Never returns spec secrets (none exist). |
| 27 | `GET /agents/{id}/capabilities` | Capability/permission profile inspection | `factory.agent.read` | |
| 28 | `POST /agents/{id}/assignments` | Assign/reassign to employee/department/team/assistant | `factory.agent.assign` | Provisioning through `WorkforcePort`. |
| 29 | `DELETE /assignments/{id}` | Revoke assignment | `factory.agent.assign` | |
| 30 | `GET /agents/{id}/monitoring` | Health, SLOs, cost, incidents, feedback | `factory.agent.monitor` | |
| 31 | `POST /agents/{id}/upgrades` | Request an upgrade (config, tool, template, model) | `factory.agent.upgrade` | Creates new version request (mode=upgrade); never mutates in place. |
| 32 | `POST /agents/{id}/rollback` | Roll back to a previous certified version | `factory.agent.rollback` | Body `{to_version}`; only certified, non-withdrawn versions. |
| 33 | `POST /agents/{id}/suspend`, `POST /agents/{id}/resume` | Suspend / resume | `factory.agent.suspend` | Suspend is immediate and always allowed to AI CEO, owner, Security. |
| 34 | `POST /agents/{id}/retire` | Retire (irreversible) | `factory.agent.retire` | Revokes identity, tool bindings, memory per retention policy. |
| 35 | `POST /agents/{id}/feedback` | Employee feedback | `factory.agent.feedback` | |
| 36 | `POST /kill` | Kill switch: scope `agent|team|batch|tenant|factory` | `factory.kill` | Delegates to KillSwitchMatrix; evidence mandatory. |
| 37 | `GET /quotas`, `GET /usage` | Tenant quotas and consumption | `factory.quota.read` | |
| 38 | `GET /evidence/{subject_kind}/{id}` | Evidence chain + Merkle proof for a subject | `factory.evidence.read` | Verifiable offline. |
| 39 | `GET /health`, `GET /ready` | Liveness/readiness (workers, queue depth, sandbox availability) | none (internal) | Reports `sandbox_tiers_available`. |

**Error codes (stable)**: `AF-AUTHZ-DENIED`, `AF-KILLED`, `AF-IDEMPOTENCY-MISMATCH`, `AF-VALIDATION`, `AF-QUOTA-EXCEEDED`, `AF-BUDGET-EXCEEDED`, `AF-DAG-INVALID`, `AF-GATE-FAILED`, `AF-SELF-APPROVAL`, `AF-FINDING-NOT-WAIVABLE`, `AF-VERSION-FROZEN`, `AF-NOT-CERTIFIED`, `AF-SANDBOX-UNAVAILABLE`, `AF-TENANT-MISMATCH`, `AF-CONFLICT-STATE`.

**Example — create a team request**

```http
POST /requests
Idempotency-Key: 7d1c3b9e-5a4f-4d11-9a9b-2f0a6c9e1b11
X-Company-ID: 7a2c…
{ "mode": "team",
  "natural_language": "Build a marketing intelligence department: supervisor, market research, competitor analysis, customer intelligence, trend analysis, campaign strategy and reporting agents. Weekly brief to me every Monday.",
  "release_policy": "atomic_team", "budget_cap_usd": 18.0 }
→ 202 Accepted
Location: /requests/r7a0c1d4-…
X-Evidence-Id: led_01HZ…
{ "request_id": "r7a0c1d4-…", "status": "REQUESTED", "correlation_id": "…" }
```
