"""
ZONATA Universal AI Co-worker Fabric — Remote Node Worker Agent & Protocol
Handles node-side task execution, heartbeat daemon loop, and remote human takeover across nodes.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid
from .node_contracts import (
    WorkerNodeProfile,
    NodeTaskAssignment,
    NodeTaskResult,
    NodeState
)
from ..contracts import SupervisedControlMode

class RemoteNodeWorkerAgent:
    """
    Agent running on an execution plane worker node.
    Executes assigned tasks, sends heartbeats, and supports remote human takeover.
    """

    def __init__(self, profile: WorkerNodeProfile, auth_token: str):
        self.profile = profile
        self.auth_token = auth_token
        self.control_mode = SupervisedControlMode.AI_CONTROL
        self.active_tasks: Dict[str, NodeTaskAssignment] = {}
        self.simulated_gui_state: Dict[str, Any] = {
            "active_window": "DesktopRoot",
            "open_apps": [],
            "focus_element": None
        }
        self.execution_history: List[Dict[str, Any]] = []

    def receive_assignment(self, assignment: NodeTaskAssignment) -> Tuple[bool, str]:
        """Validates assignment and accepts task lease."""
        if self.profile.state not in [NodeState.AUTHORIZED, NodeState.HEALTHY]:
            return False, f"Node {self.profile.node_id} is in state {self.profile.state.value}; rejecting assignment"
        if assignment.capability_id not in self.profile.capabilities and "*" not in self.profile.capabilities:
            return False, f"Capability {assignment.capability_id} not supported on node {self.profile.node_id}"

        self.active_tasks[assignment.task_id] = assignment
        self.profile.active_leases.append(assignment.assignment_id)
        self.profile.lease_state = "BUSY"
        return True, "TASK_ACKNOWLEDGED"

    def execute_assignment(self, assignment: NodeTaskAssignment) -> NodeTaskResult:
        """Executes the task on the node under current control mode."""
        if self.control_mode == SupervisedControlMode.HUMAN_CONTROL:
            return NodeTaskResult(
                assignment_id=assignment.assignment_id,
                node_id=self.profile.node_id,
                task_id=assignment.task_id,
                status="FROZEN_FOR_HUMAN_TAKEOVER",
                output={},
                error_message="Execution paused: human operator has taken over the remote node",
                idempotency_key=assignment.idempotency_key
            )

        # Execute simulated or real node action
        pre_hash = f"pre_{hash(str(self.simulated_gui_state))}"
        
        # Capability specific simulated node execution
        output = {
            "node_id": self.profile.node_id,
            "platform": self.profile.platform.value,
            "executed_capability": assignment.capability_id,
            "parameters": assignment.parameters,
            "result_status": "SUCCESS"
        }

        if "app" in assignment.parameters:
            app_name = assignment.parameters["app"]
            if app_name not in self.simulated_gui_state["open_apps"]:
                self.simulated_gui_state["open_apps"].append(app_name)
            self.simulated_gui_state["active_window"] = app_name

        post_hash = f"post_{hash(str(self.simulated_gui_state))}"

        result = NodeTaskResult(
            assignment_id=assignment.assignment_id,
            node_id=self.profile.node_id,
            task_id=assignment.task_id,
            status="SUCCESS",
            output=output,
            pre_state_hash=pre_hash,
            post_state_hash=post_hash,
            idempotency_key=assignment.idempotency_key
        )

        self.execution_history.append({"task_id": assignment.task_id, "status": "SUCCESS"})
        if assignment.assignment_id in self.profile.active_leases:
            self.profile.active_leases.remove(assignment.assignment_id)
        self.profile.lease_state = "IDLE" if not self.profile.active_leases else "BUSY"
        return result

    # -------------------------------------------------------------------------
    # Remote Human Takeover Protocol
    # -------------------------------------------------------------------------
    def remote_human_takeover(self, operator_id: str) -> Tuple[bool, str]:
        """Freezes AI execution on remote node and transfers control to human."""
        self.control_mode = SupervisedControlMode.HUMAN_CONTROL
        self.profile.metadata["human_operator"] = operator_id
        self.profile.metadata["takeover_started"] = time.time()
        return True, f"Remote node {self.profile.node_id} frozen: control granted to human operator {operator_id}"

    def remote_human_action(self, manual_state_mutation: Dict[str, Any]) -> Tuple[bool, str]:
        """Human modifies application or files on remote desktop."""
        if self.control_mode != SupervisedControlMode.HUMAN_CONTROL:
            return False, "Node is not under human control"
        self.simulated_gui_state.update(manual_state_mutation)
        return True, "Human mutation applied to remote node state"

    def remote_release_control_to_ai(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Human releases control; AI re-observes and reconciles state."""
        self.control_mode = SupervisedControlMode.AI_CONTROL
        self.profile.metadata.pop("human_operator", None)
        reconciled_state = dict(self.simulated_gui_state)
        return True, "Control returned to AI worker with reconciled state", reconciled_state
