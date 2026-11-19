"""
ZONATA Universal AI Co-worker Fabric — Autonomy Runtime Supervisor
===================================================================

The co-worker fabric already contains the actual work engines:

* ``BackgroundMissionDispatcher`` — one-prompt background missions.
* ``ExecutiveOperatingLoop``      — priority queue with DoA approval gates.
* ``DefensiveCybersecurityMonitor`` — defensive security patrols.

Historically each engine only moved when an HTTP request called it.  This
module owns the missing piece: a tenant-scoped, always-on scheduler that
ticks those engines on their own schedule.

Design rules (non-negotiable)
-----------------------------
* This is a deterministic scheduler, not a model.  It never fabricates work
  results; it simply advances engines that already do real work.
* It does **not** bypass governance.  Every tick first evaluates the
  KillSwitch matrix (fail-closed).  Missions with ``human_control`` set, or
  in ``WAITING``/``AWAITING_APPROVAL``, are left untouched.  Delegation of
  Authority approvals are surfaced, never auto-approved.
* Only one supervisor per tenant/company per host may be active.  A process
  file lock prevents two API workers from double-advancing the same mission.
* Autonomy is opt-out, not opt-in: ``ZONATA_COWORKER_AUTONOMY=0`` disables it.
  It is disabled by default under ``ZONATA_TEST_MODE=1`` so tests stay
  deterministic unless they explicitly enable it.

Environment
-----------
``ZONATA_COWORKER_AUTONOMY``             1/0 (default: on outside tests)
``ZONATA_COWORKER_TICK_INTERVAL_SEC``    scheduler period (default 5)
``ZONATA_COWORKER_PATROL_INTERVAL_SEC``  security sweep period (default 900)
``ZONATA_COWORKER_MAX_MISSIONS_PER_TICK`` default 5
``ZONATA_COWORKER_MAX_QUEUE_ITEMS``      default 10
``ZONATA_COWORKER_MISSION_COOLDOWN_SEC`` default 2
``ZONATA_COWORKER_RETRY_BLOCKED``        1/0 retry model-blocked missions
``ZONATA_AUTONOMY_PROCESS_LOCK``         1/0 (default 1)
``ZONATA_AUTONOMY_LOCK_DIR``             lock directory (default tmp)
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from ..killswitch_matrix import KillSwitchLevel


# Mission states that the scheduler may advance without a human decision.
_ADVANCEABLE = frozenset({
    "MISSION_CREATED",
    "PLANNED",
    "QUEUED",
    "RUNNING",
    "RECOVERING",
    "VERIFYING",
})

# States that are explicitly held for a human or an approval decision.
_HELD_FOR_HUMAN = frozenset({"WAITING", "AWAITING_APPROVAL"})

# Terminal states: never touched again.
_TERMINAL = frozenset({"COMPLETED", "FAILED", "CANCELLED", "UNCERTAIN"})


def _env_truthy(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _env_float(name: str, default: float, minimum: float = 0.05) -> float:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def autonomy_enabled_by_default() -> bool:
    """Autonomy is on in the SaaS runtime, off in the test harness by default."""
    explicit = os.environ.get("ZONATA_COWORKER_AUTONOMY")
    if explicit is not None:
        return _env_truthy("ZONATA_COWORKER_AUTONOMY", True)
    return not _env_truthy("ZONATA_TEST_MODE", False)


class CoworkerAutonomySupervisor:
    """Always-on scheduler for one tenant/company co-worker runtime."""

    PRODUCT = "ZONATA Coworker Autonomy Supervisor"
    ENGINE_KIND = "DETERMINISTIC_SCHEDULER"

    def __init__(
        self,
        engine: Any,
        tick_interval_sec: Optional[float] = None,
        patrol_interval_sec: Optional[float] = None,
        max_missions_per_tick: Optional[int] = None,
        max_queue_items: Optional[int] = None,
        mission_cooldown_sec: Optional[float] = None,
        enable_patrol: bool = True,
        retry_blocked: Optional[bool] = None,
        acquire_process_lock: Optional[bool] = None,
    ):
        self.engine = engine
        self.tenant_id = getattr(engine, "tenant_id", "tnt_primary")
        self.company_id = getattr(engine, "company_id", "comp_primary")

        self.tick_interval_sec = (
            tick_interval_sec
            if tick_interval_sec is not None
            else _env_float("ZONATA_COWORKER_TICK_INTERVAL_SEC", 5.0, 0.1)
        )
        self.patrol_interval_sec = (
            patrol_interval_sec
            if patrol_interval_sec is not None
            else _env_float("ZONATA_COWORKER_PATROL_INTERVAL_SEC", 900.0, 1.0)
        )
        self.max_missions_per_tick = (
            max_missions_per_tick
            if max_missions_per_tick is not None
            else _env_int("ZONATA_COWORKER_MAX_MISSIONS_PER_TICK", 5, 0)
        )
        self.max_queue_items = (
            max_queue_items
            if max_queue_items is not None
            else _env_int("ZONATA_COWORKER_MAX_QUEUE_ITEMS", 10, 0)
        )
        self.mission_cooldown_sec = (
            mission_cooldown_sec
            if mission_cooldown_sec is not None
            else _env_float("ZONATA_COWORKER_MISSION_COOLDOWN_SEC", 2.0, 0.0)
        )
        self.enable_patrol = enable_patrol and self.patrol_interval_sec > 0
        self.retry_blocked = (
            retry_blocked
            if retry_blocked is not None
            else _env_truthy("ZONATA_COWORKER_RETRY_BLOCKED", False)
        )
        self.acquire_process_lock = (
            acquire_process_lock
            if acquire_process_lock is not None
            else _env_truthy("ZONATA_AUTONOMY_PROCESS_LOCK", True)
        )
        self.enabled = autonomy_enabled_by_default()

        self._state_lock = threading.RLock()
        self._tick_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._manual_start = False
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._last_tick_at: Optional[float] = None
        self._last_tick_duration_ms: Optional[float] = None
        self._last_tick_status = "NEVER_RUN"
        self._last_error: Optional[str] = None
        self._consecutive_errors = 0
        self._tick_count = 0
        self._missions_advanced_total = 0
        self._missions_held_total = 0
        self._queue_processed_total = 0
        self._patrol_runs = 0
        self._last_patrol_at: Optional[float] = None
        self._last_patrol_summary: Dict[str, Any] = {}
        self._last_killswitch: Dict[str, Any] = {}
        self._mission_last_attempt: Dict[str, float] = {}
        self._last_persist_at = 0.0
        self._persist_enabled = True
        self._lock_handle = None
        self._lock_path: Optional[str] = None
        self._lock_acquired = not self.acquire_process_lock
        self._errors: List[str] = []

        self._init_state_store()
        self._load_state()

    # ------------------------------------------------------------------ state
    def _db_path(self) -> Optional[str]:
        path = getattr(self.engine, "db_path", None)
        return path or None

    def _state_db_path(self) -> Optional[str]:
        """Sidecar DB so scheduler bookkeeping never blocks the main database."""
        override = os.environ.get("ZONATA_AUTONOMY_STATE_DB")
        if override:
            return override
        base = self._db_path()
        if not base:
            return None
        root = os.path.dirname(os.path.abspath(base))
        return os.path.join(root, "autonomy_state.db")

    def _get_connection(self):
        path = self._state_db_path()
        if not path:
            raise RuntimeError("engine has no db_path")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        conn = sqlite3.connect(path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_state_store(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS coworker_autonomy_state (
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    last_tick_at REAL,
                    last_patrol_at REAL,
                    tick_count INTEGER NOT NULL DEFAULT 0,
                    missions_advanced INTEGER NOT NULL DEFAULT 0,
                    queue_processed INTEGER NOT NULL DEFAULT 0,
                    last_tick_status TEXT,
                    last_error TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (tenant_id, company_id)
                )
                """)
                conn.commit()
        except Exception as exc:
            self._persist_enabled = False
            self._last_error = f"STATE_STORE_UNAVAILABLE: {type(exc).__name__}"

    def _load_state(self) -> None:
        if not self._persist_enabled:
            return
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM coworker_autonomy_state WHERE tenant_id = ? AND company_id = ?",
                    (self.tenant_id, self.company_id),
                ).fetchone()
            if row:
                self._last_tick_at = row["last_tick_at"]
                self._last_patrol_at = row["last_patrol_at"]
                self._tick_count = int(row["tick_count"] or 0)
                self._missions_advanced_total = int(row["missions_advanced"] or 0)
                self._queue_processed_total = int(row["queue_processed"] or 0)
                self._last_tick_status = row["last_tick_status"] or "NEVER_RUN"
                self._last_error = row["last_error"]
        except Exception:
            pass

    def _persist_state(self, force: bool = False) -> None:
        if not self._persist_enabled:
            return
        now = time.time()
        if not force and (now - self._last_persist_at) < 30.0:
            return
        self._last_persist_at = now
        try:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT INTO coworker_autonomy_state (
                    tenant_id, company_id, last_tick_at, last_patrol_at,
                    tick_count, missions_advanced, queue_processed,
                    last_tick_status, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (tenant_id, company_id) DO UPDATE SET
                    last_tick_at = excluded.last_tick_at,
                    last_patrol_at = excluded.last_patrol_at,
                    tick_count = excluded.tick_count,
                    missions_advanced = excluded.missions_advanced,
                    queue_processed = excluded.queue_processed,
                    last_tick_status = excluded.last_tick_status,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """, (
                    self.tenant_id, self.company_id, self._last_tick_at,
                    self._last_patrol_at, self._tick_count,
                    self._missions_advanced_total, self._queue_processed_total,
                    self._last_tick_status, self._last_error, now,
                ))
                conn.commit()
        except Exception:
            pass

    # ---------------------------------------------------------- process lock
    def _acquire_lock(self) -> bool:
        if not self.acquire_process_lock:
            self._lock_acquired = True
            return True
        if self._lock_acquired and self._lock_handle is not None:
            return True
        try:
            import fcntl  # POSIX only; the host is Linux.
        except Exception:
            self._lock_acquired = True
            return True
        try:
            base = os.environ.get("ZONATA_AUTONOMY_LOCK_DIR") or os.path.join(
                tempfile.gettempdir(), "zonata_autonomy"
            )
            os.makedirs(base, exist_ok=True)
            safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in f"{self.tenant_id}__{self.company_id}")
            path = os.path.join(base, f"{safe}.lock")
            handle = open(path, "a+")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close()
                self._lock_acquired = False
                self._lock_path = path
                return False
            handle.seek(0)
            handle.truncate()
            handle.write(f"pid={os.getpid()} started={time.time()}\n")
            handle.flush()
            self._lock_handle = handle
            self._lock_path = path
            self._lock_acquired = True
            return True
        except Exception as exc:
            # Fail open on a non-security lock failure: the lock is an
            # anti-duplication guard, not a governance boundary.
            self._lock_acquired = True
            self._last_error = f"PROCESS_LOCK_UNAVAILABLE: {type(exc).__name__}"
            return True

    def _release_lock(self) -> None:
        handle = self._lock_handle
        self._lock_handle = None
        if handle is not None:
            try:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                handle.close()
            except Exception:
                pass
        self._lock_acquired = not self.acquire_process_lock

    # -------------------------------------------------------------- lifecycle
    def is_running(self) -> bool:
        with self._state_lock:
            return self._running

    def start(self, manual: bool = False) -> Dict[str, Any]:
        """Starts the background scheduler. Idempotent."""
        with self._state_lock:
            if self._running:
                return self.status()
            if not self.enabled and not manual:
                return self.status()
            self._manual_start = manual
            if not self._acquire_lock():
                return self.status()
            self._running = True
            self._started_at = time.time()
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name=f"CoworkerAutonomy[{self.tenant_id}]",
                daemon=True,
            )
            self._thread.start()
            self._persist_state(force=True)
            return self.status()

    def stop(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Stops the background scheduler and releases the process lock."""
        with self._state_lock:
            was_running = self._running
            self._running = False
            self._stop_event.set()
            thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        with self._state_lock:
            self._thread = None
            self._stopped_at = time.time()
            if was_running:
                self._release_lock()
            self._persist_state(force=True)
            return self.status()

    def _loop(self) -> None:
        while self._running:
            try:
                self.run_once(trigger="scheduled")
            except Exception as exc:  # pragma: no cover - defensive
                with self._state_lock:
                    self._last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
                    self._consecutive_errors += 1
            if self._stop_event.wait(self.tick_interval_sec):
                break

    # ------------------------------------------------------------------ gates
    def _killswitch_state(self) -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "active": False,
            "global": False,
            "tenant": False,
            "company": False,
            "evaluated": False,
        }
        killswitch = getattr(self.engine, "killswitch", None)
        if killswitch is None:
            # Fail closed: an engine without a killswitch must not run work.
            state.update({"active": True, "error": "KILLSWITCH_UNAVAILABLE"})
            return state
        try:
            state["global"] = bool(killswitch.is_activated(KillSwitchLevel.GLOBAL))
            state["tenant"] = bool(killswitch.is_activated(KillSwitchLevel.TENANT, self.tenant_id))
            state["company"] = bool(killswitch.is_activated(KillSwitchLevel.COMPANY, self.company_id))
            state["evaluated"] = True
            state["active"] = state["global"] or state["tenant"] or state["company"]
        except Exception as exc:
            # Fail closed on any evaluation error.
            state.update({
                "active": True,
                "error": f"KILLSWITCH_EVALUATION_FAILED: {type(exc).__name__}",
            })
        return state

    # ------------------------------------------------------------------- tick
    def run_once(self, trigger: str = "manual") -> Dict[str, Any]:
        """Runs exactly one scheduler tick. Safe to call from tests/API."""
        if not self._tick_lock.acquire(blocking=False):
            return {
                "product": self.PRODUCT,
                "status": "SKIPPED",
                "reason": "TICK_ALREADY_RUNNING",
                "trigger": trigger,
                "tenant_id": self.tenant_id,
            }

        started = time.time()
        result: Dict[str, Any] = {
            "product": self.PRODUCT,
            "engine_kind": self.ENGINE_KIND,
            "status": "OK",
            "trigger": trigger,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "started_at": started,
            "missions_advanced": 0,
            "missions_held": 0,
            "queue_processed": 0,
            "patrol_ran": False,
            "approvals_pending": [],
            "approvals_auto_approved": 0,
            "errors": [],
        }

        try:
            killswitch = self._killswitch_state()
            result["killswitch"] = killswitch
            with self._state_lock:
                self._tick_count += 1
                self._last_tick_at = started
                self._last_killswitch = killswitch

            if killswitch.get("active"):
                result["status"] = "KILLSWITCH_HOLD"
                result["reason"] = "KILLSWITCH_ENGAGED"
                self._finish_tick(result, started)
                return result

            # Cheap governance/telemetry first, then the security sweep, then
            # long-running work. A slow model call must not starve patrols.
            self._surface_approvals(result)
            self._run_patrol(result)
            self._drain_executive_queue(result)
            self._advance_missions(result)
            with self._state_lock:
                self._consecutive_errors = 0
                self._last_error = None
            self._finish_tick(result, started)
            return result
        except Exception as exc:
            result["status"] = "ERROR"
            result["errors"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
            with self._state_lock:
                self._last_error = result["errors"][0]
                self._consecutive_errors += 1
            self._finish_tick(result, started)
            return result
        finally:
            self._tick_lock.release()

    def _finish_tick(self, result: Dict[str, Any], started: float) -> None:
        finished = time.time()
        result["finished_at"] = finished
        result["duration_ms"] = round((finished - started) * 1000.0, 2)
        with self._state_lock:
            self._last_tick_duration_ms = result["duration_ms"]
            self._last_tick_status = result["status"]
            self._missions_advanced_total += int(result.get("missions_advanced", 0))
            self._missions_held_total += int(result.get("missions_held", 0))
            self._queue_processed_total += int(result.get("queue_processed", 0))
        self._persist_state()

    def _advance_missions(self, result: Dict[str, Any]) -> None:
        dispatcher = getattr(self.engine, "background_dispatcher", None)
        if dispatcher is None or not hasattr(dispatcher, "list_missions"):
            result["errors"].append("MISSION_DISPATCHER_UNAVAILABLE")
            return

        try:
            missions = list(dispatcher.list_missions())
        except Exception as exc:
            result["errors"].append(f"MISSION_LIST_FAILED: {type(exc).__name__}")
            return

        now = time.time()
        advanced = 0
        for mission in missions:
            mission_id = getattr(mission, "mission_id", None)
            status = str(getattr(mission, "status", ""))
            if not mission_id:
                continue

            if getattr(mission, "human_control", False):
                result["missions_held"] += 1
                continue
            if status in _HELD_FOR_HUMAN:
                result["missions_held"] += 1
                continue
            if status in _TERMINAL:
                continue

            if status == "BLOCKED":
                if not self.retry_blocked or not self._is_model_blocked(mission):
                    continue
                last_retry = self._mission_last_attempt.get(mission_id, 0.0)
                if (now - last_retry) < max(self.patrol_interval_sec, 60.0):
                    continue
                self._mission_last_attempt[mission_id] = now
                try:
                    dispatcher.retry_mission(mission_id)
                    result.setdefault("missions_retried", []).append(mission_id)
                except Exception as exc:
                    result["errors"].append(f"MISSION_RETRY_FAILED[{mission_id}]: {type(exc).__name__}")
                    continue
                status = str(getattr(dispatcher.get_mission(mission_id), "status", "")) if hasattr(dispatcher, "get_mission") else "RUNNING"

            if status not in _ADVANCEABLE:
                continue
            if advanced >= self.max_missions_per_tick:
                result["missions_deferred"] = result.get("missions_deferred", 0) + 1
                continue
            last_attempt = self._mission_last_attempt.get(mission_id, 0.0)
            if (now - last_attempt) < self.mission_cooldown_sec:
                continue

            self._mission_last_attempt[mission_id] = now
            before_status = status
            before_progress = float(getattr(mission, "progress_percent", 0.0) or 0.0)
            try:
                updated = dispatcher.execute_compound_mission_step(mission_id)
            except Exception as exc:
                result["errors"].append(f"MISSION_STEP_FAILED[{mission_id}]: {type(exc).__name__}")
                continue

            if updated is None:
                result["errors"].append(f"MISSION_STEP_RETURNED_NONE[{mission_id}]")
                continue

            result["missions_stepped"] = int(result.get("missions_stepped", 0)) + 1
            after_status = str(getattr(updated, "status", before_status))
            after_progress = float(getattr(updated, "progress_percent", before_progress))
            if after_status != before_status or after_progress != before_progress:
                advanced += 1
                result.setdefault("missions_advanced_ids", []).append(mission_id)

        result["missions_advanced"] = advanced

    @staticmethod
    def _is_model_blocked(mission: Any) -> bool:
        stage = str(getattr(mission, "current_stage", "")).lower()
        return any(marker in stage for marker in ("model", "language model", "llm", "deliverable"))

    def _drain_executive_queue(self, result: Dict[str, Any]) -> None:
        loop = getattr(self.engine, "executive_loop", None)
        if loop is None or not hasattr(loop, "run_cycle"):
            return
        if self.max_queue_items <= 0:
            return
        try:
            processed = loop.run_cycle(max_items=self.max_queue_items) or []
        except Exception as exc:
            result["errors"].append(f"EXECUTIVE_QUEUE_FAILED: {type(exc).__name__}")
            return
        result["queue_processed"] = len(processed)
        results: List[Dict[str, Any]] = []
        for item in processed:
            entry: Dict[str, Any] = {
                "item_id": getattr(item, "item_id", None),
                "title": getattr(item, "title", None),
                "status": str(getattr(item, "status", "")),
            }
            outcome = getattr(item, "result", None)
            if outcome is not None:
                entry["execution_status"] = getattr(outcome, "execution_status", None)
                entry["mission_id"] = getattr(outcome, "mission_id", None)
                final = getattr(outcome, "final_outcome", None) or {}
                if "objective_achieved" in final:
                    entry["objective_achieved"] = final.get("objective_achieved")
            error = (getattr(item, "metadata", None) or {}).get("error")
            if error:
                entry["error"] = str(error)[:300]
            results.append(entry)
        result["queue_results"] = results

    def _surface_approvals(self, result: Dict[str, Any]) -> None:
        """Report pending approvals. Never approves them automatically."""
        pending: List[Dict[str, Any]] = []
        loop = getattr(self.engine, "executive_loop", None)
        if loop is not None and hasattr(loop, "get_pending_approvals"):
            try:
                for item in loop.get_pending_approvals():
                    pending.append({
                        "type": "DOA_APPROVAL",
                        "item_id": getattr(item, "item_id", None),
                        "title": getattr(item, "title", None),
                        "cost_estimate_usd": getattr(item, "cost_estimate_usd", None),
                        "status": str(getattr(item, "status", "")),
                    })
            except Exception as exc:
                result["errors"].append(f"APPROVAL_SURFACE_FAILED: {type(exc).__name__}")

        dispatcher = getattr(self.engine, "background_dispatcher", None)
        if dispatcher is not None and hasattr(dispatcher, "list_missions"):
            try:
                for mission in dispatcher.list_missions():
                    if str(getattr(mission, "status", "")) in _HELD_FOR_HUMAN:
                        pending.append({
                            "type": "MISSION_APPROVAL",
                            "mission_id": getattr(mission, "mission_id", None),
                            "status": str(getattr(mission, "status", "")),
                            "current_stage": getattr(mission, "current_stage", None),
                        })
            except Exception as exc:
                result["errors"].append(f"APPROVAL_SURFACE_FAILED: {type(exc).__name__}")

        result["approvals_pending"] = pending
        result["approvals_auto_approved"] = 0

    def _run_patrol(self, result: Dict[str, Any]) -> None:
        if not self.enable_patrol:
            return
        now = time.time()
        last = self._last_patrol_at or 0.0
        if last and (now - last) < self.patrol_interval_sec:
            return

        monitor = getattr(self.engine, "defense_monitor", None)
        if monitor is None:
            try:
                from .defense_monitor import DefensiveCybersecurityMonitor
                monitor = DefensiveCybersecurityMonitor.get_instance()
                try:
                    self.engine.defense_monitor = monitor
                except Exception:
                    pass
            except Exception as exc:
                result["errors"].append(f"PATROL_UNAVAILABLE: {type(exc).__name__}")
                return
        try:
            report = monitor.run_full_defensive_patrol()
        except Exception as exc:
            result["errors"].append(f"PATROL_FAILED: {type(exc).__name__}")
            return

        with self._state_lock:
            self._patrol_runs += 1
            self._last_patrol_at = now
            self._last_patrol_summary = {
                "status": report.get("status"),
                "total_findings": report.get("total_findings"),
                "critical_count": report.get("critical_count"),
                "high_count": report.get("high_count"),
                "medium_count": report.get("medium_count"),
                "timestamp": report.get("timestamp"),
            }
        result["patrol_ran"] = True
        result["patrol"] = self._last_patrol_summary

    # ----------------------------------------------------------------- status
    def _mode(self) -> str:
        if self._running:
            if self._last_killswitch.get("active"):
                return "KILLSWITCH_HOLD"
            if not self._lock_acquired:
                return "STANDBY"
            return "RUNNING"
        if self._last_killswitch.get("active") and self._last_tick_status == "KILLSWITCH_HOLD":
            return "KILLSWITCH_HOLD"
        if not self.enabled and not self._manual_start:
            return "DISABLED"
        if not self._lock_acquired:
            return "STANDBY"
        return "STOPPED"

    def status(self) -> Dict[str, Any]:
        with self._state_lock:
            return {
                "product": self.PRODUCT,
                "engine_kind": self.ENGINE_KIND,
                "mode": self._mode(),
                "enabled_by_default": self.enabled,
                "manual_start": self._manual_start,
                "running": self._running,
                "thread_alive": bool(self._thread and self._thread.is_alive()),
                "tenant_id": self.tenant_id,
                "company_id": self.company_id,
                "pid": os.getpid(),
                "process_lock": {
                    "required": self.acquire_process_lock,
                    "acquired": self._lock_acquired,
                    "path": self._lock_path,
                },
                "schedule": {
                    "tick_interval_sec": self.tick_interval_sec,
                    "patrol_interval_sec": self.patrol_interval_sec,
                    "max_missions_per_tick": self.max_missions_per_tick,
                    "max_queue_items": self.max_queue_items,
                    "mission_cooldown_sec": self.mission_cooldown_sec,
                    "retry_blocked": self.retry_blocked,
                    "patrol_enabled": self.enable_patrol,
                },
                "counters": {
                    "ticks": self._tick_count,
                    "missions_advanced_total": self._missions_advanced_total,
                    "missions_held_total": self._missions_held_total,
                    "queue_processed_total": self._queue_processed_total,
                    "patrol_runs": self._patrol_runs,
                    "consecutive_errors": self._consecutive_errors,
                },
                "last_tick": {
                    "at": self._last_tick_at,
                    "status": self._last_tick_status,
                    "duration_ms": self._last_tick_duration_ms,
                },
                "last_patrol": {
                    "at": self._last_patrol_at,
                    "summary": self._last_patrol_summary,
                },
                "last_killswitch": self._last_killswitch,
                "last_error": self._last_error,
                "started_at": self._started_at,
                "stopped_at": self._stopped_at,
                "governance": {
                    "killswitch": "FAIL_CLOSED",
                    "human_control_missions": "HELD",
                    "approvals": "SURFACED_NOT_AUTO_APPROVED",
                    "autonomy_levels": "NOT_RAISED_BY_SUPERVISOR",
                    "evidence": "ENGINES_WRITE_THEIR_OWN_EVIDENCE",
                },
            }


# ---------------------------------------------------------------------------
# Process-wide registry (one supervisor per tenant/company/engine instance)
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, CoworkerAutonomySupervisor] = {}
_REGISTRY_LOCK = threading.Lock()


