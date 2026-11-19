# MULTI_AGENT_MANUFACTURING — batches, teams, parallelism, dependencies, publication

## 1. Request shapes

| Shape | `mode` | Release policy default | Example |
|---|---|---|---|
| One agent | `single` / `from_template` / `from_scratch` | n/a | "Agent that reconciles daily bookings" |
| Several independent agents | `multi` | `independent` | "Build five agents: invoice checker, lead scorer, …" |
| Supervisor + subordinates | `team` | `atomic_team` | "Marketing intelligence department" |
| Hierarchical organisation | `hierarchy` | `atomic_team` | "Sales org: head → regional leads → reps" |
| Upgrade/modify | `upgrade` | `independent` | "Add PDF reports to agent X" |
| Import OSS agent | `import` | `independent` | "Use this GitHub agent" (quarantined lane) |

"Hundreds of agents" is supported as a **fleet batch** (`agent_count ≤ 500`, processed in waves with the same planner), subject to a higher approval class and tenant quota. A hard cap per batch (500) prevents unbounded fan-out; larger programmes are multiple batches.

## 2. Manufacturing manifest

One `af_batch` row + `af_batch_item` rows + the **manifest JSON** (immutable parts hashed into `manifest_sha256`). Contents requested by the brief and where they live:

| Manifest field (brief) | Location |
|---|---|
| Batch ID, requesting employee, tenant | `af_batch.id`, `af_request.requester_principal_id`, `tenant_id` |
| Number of agents, specifications | `agent_count`, `af_batch_item` → `af_requirement_spec` + (after build) `af_agent_version.spec` |
| Dependency graph | `af_batch.dependency_graph` (`build_requires`, `runtime_delegates_to`, `reports_to` edges) |
| Build status | `af_batch_item.status`, `af_build` |
| Individual QA results | `af_eval_run(phase=independent_qa, agent_version_id)` |
| Team QA results | `af_batch.team_qa_eval_run_id` → `af_eval_run(subject_kind=batch_team)` |
| Release status | `af_release`, `af_batch.status` |
| Final evidence | `af_certification` (+ team certification) with ledger refs |

Example (valid against the planner; produces three waves):

```json
{
  "apiVersion": "zonata.batch/v1",
  "kind": "ManufacturingManifest",
  "batch_id": "b3f1a8e2-0000-4000-8000-000000000001",
  "request_id": "r7a0c1d4-0000-4000-8000-000000000002",
  "tenant_id": "<tenant-uuid>",
  "company_id": "<company-uuid>",
  "requesting_principal": { "id": "<employee-uuid>", "kind": "ai_employee", "role": "CMO" },
  "release_policy": "atomic_team",
  "risk_tier": "R1",
  "budget": { "cap_usd": 18.0, "reserved_usd": 12.5, "per_agent_cap_usd": 2.5 },
  "concurrency": { "max_parallel_builds": 4, "tenant_concurrent_builds_limit": 4 },
  "agent_count": 7,
  "agents": [
    { "key": "market_research",  "role": "Market Research Agent",       "template": "research-agent@1.2.0", "risk_tier": "R1", "wave": 0 },
    { "key": "competitor",       "role": "Competitor Analysis Agent",   "template": "research-agent@1.2.0", "risk_tier": "R1", "wave": 0 },
    { "key": "customer_intel",   "role": "Customer Intelligence Agent", "template": "data-analysis-agent@1.0.0", "risk_tier": "R1", "wave": 0 },
    { "key": "trend",            "role": "Trend Analysis Agent",        "template": "research-agent@1.2.0", "risk_tier": "R1", "wave": 0 },
    { "key": "campaign",         "role": "Campaign Strategy Agent",     "template": "marketing-strategy-agent@1.0.0", "risk_tier": "R1", "wave": 1 },
    { "key": "reporting",        "role": "Reporting Agent",             "template": "document-reporting-agent@1.1.0", "risk_tier": "R0", "wave": 1 },
    { "key": "supervisor",       "role": "Marketing Supervisor Agent",  "template": "supervisor-agent@1.0.0", "risk_tier": "R1", "wave": 2 }
  ],
  "dependency_graph": {
    "edges": [
      ["market_research", "campaign", "build_requires"], ["competitor", "campaign", "build_requires"],
      ["customer_intel", "campaign", "build_requires"],  ["trend", "campaign", "build_requires"],
      ["market_research", "reporting", "build_requires"],
      ["campaign", "supervisor", "build_requires"], ["reporting", "supervisor", "build_requires"],
      ["supervisor", "market_research", "runtime_delegates_to"], ["supervisor", "competitor", "runtime_delegates_to"],
      ["supervisor", "customer_intel", "runtime_delegates_to"], ["supervisor", "trend", "runtime_delegates_to"],
      ["supervisor", "campaign", "runtime_delegates_to"], ["supervisor", "reporting", "runtime_delegates_to"],
      ["market_research", "supervisor", "reports_to"], ["competitor", "supervisor", "reports_to"],
      ["customer_intel", "supervisor", "reports_to"], ["trend", "supervisor", "reports_to"],
      ["campaign", "supervisor", "reports_to"], ["reporting", "supervisor", "reports_to"]
    ]
  },
  "communication_contracts": [
    { "from": "supervisor", "to": "*", "protocol": "a2a", "task_schema": "contracts/delegation-task@1", "result_schema": "contracts/agent-result@1", "max_depth": 2 }
  ],
  "shared_knowledge": [
    { "collection": "marketing-shared", "access": { "supervisor": "read", "market_research": "write", "competitor": "write", "customer_intel": "write", "trend": "write", "campaign": "read", "reporting": "read" }, "isolation": "tenant+company, row-level, no cross-company reads" }
  ],
  "status": { "batch": "BUILDING", "items": { "market_research": "BUILT", "competitor": "BUILDING", "customer_intel": "BUILDING", "trend": "BUILDING", "campaign": "PENDING", "reporting": "PENDING", "supervisor": "PENDING" } },
  "individual_qa": {}, "team_qa": null,
  "release": { "status": "NOT_SUBMITTED", "approval_id": null },
  "evidence": { "ledger_entries": [], "merkle_root_at_last_checkpoint": null },
  "manifest_sha256": "<computed over canonical JSON of the immutable parts: agents, dependency_graph, contracts, release_policy>"
}
```

