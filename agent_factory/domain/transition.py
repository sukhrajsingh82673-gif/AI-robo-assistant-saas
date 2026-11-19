"""
ZONATA Agent Factory — Evidence-Before-Effect Transition Engine
Guarantees:
  1. All state mutations pass through transition()
  2. Allowed transitions enforced against explicit state transition table
  3. KillSwitch checked before mutation
  4. AuthorityGateway evaluated before mutation
  5. Evidence append occurs BEFORE database mutation (fail-closed)
  6. Every af_lifecycle_event has NOT NULL evidence_ledger_id
"""

from __future__ import annotations
import time
import json
import uuid
import hashlib
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from agent_factory.ports import Principal, Resource, EvidenceEvent, Decision


class InvalidTransitionError(Exception):
    """Raised when a state transition violates the state machine."""
    pass


class TransitionForbiddenError(Exception):
    """Raised when authority denies the state transition."""
    pass


ALLOWED_TRANSITIONS: Dict[str, Dict[str, Set[str]]] = {
    "request": {
        "REQUESTED": {"ANALYSING", "REJECTED", "CANCELLED", "KILLED"},
        "ANALYSING": {"CLARIFYING", "DESIGNING", "FAILED", "CANCELLED", "KILLED"},
        "CLARIFYING": {"ANALYSING", "FAILED", "CANCELLED"},
        "DESIGNING": {"AWAITING_DESIGN_APPROVAL", "BUILDING", "FAILED", "CANCELLED"},
        "AWAITING_DESIGN_APPROVAL": {"BUILDING", "REJECTED", "CANCELLED"},
        "BUILDING": {"QA", "FAILED", "CANCELLED", "KILLED"},
        "QA": {"CERTIFYING", "FAILED", "CANCELLED"},
        "CERTIFYING": {"AWAITING_RELEASE_APPROVAL", "PUBLISHING", "FAILED", "CANCELLED"},
        "AWAITING_RELEASE_APPROVAL": {"PUBLISHING", "REJECTED", "CANCELLED"},
        "PUBLISHING": {"PROVISIONED", "PARTIAL", "FAILED"},
        "PARTIAL": {"PROVISIONED", "FAILED"},
        "PROVISIONED": set(),
        "REJECTED": set(),
        "FAILED": set(),
        "CANCELLED": set(),
        "KILLED": set()
    },
    "batch": {
        "PLANNED": {"BUILDING", "CANCELLED", "KILLED"},
        "BUILDING": {"TEAM_QA", "FAILED", "PARTIAL", "CANCELLED", "KILLED"},
        "TEAM_QA": {"CERTIFIED", "FAILED", "CANCELLED"},
        "CERTIFIED": {"AWAITING_RELEASE_APPROVAL", "RELEASED", "CANCELLED"},
        "AWAITING_RELEASE_APPROVAL": {"RELEASED", "CANCELLED", "FAILED"},
        "RELEASED": set(),
        "PARTIAL": {"RELEASED", "FAILED"},
        "FAILED": set(),
        "CANCELLED": set(),
        "KILLED": set()
    },
    "batch_item": {
        "PENDING": {"BLOCKED", "READY", "SKIPPED", "KILLED"},
        "BLOCKED": {"READY", "SKIPPED", "KILLED"},
        "READY": {"BUILDING", "SKIPPED", "KILLED"},
        "BUILDING": {"BUILT", "FAILED", "KILLED"},
        "BUILT": {"UNIT_TESTED", "FAILED"},
        "UNIT_TESTED": {"QA_PASSED", "FAILED"},
        "QA_PASSED": {"CERTIFIED", "FAILED"},
        "CERTIFIED": set(),
        "SKIPPED": set(),
        "FAILED": {"READY", "SKIPPED"},  # retryable
        "KILLED": set()
    },
    "agent": {
        "DRAFT": {"BUILT", "DEPRECATED", "RETIRED"},
        "BUILT": {"CERTIFIED", "DEPRECATED", "RETIRED"},
        "CERTIFIED": {"APPROVED", "DEPRECATED", "RETIRED"},
        "APPROVED": {"PUBLISHED", "DEPRECATED", "RETIRED"},
        "PUBLISHED": {"ACTIVE", "SUSPENDED", "DEPRECATED", "RETIRED"},
        "ACTIVE": {"SUSPENDED", "DEPRECATED", "RETIRED"},
        "SUSPENDED": {"ACTIVE", "RETIRED", "DEPRECATED"},
        "DEPRECATED": {"RETIRED"},
        "RETIRED": set()
    },
    "agent_version": {
        "BUILDING": {"BUILT", "FAILED_QA", "WITHDRAWN"},
        "BUILT": {"CERTIFIED", "FAILED_QA", "WITHDRAWN"},
        "FAILED_QA": {"BUILDING", "WITHDRAWN"},
        "CERTIFIED": {"APPROVED", "WITHDRAWN"},
        "APPROVED": {"PUBLISHED", "SUPERSEDED", "WITHDRAWN"},
        "PUBLISHED": {"SUPERSEDED", "ROLLED_BACK", "WITHDRAWN"},
        "SUPERSEDED": {"ROLLED_BACK", "WITHDRAWN"},
        "ROLLED_BACK": {"WITHDRAWN"},
        "WITHDRAWN": set()
    },
    "release": {
        "PENDING": {"APPROVED", "REJECTED", "EXPIRED", "REVOKED"},
        "APPROVED": {"REVOKED"},
        "REJECTED": set(),
        "EXPIRED": set(),
        "REVOKED": set()
    },
    "build": {
        "QUEUED": {"RUNNING", "CANCELLED", "KILLED"},
        "RUNNING": {"SUCCEEDED", "FAILED", "CANCELLED", "KILLED", "LOST"},
        "SUCCEEDED": set(),
        "FAILED": set(),
        "CANCELLED": set(),
        "KILLED": set(),
        "LOST": set()
    }
}


