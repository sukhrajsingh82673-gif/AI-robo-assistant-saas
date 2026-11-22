"""
ZONATA SOP Subsystem Types & Data Models
OpenCode Step 2G: Executable SOP step definitions, instance lifecycles, and compliance models.
"""

from __future__ import annotations

import enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SOPStepType(str, enum.Enum):
    TOOL = "TOOL"
    MODEL = "MODEL"
    HUMAN = "HUMAN"
    APPROVAL = "APPROVAL"
    CHECK = "CHECK"


class SOPInstanceStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"
    CANCELLED = "CANCELLED"


class SOPVersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    NOT_EXECUTABLE = "NOT_EXECUTABLE"


class SOPStepReversibility(str, enum.Enum):
    IRREVERSIBLE = "IRREVERSIBLE"
    COMPENSABLE = "COMPENSABLE"
    IDEMPOTENT = "IDEMPOTENT"


class SOPStepOutcome(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SOPError(Exception):
    """Base exception for SOP subsystem."""
    pass


class SOPNotFoundError(SOPError):
    """Raised when an SOP definition is not found."""
    pass


class SOPVersionNotFoundError(SOPError):
    """Raised when an SOP version is not found."""
    pass


class SOPNotExecutableError(SOPError):
    """Raised when attempting to execute an SOP stub with no executable steps."""
    pass


class SOPPreconditionFailedError(SOPError):
    """Raised when a step precondition fails before execution."""
    pass


class SOPPostconditionFailedError(SOPError):
    """Raised when a step postcondition fails after execution."""
    pass


class SOPStepTimeoutError(SOPError):
    """Raised when a step execution exceeds its allowed timeout."""
    pass


class SOPCompensationFailedError(SOPError):
    """Raised when a compensation action fails during rollback."""
    pass


class SOPStepExecutionError(SOPError):
    """Raised when step action execution fails."""
    pass


# =============================================================================
# DATA TRANSFER MODELS
# =============================================================================

class SOPStepDefinition(BaseModel):
    step_number: int
    name: str
    role: Optional[str] = None
    step_type: SOPStepType = SOPStepType.TOOL
    tool_name: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs_schema: Dict[str, Any] = Field(default_factory=dict)
    preconditions: List[Dict[str, Any]] = Field(default_factory=list)
    postconditions: List[Dict[str, Any]] = Field(default_factory=list)
    failure_handler: Optional[Dict[str, Any]] = None
    max_duration: int = 60
    timeout_seconds: int = 60
    reversibility: SOPStepReversibility = SOPStepReversibility.IDEMPOTENT
    compensation_step: Optional[Dict[str, Any]] = None
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key_rule: Optional[str] = None


class SOPDefinitionCreateRequest(BaseModel):
    department_id: str
    code: str
    title: str
    category: str = "OPERATIONAL"
    objective: str = ""
    risk_level: str = "MEDIUM"


class SOPVersionCreateRequest(BaseModel):
    sop_id: str
    semver: str
    steps: List[Dict[str, Any]]
    required_authority_level: str = "DELEGATED"
    author_employee_id: str
    evidence_requirements: List[str] = Field(default_factory=list)
    approved_by_role: Optional[str] = None


class SOPRunRequest(BaseModel):
    sop_id: str
    version_id: Optional[str] = None  # None -> uses latest approved version
    executor_id: str
    context_inputs: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class SOPStepRecordModel(BaseModel):
    id: str
    instance_id: str
    tenant_id: str
    company_id: str
    step_number: int
    step_name: str
    step_type: str
    tool_name: Optional[str] = None
    actor_id: Optional[str] = None
    input_hash: str
    step_def_hash: str
    output_hash: Optional[str] = None
    outcome: str = "PASSED"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    preconditions_passed: int = 1
    postconditions_passed: int = 1
    start_time: float
    finish_time: float
    duration_ms: float = 0.0
    reversibility: str = "IDEMPOTENT"
    error: Optional[str] = None
    evidence_event_id: Optional[str] = None
    execution_timestamp: float
