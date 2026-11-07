"""
ZONATA Autonomous Coworker 3.0 — Executive Authority & Employee Escalation Router
Provides a governed resolution pipeline for blocked enterprise employees and agents:
  1. Escalation intake with root-cause diagnostic classification.
  2. Subordinate specialist delegation matching the blocker domain.
  3. Verified resolution return preserving original employee ownership and task history.
  4. Unified Communication Bus with correlation IDs connecting AI CEO, Coworker, employees, and remote nodes.
"""

from __future__ import annotations
import os
import time
import json
import uuid
import hashlib
from typing import Callable, Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .contracts_v3 import EscalationStatus, EscalationTicket


# =============================================================================
# 1. UNIFIED CORRELATION-ID AGENT COMMUNICATION BUS
# =============================================================================

@dataclass
class AgentBusMessage:
    message_id: str
    correlation_id: str
    sender_id: str
    recipient_id: str
    priority: str # "CRITICAL", "HIGH", "NORMAL", "BACKGROUND"
    message_type: str # "ASSIGNMENT", "ESCALATION", "RESOLUTION", "TELEMETRY", "ALERT"
    payload: Dict[str, Any]
    parent_message_id: Optional[str] = None
    signature_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def compute_signature(self) -> str:
        blob = f"{self.message_id}:{self.correlation_id}:{self.sender_id}:{self.recipient_id}:{self.message_type}"
        self.signature_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return self.signature_hash


class AgentCommunicationBus:
    """
    Unified Message Router across AI CEO, Coworker 3.0, Employees, and Remote Nodes.
    Preserves end-to-end trace correlation and causal message lineage.
    """

    def __init__(self):
        self._messages: List[AgentBusMessage] = []
        self._subscribers: Dict[str, List[Any]] = {} # recipient_id -> callbacks

    def publish(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: str = "NORMAL",
        parent_message_id: Optional[str] = None
    ) -> AgentBusMessage:
        """Publishes a verified message envelope onto the bus."""
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        corr_id = correlation_id or f"corr_{uuid.uuid4().hex[:8]}"
        msg = AgentBusMessage(
            message_id=msg_id,
            correlation_id=corr_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            priority=priority,
            message_type=message_type,
            payload=payload,
            parent_message_id=parent_message_id
        )
        msg.compute_signature()
        self._messages.append(msg)

        # Notify direct subscribers if registered
        callbacks = self._subscribers.get(recipient_id, [])
        for cb in callbacks:
            try:
                cb(msg)
            except Exception:
                pass

        return msg

    def get_correlation_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Returns the full causal history for a correlation ID."""
        return [
            {
                "message_id": m.message_id,
                "sender": m.sender_id,
                "recipient": m.recipient_id,
                "type": m.message_type,
                "priority": m.priority,
                "payload": m.payload,
                "timestamp": m.timestamp,
                "signature": m.signature_hash
            }
            for m in self._messages
            if m.correlation_id == correlation_id
        ]


# =============================================================================
# 2. EXECUTIVE ESCALATION ROUTER
# =============================================================================

class ExecutiveEscalationRouter:
    """
    Manages task escalations when corporate employees or subordinate agents become blocked.
    Performs diagnostic triage, assigns appropriate specialists, executes resolution,
    and returns verified deliverables to the original employee.
    """

    def __init__(self, bus: Optional[AgentCommunicationBus] = None):
        self.bus = bus or AgentCommunicationBus()
        self.tickets: Dict[str, EscalationTicket] = {}

    def submit_escalation(
        self,
        employee_id: str,
        task_id: str,
        error_context: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> EscalationTicket:
        """Intake for an employee blocker."""
        ticket_id = f"esc_{uuid.uuid4().hex[:8]}"
        ticket = EscalationTicket(
            ticket_id=ticket_id,
            source_employee_id=employee_id,
            task_id=task_id,
            failure_context=error_context,
            status=EscalationStatus.PENDING
        )
        self.tickets[ticket_id] = ticket

        # Broadcast escalation event on the communication bus
        self.bus.publish(
            sender_id=employee_id,
            recipient_id="coworker_3.0_lead",
            message_type="ESCALATION",
            payload={"ticket_id": ticket_id, "task_id": task_id, "error": error_context},
            correlation_id=correlation_id,
            priority="HIGH"
        )
        return ticket

    def diagnose_blocker(self, ticket: EscalationTicket) -> Tuple[str, str]:
        """
        Triage: keyword-based classification of the failure context and selection
        of a specialist archetype. This is a heuristic routing decision, not a
        verified root-cause analysis.
        """
        ticket.status = EscalationStatus.DIAGNOSING
        ctx = ticket.failure_context
        error_msg = str(ctx.get("error", "")).lower()

        if "modulenotfound" in error_msg or "import" in error_msg or "dependency" in error_msg:
            diagnosis = "Missing software package or Python dependency."
            archetype = "Software Installation Specialist"
        elif "syntaxerror" in error_msg or "indentationerror" in error_msg:
            diagnosis = "Code syntax defect or invalid indentation."
            archetype = "Python Dev Specialist"
        elif "permission" in error_msg or "access denied" in error_msg or "chmod" in error_msg:
            diagnosis = "Filesystem permission restriction."
            archetype = "Linux Admin Specialist"
        elif "test" in error_msg or "assertion" in error_msg or "pytest" in error_msg:
            diagnosis = "Test suite regression or broken assertion."
            archetype = "Testing Specialist"
        else:
            diagnosis = "General runtime exception or unhandled state."
            archetype = "Diagnostics Specialist"

        ticket.diagnosis = diagnosis
        ticket.specialist_archetype = archetype
        ticket.assigned_specialist_id = f"spec_{uuid.uuid4().hex[:6]}"
        return diagnosis, archetype

    def resolve_and_return(
        self,
        ticket: EscalationTicket,
        resolution_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        verification_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> EscalationTicket:
        """
        Returns a resolution to the original employee.

        `verified` is only true when `verification_fn` independently confirms the
        resolution. A caller-supplied boolean inside `resolution_data` is not
        treated as verification.
        """
        verified = False
        notes = "NO_VERIFICATION_FUNCTION"
        if verification_fn is not None:
            try:
                verified = bool(verification_fn(resolution_data))
                notes = "INDEPENDENTLY_VERIFIED" if verified else "VERIFICATION_FAILED"
            except Exception as exc:
                verified = False
                notes = f"VERIFICATION_ERROR: {exc}"

        ticket.status = EscalationStatus.RESOLVED
        ticket.verified = verified
        ticket.verification_notes = notes
        ticket.resolution_artifact = json.dumps(resolution_data)
        ticket.resolved_at = time.time()
        ticket.compute_evidence_hash()

        # Send resolution back to employee via communication bus
        self.bus.publish(
            sender_id="coworker_3.0_lead",
            recipient_id=ticket.source_employee_id,
            message_type="RESOLUTION",
            payload={
                "ticket_id": ticket.ticket_id,
                "task_id": ticket.task_id,
                "resolution": resolution_data,
                "verified": verified,
                "verification_notes": notes,
                "evidence_hash": ticket.evidence_hash,
                "diagnosis": ticket.diagnosis
            },
            correlation_id=correlation_id,
            priority="NORMAL"
        )

        ticket.status = EscalationStatus.RETURNED_TO_EMPLOYEE
        return ticket

    def get_escalation_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "ticket_id": t.ticket_id,
                "employee_id": t.source_employee_id,
                "task_id": t.task_id,
                "diagnosis": t.diagnosis,
                "specialist": t.specialist_archetype,
                "verified": t.verified,
                "verification_notes": t.verification_notes,
                "status": t.status.value,
                "evidence_hash": t.evidence_hash,
                "created_at": t.created_at,
                "resolved_at": t.resolved_at
            }
            for t in self.tickets.values()
        ]
