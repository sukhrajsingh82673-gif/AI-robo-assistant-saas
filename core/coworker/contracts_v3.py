"""
ZONATA Autonomous Coworker 3.0 — Core Contracts & Schemas
Defines interfaces and domain contracts for:
  1. Hermes Agent runtime lifecycle, session persistence, and tool dispatch.
  2. OpenCode governed software engineering loop (Inspect -> Plan -> Implement -> Test -> Review -> Repair -> Submit).
  3. OpenCloud remote worker execution protocol, lease heartbeats, and failover.
  4. Enterprise Agent Cloud (5,000-6,000 logical capacity) with bounded scheduling and quotas.
  5. OpenDots X11 visual perception, screenshot hashing, and always-on scheduling.
  6. Executive Authority, employee task escalation, and unified correlation bus.
  7. Senior Defensive Cybersecurity Operations across 5 severity levels.
  8. Executive Operations Cockpit telemetry.
"""

from __future__ import annotations
import time
import uuid
import hashlib
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .contracts_v2 import (
    TaskLifecycleState, LeaseStatus, CoworkerExecutionLease,
    PatrolSeverity, SecurityPatrolFinding
)


# =============================================================================
# 1. HERMES AGENT RUNTIME CONTRACTS
# =============================================================================

@dataclass
class HermesSessionContext:
    session_id: str
    tenant_id: str = "tnt_primary"
    model: str = "hermes-3-llama-3.1-8b"
    memory_store: Dict[str, Any] = field(default_factory=dict)
    active_skills: List[str] = field(default_factory=list)
    tool_registry: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_checkpoint_at: float = field(default_factory=time.time)
    restart_count: int = 0

    def serialize(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "model": self.model,
            "memory_store": self.memory_store,
            "active_skills": self.active_skills,
            "tool_registry": self.tool_registry,
            "created_at": self.created_at,
            "last_checkpoint_at": self.last_checkpoint_at,
            "restart_count": self.restart_count
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> HermesSessionContext:
        return cls(
            session_id=data["session_id"],
            tenant_id=data.get("tenant_id", "tnt_primary"),
            model=data.get("model", "hermes-3-llama-3.1-8b"),
            memory_store=data.get("memory_store", {}),
            active_skills=data.get("active_skills", []),
            tool_registry=data.get("tool_registry", []),
            created_at=data.get("created_at", time.time()),
            last_checkpoint_at=data.get("last_checkpoint_at", time.time()),
            restart_count=data.get("restart_count", 0)
        )


# =============================================================================
# 2. OPENCODE GOVERNED SOFTWARE ENGINEERING LOOP
# =============================================================================

class OpenCodeLoopPhase(str, Enum):
    INSPECT = "INSPECT"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    TEST = "TEST"
    REVIEW = "REVIEW"
    REPAIR = "REPAIR"
    VERIFY = "VERIFY"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class OpenCodeMission:
    mission_id: str
    objective: str
    repo_path: str
    worktree_path: str
    branch_name: str
    phase: OpenCodeLoopPhase = OpenCodeLoopPhase.INSPECT
    plan_steps: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    diff_content: str = ""
    diff_hash: str = ""
    test_suite_command: str = "pytest"
    test_passed: bool = False
    test_output: str = ""
    code_review_approved: bool = False
    review_comments: List[str] = field(default_factory=list)
    repaired_iterations: int = 0
    max_repair_iterations: int = 3
    evidence_hash: str = ""
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def compute_evidence_hash(self) -> str:
        blob = f"{self.mission_id}:{self.phase}:{self.diff_hash}:{self.test_passed}:{self.code_review_approved}"
        self.evidence_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return self.evidence_hash


# =============================================================================
# 3. OPENCLOUD REMOTE WORKER EXECUTION PROTOCOL
# =============================================================================

class RemoteWorkerState(str, Enum):
    ONLINE = "ONLINE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    DRAINING = "DRAINING"
    FAILED = "FAILED"


@dataclass
class RemoteWorkerNode:
    node_id: str
    endpoint: str
    auth_token: str
    capabilities: List[str] = field(default_factory=lambda: ["terminal", "python", "computer_use", "pytest"])
    state: RemoteWorkerState = RemoteWorkerState.ONLINE
    active_lease_id: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    heartbeat_ttl_sec: float = 10.0
    registered_at: float = field(default_factory=time.time)
    cpu_pct: float = 0.0
    memory_mb: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0

    def is_alive(self) -> bool:
        if self.state in (RemoteWorkerState.OFFLINE, RemoteWorkerState.FAILED):
            return False
        return (time.time() - self.last_heartbeat) < self.heartbeat_ttl_sec


# =============================================================================
# 4. ENTERPRISE AGENT CLOUD (5,000 - 6,000 CAPACITY & SCHEDULING)
# =============================================================================

class AgentRegistrationStatus(str, Enum):
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"
    BUSY = "BUSY"
    SUSPENDED = "SUSPENDED"
    FAILED = "FAILED"
    DECOMMISSIONED = "DECOMMISSIONED"


@dataclass
class AgentIdentityRecord:
    agent_id: str
    tenant_id: str
    archetype: str
    name: str
    status: AgentRegistrationStatus = AgentRegistrationStatus.REGISTERED
    allocated_worker_node: Optional[str] = None
    max_ram_mb: int = 256
    max_cpu_pct: int = 25
    storage_mb: int = 500
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "archetype": self.archetype,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "allocated_worker_node": self.allocated_worker_node,
            "max_ram_mb": self.max_ram_mb,
            "max_cpu_pct": self.max_cpu_pct,
            "storage_mb": self.storage_mb,
            "created_at": self.created_at,
            "last_active_at": self.last_active_at
        }


