"""
Agent Factory — Port Fakes
In-memory implementations of all ports for deterministic unit testing.
"""

from __future__ import annotations
import time
import uuid
import hashlib
from typing import Dict, List, Optional, Any

from agent_factory.ports import (
    AuthorityPort, PolicyPort, EvidenceLedgerPort, KillSwitchPort,
    CompanyKernelPort, ApprovalPort, WorkforcePort, RuntimePort,
    SecretsPort, IdentityPort, DlpPort, TelemetryPort,
    Principal, Resource, Decision, EvidenceEvent, BuildJob
)


class FakeAuthorityAdapter(AuthorityPort):
    def __init__(self, default_allow: bool = True, allow_all: Optional[bool] = None):
        if allow_all is not None:
            self.default_allow = allow_all
        else:
            self.default_allow = default_allow
        self.deny_actions: set = set()
        self.calls: List[Dict[str, Any]] = []

    def authorize(
        self,
        principal: Principal,
        action: str,
        resource: Resource,
        meta: Optional[Dict[str, Any]] = None
    ) -> Decision:
        self.calls.append({"principal": principal, "action": action, "resource": resource, "meta": meta})
        if action in self.deny_actions or not self.default_allow:
            return Decision(allow=False, deny=True, require_approval=False, reason="Denied by fake authority")
        return Decision(allow=True, deny=False, require_approval=False, reason="Allowed by fake authority")


class FakeEvidenceAdapter(EvidenceLedgerPort):
    def __init__(self, fail_append: bool = False):
        self.fail_append = fail_append
        self.events: List[EvidenceEvent] = []
        self.ledger_ids: List[str] = []

    def append_event(self, event: EvidenceEvent) -> str:
        if self.fail_append:
            raise RuntimeError("Fake evidence append failure (simulated ledger outage)")
        lid = f"EV-FAKE-{uuid.uuid4().hex[:8].upper()}"
        self.events.append(event)
        self.ledger_ids.append(lid)
        return lid

    def verify_chain(self) -> Dict[str, Any]:
        return {"valid": True, "records_checked": len(self.events)}


class FakeKillSwitchAdapter(KillSwitchPort):
    def __init__(self):
        self.killed_targets: set = set()

    @property
    def killed_scopes(self) -> set:
        return self.killed_targets

    def is_killed(self, scope: str, target_id: str, tenant_id: str) -> bool:
        return (scope, target_id) in self.killed_targets or ("GLOBAL", "SYSTEM") in self.killed_targets

    def assert_not_killed(self, scope: str, target_id: str, tenant_id: str) -> None:
        if self.is_killed(scope, target_id, tenant_id):
            raise PermissionError(f"Killswitch engaged for {scope}:{target_id}")

    def activate(self, scope: str, target_id: str):
        self.killed_targets.add((scope, target_id))

    def deactivate(self, scope: str, target_id: str):
        self.killed_targets.discard((scope, target_id))


class FakePolicyAdapter(PolicyPort):
    def evaluate_risk(self, capabilities: List[str], tools: List[str], data_scopes: List[str]) -> str:
        if any("destructive" in t or "payment" in t for t in tools):
            return "R3"
        if capabilities or tools:
            return "R1"
        return "R0"

    def assert_not_killed(self, tenant_id: str, subject_kind: str, subject_id: str) -> None:
        pass


class FakeApprovalAdapter(ApprovalPort):
    def __init__(self):
        self.approvals: Dict[str, Dict[str, Any]] = {}

    def request_approval(self, tenant_id: str, company_id: str, requester_id: str, action_name: str, certification_hash: str, risk_tier: str) -> str:
        aid = f"appr_fake_{uuid.uuid4().hex[:8]}"
        self.approvals[aid] = {
            "tenant_id": tenant_id, "company_id": company_id, "requester_id": requester_id,
            "action_name": action_name, "certification_hash": certification_hash,
            "risk_tier": risk_tier, "status": "PENDING"
        }
        return aid

    def get_decision(self, approval_id: str) -> Optional[Dict[str, Any]]:
        return self.approvals.get(approval_id)

    def decide(self, approval_id: str, status: str, decided_by: str):
        if approval_id in self.approvals:
            self.approvals[approval_id]["status"] = status
            self.approvals[approval_id]["decided_by"] = decided_by


class FakeIdentityAdapter(IdentityPort):
    def mint_agent_principal(self, tenant_id: str, company_id: str, slug: str, role_title: str) -> str:
        return f"principal.agent.{slug}_{uuid.uuid4().hex[:8]}"


class FakeCompanyAdapter(CompanyKernelPort):
    def get_company_hierarchy(self, tenant_id: str, company_id: str) -> Dict[str, Any]:
        return {"company_id": company_id, "departments": []}

    def validate_reporting_line(self, tenant_id: str, supervisor_id: str, subordinate_id: str) -> bool:
        return supervisor_id != subordinate_id


class FakeWorkforceAdapter(WorkforcePort):
    def __init__(self):
        self.assignments: List[Dict[str, Any]] = []

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
        asgn_id = f"asgn_{uuid.uuid4().hex[:8]}"
        self.assignments.append({
            "id": asgn_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "agent_version_id": agent_version_id,
            "assignee_kind": assignee_kind,
            "assignee_id": assignee_id
        })
        return asgn_id


class FakeRuntimeAdapter(RuntimePort):
    def __init__(self):
        self.deployments: List[Dict[str, Any]] = []

    def deploy_agent(
        self,
        tenant_id: str,
        agent_id: str,
        agent_version_id: str,
        channel: str,
        traffic_percent: int = 100
    ) -> str:
        dep_id = f"dep_{uuid.uuid4().hex[:8]}"
        self.deployments.append({
            "id": dep_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "agent_version_id": agent_version_id,
            "channel": channel,
            "traffic_percent": traffic_percent
        })
        return dep_id

    def deploy(self, job: BuildJob, environment: str = "staging") -> Dict[str, Any]:
        return {"status": "ok", "environment": environment, "build_id": job.build_id}


# Port aliases
FakeAuthorityPort = FakeAuthorityAdapter
FakeEvidencePort = FakeEvidenceAdapter
FakeKillSwitchPort = FakeKillSwitchAdapter
FakePolicyPort = FakePolicyAdapter
FakeApprovalPort = FakeApprovalAdapter
FakeIdentityPort = FakeIdentityAdapter
FakeCompanyPort = FakeCompanyAdapter
FakeWorkforcePort = FakeWorkforceAdapter
FakeRuntimePort = FakeRuntimeAdapter
