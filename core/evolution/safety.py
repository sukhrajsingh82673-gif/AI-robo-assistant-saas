"""
ZONATA Evolution Safety Services & Tripwires (Sub-Step 6J).

Features:
- Global & Per-Company Evolution Kill Switch (Rule 50, Rule 51).
- Security Tripwires: AI attempts to write protected paths instantly trigger incidents
  and suspend evolution.
- Frozen Eval Drift Monitor: tracks semantic safety and task regression against benchmarks.
- Owner-Facing Evolution Journal: immutable audit log and weekly digest of all evolved components.
"""

import uuid
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set


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
        if scope.upper() == "GLOBAL":
            self._global_kill_switch = True
        else:
            self._company_kill_switches[scope] = True

        self._incident_log.append(record)
        return record

    def deactivate_kill_switch(
        self,
        scope: str = "GLOBAL",
        actor_principal: str = "owner:root",
    ) -> None:
        """Deactivates kill switch (requires owner principal)."""
        if not actor_principal.startswith("owner:"):
            raise PermissionError("Only repository owner can deactivate the evolution kill switch.")
        if scope.upper() == "GLOBAL":
            self._global_kill_switch = False
        elif scope in self._company_kill_switches:
            self._company_kill_switches[scope] = False

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
            cand_val = candidate_metrics.get(metric, base_val)
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
