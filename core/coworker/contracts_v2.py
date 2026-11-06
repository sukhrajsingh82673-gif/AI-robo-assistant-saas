"""
ZONATA Autonomous Coworker 2.0 — Contracts & Data Models (Phase A)
Defines the 12-state task lifecycle, execution leases, cleanup manifest records,
security patrol findings, and subworker specifications.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import time
import uuid
import json
from .contracts import RiskLevel


class TaskLifecycleState(str, Enum):
    """The 12-state autonomous coworker task lifecycle."""
    IDLE = "IDLE"
    TASK_RECEIVED = "TASK_RECEIVED"
    TASK_ANALYSIS = "TASK_ANALYSIS"
    TOOL_DISCOVERY = "TOOL_DISCOVERY"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    REPORTING_TO_CEO = "REPORTING_TO_CEO"
    SECURITY_MONITORING = "SECURITY_MONITORING"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    PAUSED = "PAUSED"
    TERMINATED = "TERMINATED"


class CleanupResourceType(str, Enum):
    """Types of temporary resources tracked in the cleanup manifest."""
    VENV = "VENV"
    TEMP_FILE = "TEMP_FILE"
    DIRECTORY = "DIRECTORY"
    PROCESS = "PROCESS"
    SOCKET = "SOCKET"
    CONTAINER = "CONTAINER"


class CleanupStatus(str, Enum):
    PENDING = "PENDING"
    CLEANED = "CLEANED"
    FAILED = "FAILED"


class PatrolType(str, Enum):
    PROCESS = "PROCESS"
    NETWORK = "NETWORK"
    FILESYSTEM = "FILESYSTEM"
    RESOURCE = "RESOURCE"
    AST = "AST"
    MEMORY = "MEMORY"
    SECRETS = "SECRETS"
    DEPENDENCIES = "DEPENDENCIES"
    ENDPOINT_AUTH = "ENDPOINT_AUTH"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    TOOL_SCOPE = "TOOL_SCOPE"


class PatrolSeverity(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    REVOKED = "REVOKED"


# Deterministic state transition invariants
VALID_TRANSITIONS: Dict[TaskLifecycleState, Set[TaskLifecycleState]] = {
    TaskLifecycleState.IDLE: {
        TaskLifecycleState.TASK_RECEIVED,
        TaskLifecycleState.SECURITY_MONITORING,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.TASK_RECEIVED: {
        TaskLifecycleState.TASK_ANALYSIS,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.TASK_ANALYSIS: {
        TaskLifecycleState.TOOL_DISCOVERY,
        TaskLifecycleState.WAITING_FOR_APPROVAL,
        TaskLifecycleState.PAUSED,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.TOOL_DISCOVERY: {
        TaskLifecycleState.EXECUTION,
        TaskLifecycleState.WAITING_FOR_APPROVAL,
        TaskLifecycleState.PAUSED,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.EXECUTION: {
        TaskLifecycleState.VERIFICATION,
        TaskLifecycleState.WAITING_FOR_APPROVAL,
        TaskLifecycleState.PAUSED,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.VERIFICATION: {
        TaskLifecycleState.REPORTING_TO_CEO,
        TaskLifecycleState.EXECUTION,
        TaskLifecycleState.PAUSED,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.WAITING_FOR_APPROVAL: {
        TaskLifecycleState.EXECUTION,
        TaskLifecycleState.TASK_ANALYSIS,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.REPORTING_TO_CEO: {
        TaskLifecycleState.IDLE,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.SECURITY_MONITORING: {
        TaskLifecycleState.IDLE,
        TaskLifecycleState.TASK_RECEIVED,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.ERROR_RECOVERY: {
        TaskLifecycleState.TASK_ANALYSIS,
        TaskLifecycleState.TOOL_DISCOVERY,
        TaskLifecycleState.EXECUTION,
        TaskLifecycleState.WAITING_FOR_APPROVAL,
        TaskLifecycleState.IDLE,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.PAUSED: {
        TaskLifecycleState.TASK_ANALYSIS,
        TaskLifecycleState.TOOL_DISCOVERY,
        TaskLifecycleState.EXECUTION,
        TaskLifecycleState.ERROR_RECOVERY,
        TaskLifecycleState.TERMINATED,
    },
    TaskLifecycleState.TERMINATED: {
        TaskLifecycleState.IDLE,  # Re-initialize on reset
    },
}


@dataclass
class TaskStateTransition:
    transition_id: str
    task_id: str
    from_state: TaskLifecycleState
    to_state: TaskLifecycleState
    reason: str
    trigger: str = "orchestrator"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "task_id": self.task_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "trigger": self.trigger,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class CoworkerExecutionLease:
    lease_id: str
    task_id: str
    worker_id: str
    acquired_at: float
    expires_at: float
    heartbeat_at: float
    ttl_seconds: float = 300.0
    status: LeaseStatus = LeaseStatus.ACTIVE

    def is_valid(self, now: Optional[float] = None) -> bool:
        current = now or time.time()
        if self.status != LeaseStatus.ACTIVE:
            return False
        return current <= self.expires_at

    def renew(self, ttl: Optional[float] = None, now: Optional[float] = None) -> None:
        current = now or time.time()
        eff_ttl = ttl or self.ttl_seconds
        self.heartbeat_at = current
        self.expires_at = current + eff_ttl
        self.status = LeaseStatus.ACTIVE

    def expire(self) -> None:
        self.status = LeaseStatus.EXPIRED

    def release(self) -> None:
        self.status = LeaseStatus.RELEASED

    def revoke(self) -> None:
        self.status = LeaseStatus.REVOKED


@dataclass
class CleanupManifestRecord:
    manifest_id: str
    task_id: str
    mission_id: str
    resource_type: CleanupResourceType
    resource_path: str
    status: CleanupStatus = CleanupStatus.PENDING
    created_at: float = field(default_factory=time.time)
    cleaned_at: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "resource_type": self.resource_type.value,
            "resource_path": self.resource_path,
            "status": self.status.value,
            "created_at": self.created_at,
            "cleaned_at": self.cleaned_at,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class SecurityPatrolFinding:
    finding_id: str
    patrol_type: PatrolType
    severity: PatrolSeverity
    description: str
    target: str
    auto_remediated: bool = False
    remediation_action: Optional[str] = None
    detected_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "patrol_type": self.patrol_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "target": self.target,
            "auto_remediated": self.auto_remediated,
            "remediation_action": self.remediation_action,
            "detected_at": self.detected_at,
            "metadata": self.metadata,
        }


@dataclass
class CoworkerV2Task:
    task_id: str
    mission_id: str
    tenant_id: str
    company_id: str
    title: str
    description: str
    state: TaskLifecycleState = TaskLifecycleState.TASK_RECEIVED
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "LOW"
    authority_scope: List[str] = field(default_factory=lambda: ["read_only"])
    budget_allocated_usd: float = 5.0
    budget_spent_usd: float = 0.0
    lease_id: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> TaskLifecycleState:
        return self.state

    @status.setter
    def status(self, val: TaskLifecycleState):
        self.state = val

    @property
    def prompt(self) -> str:
        return self.title

    def can_transition_to(self, target: TaskLifecycleState) -> bool:
        allowed = VALID_TRANSITIONS.get(self.state, set())
        return target in allowed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "status": self.state.value,
            "parameters": self.parameters,
            "risk_level": self.risk_level,
            "authority_scope": self.authority_scope,
            "budget_allocated_usd": self.budget_allocated_usd,
            "budget_spent_usd": self.budget_spent_usd,
            "lease_id": self.lease_id,
            "assigned_worker_id": self.assigned_worker_id,
            "result": self.result,
            "verification": self.verification,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CoworkerV2Task:
        state_val = data.get("state", TaskLifecycleState.TASK_RECEIVED.value)
        try:
            state = TaskLifecycleState(state_val)
        except ValueError:
            state = TaskLifecycleState.TASK_RECEIVED
        return cls(
            task_id=data["task_id"],
            mission_id=data["mission_id"],
            tenant_id=data.get("tenant_id", "tnt_primary"),
            company_id=data.get("company_id", "cmp_primary"),
            title=data.get("title", "Untitled Task"),
            description=data.get("description", ""),
            state=state,
            parameters=data.get("parameters", {}),
            risk_level=data.get("risk_level", "LOW"),
            authority_scope=data.get("authority_scope", ["read_only"]),
            budget_allocated_usd=float(data.get("budget_allocated_usd", 5.0)),
            budget_spent_usd=float(data.get("budget_spent_usd", 0.0)),
            lease_id=data.get("lease_id"),
            assigned_worker_id=data.get("assigned_worker_id"),
            result=data.get("result"),
            verification=data.get("verification"),
            error_message=data.get("error_message"),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SubworkerV2Record:
    worker_id: str
    parent_task_id: str
    parent_worker_id: str
    mission_id: str
    archetype: str
    authority_scope: List[str]
    budget_limit_usd: float
    budget_spent_usd: float = 0.0
    lease_id: str = ""
    status: str = "ACTIVE"
    created_at: float = field(default_factory=time.time)
    decommissioned_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def subworker_id(self) -> str:
        return self.worker_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "parent_task_id": self.parent_task_id,
            "parent_worker_id": self.parent_worker_id,
            "mission_id": self.mission_id,
            "archetype": self.archetype,
            "authority_scope": self.authority_scope,
            "budget_limit_usd": self.budget_limit_usd,
            "budget_spent_usd": self.budget_spent_usd,
            "lease_id": self.lease_id,
            "status": self.status,
            "created_at": self.created_at,
            "decommissioned_at": self.decommissioned_at,
            "metadata": self.metadata,
        }
