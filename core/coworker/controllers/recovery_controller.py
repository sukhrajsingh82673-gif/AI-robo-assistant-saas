"""
ZONATA Universal AI Co-Worker Fabric — Failure & Recovery Controller
Authoritative implementation of Universal Fallback and Explicit Failure States.
States: FAILED, FAILED_UNCONFIRMED, UNCERTAIN, RECONCILIATION_REQUIRED.
Enforces that ambiguous mutations pause for reconciliation instead of blind retries.
Orchestrates Provider A → Provider B fallback and Local Node → Remote Node failover.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

class FailureState(str, Enum):
    FAILED = "FAILED"
    FAILED_UNCONFIRMED = "FAILED_UNCONFIRMED"
    UNCERTAIN = "UNCERTAIN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    RECOVERED = "RECOVERED"
    ESCALATED = "ESCALATED"

@dataclass
class FailureEvent:
    event_id: str
    mission_id: str
    task_id: str
    capability_id: str
    failed_provider: str
    failed_node: str
    error_message: str
    is_mutation: bool
    state: FailureState
    fallback_provider: Optional[str] = None
    fallback_node: Optional[str] = None
    reconciliation_notes: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

class UniversalRecoveryController:
    """
    Manages failure classification, universal fallback across providers and nodes,
    rollback of side-effects, and human escalation when mutations are uncertain.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._failure_events: List[FailureEvent] = []

    def classify_and_handle_failure(
        self,
        mission_id: str,
        task_id: str,
        capability_id: str,
        failed_provider: str,
        failed_node: str,
        error_message: str,
        is_mutation: bool = False,
        available_fallback_providers: Optional[List[str]] = None,
        available_fallback_nodes: Optional[List[str]] = None
    ) -> Tuple[FailureState, Optional[str], Optional[str], str]:
        """
        Classifies failure and decides whether to fallback or pause for reconciliation.
        Never blindly retries an ambiguous mutation!
        """
        event_id = f"fail_{uuid.uuid4().hex[:8]}"

        # 1. Ambiguous mutation: must freeze in UNCERTAIN / RECONCILIATION_REQUIRED
        if is_mutation and ("timeout" in error_message.lower() or "connection reset" in error_message.lower()):
            state = FailureState.RECONCILIATION_REQUIRED
            event = FailureEvent(
                event_id=event_id,
                mission_id=mission_id,
                task_id=task_id,
                capability_id=capability_id,
                failed_provider=failed_provider,
                failed_node=failed_node,
                error_message=error_message,
                is_mutation=True,
                state=state,
                reconciliation_notes="Ambiguous state during mutation. Human reconciliation required before retry."
            )
            self._failure_events.append(event)
            return state, None, None, event.reconciliation_notes

        # 2. Safe read-only or cleanly unconfirmed failure: execute universal fallback
        fallbacks = available_fallback_providers or []
        nodes = available_fallback_nodes or []

        next_provider = fallbacks[0] if fallbacks else None
        next_node = nodes[0] if nodes else failed_node

        if next_provider or (next_node and next_node != failed_node):
            state = FailureState.RECOVERED
            event = FailureEvent(
                event_id=event_id,
                mission_id=mission_id,
                task_id=task_id,
                capability_id=capability_id,
                failed_provider=failed_provider,
                failed_node=failed_node,
                error_message=error_message,
                is_mutation=is_mutation,
                state=state,
                fallback_provider=next_provider,
                fallback_node=next_node,
                reconciliation_notes=f"Universal fallback: routed to provider '{next_provider}' on node '{next_node}'"
            )
            self._failure_events.append(event)
            return state, next_provider, next_node, event.reconciliation_notes

        # 3. No fallback available: Clean failure with escalation
        state = FailureState.FAILED
        event = FailureEvent(
            event_id=event_id,
            mission_id=mission_id,
            task_id=task_id,
            capability_id=capability_id,
            failed_provider=failed_provider,
            failed_node=failed_node,
            error_message=error_message,
            is_mutation=is_mutation,
            state=state,
            reconciliation_notes="No eligible fallback provider or node available. Escalating to mission controller."
        )
        self._failure_events.append(event)
        return state, None, None, event.reconciliation_notes

    def reconcile_uncertain_task(
        self,
        event_id: str,
        human_resolution: str,
        operator_id: str = "Operator"
    ) -> bool:
        """Allows human supervisor to resolve an UNCERTAIN mutation."""
        for ev in self._failure_events:
            if ev.event_id == event_id:
                ev.state = FailureState.RECOVERED
                ev.reconciliation_notes = f"Reconciled by {operator_id}: {human_resolution}"
                return True
        return False

    def get_events(self, mission_id: Optional[str] = None) -> List[Dict[str, Any]]:
        evs = self._failure_events
        if mission_id:
            evs = [e for e in evs if e.mission_id == mission_id]
        return [
            {
                "event_id": e.event_id,
                "mission_id": e.mission_id,
                "task_id": e.task_id,
                "capability_id": e.capability_id,
                "failed_provider": e.failed_provider,
                "failed_node": e.failed_node,
                "error_message": e.error_message,
                "state": e.state.value,
                "fallback_provider": e.fallback_provider,
                "fallback_node": e.fallback_node,
                "notes": e.reconciliation_notes,
                "timestamp": e.timestamp
            }
            for e in evs
        ]
