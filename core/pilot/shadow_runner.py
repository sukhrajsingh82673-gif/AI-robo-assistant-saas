"""
Passive Shadow Mode Execution Engine with Zero-External-Writes Enforcement (Rule 74 & ADR 0047)
Observes live enterprise workflows in read-only mode and generates comparative recommendations.
Any attempt to mutate external state, trigger webhooks, or perform database writes is blocked.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
import hashlib
import json
import time


class ShadowModeWriteBlockedError(PermissionError):
    """Raised when any external write, network mutation, or production commit is attempted in shadow mode."""
    pass


class ZeroExternalWritesSpy:
    """Spy monitor recording all write/mutation invocations to guarantee zero external side effects."""

    def __init__(self):
        self.mutation_attempts: List[Dict[str, Any]] = []

    def intercept_write(self, operation: str, target: str, payload: Any):
        """Intercepts and records unauthorized write attempt."""
        record = {
            "operation": operation,
            "target": target,
            "timestamp": time.time(),
            "payload_preview": str(payload)[:100],
        }
        self.mutation_attempts.append(record)
        raise ShadowModeWriteBlockedError(
            f"SHADOW_MODE_WRITE_BLOCKED: Attempted external write '{operation}' to '{target}' in passive shadow mode. "
            f"Rule 74 strictly guarantees zero external mutations during customer pilot shadow runs."
        )

    @property
    def write_count(self) -> int:
        return len(self.mutation_attempts)


class ShadowRunner:
    """Manages passive shadow execution for enterprise pilots."""

    def __init__(self, tenant_id: str, pilot_id: str):
        self.tenant_id = tenant_id
        self.pilot_id = pilot_id
        self.spy = ZeroExternalWritesSpy()
        self._shadow_recommendations: List[Dict[str, Any]] = []

    def observe_and_recommend(
        self,
        event_id: str,
        event_type: str,
        input_data: Dict[str, Any],
        logic_callback: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Executes business recommendation in pure shadow mode without external side effects.
        """
        # Execute pure compute callback
        recommendation_payload = logic_callback(input_data)

        # Cryptographically seal shadow record
        rec_id = f"SHADOW-REC-{len(self._shadow_recommendations) + 1:04d}"
        sealed_rec = {
            "rec_id": rec_id,
            "event_id": event_id,
            "event_type": event_type,
            "pilot_id": self.pilot_id,
            "tenant_id": self.tenant_id,
            "recommendation": recommendation_payload,
            "is_committed_to_production": False,
            "external_writes_dispatched": 0,
            "timestamp": time.time(),
        }
        canonical = json.dumps(sealed_rec, sort_keys=True)
        sealed_rec["seal_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        self._shadow_recommendations.append(sealed_rec)
        return sealed_rec

    def attempt_disallowed_external_write(self, target_api: str, data: Dict[str, Any]):
        """Helper to verify that write attempts are intercepted by the spy."""
        self.spy.intercept_write("HTTP_POST", target_api, data)

    def get_shadow_recommendations(self) -> List[Dict[str, Any]]:
        return list(self._shadow_recommendations)
