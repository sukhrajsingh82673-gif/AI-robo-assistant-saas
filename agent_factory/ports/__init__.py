"""
ZONATA Agent Factory — Port Definitions
Defines all protocol interfaces connecting the Factory to ZONATA Sovereign Core.
No implementation code or direct DB/subsystem dependencies belong here.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    company_id: str
    kind: str  # human_owner, ai_employee, ai_ceo, factory_role, service, agent
    roles: List[str]


class Resource:
    def __init__(
        self,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        tenant_id: str = "",
        meta: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        kind: Optional[str] = None
    ):
        self.resource_id = resource_id or id or ""
        self.resource_type = resource_type or kind or ""
        self.tenant_id = tenant_id
        self.meta = meta or {}

    @property
    def id(self) -> str:
        return self.resource_id

    @property
    def kind(self) -> str:
        return self.resource_type


@dataclass(frozen=True)
class Decision:
    allow: bool
    deny: bool
    require_approval: bool
    reason: str
    approval_ref: Optional[str] = None
    scope: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class EvidenceEvent:
    subject_kind: str
    subject_id: str
    event_type: str
    actor: str
    payload_hashes: Dict[str, str]
    timestamp: float
    tenant_id: str


@dataclass
class BuildJob:
    build_id: str
    request_id: str
    tenant_id: str
    agent_version_id: str
    stages: List[str]
    status: str


class AuthorityPort(ABC):
    @abstractmethod
    def authorize(
        self,
        principal: Principal,
        action: str,
        resource: Resource,
        meta: Optional[Dict[str, Any]] = None
    ) -> Decision:
        """Evaluate whether a principal has authority to perform action on resource."""
        pass


class PolicyPort(ABC):
    @abstractmethod
    def evaluate_risk(
        self,
        capabilities: List[str],
        tools: List[str],
        data_scopes: List[str]
    ) -> str:
        """Calculate risk tier (R0, R1, R2, R3)."""
        pass

    @abstractmethod
    def assert_not_killed(
        self,
        tenant_id: str,
        subject_kind: str,
        subject_id: str
    ) -> None:
        """Raise error if kill switch active for tenant/agent/system."""
        pass


class EvidenceLedgerPort(ABC):
    @abstractmethod
    def append_event(self, event: EvidenceEvent) -> str:
        """Append an event to the tamper-evident Merkle ledger and return ledger id."""
        pass

    @abstractmethod
    def verify_chain(self) -> Dict[str, Any]:
        """Verify full chain integrity on disk."""
        pass


class KillSwitchPort(ABC):
    @abstractmethod
    def is_killed(self, scope: str, target_id: str, tenant_id: str) -> bool:
        """Check if kill switch is activated."""
        pass

    @abstractmethod
    def assert_not_killed(self, scope: str, target_id: str, tenant_id: str) -> None:
        """Raise exception if killed."""
        pass


class CompanyKernelPort(ABC):
    @abstractmethod
    def get_company_hierarchy(self, tenant_id: str, company_id: str) -> Dict[str, Any]:
        """Fetch departments, positions, and reporting lines."""
        pass

    @abstractmethod
    def validate_reporting_line(self, tenant_id: str, supervisor_id: str, subordinate_id: str) -> bool:
        """Ensure no circular reporting lines."""
        pass


class ApprovalPort(ABC):
    @abstractmethod
    def request_approval(
        self,
        tenant_id: str,
        company_id: str,
        requester_id: str,
        action_name: str,
        certification_hash: str,
        risk_tier: str
    ) -> str:
        """Create an ApprovalEngine record bound to certification hash; return approval_id."""
        pass

    @abstractmethod
    def get_decision(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Fetch decision status, approver principal, and timestamp."""
        pass


class WorkforcePort(ABC):
    @abstractmethod
    def assign_agent(
        self,
        tenant_id: str,
        company_id: str,
        agent_id: str,
        agent_version_id: str,
        assignee_kind: str,
        assignee_id: str,
        assigned_by: str
    ) -> str:
        """Assign certified agent to department, employee, or team."""
        pass


class RuntimePort(ABC):
    @abstractmethod
    def deploy_agent(
        self,
        tenant_id: str,
        agent_id: str,
        agent_version_id: str,
        channel: str,
        traffic_percent: int = 100
    ) -> str:
        """Mount compiled agent graph into execution runtime."""
        pass

    def deploy(self, job: BuildJob, environment: str = "staging") -> Dict[str, Any]:
        return {"status": "ok", "environment": environment, "build_id": job.build_id}


class SecretsPort(ABC):
    @abstractmethod
    def resolve_reference(self, tenant_id: str, secret_handle: str) -> str:
        """Resolve short-lived secret reference; raw secrets never logged or exposed."""
        pass


class IdentityPort(ABC):
    @abstractmethod
    def mint_agent_principal(
        self,
        tenant_id: str,
        company_id: str,
        slug: str,
        role_title: str
    ) -> str:
        """Mint a distinct AGENT principal (never an employee principal)."""
        pass


class DlpPort(ABC):
    @abstractmethod
    def scan_input(self, data: Any) -> Any:
        """Detect and redact secrets, credentials, or PII before prompt ingestion."""
        pass

    @abstractmethod
    def scan_output(self, data: Any) -> Any:
        """Sanitize output before returning to caller."""
        pass


class TelemetryPort(ABC):
    @abstractmethod
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        pass

    @abstractmethod
    def record_latency(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        pass
