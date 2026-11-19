# Coworker Autonomy Runtime

**Status:** Implemented and verified on a single host. Distributed (multi-host)
coordination remains **Partial** — see the limitations section.

## Why this component exists

Before this runtime, the co-worker fabric only moved when an HTTP request
happened to call an engine method:

| Engine | Old trigger |
|---|---|
| `BackgroundMissionDispatcher` | `POST /api/coworker/mission` advanced exactly one step, then nothing. |
| `ExecutiveOperatingLoop` | Never scheduled by the server. |
| `DefensiveCybersecurityMonitor` | Existed, but no server-owned patrol loop. |

The work engines themselves were real. The missing piece was an owner that ticks
them. `core/coworker/runtime_supervisor.py` is that owner.

## Architecture

```
TenantRuntime.coworker
        │ first access
        ▼
UniversalCoworkerEngine.get_instance(tenant, company)
        │
        ▼
ensure_supervisor(engine)                      ← process-wide registry
        │
        ▼
CoworkerAutonomySupervisor (daemon thread, one per tenant/company/host)
        │
        ├── 1. surface approvals (never auto-approve)
        ├── 2. security patrol (DefensiveCybersecurityMonitor)
        ├── 3. executive queue  (ExecutiveOperatingLoop.run_cycle)
        └── 4. background missions (BackgroundMissionDispatcher)
```

The order is deliberate: a slow model call in a mission must not starve the
security patrol or hide an approval hold.

`POST /api/coworker/work-items` is the production entry point for the
executive queue. It builds an `AICeoMissionRequest` and submits it through the
Delegation-of-Authority gate; the supervisor drains the queue on the next tick.
Without this entry point the queue would only ever be populated by tests.

### Mission eligibility

| Mission state | Supervisor action |
|---|---|
| `MISSION_CREATED`, `PLANNED`, `QUEUED`, `RUNNING`, `RECOVERING`, `VERIFYING` | Advance one step |
| `WAITING`, `AWAITING_APPROVAL` | Hold; surface in approvals |
| `BLOCKED` | Hold by default; optional bounded retry for model/deliverable blockers |
| `COMPLETED`, `FAILED`, `CANCELLED`, `UNCERTAIN` | Never touched |
| Any state with `human_control = True` | Hold |

`execute_compound_mission_step()` is serialized with an `RLock`, so the HTTP
endpoint and the supervisor cannot advance the same mission concurrently.

## Governance gates

The supervisor is a scheduler, not an authority. It adds no bypasses:

| Gate | Behaviour |
|---|---|
| KillSwitch `GLOBAL`, `TENANT`, `COMPANY` | Evaluated before every tick. Any error evaluating the matrix fails **closed**. |
| KillSwitch inside mission execution | `BackgroundMissionDispatcher` re-checks the matrix itself, so direct HTTP `step` calls are gated too. |
| Human takeover | `human_control` missions are held, never resumed. |
| Delegation of Authority | Pending work items are surfaced and can only be approved by a human via the approvals API. |
| Tenant/company isolation | Every supervisor is bound to one tenant/company; missions are re-checked against that binding. |
| Autonomy levels | The supervisor never raises an employee or agent autonomy level. |
| Evidence | The underlying engines write their own evidence; the scheduler adds no success claims. |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `ZONATA_COWORKER_AUTONOMY` | on outside tests | `0` disables auto-start. |
| `ZONATA_COWORKER_TICK_INTERVAL_SEC` | `5` | Scheduler period. |
| `ZONATA_COWORKER_PATROL_INTERVAL_SEC` | `900` | Security sweep period. |
| `ZONATA_COWORKER_MAX_MISSIONS_PER_TICK` | `5` | Fairness limit. |
| `ZONATA_COWORKER_MAX_QUEUE_ITEMS` | `10` | Executive queue drain limit. |
| `ZONATA_COWORKER_MISSION_COOLDOWN_SEC` | `2` | Per-mission retry spacing. |
| `ZONATA_COWORKER_RETRY_BLOCKED` | `0` | Retry missions blocked by model/deliverable failures (hourly). |
| `ZONATA_AUTONOMY_PROCESS_LOCK` | `1` | Host-local `flock` guard against duplicate schedulers. |
| `ZONATA_AUTONOMY_LOCK_DIR` | `$TMPDIR/zonata_autonomy` | Lock directory. |
| `ZONATA_AUTONOMY_STATE_DB` | `<db_dir>/autonomy_state.db` | Sidecar persistence DB. |
| `ZONATA_COWORKER_AUTONOMY_BOOTSTRAP_LIMIT` | `25` | Companies started at server boot; `0` disables bootstrapping. |

Under `ZONATA_TEST_MODE=1` the supervisor defaults to disabled so tests remain
deterministic. It can still be started explicitly.

On server boot, `bootstrap_tenant_supervisors()` walks the `companies` table and
starts a scheduler for each company (bounded and asynchronous). The lazy start
on first tenant access remains as a fallback.

## API

| Method | Path | Effect |
|---|---|---|
| `GET` | `/api/coworker/autonomy` | Real scheduler status, counters, last tick/patrol, governance mode. |
| `POST` | `/api/coworker/autonomy` `{"action":"START"}` | Start (manual override). |
| `POST` | `/api/coworker/autonomy` `{"action":"STOP"}` | Stop and release the host lock. |
| `POST` | `/api/coworker/autonomy` `{"action":"TICK"}` | Run exactly one tick; returns `SKIPPED` if a tick is already running. |
| `POST` | `/api/coworker/autonomy` `{"action":"STATUS"}` | Same payload as `GET`. |
| `GET` | `/api/coworker/work-items` | Executive-loop telemetry and pending DoA holds. |
| `POST` | `/api/coworker/work-items` | Queue a governed mission for the next tick. Over-ceiling items are held for approval. |
| `GET` | `/api/coworker/approvals` | Mission holds **and** DoA work-item holds. |
| `POST` | `/api/coworker/approvals/{id}/decide` | Approve/reject. DoA approvals only re-queue; the next tick executes them. |

The dashboard snapshot also includes an `autonomy` object, and the
cybersecurity panel now reports the patrol that the supervisor actually ran.

## Live verification (2026-11-07)

Run against a real `api_server.py` on port 8102 with `ZONATA_COWORKER_AUTONOMY=1`
and a SQLite database under `/tmp`:

| Check | Observed |
|---|---|
| Scheduler auto-start | `GET /api/coworker/autonomy` → `mode=RUNNING`, host lock acquired, `ticks` increasing. |
| Background mission autonomy | A mission submitted with `auto_step=false` advanced `20% → 50% → 80%` with no `/step` call, then honestly became `BLOCKED — deliverable generation failed`. |
| Security patrol | First tick ran a real sweep: `24 findings`, `0 critical`, `0 high`; dashboard showed the same timestamp. |
| KillSwitch | Engaged `TENANT` switch → `POST {"action":"TICK"}` returned `KILLSWITCH_HOLD` with `queue_processed=0`; disengaged → next tick returned `OK`. |
| DoA hold | A $50,000 item → `AWAITING_APPROVAL`, visible in `GET /api/coworker/approvals` as `DOA_APPROVAL`; approving via the API re-queued it. |
| Queue drain | A within-ceiling item was processed on the next tick; `queue_results` reported `execution_status=COMPLETED` **and** `objective_achieved=false`. |
| Regression | 15 coworker/enterprise suites exited 0; the autonomy suite is 12 tests. |

### What `COMPLETED` means for an executive work item

The CEO bridge writes a `MISSION_PLAN_RECORD` JSON file, re-reads it and seals
its SHA-256 in the evidence ledger. `execution_status=COMPLETED` means that
pipeline finished — **not** that the business objective was achieved. The bridge
sets `final_outcome.objective_achieved=false`, the evidence action is
`CEO_MISSION_PLAN_RECORD_SEALED`, and the supervisor copies the flag into
`queue_results`. Treat a green work item as "a verifiable plan record exists",
never as "the goal is done".

## What "automatic" means here

Verified on this host:

* The scheduler thread starts when a tenant runtime is first used.
* It advances background missions without any `auto_step` / `/step` call.
* It runs real terminal tool delegation inside those missions.
* It runs the defensive patrol and feeds the dashboard.
* Engage a tenant KillSwitch → the next tick returns `KILLSWITCH_HOLD` and does
  no work; disengage → work resumes.
* Held approvals are surfaced and never auto-approved.

It does **not** mean:

* Missions succeed without a language model. A mission that cannot produce a
  deliverable is marked `BLOCKED` with an explicit reason; the supervisor does
  not fabricate one.
* Browser, OCR, or container work that the host cannot perform.
* A stronger autonomy level for any employee or agent.

## Limitations

1. **Host-local lock only.** `flock` prevents two API processes on the same host
   from double-advancing a mission. It does not coordinate across hosts. A
   PostgreSQL advisory lock or lease table is required before claiming
   distributed exclusivity.
2. **One tick is sequential.** A long model call delays the rest of that tick.
   Patrol and approvals run first, but mission concurrency within a tenant is
   still one-at-a-time.
3. **Approval UI coverage.** The approval decision endpoint handles mission holds
   and DoA work items; other specialised approval surfaces remain their own
   systems.
4. **Patrols are host-scoped.** The defensive monitor scans the repository,
   processes, dependencies and ports of the host. It is not a per-tenant data
   scanner, and its findings are shared by tenant dashboards on that host.
