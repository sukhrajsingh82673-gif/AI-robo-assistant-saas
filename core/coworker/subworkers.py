"""
ZONATA Universal AI Co-worker Fabric — Parallel Sub-Worker Coordination
Manages parent-child worker delegation for specialized tasks:
- Research Worker
- Browser Worker
- Data Worker
- Coding Worker
- Verification Worker
- Document Worker
- Terminal Worker
- Communication Worker

Non-Negotiable Invariants:
1. Sub-workers are strictly subordinate to the parent mission and ZONATA sovereign authority.
2. No child worker can escalate its authority, budget, or permission scope beyond its parent.
3. Every sub-worker tracks parent_worker_id, child_worker_id, mission_id, task_id, lease, result, evidence.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from enum import Enum

from .contracts import RiskLevel, ExecutionResult, VerificationStatus

class SubWorkerRole(str, Enum):
    RESEARCH = "Research Worker"
    BROWSER = "Browser Worker"
    DATA = "Data Worker"
    CODING = "Coding Worker"
    VERIFICATION = "Verification Worker"
    DOCUMENT = "Document Worker"
    TERMINAL = "Terminal Worker"
    COMMUNICATION = "Communication Worker"

@dataclass
class SubWorkerAssignment:
    parent_worker_id: str
    child_worker_id: str
    mission_id: str
    task_id: str
    role: SubWorkerRole
    scope: List[str]
    lease_expires_at: float
    budget_allocated_usd: float
    permissions: List[str]
    status: str = "ALLOCATED" # ALLOCATED, RUNNING, COMPLETED, FAILED, REVOKED
    result: Optional[Dict[str, Any]] = None
    evidence_hash: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

class SubWorkerCoordinator:
    """
    Coordinates multi-sub-worker swarms under strict parent hierarchy.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._assignments: Dict[str, SubWorkerAssignment] = {} # child_worker_id -> assignment

    def spawn_subworker(
        self,
        parent_worker_id: str,
        mission_id: str,
        role: SubWorkerRole,
        parent_scope: List[str],
        parent_budget_usd: float,
        task_id: Optional[str] = None,
        requested_scope: Optional[List[str]] = None,
        budget_usd: float = 0.0,
        lease_sec: float = 300.0
    ) -> SubWorkerAssignment:
        """
        Spawns a specialized sub-worker.
        Enforces that child scope is a strict subset of parent scope and child budget <= parent budget.
        """
        child_id = f"cw_{role.name.lower()}_{uuid.uuid4().hex[:6]}"
        tid = task_id or f"task_{uuid.uuid4().hex[:6]}"

        # Authority invariant: Child scope must be subset of parent scope
        effective_scope = []
        req_scope = requested_scope or parent_scope
        for item in req_scope:
            if item in parent_scope or "all" in parent_scope:
                effective_scope.append(item)

        # Budget invariant: Child budget cannot exceed parent budget
        effective_budget = min(budget_usd, parent_budget_usd)

        assignment = SubWorkerAssignment(
            parent_worker_id=parent_worker_id,
            child_worker_id=child_id,
            mission_id=mission_id,
            task_id=tid,
            role=role,
            scope=effective_scope,
            lease_expires_at=time.time() + lease_sec,
            budget_allocated_usd=effective_budget,
            permissions=[f"subworker:{role.name.lower()}:execute"],
            status="ALLOCATED"
        )
        self._assignments[child_id] = assignment
        return assignment

    def complete_subworker_task(
        self,
        child_worker_id: str,
        result: Dict[str, Any],
        evidence_digest: Optional[str] = None
    ) -> bool:
        assign = self._assignments.get(child_worker_id)
        if not assign or assign.status in ["COMPLETED", "REVOKED"]:
            return False

        assign.status = "COMPLETED"
        assign.result = result
        digest = evidence_digest or hashlib.sha256(str(result).encode()).hexdigest()
        assign.evidence_hash = digest
        assign.completed_at = time.time()
        return True

    def fail_subworker_task(self, child_worker_id: str, error: str) -> bool:
        assign = self._assignments.get(child_worker_id)
        if not assign:
            return False
        assign.status = "FAILED"
        assign.result = {"error": error}
        assign.completed_at = time.time()
        return True

    def get_mission_subworkers(self, mission_id: str) -> List[SubWorkerAssignment]:
        return [a for a in self._assignments.values() if a.mission_id == mission_id]

    def get_subworker(self, child_worker_id: str) -> Optional[SubWorkerAssignment]:
        return self._assignments.get(child_worker_id)