# =============================================================================
# 5. OPENDOTS COMPUTER-USE & ALWAYS-ON SCHEDULES
# =============================================================================

@dataclass
class VisualObservation:
    display: str = ":99"
    width: int = 1920
    height: int = 1080
    screenshot_bytes: bytes = field(default_factory=bytes)
    screenshot_sha256: str = ""
    active_window_title: str = ""
    detected_elements_count: int = 0
    perception_mode: str = "REAL_VIRTUAL_X11" # REAL_HOST_X11, REAL_VIRTUAL_X11, BROWSER_ONLY, HEADLESS_SIMULATED
    # False when no frame was captured. `width`/`height` are the configured
    # screen size; `capture_width`/`capture_height` are 0 without a frame.
    capture_available: bool = False
    capture_width: int = 0
    capture_height: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ScheduledTaskEntry:
    schedule_id: str
    name: str
    cron_or_interval_sec: float
    command_type: str # "SECURITY_PATROL", "HEALTH_AUDIT", "DEPENDENCY_REFRESH", "CUSTOM"
    payload: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    last_run_timestamp: float = 0.0
    last_status: str = "PENDING"
    run_count: int = 0


# =============================================================================
# 6. EXECUTIVE AUTHORITY & EMPLOYEE ESCALATION ROUTER
# =============================================================================

class EscalationStatus(str, Enum):
    PENDING = "PENDING"
    DIAGNOSING = "DIAGNOSING"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"
    RETURNED_TO_EMPLOYEE = "RETURNED_TO_EMPLOYEE"
    ESCALATED_TO_CEO = "ESCALATED_TO_CEO"
    FAILED = "FAILED"


@dataclass
class EscalationTicket:
    ticket_id: str
    source_employee_id: str
    task_id: str
    failure_context: Dict[str, Any]
    diagnosis: str = ""
    specialist_archetype: str = ""
    assigned_specialist_id: Optional[str] = None
    status: EscalationStatus = EscalationStatus.PENDING
    resolution_artifact: Optional[str] = None
    verified: bool = False
    verification_notes: str = ""
    evidence_hash: str = ""
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def compute_evidence_hash(self) -> str:
        raw = f"{self.ticket_id}:{self.task_id}:{self.status}:{self.resolution_artifact}"
        self.evidence_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.evidence_hash


# =============================================================================
# 7. SENIOR DEFENSIVE CYBERSECURITY OPERATIONS (5 SEVERITIES)
# =============================================================================

class CybersecuritySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class IncidentCategory(str, Enum):
    HOST_PROCESS = "HOST_PROCESS"
    NETWORK_EXPOSURE = "NETWORK_EXPOSURE"
    APPLICATION_API = "APPLICATION_API"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    AI_AGENT_INJECTION = "AI_AGENT_INJECTION"
    MCP_SCOPE_VIOLATION = "MCP_SCOPE_VIOLATION"


@dataclass
class DefensiveSecurityIncident:
    incident_id: str
    severity: CybersecuritySeverity
    category: IncidentCategory
    target: str
    description: str
    evidence_details: Dict[str, Any] = field(default_factory=dict)
    remediation_action: Optional[str] = None
    remediation_status: str = "DETECTED" # "DETECTED", "CONTAINED", "REMEDIATED", "CEO_NOTIFIED", "REJECTED"
    immutable_evidence_hash: str = ""
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def compute_hash(self) -> str:
        s = f"{self.incident_id}:{self.severity}:{self.category}:{self.target}:{self.remediation_status}"
        self.immutable_evidence_hash = hashlib.sha256(s.encode("utf-8")).hexdigest()
        return self.immutable_evidence_hash


# =============================================================================
# 8. EXECUTIVE OPERATIONS COCKPIT TELEMETRY
# =============================================================================

@dataclass
class ExecutiveCockpitTelemetry:
    operating_mode: str = "AUTONOMOUS_OPERATOR"
    current_assignment: Optional[str] = None
    assignment_priority: str = "P1_EXECUTIVE"
    total_registered_agents: int = 5000
    available_agents: int = 4980
    active_agents: int = 15
    busy_agents: int = 5
    suspended_agents: int = 0
    failed_agents: int = 0
    decommissioned_agents: int = 0
    remote_workers_count: int = 1
    bounded_worker_concurrency: int = 20
    queue_depth: int = 0
    memory_usage_mb: float = 128.0
    cpu_usage_pct: float = 2.5
    cybersecurity_threat_level: str = "LOW"
    active_incidents_count: int = 0
    critical_findings_count: int = 0
    high_findings_count: int = 0
    last_patrol_timestamp: float = field(default_factory=time.time)
    integrations_status: Dict[str, str] = field(default_factory=lambda: {
        "hermes_runtime": "VERIFIED_OPERATIONAL",
        "opencode_engine": "VERIFIED_OPERATIONAL",
        "opencloud_remote_workers": "VERIFIED_OPERATIONAL",
        "opendots_computer_use": "VERIFIED_OPERATIONAL",
        "terminal_sandboxed": "VERIFIED_OPERATIONAL",
        "mcp_registry": "VERIFIED_OPERATIONAL"
    })