def validate_transition(subject_kind: str, from_state: str, to_state: str, expect_from: Optional[str] = None):
    if expect_from and from_state != expect_from:
        raise InvalidTransitionError(f"Expected state {expect_from} for {subject_kind}, found {from_state}")
    allowed_map = ALLOWED_TRANSITIONS.get(subject_kind)
    if not allowed_map:
        raise InvalidTransitionError(f"Unknown subject kind: {subject_kind}")
    valid_targets = allowed_map.get(from_state, set())
    if to_state not in valid_targets:
        raise InvalidTransitionError(
            f"Invalid transition for {subject_kind}: {from_state} -> {to_state}. "
            f"Allowed next states: {sorted(list(valid_targets))}"
        )


@dataclass
class TransitionContext:
    tenant_id: str
    principal: Principal
    conn: Any
    authority_port: Any
    evidence_port: Any
    killswitch_port: Any
    meta: Optional[Dict[str, Any]] = None


def get_subject_state(conn: Any, subject_kind: str, subject_id: str) -> str:
    table_name = f"af_{subject_kind}"
    status_col = "decision" if subject_kind == "release" else ("lifecycle" if subject_kind == "agent" else "status")
    cur = conn.execute(f"SELECT {status_col} FROM {table_name} WHERE id = ?", (subject_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"{subject_kind} {subject_id} not found")
    return row[0]


def update_subject_state(conn: Any, subject_kind: str, subject_id: str, to_state: str):
    table_name = f"af_{subject_kind}"
    status_col = "decision" if subject_kind == "release" else ("lifecycle" if subject_kind == "agent" else "status")
    conn.execute(f"UPDATE {table_name} SET {status_col} = ? WHERE id = ?", (to_state, subject_id))


def transition(
    ctx: TransitionContext,
    subject_kind: str,
    subject_id: str,
    to_state: str,
    *,
    reason: str,
    expect_from: Optional[str] = None,
    payload_hashes: Optional[Dict[str, str]] = None
) -> str:
    """
    Authoritative state transition helper.
    Enforces evidence-before-effect guarantees.
    """
    payload_hashes = payload_hashes or {}

    # 1. Fetch current state
    current_state = get_subject_state(ctx.conn, subject_kind, subject_id)

    # 2. Validate against explicit state machine
    validate_transition(subject_kind, current_state, to_state, expect_from)

    # 3. Assert KillSwitch is not active
    ctx.killswitch_port.assert_not_killed(subject_kind.upper(), subject_id, ctx.tenant_id)

    # 4. Authority authorization check
    action_name = f"factory.{subject_kind}.{to_state.lower()}"
    res = Resource(kind=subject_kind, id=subject_id, tenant_id=ctx.tenant_id, meta={"from_state": current_state, "to_state": to_state})
    decision = ctx.authority_port.authorize(ctx.principal, action_name, res, ctx.meta)
    if decision.deny:
        raise TransitionForbiddenError(f"Authority denied transition to {to_state}: {decision.reason}")

    # 5. Append evidence to EvidenceLedger BEFORE modifying state (fail-closed)
    event = EvidenceEvent(
        subject_kind=subject_kind,
        subject_id=subject_id,
        event_type=f"{subject_kind}.transition.{to_state.lower()}",
        actor=ctx.principal.principal_id,
        payload_hashes={
            "from_state": current_state,
            "to_state": to_state,
            "reason": reason,
            **payload_hashes
        },
        timestamp=time.time(),
        tenant_id=ctx.tenant_id
    )
    # If this raises, the transaction fails and nothing commits
    ledger_id = ctx.evidence_port.append_event(event)

    # 6. Apply database mutation and insert lifecycle event projection
    now = time.time()
    update_subject_state(ctx.conn, subject_kind, subject_id, to_state)
    ctx.conn.execute("""
        INSERT INTO af_lifecycle_event (
            tenant_id, subject_kind, subject_id, from_state, to_state,
            actor, reason, evidence_ledger_id, correlation_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ctx.tenant_id, subject_kind, subject_id, current_state, to_state,
        ctx.principal.principal_id, reason, ledger_id,
        ctx.meta.get("correlation_id") if ctx.meta else None, now
    ))

    return ledger_id
