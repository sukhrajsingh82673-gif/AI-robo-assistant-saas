"""
RoboAssistant 1.0.0-GA / ROBO-GA-1.0.0-PROD
Core Data Models and Type Contracts
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import uuid

class AuthorityLevel(str, Enum):
    """
    Action-authority classification for a single action: how much human
    involvement the action needs.

    Naming hazard: `core.aic_ceo_constitution.AuthorityLevel` is a *different*
    enum (actor hierarchy: owner → board → CEO → … → tool). This one answers
    "may this action run unattended?", the other answers "who is asking?".
    Never substitute one for the other.
    """
    SANDBOXED_READ_ONLY = "SANDBOXED_READ_ONLY"
    AUTOMATIC_IDEMPOTENT = "AUTOMATIC_IDEMPOTENT"
    ASK_ME = "ASK_ME"
    NEVER_ALLOWED = "NEVER_ALLOWED"

class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SELF_TESTED = "SELF_TESTED"
    PENDING_EVIDENCE = "PENDING_EVIDENCE"
    SIMULATED = "SIMULATED"
    TEST = "TEST"

class ExecutionClassification(str, Enum):
    SIMULATED = "SIMULATED"
    TEST = "TEST"
    LIVE = "LIVE"

class HostType(str, Enum):
    LINUX_CLOUD = "LINUX_CLOUD"
    WINDOWS_WORKSTATION = "WINDOWS_WORKSTATION"
    MACOS_STUDIO = "MACOS_STUDIO"
    ANDROID_HOST = "ANDROID_HOST"
    IOS_REMOTE = "IOS_REMOTE"

class MissionStatus(str, Enum):
    DISCOVER = "DISCOVER"
    UNDERSTAND = "UNDERSTAND"
    CHECK_CAPABILITIES = "CHECK_CAPABILITIES"
    PLAN = "PLAN"
    REQUEST_PERMISSION = "REQUEST_PERMISSION"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    SUCCESS = "SUCCESS"
    ESCALATE_TO_OWNER = "ESCALATE_TO_OWNER"

@dataclass
class AgentEmploymentContract:
    agent_id: str
    role: str
    department: str
    manager: str
    responsibilities: List[str]
    objectives: List[str]
    allowed_tools: List[str]
    allowed_hosts: List[HostType]
    data_access: List[str]
    budget_limit: float
    spending_limit: float
    decision_authority: List[str]
    approval_requirements: List[str]
    forbidden_actions: List[str]
    kpis: Dict[str, str]
    escalation_rules: List[str]
    working_state: str = "ACTIVE"
    memory_scope: str = "DEPARTMENT_ISOLATED"
    created_at: float = field(default_factory=time.time)

@dataclass
class ActionContract:
    action_id: str
    mission_id: str
    agent_id: str
    capability: str
    target: str
    host: HostType
    scope: str
    permissions_required: AuthorityLevel
    resources_locked: List[str]
    expected_outcome: str
    verification_requirements: List[str]
    timestamp: float = field(default_factory=time.time)

@dataclass
class PhysicalVerification:
    check_type: str  # file_exists, sha256_match, exit_code_zero, elf_pe_header, smoke_test_pass
    target_path: str
    expected_val: str
    actual_val: str
    verified: bool
    details: str

@dataclass
class EvidencePackage:
    evidence_id: str
    action_id: str
    mission_id: str
    agent_id: str
    timestamp: float
    status: EvidenceStatus
    physical_verifications: List[PhysicalVerification]
    sha256_digest: str
    signature: str
    merkle_index: int
    execution_classification: str = "LIVE"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def merkle_root(self) -> str:
        return self.sha256_digest

    @property
    def package_id(self) -> str:
        return self.evidence_id

@dataclass
class DataSource:
    source_id: str
    name: str
    source_type: str  # PMS, ERP, CRM, POS, API, DB, FILE
    connection_method: str  # API, OAUTH, FILE_UPLOAD, DB_CONN
    freshness: str  # e.g., "14m ago"
    permission_level: str  # "READ_ONLY_VISIBILITY", "WRITE_ALLOWED"
    synchronized_at: float = field(default_factory=time.time)
    health: str = "GOOD"
    available_data: List[str] = field(default_factory=list)

@dataclass
class Mission:
    mission_id: str
    title: str
    company_id: str
    owner_agent: str
    department: str
    target_outcome: str
    status: MissionStatus = MissionStatus.DISCOVER
    kpis: Dict[str, Any] = field(default_factory=dict)
    financials: Dict[str, float] = field(default_factory=lambda: {"revenue_generated": 0.0, "cost_incurred": 0.0, "contribution": 0.0})
    assigned_agents: List[str] = field(default_factory=list)
    action_contracts: List[ActionContract] = field(default_factory=list)
    evidence_packages: List[EvidencePackage] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    verification_summary: str = "PENDING"

@dataclass
class ApprovalRequest:
    request_id: str
    mission_id: str
    agent_id: str
    action_desc: str
    reason: str
    host: HostType
    scope: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    consequence: str
    status: str = "PENDING"  # PENDING, APPROVED, DENIED
    signed_grant_hash: Optional[str] = None
    requested_at: float = field(default_factory=time.time)

@dataclass
class OperatingContext:
    company_id: str
    name: str
    industry: str
    company_type: str  # "NEW" or "EXISTING"
    status: str = "OPERATIONAL"  # OPERATIONAL, ATTENTION, ONBOARDING
    revenue: float = 0.0
    cost: float = 0.0
    contribution: float = 0.0
    departments: List[str] = field(default_factory=list)
    workforce: Dict[str, AgentEmploymentContract] = field(default_factory=dict)
    missions: List[Mission] = field(default_factory=list)
    data_sources: List[DataSource] = field(default_factory=list)
    operating_rules: List[str] = field(default_factory=list)
    understanding_pct: float = 100.0
    baseline_summary: Optional[Dict[str, Any]] = None