## 3. Planning (tested reference: `reference/qa/batch_scheduler.py`)

1. **Validate** nodes unique, ≤500; edges reference known nodes; kinds in {`build_requires`, `runtime_delegates_to`, `reports_to`}.
2. **Acyclicity** is checked separately for build ordering, runtime delegation (delegation loops are forbidden) and reporting (each agent reports to exactly one supervisor; no cycles).
3. **Waves** = longest `build_requires` path. The marketing team plans into `[competitor, customer_intel, market_research, trend] → [campaign, reporting] → [supervisor]`.
4. **Ready set** = PENDING items whose prerequisites are `BUILT` or later, ordered by wave, capped by parallelism.
5. **Failure propagation:** a failed item is `FAILED`; every transitive dependent becomes `BLOCKED`; independent siblings continue. Nothing becomes `CERTIFIED` by default. (Unit-tested: 15/15 checks pass, including 300-agent planning, cycles, two supervisors, partial failure.)

*Why `build_requires` is separate from `runtime_delegates_to`:* the supervisor needs the specialists' **contracts** to be designed first, but to be **certified as a team** it needs their built versions; delegation direction (supervisor → specialist) is opposite to build direction in some designs, so conflating them would create false cycles.

## 4. Concurrency, queues, workers, quotas

| Control | Default (free tier / pilot / paid) | Enforced by |
|---|---|---|
| Global build workers | 1 / 2–4 / autoscaled | Orchestrator worker pool size |
| Per-tenant concurrent builds | 1 / 2 / 4 | `af_quota_usage(concurrent_builds)` checked atomically (`UPDATE … WHERE used < limit`) |
| Per-batch parallel builds | 1 / 3 / 4 (≤ tenant limit) | Planner `max_parallel` |
| QA workers (separate pool from build) | 1 / 2 / 4 | Orchestrator |
| Sandbox workers (T1/T2) | 0 (disabled) / 0–1 / host-dependent | Sandbox broker capacity |
| Agents per batch | 5 / 12 / 500 | Policy |
| Batches per tenant per hour | 3 / 10 / 60 | Rate limit |
| Worker heartbeat | 15 s; lost after 60 s | `af_build.heartbeat_at` |
| Attempts per item | 3 | Director |

**Queue management.** Work items are classed `interactive` (single agent, employee waiting), `batch`, `fleet`, `maintenance` (upgrades, re-certification). Dispatch = weighted fair queuing **per tenant** (no tenant can starve others), strict priority only for `kill`/`rollback`/`suspend` control messages, aging to avoid starvation. Queue depth and oldest-age are exported as metrics; `/ready` fails open-to-degraded, not silently.

