"""
OpenFeature Compliant Feature Flag Provider (ADR 0052, Rules 80, 84).
Provides safe defaults (OFF by default), evaluation contexts, fast kill-switches,
and an immutable in-memory audit trail.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class EvaluationContext:
    targeting_key: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlagAuditRecord:
    timestamp: float
    flag_key: str
    action: str
    details: Dict[str, Any]
    operator_id: str


class OpenFeatureProvider:
    """
    In-process OpenFeature Provider implementation with tenant-level overrides,
    kill-switches, and audit logging.
    """

    def __init__(self):
        # flag_key -> bool (global default)
        self._flags: Dict[str, bool] = {}
        # (flag_key, tenant_id) -> bool
        self._tenant_flags: Dict[Tuple[str, str], bool] = {}
        # flag_key -> reason
        self._kill_switches: Dict[str, str] = {}
        # audit log
        self._audit_log: List[FlagAuditRecord] = []

    def set_global_flag(self, flag_key: str, enabled: bool, operator_id: str = "system"):
        self._flags[flag_key] = enabled
        self._audit_log.append(
            FlagAuditRecord(
                timestamp=time.time(),
                flag_key=flag_key,
                action="SET_GLOBAL",
                details={"enabled": enabled},
                operator_id=operator_id,
            )
        )

    def set_tenant_flag(self, flag_key: str, tenant_id: str, enabled: bool, operator_id: str = "admin"):
        self._tenant_flags[(flag_key, tenant_id)] = enabled
        self._audit_log.append(
            FlagAuditRecord(
                timestamp=time.time(),
                flag_key=flag_key,
                action="SET_TENANT",
                details={"tenant_id": tenant_id, "enabled": enabled},
                operator_id=operator_id,
            )
        )

    def engage_kill_switch(self, flag_key: str, reason: str, operator_id: str):
        """Immediately disables flag globally, superseding all tenant overrides."""
        self._kill_switches[flag_key] = reason
        self._audit_log.append(
            FlagAuditRecord(
                timestamp=time.time(),
                flag_key=flag_key,
                action="ENGAGE_KILL_SWITCH",
                details={"reason": reason},
                operator_id=operator_id,
            )
        )

    def disengage_kill_switch(self, flag_key: str, operator_id: str):
        self._kill_switches.pop(flag_key, None)
        self._audit_log.append(
            FlagAuditRecord(
                timestamp=time.time(),
                flag_key=flag_key,
                action="DISENGAGE_KILL_SWITCH",
                details={},
                operator_id=operator_id,
            )
        )

    def is_kill_switched(self, flag_key: str) -> Tuple[bool, Optional[str]]:
        if flag_key in self._kill_switches:
            return True, self._kill_switches[flag_key]
        return False, None

    def get_boolean_value(
        self, flag_key: str, default_value: bool = False, context: Optional[EvaluationContext] = None
    ) -> bool:
        """
        Evaluate boolean flag.
        1. If kill-switched: always returns False.
        2. If tenant override exists for context targeting_key: return override.
        3. If global flag configured: return global value.
        4. Otherwise: return default_value (defaults to False per Safe Defaults rule).
        """
        if flag_key in self._kill_switches:
            return False

        if context and context.targeting_key:
            tenant_key = (flag_key, context.targeting_key)
            if tenant_key in self._tenant_flags:
                return self._tenant_flags[tenant_key]

        return self._flags.get(flag_key, default_value)

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": r.timestamp,
                "flag_key": r.flag_key,
                "action": r.action,
                "details": r.details,
                "operator_id": r.operator_id,
            }
            for r in self._audit_log
        ]
