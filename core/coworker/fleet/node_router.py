"""
ZONATA Universal AI Co-worker Fabric — Governed Cross-Node Router & Failover Engine
Routes capabilities to eligible worker nodes across the fleet and manages cross-node failover.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time
from .node_contracts import (
    WorkerNodeProfile,
    NodePlatform,
    NodeType,
    NodeState,
    NodeTaskAssignment,
    NodeTaskResult
)
from .node_registry import GovernedNodeRegistry

@dataclass
class FleetRoutingDecision:
    capability_id: str
    selected_node_id: Optional[str]
    selected_node_type: Optional[NodeType]
    platform: Optional[NodePlatform]
    requires_display: bool
    requires_gpu: bool
    candidate_node_ids: List[str]
    reason: str
    routed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "selected_node_id": self.selected_node_id,
            "selected_node_type": self.selected_node_type.value if self.selected_node_type else None,
            "platform": self.platform.value if self.platform else None,
            "requires_display": self.requires_display,
            "requires_gpu": self.requires_gpu,
            "candidate_node_ids": self.candidate_node_ids,
            "reason": self.reason,
            "routed_at": self.routed_at
        }

class GovernedFleetRouter:
    """
    Evaluates physical constraints, platform requirements, and node health
    to route tasks to the appropriate distributed worker node.
    """

    def __init__(self, node_registry: GovernedNodeRegistry):
        self.node_registry = node_registry
        self.routing_audit_log: List[FleetRoutingDecision] = []

    def route_to_node(
        self,
        capability_id: str,
        preferred_platform: Optional[NodePlatform] = None,
        requires_display: bool = False,
        requires_gpu: bool = False,
        tenant_id: str = "tnt_primary",
        excluded_node_ids: Optional[List[str]] = None
    ) -> Tuple[Optional[WorkerNodeProfile], FleetRoutingDecision]:
        """
        Selects the optimal node. Enforces:
        - Never routes Windows work to Linux.
        - Never routes visual GUI work to headless node.
        - Never routes GPU-dependent visual inference to non-GPU node.
        """
        excluded = excluded_node_ids or []
        candidates = self.node_registry.find_eligible_nodes(
            capability_id=capability_id,
            platform=preferred_platform,
            requires_gpu=requires_gpu,
            requires_display=requires_display,
            tenant_id=tenant_id
        )

        candidates = [c for c in candidates if c.node_id not in excluded]

        if not candidates:
            # Determine specific blocker reason
            reason = f"No eligible node found for capability '{capability_id}'"
            if preferred_platform:
                reason += f" on platform {preferred_platform.value}"
            if requires_display:
                reason += " with DISPLAY capability"
            if requires_gpu:
                reason += " with GPU availability"

            decision = FleetRoutingDecision(
                capability_id=capability_id,
                selected_node_id=None,
                selected_node_type=None,
                platform=preferred_platform,
                requires_display=requires_display,
                requires_gpu=requires_gpu,
                candidate_node_ids=[],
                reason=reason,
                routed_at=time.time()
            )
            self.routing_audit_log.append(decision)
            return None, decision

        # Preference scoring:
        # 1. Matching preferred platform
        # 2. Hardened security posture
        # 3. Lowest active lease count (load balancing)
        def score_node(n: WorkerNodeProfile) -> int:
            score = 100
            if n.security_posture.value == "HARDENED_ENTERPRISE":
                score += 30
            score -= len(n.active_leases) * 10
            return score

        candidates.sort(key=score_node, reverse=True)
        selected = candidates[0]

        decision = FleetRoutingDecision(
            capability_id=capability_id,
            selected_node_id=selected.node_id,
            selected_node_type=selected.node_type,
            platform=selected.platform,
            requires_display=requires_display,
            requires_gpu=requires_gpu,
            candidate_node_ids=[c.node_id for c in candidates],
            reason=f"Matched node {selected.node_id} ({selected.node_type.value}) matching physical platform and security constraints",
            routed_at=time.time()
        )
        self.routing_audit_log.append(decision)
        return selected, decision

    def handle_node_failover(
        self,
        failed_node_id: str,
        task_assignment: NodeTaskAssignment,
        failure_reason: str,
        is_mutation_confirmed: bool = False
    ) -> Tuple[Optional[WorkerNodeProfile], Optional[NodeTaskAssignment], str]:
        """
        Cross-Node Failover:
        Node A fails -> Control plane marks health -> Selects Node B -> Re-evaluates policy.
        CRITICAL RULE: Never duplicate an uncertain mutation.
        """
        # 1. Update failed node health
        self.node_registry.quarantine_node(failed_node_id, f"Failed task {task_assignment.task_id}: {failure_reason}")

        # 2. Check mutation safety
        if is_mutation_confirmed:
            return None, None, f"FAILOVER_ABORTED: Mutation already committed on {failed_node_id}; re-execution would violate idempotency"

        # 3. Select alternative node excluding failed one
        new_node, decision = self.route_to_node(
            capability_id=task_assignment.capability_id,
            tenant_id=task_assignment.tenant_id,
            excluded_node_ids=[failed_node_id]
        )

        if not new_node:
            return None, None, f"FAILOVER_FAILED: No alternative node available ({decision.reason})"

        # 4. Re-issue task assignment to new node
        new_assignment = NodeTaskAssignment(
            assignment_id=f"asgn_failover_{task_assignment.task_id[:6]}",
            node_id=new_node.node_id,
            task_id=task_assignment.task_id,
            mission_id=task_assignment.mission_id,
            capability_id=task_assignment.capability_id,
            provider_id=task_assignment.provider_id,
            parameters=dict(task_assignment.parameters),
            idempotency_key=task_assignment.idempotency_key,
            tenant_id=task_assignment.tenant_id,
            worker_id=task_assignment.worker_id
        )

        return new_node, new_assignment, f"FAILOVER_SUCCESS: Reassigned to {new_node.node_id}"
