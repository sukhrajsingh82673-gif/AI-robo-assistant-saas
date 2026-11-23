"""
ZONATA Task State Machine
Strict 7-State lifecycle enforcement with Rule 17 (assignee cannot self-complete).
"""

from __future__ import annotations

from typing import Set, Dict, Optional, Any
from core.work.types import (
    TaskStatus,
    IllegalStateTransitionError,
    AssigneeSelfCompletionForbiddenError,
)

VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PROPOSED: {
        TaskStatus.ASSIGNED,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.ASSIGNED: {
        TaskStatus.ACCEPTED,
        TaskStatus.ASSIGNED,  # Reassignment
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.ACCEPTED: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.SUBMITTED,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.SUBMITTED: {
        TaskStatus.VERIFYING,
        TaskStatus.COMPLETED,
        TaskStatus.REJECTED,
        TaskStatus.IN_PROGRESS,  # Return for revision
        TaskStatus.CANCELLED,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.COMPLETED,
        TaskStatus.REJECTED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.CANCELLED,
    },
    TaskStatus.REJECTED: {
        TaskStatus.IN_PROGRESS,  # Re-work after rejection
        TaskStatus.ASSIGNED,     # Reassigned/routed back
        TaskStatus.CANCELLED,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.PROPOSED,
        TaskStatus.ASSIGNED,
        TaskStatus.ACCEPTED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.CANCELLED,
    },
    TaskStatus.COMPLETED: set(),  # Terminal state
    TaskStatus.CANCELLED: set(),  # Terminal state
}


class TaskStateMachine:
    """
    Enforces atomic, rule-governed state transitions on tasks.
    Guarantees Rule 17: 'Done' is a claim, not a fact. Assignee cannot self-complete.
    """

    @classmethod
    def validate_transition(
        cls,
        current_status: TaskStatus,
        target_status: TaskStatus,
        actor_id: str,
        assignee_id: Optional[str] = None,
        is_verifier: bool = False,
    ) -> None:
        """
        Validates whether a transition from current_status to target_status is permitted.
        Raises IllegalStateTransitionError or AssigneeSelfCompletionForbiddenError on violation.
        """
        # Rule 17: Done is a claim, not a fact
        if target_status == TaskStatus.COMPLETED:
            if assignee_id and actor_id == assignee_id:
                raise AssigneeSelfCompletionForbiddenError(
                    f"ASSIGNEE_SELF_COMPLETION_FORBIDDEN: Assignee '{actor_id}' cannot complete its own task. "
                    "Rule 17: 'Done' is a claim, not a fact. Tasks must transition through SUBMITTED and be completed by verification."
                )
            if not is_verifier:
                raise IllegalStateTransitionError(
                    f"UNAUTHORIZED_VERIFIER: Only the verification service or an authorized verifier can mark a task COMPLETED."
                )

        if current_status not in VALID_TRANSITIONS:
            raise IllegalStateTransitionError(f"Unknown current status: {current_status}")

        allowed = VALID_TRANSITIONS[current_status]
        if target_status not in allowed:
            raise IllegalStateTransitionError(
                f"ILLEGAL_STATE_TRANSITION: Cannot transition task from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )
