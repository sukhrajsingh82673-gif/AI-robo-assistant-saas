"""
ZONATA Evolution Safety Services & Tripwires (Sub-Step 6J).

Features:
- Global & Per-Company Evolution Kill Switch (Rule 50, Rule 51).
- Security Tripwires: AI attempts to write protected paths instantly trigger incidents
  and suspend evolution.
- Frozen Eval Drift Monitor: tracks semantic safety and task regression against benchmarks.
- Owner-Facing Evolution Journal: immutable audit log and weekly digest of all evolved components.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set

from core.db import db


class KillSwitchStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class EvolutionSuspendedError(Exception):
    """Raised when evolution operations are attempted while a kill switch is active."""
    pass


class TripwireBreachError(Exception):
    """Raised when an actor breaches a protected path tripwire."""
    pass


class EvaluationDriftDetectedError(Exception):
    """Raised when performance or safety metrics regress on frozen held-out evaluation sets."""
    pass


class EvolutionSafetyEngine:
    """Manages kill switches and permissions for self-improvement operations."""

    def __init__(self):
        self._global_kill_switch: bool = False
        self._company_kill_switches: Dict[str, bool] = {}
        self._incident_log: List[Dict[str, Any]] = []
        self._persistent = os.environ.get("ZONATA_TEST_MODE") != "1"
        if self._persistent:
            self._init_db()
            self._load_state()

    def _init_db(self) -> None:
        with db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_kill_switches (
                    scope TEXT PRIMARY KEY,
                    active INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_incident_log (
                    event_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    activated_by TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_state(self) -> None:
        with db.get_connection() as conn:
            for scope, active in conn.execute(
                "SELECT scope, active FROM evolution_kill_switches"
            ).fetchall():
                if scope == "GLOBAL":
                    self._global_kill_switch = bool(active)
                else:
                    self._company_kill_switches[scope] = bool(active)
            for row in conn.execute(
                "SELECT event_id, scope, activated_by, reason, timestamp "
                "FROM evolution_incident_log ORDER BY timestamp"
            ).fetchall():
                self._incident_log.append({
                    "event_id": row[0],
                    "scope": row[1],
                    "activated_by": row[2],
                    "reason": row[3],
                    "timestamp": row[4],
                })

    def _persist_scope(self, scope: str, active: bool) -> None:
        if not self._persistent:
            return
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO evolution_kill_switches (scope, active, updated_at) "
                "VALUES (?, ?, ?) ON CONFLICT(scope) DO UPDATE SET "
                "active = excluded.active, updated_at = excluded.updated_at",
                (scope, 1 if active else 0, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def _persist_incident(self, record: Dict[str, Any]) -> None:
        if not self._persistent:
            return
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO evolution_incident_log "
                "(event_id, scope, activated_by, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    record["event_id"],
                    record["scope"],
                    record["activated_by"],
                    record["reason"],
                    record["timestamp"],
                ),
            )
            conn.commit()

    def is_evolution_enabled(self, company_id: Optional[str] = None) -> bool:
        if self._global_kill_switch:
            return False
        if company_id and self._company_kill_switches.get(company_id, False):
            return False
        return True

    def activate_kill_switch(
        self,
        scope: str = "GLOBAL",
        actor_principal: str = "human:system_admin",
        reason: str = "Emergency suspension",
    ) -> Dict[str, Any]:
        """Activates global or per-company kill switch."""
        record = {
            "event_id": f"kill_{uuid.uuid4().hex[:8]}",
            "scope": scope,
            "activated_by": actor_principal,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        persisted_scope = "GLOBAL" if scope.upper() == "GLOBAL" else scope
        if persisted_scope == "GLOBAL":
            self._global_kill_switch = True
        else:
            self._company_kill_switches[persisted_scope] = True

        self._persist_scope(persisted_scope, True)
        self._persist_incident(record)
        self._incident_log.append(record)
        return record

    def deactivate_kill_switch(
        self,
        scope: str = "GLOBAL",
        actor_principal: str = "owner:root",
    ) -> None:
        """Deactivates kill switch (requires owner principal)."""
        from core.evolution.principal import is_owner_principal

        if not is_owner_principal(actor_principal):
            raise PermissionError("Only an authenticated repository owner can deactivate the evolution kill switch.")
        persisted_scope = "GLOBAL" if scope.upper() == "GLOBAL" else scope
        if persisted_scope == "GLOBAL":
            self._global_kill_switch = False
        elif persisted_scope in self._company_kill_switches:
            self._company_kill_switches[persisted_scope] = False
        self._persist_scope(persisted_scope, False)

    def check_evolution_permitted(self, company_id: Optional[str] = None) -> None:
        if not self.is_evolution_enabled(company_id):
            raise EvolutionSuspendedError(
                f"Evolution is currently suspended by kill switch (Scope: {'GLOBAL' if self._global_kill_switch else company_id})."
            )


class TripwireManager:
    """Detects and reacts to unauthorized AI principal writes on protected paths."""

    PROTECTED_PATTERNS = [
        "security/protected_paths.yaml",
        "CODEOWNERS",
        ".github/workflows/",
        "core/ledger/",
        "eval/ground_truth/",
    ]

    def __init__(self, safety_engine: EvolutionSafetyEngine):
        self.safety_engine = safety_engine
        self.tripped_events: List[Dict[str, Any]] = []

    def check_write_attempt(
        self,
        target_path: str,
        actor_principal: str,
        company_id: str,
    ) -> None:
        """Checks if a write attempt hits a protected tripwire."""
        for pattern in self.PROTECTED_PATTERNS:
            if pattern in target_path:
                event = {
                    "event_id": f"trip_{uuid.uuid4().hex[:8]}",
                    "target_path": target_path,
                    "actor_principal": actor_principal,
                    "company_id": company_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action_taken": "SUSPEND_COMPANY_EVOLUTION_AND_EMIT_ALERT",
                }
                self.tripped_events.append(event)
                # Instantly suspend evolution for the company
                self.safety_engine.activate_kill_switch(
                    scope=company_id,
                    actor_principal="system:tripwire_monitor",
                    reason=f"Tripwire breach on protected path: {target_path}",
                )
                raise TripwireBreachError(
                    f"Tripwire Breach: AI principal '{actor_principal}' attempted to write protected path '{target_path}'. "
                    f"Evolution suspended for company '{company_id}'."
                )


class EvalDriftMonitor:
    """Monitors held-out evaluation performance and flags drift/regression."""

    @classmethod
    def evaluate_drift(
        cls,
        baseline_metrics: Dict[str, float],
        candidate_metrics: Dict[str, float],
        max_regression_tolerance: float = 0.05,
    ) -> Dict[str, Any]:
        regressions = []
        missing = set(baseline_metrics) - set(candidate_metrics)
        if missing:
            raise EvaluationDriftDetectedError(
                f"Candidate did not report required frozen metrics: {sorted(missing)}. "
                "Missing metrics fail closed under Rule 52."
            )

        # Rule 52 Safety semantic floor: safety cannot drop at all
        base_safety = baseline_metrics.get("safety_pass_rate", 1.0)
        cand_safety = candidate_metrics.get("safety_pass_rate", 1.0)
        if cand_safety < base_safety:
            raise EvaluationDriftDetectedError(
                f"Safety floor breached: baseline {base_safety:.2f} -> candidate {cand_safety:.2f}."
            )

        for metric, base_val in baseline_metrics.items():
            if metric == "safety_pass_rate":
                continue
            cand_val = candidate_metrics[metric]
            delta = cand_val - base_val
            if delta < -max_regression_tolerance:
                regressions.append({"metric": metric, "delta": delta, "baseline": base_val, "candidate": cand_val})

        if regressions:
            raise EvaluationDriftDetectedError(
                f"Evaluation drift detected beyond tolerance ({max_regression_tolerance:.1%}): {regressions}"
            )

        return {"drift_detected": False, "status": "WITHIN_TOLERANCE"}


class EvolutionJournal:
    """Immutable log of evolved components for owner weekly reviews."""

    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        self._persistent = os.environ.get("ZONATA_TEST_MODE") != "1"
        if self._persistent:
            self._init_db()
            self._load_entries()

    def _init_db(self) -> None:
        with db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_journal (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    change_class TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    measured_effect_json TEXT NOT NULL,
                    rollback_id TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_entries(self) -> None:
        with db.get_connection() as conn:
            for row in conn.execute(
                "SELECT entry_id, timestamp, company_id, change_class, target_name, "
                "rationale, measured_effect_json, rollback_id "
                "FROM evolution_journal ORDER BY timestamp"
            ).fetchall():
                self._entries.append({
                    "entry_id": row[0],
                    "timestamp": row[1],
                    "company_id": row[2],
                    "change_class": row[3],
                    "target_name": row[4],
                    "rationale": row[5],
                    "measured_effect": json.loads(row[6]),
                    "rollback_id": row[7],
                })

    def _persist_entry(self, entry: Dict[str, Any]) -> None:
        if not self._persistent:
            return
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO evolution_journal (entry_id, timestamp, company_id, "
                "change_class, target_name, rationale, measured_effect_json, rollback_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["entry_id"],
                    entry["timestamp"],
                    entry["company_id"],
                    entry["change_class"],
                    entry["target_name"],
                    entry["rationale"],
                    json.dumps(entry["measured_effect"], sort_keys=True),
                    entry["rollback_id"],
                ),
            )
            conn.commit()

    def record_evolution(
        self,
        change_class: str,
        target_name: str,
        rationale: str,
        measured_effect: Dict[str, Any],
        rollback_id: str,
        company_id: str,
    ) -> Dict[str, Any]:
        entry = {
            "entry_id": f"jrn_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "company_id": company_id,
            "change_class": change_class,
            "target_name": target_name,
            "rationale": rationale,
            "measured_effect": measured_effect,
            "rollback_id": rollback_id,
        }
        self._persist_entry(entry)
        self._entries.append(entry)
        return entry

    def generate_weekly_digest(self, company_id: str) -> str:
        entries = [e for e in self._entries if e["company_id"] == company_id]
        digest = f"# Weekly Evolution Journal (Company: {company_id})\n"
        digest += f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        if not entries:
            digest += "No autonomous changes made during this period.\n"
            return digest

        for idx, e in enumerate(entries, 1):
            digest += f"### {idx}. [{e['change_class']}] {e['target_name']}\n"
            digest += f"- **Rationale:** {e['rationale']}\n"
            digest += f"- **Measured Effect:** {e['measured_effect']}\n"
            digest += f"- **Rollback Reference:** `{e['rollback_id']}`\n\n"
        return digest
