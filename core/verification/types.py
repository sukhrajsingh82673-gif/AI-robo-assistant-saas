"""
ZONATA Verification Pyramid Subsystem Types & Models
OpenCode Step 2H: Five-layer verification engine, layer results, and spot checks.
"""

from __future__ import annotations

import enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class VerificationLayer(str, enum.Enum):
    """
    Five progressive layers of verification from cheap schema checks to expensive human review.
    """
    SCHEMA = "SCHEMA"
    DETERMINISTIC_CODE = "DETERMINISTIC_CODE"
    CROSS_RECORD = "CROSS_RECORD"
    PEER_MODEL = "PEER_MODEL"
    HUMAN = "HUMAN"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class LayerResultStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class VerificationError(Exception):
    """Base exception for verification subsystem."""
    pass


class VerificationLayerFailedError(VerificationError):
    """Raised when a specific verification layer check fails."""
    pass


class UnauthorizedLayerInvokerError(VerificationError):
    """Raised when a principal attempts to invoke a layer forbidden to them."""
    pass


class VerificationRecipeNotFoundError(VerificationError):
    """Raised when no verification recipe is registered or defined for a task type."""
    pass


class IncompleteVerificationError(VerificationError):
    """Raised when task completion is attempted without all required layers passing."""
    pass


# =============================================================================
# DATA TRANSFER MODELS
# =============================================================================

class VerificationLayerResult(BaseModel):
    layer: VerificationLayer
    status: LayerResultStatus
    rule_name: Optional[str] = None
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    scorecard: Dict[str, Any] = Field(default_factory=dict)
    evidence_pointers: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    evaluated_at: float


class VerificationReport(BaseModel):
    verification_id: str
    task_id: str
    overall_status: VerificationStatus
    required_layers: List[VerificationLayer]
    passed_layers: List[VerificationLayer] = Field(default_factory=list)
    failing_layer: Optional[VerificationLayer] = None
    rejection_reason: Optional[str] = None
    layer_results: List[VerificationLayerResult] = Field(default_factory=list)
    is_spot_check: bool = False

    @property
    def is_passed(self) -> bool:
        return self.overall_status == VerificationStatus.PASSED


class VerificationRecipe(BaseModel):
    task_type: str
    required_layers: List[VerificationLayer]
    layer_configs: Dict[str, Any] = Field(default_factory=dict)
