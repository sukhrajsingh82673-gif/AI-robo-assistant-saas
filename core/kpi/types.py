"""
ZONATA KPI & Goal Engine Types and Data Models
OpenCode Step 2I: Hierarchical KPI trees, snapshot proofs, thresholds, and Kaizen loops.
"""

from __future__ import annotations

import enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class KPIScopeLevel(str, enum.Enum):
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    POSITION = "POSITION"
    EMPLOYEE = "EMPLOYEE"
    MISSION = "MISSION"
    TASK = "TASK"


class KPIMetricType(str, enum.Enum):
    TASK_DURATION = "TASK_DURATION"
    PRODUCTIVITY = "PRODUCTIVITY"
    PASS_RATE = "PASS_RATE"
    COST_PER_MISSION = "COST_PER_MISSION"
    LEDGER_BALANCE = "LEDGER_BALANCE"
    DEFECT_RATE = "DEFECT_RATE"


class KPIDirection(str, enum.Enum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


class KPICadence(str, enum.Enum):
    REALTIME = "REALTIME"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class KPIStatus(str, enum.Enum):
    ON_TRACK = "ON_TRACK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DefectType(str, enum.Enum):
    SCHEMA_DEFECT = "SCHEMA_DEFECT"
    ARITHMETIC_DEFECT = "ARITHMETIC_DEFECT"
    CROSS_RECORD_DEFECT = "CROSS_RECORD_DEFECT"
    QUALITY_DEFECT = "QUALITY_DEFECT"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class KaizenProposalType(str, enum.Enum):
    COACHING_PROMPT = "COACHING_PROMPT"
    SOP_REVISION_PROPOSAL = "SOP_REVISION_PROPOSAL"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class KPIError(Exception):
    """Base exception for KPI subsystem."""
    pass


class KPINotFoundError(KPIError):
    """Raised when a requested KPI definition is not found."""
    pass


class InvalidKPIComputationError(KPIError):
    """Raised when KPI computation fails or missing required inputs."""
    pass


class MissingComputationProofError(KPIError):
    """Raised when an attempt is made to store a KPI snapshot without an inputs hash."""
    pass


# =============================================================================
# DATA TRANSFER MODELS
# =============================================================================

class KPIDefinitionCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    scope_level: KPIScopeLevel
    scope_id: Optional[str] = None
    metric_type: KPIMetricType
    target_value: float
    warning_threshold: float
    critical_threshold: float
    direction: KPIDirection = KPIDirection.HIGHER_IS_BETTER
    unit: str = "COUNT"
    cadence: KPICadence = KPICadence.DAILY
    parent_kpi_id: Optional[str] = None


class KPISnapshotModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    kpi_id: str
    scope_level: KPIScopeLevel
    scope_id: Optional[str] = None
    current_value: float
    target_value: float
    warning_threshold: float
    critical_threshold: float
    status: KPIStatus
    computation_proof: Dict[str, Any] = Field(default_factory=dict)
    inputs_hash: str
    effective_date: str
    computed_at: float


class KPIAlertModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    kpi_id: str
    snapshot_id: str
    severity: str
    observed_value: float
    threshold_value: float
    escalated_to_role: Optional[str] = None
    status: str = "OPEN"
    playbook_triggered: Optional[str] = None
    created_at: float


class KaizenDefectRecordModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    task_id: str
    position_id: Optional[str] = None
    employee_id: Optional[str] = None
    sop_id: Optional[str] = None
    defect_type: DefectType
    details: Dict[str, Any] = Field(default_factory=dict)
    recorded_at: float


class KaizenProposalModel(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    proposal_type: KaizenProposalType
    target_type: str
    target_id: str
    cluster_defect_type: DefectType
    cluster_count: int
    title: str
    content: Dict[str, Any] = Field(default_factory=dict)
    status: str = "DRAFT"
    created_at: float
