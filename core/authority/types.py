"""
ZONATA Canonical Authority, Approvals, Delegations, and Principal Separation (OpenCode Step 2C)
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class ActionClass(str, Enum):
    """Canonical action classes. Every gateway call must declare one."""
    READ_INTERNAL = "READ_INTERNAL"
    WRITE_INTERNAL = "WRITE_INTERNAL"
    CREATE_DOCUMENT = "CREATE_DOCUMENT"
    SEND_EXTERNAL_MESSAGE = "SEND_EXTERNAL_MESSAGE"
    COMMIT_SPEND = "COMMIT_SPEND"
    POST_LEDGER = "POST_LEDGER"
    PROVISION_AGENT_OR_HIRE = "PROVISION_AGENT_OR_HIRE"
    CHANGE_PERMISSION = "CHANGE_PERMISSION"
    DELETE_DATA = "DELETE_DATA"
    EXTERNAL_API_WRITE = "EXTERNAL_API_WRITE"
    LEGAL_COMMITMENT = "LEGAL_COMMITMENT"
    # Reserved classes: always NOT_IMPLEMENTED until Step 3
    INSTALL_SOFTWARE = "INSTALL_SOFTWARE"
    DESKTOP_CONTROL = "DESKTOP_CONTROL"
    BROWSER_SUBMIT = "BROWSER_SUBMIT"


RESERVED_ACTION_CLASSES = {
    ActionClass.INSTALL_SOFTWARE,
    ActionClass.DESKTOP_CONTROL,
    ActionClass.BROWSER_SUBMIT,
}


class PrincipalType(str, Enum):
    """Principal types for segregation of duties and Rule 15 boundaries."""
    HUMAN = "HUMAN"
    OWNER = "OWNER"
    BOARD = "BOARD"
    AI_EMPLOYEE = "AI_EMPLOYEE"
    AGENT = "AGENT"
    MODEL = "MODEL"
    SYSTEM = "SYSTEM"


GOVERNED_PRINCIPAL_TYPES = {
    PrincipalType.AGENT,
    PrincipalType.AI_EMPLOYEE,
    PrincipalType.MODEL,
}


class AutonomyLevel(str, Enum):
    """Autonomy ceiling tiers (Rule 19)."""
    SHADOW = "SHADOW"
    SUPERVISED = "SUPERVISED"
    LIMITED_AUTONOMY = "LIMITED_AUTONOMY"
    AUTONOMOUS = "AUTONOMOUS"


AUTONOMY_RANK: Dict[AutonomyLevel, int] = {
    AutonomyLevel.SHADOW: 0,
    AutonomyLevel.SUPERVISED: 1,
    AutonomyLevel.LIMITED_AUTONOMY: 2,
    AutonomyLevel.AUTONOMOUS: 3,
}


class AuthorityError(Exception):
    """Base exception for authority and governance violations."""
    pass


class Rule15Violation(AuthorityError):
    """Raised when an agent, AI-employee, or model principal attempts to write governance state."""
    pass


class DelegationError(AuthorityError):
    """Base delegation exception."""
    pass


class DelegationAuthorityExceededError(DelegationError):
    """Raised when a delegation exceeds the delegator's own authority."""
    pass


class DelegationRevokedError(DelegationError):
    """Raised when an action is attempted via a revoked delegation."""
    pass


class SelfApprovalError(AuthorityError):
    """Raised when a principal attempts to approve its own request."""
    pass


class AIApprovalError(AuthorityError):
    """Raised when an agent or AI-employee attempts to approve high-risk actions."""
    pass


class PayloadDigestMismatchError(AuthorityError):
    """Raised when action payload differs from the approved payload digest."""
    pass


@dataclass
class PolicyStepOutcome:
    step: int
    gate: str
    status: str  # "PASSED", "DENIED", "SKIPPED"
    rule_id: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecisionResult:
    decision_id: str
    action_id: str
    allowed: bool
    step_number: int
    rule_id: str
    reason: str
    decision_path: List[Dict[str, Any]]
    evidence_id: Optional[str] = None
    created_at: float = 0.0

    @property
    def status(self) -> str:
        return "APPROVED" if self.allowed else "REJECTED"
