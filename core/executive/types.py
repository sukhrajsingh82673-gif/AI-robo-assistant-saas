"""
ZONATA Executive Brain & Workforce Trust Types and Data Models
OpenCode Step 2J: Directives, Plan Validation, Decision Records, Risk Register, and Trust Levels.
"""

from __future__ import annotations

import enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TrustLevel(str, enum.Enum):
    """
    Workforce Trust Hierarchy.
    Rule 19: Conservative by default. New employees start in SHADOW.
    """
    SHADOW = "SHADOW"
    SUPERVISED = "SUPERVISED"
    LIMITED_AUTONOMY = "LIMITED_AUTONOMY"
    AUTONOMOUS = "AUTONOMOUS"


class DirectiveStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RiskTriggerType(str, enum.Enum):
    KPI_OFF_TRACK = "KPI_OFF_TRACK"
    BUDGET_BURN_SPIKE = "BUDGET_BURN_SPIKE"
    SLA_BREACH = "SLA_BREACH"
    VERIFICATION_FAILURE_RATE = "VERIFICATION_FAILURE_RATE"
    REPEATED_DENIALS = "REPEATED_DENIALS"


class RiskSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ExecutiveError(Exception):
    """Base exception for executive brain and workforce trust subsystem."""
    pass


class ClarificationRequiredError(ExecutiveError):
    """Raised when high-stakes ambiguity requires owner clarification before planning."""
    def __init__(self, question: str, ambiguity_domain: str):
        super().__init__(f"High-stakes ambiguity in {ambiguity_domain} requires clarification: {question}")
        self.question = question
        self.ambiguity_domain = ambiguity_domain


class PlanValidationFailedError(ExecutiveError):
    """Raised when deterministic plan validation fails (budget, authority, capability, or chronology)."""
    def __init__(self, reasons: List[str]):
        super().__init__(f"Plan validation failed: {'; '.join(reasons)}")
        self.reasons = reasons


class NumberLockViolationError(ExecutiveError):
    """Rule 18: Raised when owner report contains numbers not backed by real stored facts."""
    def __init__(self, unverified_numbers: List[str]):
        super().__init__(f"Number-lock violation: unverified numbers found in narrative: {unverified_numbers}")
        self.unverified_numbers = unverified_numbers


class PromotionThresholdNotMetError(ExecutiveError):
    """Raised when employee promotion is attempted without meeting measured thresholds."""
    pass


class UnauthorizedPromotionApproverError(ExecutiveError):
    """Rule 15: Raised when a non-human principal attempts to approve an employee promotion."""
    pass


class EmployeeSuspendedError(ExecutiveError):
    """Raised when a suspended or killed employee attempts an operation."""
    pass


# =============================================================================
# DATA TRANSFER MODELS
# =============================================================================

class DirectiveModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    owner_command: str
    objective: str
    constraints: List[str] = Field(default_factory=list)
    deadline_ts: Optional[float] = None
    budget_minor_units: int = 0
    target_kpis: List[str] = Field(default_factory=list)
    scope: Dict[str, Any] = Field(default_factory=dict)
    is_ambiguous: bool = False
    clarifying_question: Optional[str] = None
    status: DirectiveStatus = DirectiveStatus.PROPOSED
    created_at: float
    updated_at: float


class PlanTaskSpec(BaseModel):
    task_id: str
    title: str
    department_code: str
    position_code: str
    action_class: str
    required_capabilities: List[str] = Field(default_factory=list)
    estimate_minor_units: int = 0
    estimate_seconds: int = 3600
    prerequisites: List[str] = Field(default_factory=list)
    deadline_ts: Optional[float] = None


class PlanProjectSpec(BaseModel):
    project_id: str
    title: str
    department_code: str
    tasks: List[PlanTaskSpec]
    deadline_ts: Optional[float] = None


class PlanMissionSpec(BaseModel):
    mission_id: str
    title: str
    objective: str
    lead_position_code: str
    budget_minor_units: int = 0
    projects: List[PlanProjectSpec]
    deadline_ts: Optional[float] = None


class PlanGraphModel(BaseModel):
    directive_id: str
    missions: List[PlanMissionSpec]
    total_estimated_cost_minor_units: int = 0


class CEODecisionRecordModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    directive_id: Optional[str] = None
    title: str
    options: List[Dict[str, Any]]
    evidence_ids: List[str]
    chosen_option: str
    reason: str
    approver_id: str
    outcome_review_date: Optional[str] = None
    created_at: float


class RiskRecordModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    trigger_type: RiskTriggerType
    severity: RiskSeverity
    details: Dict[str, Any]
    corrective_task_id: Optional[str] = None
    status: str = "OPEN"
    detected_at: float
    resolved_at: Optional[float] = None


class EmployeeTrustModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    employee_id: str
    current_level: TrustLevel = TrustLevel.SHADOW
    tasks_completed_count: int = 0
    verified_pass_rate: float = 1.0
    sop_compliance_score: float = 100.0
    policy_violation_count: int = 0
    last_promoted_at: Optional[float] = None
    is_suspended: bool = False
    is_killed: bool = False
    created_at: float
    updated_at: float