**Orchestration.** `OrchestratorPort`: Temporal where it exists (parent workflow per batch, child workflow per item, signals for approvals, schedules for monitoring/re-cert); otherwise `DbQueueOrchestrator` (Postgres `SELECT … FOR UPDATE SKIP LOCKED`, lease + heartbeat, resume from the last durable stage using the `af_build.stages` log). Both satisfy the same acceptance tests AT-06/07/08/19.

## 5. Cost controls

1. **Estimate before start** (`GET /requests/{id}/estimate`): Σ over items of (expected tokens × profile price) + QA runs (cases × repeats × tokens) + sandbox seconds, with a 1.5× safety factor; shown to the requester and approver.
2. **Reserve** budget at `batches/{id}/start` (`af_request.budget_cap_usd`, tenant monthly counter).
3. **Meter** every model call through the gateway with the job's budget token; accumulate in `af_build.cost_usd` and `af_request.spent_usd`.
4. **Hard stop** when spend ≥ cap (one in-flight call may overshoot; the overshoot is bounded by `max_tokens`). Resume needs a raised cap by an authorised principal.
5. **No silent downgrade:** the Factory never swaps to a cheaper model to fit budget unless that profile is in the spec's approved `fallback_profiles` **and** the certification covered it.
6. **Per-agent caps** (`limits.max_cost_usd_per_task`) are tested in G09 and enforced at runtime.

Planning formula (assumptions to be replaced by measured values in Phase 7): `cost ≈ Σ_agents [ build_tokens·p_build + cases·repeats·tokens_per_case·p_qa ] × 1.5`.

## 6. Team-level construction and testing

- **Identities:** each member has its own agent principal; the **team** has a manifest artifact (signed) and an `af_team` row; the supervisor's delegation targets are exactly the manifest's `runtime_delegates_to` set.
- **Communication contracts:** A2A task/result schemas (`delegation-task@1`, `agent-result@1`), `max_depth`, timeouts. Delegation can only **narrow**: effective permissions of a delegated task = `min(delegator, delegatee)`; a specialist never gains the supervisor's rights and vice versa (tested AT-11c, G07).
- **Shared knowledge:** one collection per team with explicit per-member access (`read`/`write`), tenant+company scoped; write access is exceptional and logged; no cross-company reads; DLP applies to writes.
- **Team QA (G13):** end-to-end scenarios through the supervisor (e.g. weekly brief): delegation correctness, reporting-line adherence to the org chart, specialist failure surfaced, shared-knowledge isolation, depth/cycle limits. Requires all members `QA_PASSED` first.

## 7. Partial failure and publication

| Release policy | Behaviour |
|---|---|
| **`atomic_team`** (default for teams) | All members must be `CERTIFIED` **and** team certification (G13) must pass. Publication is a **two-phase** operation: (1) *stage* all runtimes in `staging` and verify signatures/health; (2) one DB transaction flips every member version to `PUBLISHED`, writes `af_team`/`af_team_member`, assignments, and **one** `af_release`; runtime activation follows via outbox; any failure → compensating rollback (deactivate staged, versions stay `APPROVED`, alert). No state exists in which half a team is live. |
| **`independent`** (default for multi) | Each agent has its own certification and release; failed agents never certify; batch ends `PARTIAL` with an explicit per-agent report. |
| **Subset release** (exceptional, atomic teams only) | If a member fails permanently, a human may approve a **new manifest version** with that member removed or replaced; the reduced team must pass G13 again. It is never automatic and never silent. |

Failure semantics for the requester: the batch view lists, per agent, *what failed, why (gate, finding, cost, infra), what is blocked because of it, and the available actions* (retry, replace, release subset, cancel).

## 8. Worked example — marketing intelligence department (7 agents)

| Wave | Agents | Notes |
|---|---|---|
| 0 | Market Research, Competitor Analysis, Customer Intelligence, Trend Analysis | Built concurrently (≤ tenant limit); research/data templates; R1 (external read) |
| 1 | Campaign Strategy (needs 4 contracts), Reporting (needs Market Research output schema) | Reporting is R0 (documents only) |
| 2 | Marketing Supervisor | Delegates to all six; reports to the requesting CMO employee |
| Team QA | Supervisor-driven scenarios | G13 + each agent's G01–G11 |
| Approval | R1 team → AI CEO approves; autonomy "Ask me first" adds the human owner | Atomic publish |

On a free tier with one build worker the same batch runs strictly sequentially in dependency order; correctness is identical, wall-clock is longer. This is stated in the estimate shown to the requester.

## 9. What is *not* claimed

Throughput, concurrency and cost figures above are **design limits and planning assumptions**, not measurements. They become claims only after the load/soak tests in Phase 10 run on production-grade infrastructure (see Infrastructure doc §6).