def supervisor_key(engine: Any) -> str:
    tenant = getattr(engine, "tenant_id", "tnt_primary")
    company = getattr(engine, "company_id", "comp_primary")
    return f"{tenant}::{company}"


def ensure_supervisor(engine: Any, autostart: Optional[bool] = None) -> CoworkerAutonomySupervisor:
    """Return (creating if needed) the supervisor for this engine instance."""
    key = supervisor_key(engine)
    replaced: Optional[CoworkerAutonomySupervisor] = None
    with _REGISTRY_LOCK:
        supervisor = _REGISTRY.get(key)
        if supervisor is None or supervisor.engine is not engine:
            replaced = supervisor
            supervisor = CoworkerAutonomySupervisor(engine)
            _REGISTRY[key] = supervisor
    if replaced is not None and replaced.is_running():
        try:
            replaced.stop(timeout=2.0)
        except Exception:
            pass
    if autostart is None:
        autostart = supervisor.enabled
    if autostart and not supervisor.is_running():
        supervisor.start(manual=False)
    return supervisor


def get_supervisor(engine: Any) -> Optional[CoworkerAutonomySupervisor]:
    with _REGISTRY_LOCK:
        return _REGISTRY.get(supervisor_key(engine))


def shutdown_all_supervisors(timeout: float = 5.0) -> int:
    """Stops every scheduler in this process. Used on graceful server shutdown."""
    with _REGISTRY_LOCK:
        supervisors = list(_REGISTRY.values())
        _REGISTRY.clear()
    stopped = 0
    for supervisor in supervisors:
        try:
            supervisor.stop(timeout=timeout)
            stopped += 1
        except Exception:
            pass
    return stopped


