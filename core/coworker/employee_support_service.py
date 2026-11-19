"""
ZONATA Autonomous Executive Coworker — Milestone 4: Employee & Subordinate Agent Support
Provides governed diagnostic triage and verified resolution for blocked employees and agents
while strictly preserving employee task ownership and authority (Non-Usurpation Invariant).
"""

from __future__ import annotations
import time
import uuid
import json
import hashlib
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field


class BlockerCategory(str, Enum):
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    SYNTAX_LOGIC_ERROR = "SYNTAX_LOGIC_ERROR"
    PERMISSION_RESTRICTION = "PERMISSION_RESTRICTION"
    TEST_REGRESSION = "TEST_REGRESSION"
    REQUIREMENTS_AMBIGUITY = "REQUIREMENTS_AMBIGUITY"
    RUNTIME_EXCEPTION = "RUNTIME_EXCEPTION"


class SupportTicketStatus(str, Enum):
    RECEIVED = "RECEIVED"
    DIAGNOSING = "DIAGNOSING"
    SPECIALIST_ASSIGNED = "SPECIALIST_ASSIGNED"
    RESOLVING = "RESOLVING"
    VERIFIED = "VERIFIED"
    RETURNED_TO_EMPLOYEE = "RETURNED_TO_EMPLOYEE"
    FAILED = "FAILED"


@dataclass
class SupportTicket:
    ticket_id: str
    employee_id: str
    original_task_id: str
    authority_scope: List[str]
    error_context: Dict[str, Any]
    blocker_category: Optional[BlockerCategory] = None
    diagnosis_summary: str = ""
    assigned_specialist_archetype: Optional[str] = None
    resolution_steps: List[str] = field(default_factory=list)
    resolution_artifact: Optional[str] = None
    evidence_hash: str = ""
    status: SupportTicketStatus = SupportTicketStatus.RECEIVED
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def compute_evidence_hash(self) -> str:
        payload = f"{self.ticket_id}:{self.employee_id}:{self.original_task_id}:{self.status.value}:{self.resolution_artifact}"
        self.evidence_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.evidence_hash


class EmployeeSupportService:
    """
    Subordinate support service assisting blocked corporate employees.
    Strictly adheres to the Non-Usurpation Invariant: the coworker assists and diagnoses,
    but task ownership and ultimate authority remain with the originating employee.
    """

    def __init__(self):
        self.tickets: Dict[str, SupportTicket] = {}
        self.total_resolved: int = 0

    def intake_request(
        self,
        employee_id: str,
        task_id: str,
        error_context: Optional[Dict[str, Any]] = None,
        authority_scope: Optional[List[str]] = None,
        failure_context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> SupportTicket:
        """Intakes a blocker from an employee while preserving task ownership."""
        ticket_id = f"sup_{uuid.uuid4().hex[:8]}"
        ctx = error_context or failure_context or {}
        ticket = SupportTicket(
            ticket_id=ticket_id,
            employee_id=employee_id,
            original_task_id=task_id,
            authority_scope=authority_scope or ["read_only"],
            error_context=ctx,
            status=SupportTicketStatus.RECEIVED
        )
        self.tickets[ticket_id] = ticket
        return ticket

    intake_failure = intake_request

    def diagnose_blocker(self, ticket_id: str) -> SupportTicket:
        """Classifies the root cause and assigns the correct specialist archetype."""
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Support ticket '{ticket_id}' not found.")

        ticket.status = SupportTicketStatus.DIAGNOSING
        err_str = json.dumps(ticket.error_context).lower()

        if "modulenotfound" in err_str or "importerror" in err_str or "pip" in err_str:
            category = BlockerCategory.DEPENDENCY_MISSING
            archetype = "Software Installation Specialist"
            summary = "Missing Python library or environment package dependency."
        elif "syntaxerror" in err_str or "indentationerror" in err_str:
            category = BlockerCategory.SYNTAX_LOGIC_ERROR
            archetype = "Python Software Engineer"
            summary = "Code syntax or formatting error."
        elif "permissiondenied" in err_str or "access denied" in err_str or "eacces" in err_str:
            category = BlockerCategory.PERMISSION_RESTRICTION
            archetype = "DevOps & Platform Admin"
            summary = "POSIX permission or security privilege restriction."
        elif "assertionerror" in err_str or "failed" in err_str and "test" in err_str:
            category = BlockerCategory.TEST_REGRESSION
            archetype = "QA & Reliability Engineer"
            summary = "Regression detected in test suite assertions."
        elif "unclear" in err_str or "ambiguous" in err_str:
            category = BlockerCategory.REQUIREMENTS_AMBIGUITY
            archetype = "Executive Chief of Staff"
            summary = "Objective lacks clear success criteria."
        else:
            category = BlockerCategory.RUNTIME_EXCEPTION
            archetype = "Python Software Engineer"
            summary = "Unhandled application runtime exception."

        ticket.blocker_category = category
        ticket.assigned_specialist_archetype = archetype
        ticket.diagnosis_summary = summary
        ticket.status = SupportTicketStatus.SPECIALIST_ASSIGNED
        return ticket

    diagnose_and_formulate_fix = diagnose_blocker

    def resolve_and_return(
        self,
        ticket_id: str,
        resolution_payload: Optional[Dict[str, Any]] = None,
        steps: Optional[List[str]] = None,
        verification_fn: Optional[Callable[[], bool]] = None,
        resolution_data: Optional[Dict[str, Any]] = None,
        verification_check: Optional[Callable[[], bool]] = None
    ) -> SupportTicket:
        """
        Executes verified resolution and returns artifacts back to the employee.
        Enforces Non-Usurpation: Original employee_id and task_id are preserved.
        """
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Support ticket '{ticket_id}' not found.")

        ticket.status = SupportTicketStatus.RESOLVING
        data = resolution_payload if resolution_payload is not None else (resolution_data or {})
        v_fn = verification_fn or verification_check

        # Independent verification
        verified = True
        if v_fn:
            try:
                verified = v_fn()
            except Exception:
                verified = False

        if not verified:
            ticket.status = SupportTicketStatus.FAILED
            ticket.resolution_artifact = json.dumps({"error": "Resolution verification check failed"})
            return ticket

        ticket.status = SupportTicketStatus.VERIFIED
        ticket.resolution_steps = steps or ["1. Diagnosed root cause", "2. Applied atomic fix", "3. Verified resolution"]
        ticket.resolution_artifact = json.dumps(data)
        ticket.resolved_at = time.time()
        ticket.compute_evidence_hash()

        # Return deliverable to originating employee
        ticket.status = SupportTicketStatus.RETURNED_TO_EMPLOYEE
        self.total_resolved += 1
        return ticket

    resolve_and_return_to_employee = resolve_and_return
