"""
ZONATA Universal AI Co-worker Fabric — Core Contracts & Data Models
Defines machine-readable capabilities, execution states, leases, worker profiles,
and provider contracts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import time
import uuid

class CapabilityCategory(str, Enum):
    DESKTOP = "DESKTOP"
    BROWSER = "BROWSER"
    API = "API"
    RPA = "RPA"
    VISUAL_CUA = "VISUAL_CUA"
    FILE = "FILE"
    SYSTEM = "SYSTEM"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CostClass(str, Enum):
    FREE = "FREE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class LatencyClass(str, Enum):
    SUB_SECOND = "SUB_SECOND"
    FAST = "FAST"
    MEDIUM = "MEDIUM"
    SLOW = "SLOW"

class ProviderHealthStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    CRASHED = "CRASHED"

class ExecutionState(str, Enum):
    DISCOVER = "DISCOVER"
    UNDERSTAND = "UNDERSTAND"
    CHECK_CAPABILITIES = "CHECK_CAPABILITIES"
    PLAN = "PLAN"
    RISK_ASSESS = "RISK_ASSESS"
    REQUEST_AUTHORITY = "REQUEST_AUTHORITY"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    COMMIT = "COMMIT"
    EVIDENCE = "EVIDENCE"
    SUCCESS = "SUCCESS"
    
    # Failure & Branching States
    EXECUTION_FAILURE = "EXECUTION_FAILURE"
    DIAGNOSE = "DIAGNOSE"
    RECOVER = "RECOVER"
    RETRY_FALLBACK = "RETRY_FALLBACK"
    VERIFY_UNCERTAIN = "VERIFY_UNCERTAIN"
    POLICY_DENIED = "POLICY_DENIED"
    KILLSWITCH = "KILLSWITCH"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PAUSED_TAKEOVER = "PAUSED_TAKEOVER"

class Reversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"

class SupervisedControlMode(str, Enum):
    AI_CONTROL = "AI_CONTROL"
    HUMAN_CONTROL = "HUMAN_CONTROL"
    PAUSED = "PAUSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    VERIFYING = "VERIFYING"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"

@dataclass
class CapabilityDefinition:
    capability_id: str
    name: str
    description: str
    category: CapabilityCategory
    providers: List[str]
    preferred_provider: str
    fallback_providers: List[str] = field(default_factory=list)
    supported_platforms: List[str] = field(default_factory=lambda: ["linux", "windows", "darwin"])
    risk_level: RiskLevel = RiskLevel.LOW
    requires_authorization: bool = True
    requires_human_approval: bool = False
    requires_verification: bool = True
    supports_rollback: bool = False
    supports_dry_run: bool = True
    supports_idempotency: bool = True
    timeout_sec: float = 60.0
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 3, "backoff_factor": 2.0})
    cost_class: CostClass = CostClass.LOW
    latency_class: LatencyClass = LatencyClass.FAST
    evidence_requirements: List[str] = field(default_factory=lambda: ["execution_log", "output_hash"])

@dataclass
class ProviderEstimate:
    provider_id: str
    estimated_duration_sec: float
    estimated_cost_usd: float
    confidence_score: float
    risk_assessment: str
    requires_visual: bool = False

@dataclass
class ExecutionResult:
    provider_id: str
    capability_id: str
    execution_id: str
    status: str  # "SUCCESS", "FAILED", "UNCERTAIN", "CANCELLED", "AUTH_REQUIRED"
    output: Any = None
    confidence: float = 1.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    rollback_available: bool = False
    rollback_data: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: float = 0.0

@dataclass
class VerificationResult:
    status: VerificationStatus
    verified_by: str
    independent: bool = True
    confidence: float = 1.0
    evidence_details: Dict[str, Any] = field(default_factory=dict)
    discrepancy_notes: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class CoworkerProfile:
    worker_id: str
    tenant_id: str
    role: str
    department: str
    skills: List[str]
    capabilities: List[str]
    authority_scope: Dict[str, Any]
    credential_scope: List[str]
    platform_scope: List[str]
    allowed_providers: List[str]
    risk_limit: RiskLevel = RiskLevel.MEDIUM
    working_hours: str = "24x7"
    mission_limit: int = 10
    budget_limit: float = 50.0
    status: str = "ACTIVE"
    created_at: float = field(default_factory=time.time)

@dataclass
class ExecutionLease:
    lease_id: str
    task_id: str
    worker_id: str
    acquired_at: float
    expires_at: float
    heartbeat_at: float
    status: str = "ACTIVE"  # "ACTIVE", "EXPIRED", "RELEASED"

@dataclass
class TaskNode:
    task_id: str
    mission_id: str
    title: str
    capability_id: str
    preferred_provider: Optional[str] = None
    selected_provider: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    state: ExecutionState = ExecutionState.DISCOVER
    risk_level: RiskLevel = RiskLevel.LOW
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependencies: List[str] = field(default_factory=list)
    result: Optional[ExecutionResult] = None
    verification: Optional[VerificationResult] = None
    attempts: int = 0
    max_retries: int = 3
    error_history: List[str] = field(default_factory=list)

@dataclass
class ExecutionGraph:
    mission_id: str
    tenant_id: str
    owner_objective: str
    nodes: Dict[str, TaskNode] = field(default_factory=dict)
    current_index: int = 0
    status: ExecutionState = ExecutionState.PLAN
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
