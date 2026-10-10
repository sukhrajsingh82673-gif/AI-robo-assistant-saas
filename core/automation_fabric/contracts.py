"""
URA / ZONATA Universal Automation Fabric — Contracts & Types
=============================================================
Defines foundational invariants, terminal states, data models,
and authorization contracts for the Universal Automation Fabric.

Constitutional Invariants:
1. Zero Silent Failures: Every execution reaches an evidence-backed terminal state.
2. Zero Unauthorized Execution: Every consequential action must pass the 9-stage gate.
3. Zero Fabricated Completion: Task completion != Business outcome verified.
4. Authority Boundary: Model output or workflow definitions never confer execution authority.
5. Safe Replay: Ambiguous outcomes must never be blindly retried.
"""

import time
import uuid
import hashlib
import hmac
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field, asdict


# =============================================================================
# 1. EXECUTION STATES & TERMINAL OUTCOMES
# =============================================================================

class ExecutionStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    PUBLISHED = "PUBLISHED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    PAUSED = "PAUSED"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    RECONCILING = "RECONCILING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class TerminalOutcome(str, Enum):
    """
    Mandated evidence-backed terminal states.
    Never report success without verified evidence.
    """
    TASK_SUCCESS = "TASK_SUCCESS"                      # Technical execution completed
    BUSINESS_OUTCOME_VERIFIED = "BUSINESS_OUTCOME_VERIFIED"  # Business postcondition verified
    FAILED = "FAILED"                                  # Failure confirmed
    BLOCKED = "BLOCKED"                                # Halted pending prerequisite or approval
    CANCELLED = "CANCELLED"                            # Stopped and reconciled
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"                # Ambiguous external state; requires reconciliation


class ActionRiskLevel(str, Enum):
    SAFE = "SAFE"                 # Read-only, idempotent query
    CONFIRM = "CONFIRM"           # Reversible internal mutation
    DANGEROUS = "DANGEROUS"       # External integration or significant state change
    CRITICAL = "CRITICAL"         # Financial, credential, destructive, or irreversible


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"   # Stale approval invalidated by version/scope change


class LicenseType(str, Enum):
    APACHE_2_0 = "Apache-2.0"
    MIT = "MIT"
    BSD_3_CLAUSE = "BSD-3-Clause"
    BSD_2_CLAUSE = "BSD-2-Clause"
    ISC = "ISC"
    UNAPPROVED_PROPRIETARY = "UNAPPROVED_PROPRIETARY"
    RESTRICTED_COPYLEFT = "RESTRICTED_COPYLEFT"


class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Tripped due to failures; rejecting fast
    HALF_OPEN = "HALF_OPEN" # Canary testing after cooldown


# =============================================================================
# 2. DATA STRUCTURES & LEASES
# =============================================================================

@dataclass
class ExecutionLease:
    """HMAC-signed scoped execution lease required for privileged actions."""
    lease_id: str
    tenant_id: str
    company_id: str
    workflow_id: str
    run_id: str
    action_name: str
    scope: str
    created_at: float
    expires_at: float
    signature: str

    @classmethod
    def create(cls, secret_key: str, tenant_id: str, company_id: str,
               workflow_id: str, run_id: str, action_name: str,
               scope: str, ttl_seconds: float = 300.0) -> "ExecutionLease":
        lease_id = f"lease_{uuid.uuid4().hex[:12]}"
        now = time.time()
        expires = now + ttl_seconds
        payload = f"{lease_id}:{tenant_id}:{company_id}:{workflow_id}:{run_id}:{action_name}:{scope}:{expires}"
        sig = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return cls(
            lease_id=lease_id,
            tenant_id=tenant_id,
            company_id=company_id,
            workflow_id=workflow_id,
            run_id=run_id,
            action_name=action_name,
            scope=scope,
            created_at=now,
            expires_at=expires,
            signature=sig
        )

    def verify(self, secret_key: str) -> bool:
        if time.time() > self.expires_at:
            return False
        payload = f"{self.lease_id}:{self.tenant_id}:{self.company_id}:{self.workflow_id}:{self.run_id}:{self.action_name}:{self.scope}:{self.expires_at}"
        expected = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)


@dataclass
class ConnectorDefinition:
    """Universal capability & integration connector specification."""
    connector_id: str
    provider: str
    name: str
    version: str
    license: LicenseType
    supported_operations: List[str]
    input_schemas: Dict[str, Any]
    output_schemas: Dict[str, Any]
    auth_mechanism: str             # API_KEY, OAUTH2, MTLS, NONE
    required_scopes: List[str]
    tenant_isolated: bool
    risk_classification: ActionRiskLevel
    idempotent: bool
    rate_limit_rpm: int
    timeout_seconds: float
    circuit_breaker_threshold: int
    verification_method: str        # INDEPENDENT_QUERY, MERKLE_AUDIT, API_HEAD
    health_status: str = "HEALTHY"  # HEALTHY, DEGRADED, UNHEALTHY
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["license"] = self.license.value
        d["risk_classification"] = self.risk_classification.value
        return d


@dataclass
class WorkflowTemplate:
    """Versioned reusable workflow template."""
    template_id: str
    name: str
    version: str
    category: str
    purpose: str
    required_integrations: List[str]
    inputs_schema: Dict[str, Any]
    workflow_spec: Dict[str, Any]   # Kestra / Flow specification
    permissions: List[str]
    expected_outcomes: List[str]
    compensation_strategy: str
    verification_spec: Dict[str, Any]
    license: LicenseType = LicenseType.APACHE_2_0
    author: str = "URA_AUTOMATION_FABRIC"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["license"] = self.license.value
        return d


@dataclass
class StepResult:
    """Result of a single executed workflow step."""
    step_id: str
    node_type: str
    status: ExecutionStatus
    output: Any
    duration_seconds: float
    error: Optional[str] = None
    retry_count: int = 0
    idempotency_key: Optional[str] = None
    evidence_hash: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class IndependentVerificationResult:
    """Evidence produced by independent verification agent."""
    verified: bool
    verifier_agent: str
    postcondition: str
    evidence_summary: str
    external_state_snapshot: Dict[str, Any]
    merkle_proof: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
