"""
ZONATA Work Kernel Types & Data Models
Step 2F: Missions, Projects, Work Tasks, Dependencies, Events, and Human Inbox.
"""

from __future__ import annotations

import enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TaskStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AssigneeType(str, enum.Enum):
    POSITION = "POSITION"
    OCCUPANT = "OCCUPANT"
    AGENT = "AGENT"
    HUMAN = "HUMAN"


class InboxItemType(str, enum.Enum):
    TASK_APPROVAL = "TASK_APPROVAL"
    TASK_INTERVENTION = "TASK_INTERVENTION"
    DECISION_REQUEST = "DECISION_REQUEST"
    SLA_ESCALATION = "SLA_ESCALATION"


class InboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class WorkKernelError(Exception):
    """Base exception for work kernel operations."""
    pass


class IllegalStateTransitionError(WorkKernelError):
    """Raised when an illegal task state machine transition is attempted."""
    pass


class AssigneeSelfCompletionForbiddenError(WorkKernelError):
    """
    Raised when an assignee attempts to complete its own task.
    Rule 17: 'Done' is a claim, not a fact. Tasks complete only via verification.
    """
    pass


class TaskDependencyCycleError(WorkKernelError):
    """Raised when cyclic task dependencies are detected in a delegation DAG."""
    pass


class PrerequisiteNotCompletedError(WorkKernelError):
    """Raised when attempting to activate a task whose prerequisite tasks are not COMPLETED."""
    pass


class TaskNotFoundError(WorkKernelError):
    """Raised when a referenced task does not exist."""
    pass


class MissionNotFoundError(WorkKernelError):
    """Raised when a referenced mission does not exist."""
    pass


class ProjectNotFoundError(WorkKernelError):
    """Raised when a referenced project does not exist."""
    pass


class CapabilityNotLiveBlockedError(WorkKernelError):
    """Raised or used to signal a task blocked by non-live capabilities."""
    pass


class InboxItemNotFoundError(WorkKernelError):
    """Raised when a human inbox item does not exist."""
    pass


class TaskAssignmentIneligibleError(WorkKernelError):
    """Raised when a candidate assignee is ineligible for a task."""
    pass


# =============================================================================
# DATA TRANSFER MODELS
# =============================================================================

class MissionCreateRequest(BaseModel):
    title: str
    objective: str
    lead_position_id: Optional[str] = None
    sponsor_position_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    budget_micro_units: int = 0
    target_deadline_ts: Optional[float] = None


class ProjectCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    mission_id: Optional[str] = None
    lead_position_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    mission_id: Optional[str] = None
    project_id: Optional[str] = None
    owner_id: str
    assignee_type: AssigneeType = AssigneeType.POSITION
    assignee_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    estimate_seconds: int = 0
    estimate_minor_units: int = 0
    acceptance_criteria: Dict[str, Any] = Field(default_factory=dict)
    required_capabilities: List[str] = Field(default_factory=list)
    required_autonomy_level: str = "SHADOW"
    sla_seconds: Optional[int] = None
    deadline_ts: Optional[float] = None
    dependencies: List[str] = Field(default_factory=list)
    linked_folio_id: Optional[str] = None
    linked_document_ids: List[str] = Field(default_factory=list)


class TaskSubmitRequest(BaseModel):
    deliverable: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None


class TaskVerifyRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    verifier_id: str
    verification_report_id: Optional[str] = None
    reason: Optional[str] = None
