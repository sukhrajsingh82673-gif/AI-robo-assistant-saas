# Runbook — Coworker Autonomy Supervisor

**Scope:** the tenant-scoped scheduler in `core/coworker/runtime_supervisor.py`
that advances background missions, drains the executive queue, and runs
security patrols.

## 1. Check status

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8080/api/coworker/autonomy | jq
```

Read `mode`, `last_tick`, `last_patrol`, `counters`, `last_error`.

| Mode | Meaning | First action |
|---|---|---|
| `RUNNING` | Ticking normally. | Check `last_error` and `last_tick.status`. |
| `DISABLED` | `ZONATA_COWORKER_AUTONOMY=0` (or test mode). | Start manually if intended, then fix the env. |
| `STOPPED` | Enabled but not running. | `POST {"action":"START"}`. |
| `STANDBY` | Another process on this host owns the lock. | Find the owner in the lock file; do not force a second scheduler. |
| `KILLSWITCH_HOLD` | A GLOBAL/TENANT/COMPANY switch is engaged. | Follow `KILLSWITCH_ENGAGED.md`. Do not disable the supervisor to work around it. |

Lock file: `$ZONATA_AUTONOMY_LOCK_DIR` (default `$TMPDIR/zonata_autonomy/`),
named `<tenant>__<company>.lock`, containing `pid=... started=...`.

State: `autonomy_state.db` next to the main SQLite DB, or
`ZONATA_AUTONOMY_STATE_DB`.

## 2. Missions are not moving

1. Confirm mode is `RUNNING` and `last_tick.status` is `OK`.
2. List missions: `GET /api/coworker/missions`.
3. Compare status against the eligibility table:
   * `WAITING` / `AWAITING_APPROVAL` are intentionally held.
   * `BLOCKED` is terminal unless `ZONATA_COWORKER_RETRY_BLOCKED=1`.
   * `human_control=true` is a hard hold.
4. If the mission is `BLOCKED` with a model/deliverable reason, this is an LLM
   availability problem, not a scheduler problem. Fix the provider; do not
   fabricate a deliverable.
5. Force one tick to isolate scheduling from the interval:

   ```bash
   curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"action":"TICK"}' http://127.0.0.1:8080/api/coworker/autonomy
   ```

   `SKIPPED / TICK_ALREADY_RUNNING` means a long step is in flight; wait.

## 2b. Executive work items

`POST /api/coworker/work-items` queues a governed item. The tick response
contains `queue_processed` and `queue_results`:

```json
{"item_id":"wi_...","status":"WorkItemStatus.COMPLETED",
 "execution_status":"COMPLETED","objective_achieved":false}
```

`execution_status=COMPLETED` means the CEO bridge produced and hash-verified a
`MISSION_PLAN_RECORD` file. It is **not** evidence that the business objective
was achieved; `objective_achieved` is false unless a future implementation
performs and verifies the real work. A work item over the $10,000 Delegation of
Authority ceiling returns `AWAITING_APPROVAL` and must be approved by an Owner or
Executive through the approvals endpoint.

## 3. Patrols are not running

* `schedule.patrol_enabled` must be true and `patrol_interval_sec` > 0.
* `last_patrol.at` updates only after a sweep. The first tick runs one
  immediately.
* If `last_error` contains `PATROL_UNAVAILABLE` or `PATROL_FAILED`, the monitor
  could not start; check the server log for the exception class.

## 4. Approvals

`GET /api/coworker/approvals` returns both mission holds (`app_*`) and
Delegation-of-Authority work items (`wi_*`).

```bash
# Mission hold: resumes and executes immediately.
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"decision":"APPROVE"}' \
  http://127.0.0.1:8080/api/coworker/approvals/app_msn_1234/decide

# DoA hold: re-queues; the next supervisor tick executes it.
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"decision":"APPROVE"}' \
  http://127.0.0.1:8080/api/coworker/approvals/wi_abcd1234/decide
```

The supervisor will never approve either class on its own.

## 5. Stop and rollback

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"action":"STOP"}' http://127.0.0.1:8080/api/coworker/autonomy
```

For a permanent stop, set `ZONATA_COWORKER_AUTONOMY=0` and restart. Stopping the
scheduler does not cancel missions; they remain persisted and can be retried.

## 6. Escalation

Escalate to the platform owner if:

* `process_lock.acquired=false` persists after the owning process is confirmed
  dead (remove the stale lock file only after verifying no process holds it).
* `last_tick.status=ERROR` repeats with the same exception.
* Distributed deployments show two hosts both in `RUNNING` for one tenant. This
  is a known limitation: the current lock is host-local; use a PostgreSQL
  advisory lock before scaling across hosts.