_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAP_STARTED = False


def bootstrap_tenant_supervisors(limit: Optional[int] = None, delay: float = 3.0) -> int:
    """
    Starts schedulers for companies that already exist in the database.

    Lazy start on first tenant access is enough when a human opens the
    co-worker screen. This bootstrap covers the "nobody opened the page yet"
    case. It runs in a one-shot daemon thread so server startup is not blocked,
    and it is skipped entirely in test mode.
    """
    global _BOOTSTRAP_STARTED
    if not autonomy_enabled_by_default():
        return 0
    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_STARTED:
            return 0
        _BOOTSTRAP_STARTED = True

    if limit is None:
        limit = _env_int("ZONATA_COWORKER_AUTONOMY_BOOTSTRAP_LIMIT", 25, 0)
    if limit <= 0:
        return 0

    def _run() -> None:
        if delay > 0:
            time.sleep(delay)
        try:
            from ..db import db
            from ..tenancy import get_runtime
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT tenant_id, company_id FROM companies "
                    "ORDER BY tenant_id, company_id LIMIT ?",
                    (limit,),
                ).fetchall()
        except Exception:
            return

        for row in rows:
            try:
                tenant_id = row["tenant_id"] if hasattr(row, "keys") else row[0]
                company_id = row["company_id"] if hasattr(row, "keys") else row[1]
                if not tenant_id or not company_id:
                    continue
                runtime = get_runtime(tenant_id, company_id)
                runtime.coworker  # property triggers ensure_supervisor()
            except Exception:
                continue

    threading.Thread(
        target=_run,
        name="CoworkerAutonomyBootstrap",
        daemon=True,
    ).start()
    return 1

