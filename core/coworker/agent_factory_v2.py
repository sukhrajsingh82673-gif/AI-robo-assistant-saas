"""
ZONATA Autonomous Coworker 2.0 — Ephemeral Specialized Agent Factory
Factory for dynamically creating, governing, and decommissioning ephemeral sub-workers.
Enforces non-negotiable sovereign invariants:
  1. Scope Invariant: Child authority scope <= Parent authority scope.
  2. Budget Invariant: Child micro-budget <= Parent available budget.
  3. Lease Invariant: Child lease TTL <= Parent lease expiration.
"""

from __future__ import annotations
import time
import uuid
from typing import Dict, List, Optional, Any
from .contracts_v2 import (
    SubworkerV2Record, CoworkerExecutionLease, LeaseStatus, CoworkerV2Task
)
from .subworkers_v2 import SubWorkerArchetype, ARCHETYPE_REGISTRY, ArchetypeSpec
from .db_store_v2 import CoworkerDbStoreV2


class EphemeralAgentFactoryV2:
    """
    Governed Factory for spawning and auto-decommissioning specialized sub-worker agents.
    """

    _instance: Optional[EphemeralAgentFactoryV2] = None

    @classmethod
    def get_instance(
        cls,
        db_store: Optional[CoworkerDbStoreV2] = None,
        store: Optional[CoworkerDbStoreV2] = None
    ) -> EphemeralAgentFactoryV2:
        if cls._instance is None:
            cls._instance = cls(db_store=db_store, store=store)
        return cls._instance

    def __init__(
        self,
        db_store: Optional[CoworkerDbStoreV2] = None,
        store: Optional[CoworkerDbStoreV2] = None
    ):
        self.db = store or db_store or CoworkerDbStoreV2.get_instance()
        self._active_instances: Dict[str, SubworkerV2Record] = {}

    def list_active_subworkers(self, task_id: Optional[str] = None) -> List[SubworkerV2Record]:
        active = [w for w in self._active_instances.values() if w.status == "ACTIVE"]
        if task_id:
            active = [w for w in active if w.parent_task_id == task_id]
        return active

    def spawn_agent(
        self,
        task_id: str,
        archetype: SubWorkerArchetype,
        budget_limit: Optional[float] = None,
        requested_scope: Optional[List[str]] = None,
        lease_ttl_sec: float = 300.0
    ) -> SubworkerV2Record:
        parent_task = self.db.get_task(task_id)
        if not parent_task:
            # An unknown task id must not become an authority grant. The
            # placeholder parent is least-privilege, so a caller cannot obtain
            # elevated scope by inventing a task id.
            parent_task = CoworkerV2Task(
                task_id=task_id,
                mission_id=f"msn_{uuid.uuid4().hex[:8]}",
                tenant_id="tnt_primary",
                company_id="cmp_primary",
                title="Ephemeral Task",
                description="Auto-generated parent task (least privilege placeholder)",
                budget_allocated_usd=5.0,
                authority_scope=["read_only"]
            )
            self.db.save_task(parent_task)
        return self.spawn_subworker(
            parent_task=parent_task,
            archetype=archetype,
            requested_scope=requested_scope,
            micro_budget_usd=budget_limit,
            lease_ttl_sec=lease_ttl_sec
        )

    def decommission_agent(self, worker_id: str, reason: str = "completed") -> bool:
        return self.decommission_subworker(worker_id=worker_id, reason=reason)

    def decommission_all_for_task(self, task_id: str, reason: str = "task_completed") -> int:
        count = 0
        for worker_id, subworker in list(self._active_instances.items()):
            if subworker.parent_task_id == task_id:
                if self.decommission_subworker(worker_id, reason=reason):
                    count += 1
        return count

    def spawn_subworker(
        self,
        parent_task: CoworkerV2Task,
        archetype: SubWorkerArchetype,
        requested_scope: Optional[List[str]] = None,
        micro_budget_usd: Optional[float] = None,
        lease_ttl_sec: float = 300.0
    ) -> SubworkerV2Record:
        """
        Spawns a specialized sub-worker under strict parent subordination invariants.
        """
        spec = ARCHETYPE_REGISTRY.get(archetype)
        if not spec:
            raise ValueError(f"Unknown archetype: {archetype}")

        # Invariant 1: Authority Scope Invariant (Child scope must be a strict subset of parent)
        effective_scope: List[str] = []
        target_scope = requested_scope or spec.allowed_tools
        parent_scope = parent_task.authority_scope

        def _covered(item: str) -> bool:
            """True when the parent scope actually covers `item`.

            Exact match, or the parent holds a namespace root ("browser" covers
            "browser.open"). "admin"/"all" are whole-scope grants. Substring
            matching is deliberately avoided: "read" must not cover "thread".
            """
            for perm in parent_scope:
                if perm in ("admin", "all"):
                    return True
                if item == perm:
                    return True
                if item.startswith(perm + "."):
                    return True
            return False

        for item in target_scope:
            if _covered(item):
                effective_scope.append(item)

        if not effective_scope:
            # Fallback to least-privilege read_only
            effective_scope = ["read_only"]

        # Invariant 2: Budget Invariant (Child budget <= Parent task's remaining budget)
        parent_remaining = max(0.0, parent_task.budget_allocated_usd - parent_task.budget_spent_usd)
        candidate_budget = micro_budget_usd or spec.default_max_budget_usd
        effective_budget = min(candidate_budget, parent_remaining)

        # Invariant 3: Lease Invariant
        now = time.time()
        worker_id = f"sub_{archetype.name.lower()}_{uuid.uuid4().hex[:6]}"
        lease_id = f"lease_sub_{uuid.uuid4().hex[:6]}"

        lease = CoworkerExecutionLease(
            lease_id=lease_id,
            task_id=parent_task.task_id,
            worker_id=worker_id,
            acquired_at=now,
            expires_at=now + lease_ttl_sec,
            heartbeat_at=now,
            ttl_seconds=lease_ttl_sec,
            status=LeaseStatus.ACTIVE
        )
        self.db.save_lease(lease)

        subworker = SubworkerV2Record(
            worker_id=worker_id,
            parent_task_id=parent_task.task_id,
            parent_worker_id=parent_task.assigned_worker_id or "parent_orchestrator",
            mission_id=parent_task.mission_id,
            archetype=archetype.value,
            authority_scope=effective_scope,
            budget_limit_usd=effective_budget,
            budget_spent_usd=0.0,
            lease_id=lease_id,
            status="ACTIVE",
            created_at=now,
            metadata={
                "risk_limit": spec.default_risk_limit,
                "description": spec.description
            }
        )
        self.db.save_subworker(subworker)
        self._active_instances[worker_id] = subworker
        return subworker

    def decommission_subworker(self, worker_id: str, reason: str = "completed") -> bool:
        """
        Decommissions an active sub-worker, revoking its lease and releasing its resources.
        """
        subworker = self.db.get_subworker(worker_id)
        if not subworker:
            return False

        now = time.time()
        subworker.status = "DECOMMISSIONED"
        subworker.decommissioned_at = now
        subworker.metadata["decommission_reason"] = reason
        self.db.save_subworker(subworker)

        # Revoke execution lease
        if subworker.lease_id:
            lease = self.db.get_lease(subworker.lease_id)
            if lease:
                lease.release()
                self.db.save_lease(lease)

        self._active_instances.pop(worker_id, None)
        return True

    def reap_expired_subworkers(self) -> List[str]:
        """
        Automatically decommissions any sub-workers whose execution leases have lapsed.
        """
        now = time.time()
        reaped: List[str] = []

        for worker_id, subworker in list(self._active_instances.items()):
            lease = self.db.get_lease(subworker.lease_id)
            if not lease or not lease.is_valid(now):
                self.decommission_subworker(worker_id, reason="lease_expired_auto_reaped")
                reaped.append(worker_id)

        return reaped
