"""
ZONATA Universal AI Co-worker Fabric — Governed Worker Node Registry
Manages registration, cryptographic authentication, authority gating, health heartbeats,
quarantining, and state transitions of distributed execution plane nodes.
"""

from typing import Dict, List, Optional, Tuple, Any
import hashlib
import hmac
import time
import uuid
from .node_contracts import (
    WorkerNodeRegistrationRequest,
    WorkerNodeProfile,
    NodeState,
    NodeType,
    NodePlatform,
    SecurityPosture
)

class GovernedNodeRegistry:
    """
    Authoritative Registry for Distributed Execution Plane Nodes.
    The Control Plane strictly validates every connecting node before routing tasks.
    A node never receives authority merely by connecting.
    """

    def __init__(self, heartbeat_timeout_sec: float = 60.0):
        self.heartbeat_timeout = heartbeat_timeout_sec
        self._nodes: Dict[str, WorkerNodeProfile] = {}
        self._registration_tokens: Dict[str, str] = {} # token_id -> secret_hash

    def register_registration_token(self, token_name: str, secret: str):
        """Allows Control Plane operator to issue pre-shared registration secrets."""
        h = hashlib.sha256(secret.encode()).hexdigest()
        self._registration_tokens[token_name] = h

    def register_node(
        self,
        req: WorkerNodeRegistrationRequest,
        expected_secret: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[WorkerNodeProfile]]:
        """
        Registers a worker node into the fleet.
        Initial state is REGISTERED (not yet AUTHORIZED to run production tasks).
        """
        # 1. Authenticate registration secret if configured
        if expected_secret:
            req_hash = hashlib.sha256(req.registration_secret.encode()).hexdigest()
            exp_hash = hashlib.sha256(expected_secret.encode()).hexdigest()
            if not hmac.compare_digest(req_hash, exp_hash):
                return False, "Node authentication failed: invalid registration secret", None

        # 2. Sanity check platform vs capabilities
        # A Linux node cannot claim Win32 UIA; a headless node cannot claim physical GUI display
        if req.platform == NodePlatform.LINUX and any("win32" in cap.lower() for cap in req.capabilities):
            return False, "Validation failed: Linux node cannot advertise Windows Win32 capabilities", None
        if not req.display_availability and any(cap in ["desktop.mouse_click", "desktop.window_inspect"] for cap in req.capabilities):
            return False, "Validation failed: Headless node cannot advertise physical desktop GUI capabilities", None

        # 3. Create profile
        auth_token = f"nat_{uuid.uuid4().hex}"
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()

        profile = WorkerNodeProfile(
            node_id=req.node_id,
            tenant_scope=req.tenant_scope,
            node_type=req.node_type,
            platform=req.platform,
            architecture=req.architecture,
            os_version=req.os_version,
            runtime_version=req.runtime_version,
            capabilities=list(req.capabilities),
            installed_providers=list(req.installed_providers),
            gpu_availability=req.gpu_availability,
            display_availability=req.display_availability,
            security_posture=req.security_posture,
            credential_scope=[],
            provider_qualification_status={},
            state=NodeState.REGISTERED,
            network_status="CONNECTED",
            auth_token_hash=token_hash
        )

        self._nodes[req.node_id] = profile
        return True, auth_token, profile

    def authorize_node(self, node_id: str, authorized_by: str = "ControlPlaneAuthority") -> Tuple[bool, str]:
        """Explicitly grants execution authorization to a registered node."""
        node = self._nodes.get(node_id)
        if not node:
            return False, f"Node {node_id} not found"
        if node.state == NodeState.REVOKED:
            return False, f"Node {node_id} is permanently REVOKED"
        node.state = NodeState.AUTHORIZED
        node.metadata["authorized_by"] = authorized_by
        node.metadata["authorized_at"] = time.time()
        return True, f"Node {node_id} AUTHORIZED"

    def record_heartbeat(self, node_id: str, reported_metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Records node heartbeat and transitions from AUTHORIZED to HEALTHY."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        if node.state in [NodeState.REVOKED, NodeState.QUARANTINED]:
            return False
        node.last_heartbeat = time.time()
        node.network_status = "CONNECTED"
        if node.state == NodeState.AUTHORIZED:
            node.state = NodeState.HEALTHY
        if reported_metrics:
            node.metadata["last_metrics"] = reported_metrics
        return True

    def quarantine_node(self, node_id: str, reason: str) -> bool:
        """Immediately quarantines a node (stops task routing, terminates active leases)."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.state = NodeState.QUARANTINED
        node.metadata["quarantine_reason"] = reason
        node.metadata["quarantined_at"] = time.time()
        return True

    def revoke_node(self, node_id: str, reason: str) -> bool:
        """Permanently revokes a node from the fleet."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.state = NodeState.REVOKED
        node.metadata["revocation_reason"] = reason
        node.metadata["revoked_at"] = time.time()
        return True

    def check_health_and_expire(self) -> List[str]:
        """Scans nodes for missing heartbeats and marks them OFFLINE."""
        now = time.time()
        offline_nodes = []
        for nid, node in self._nodes.items():
            if node.state in [NodeState.HEALTHY, NodeState.AUTHORIZED]:
                if now - node.last_heartbeat > self.heartbeat_timeout:
                    node.state = NodeState.OFFLINE
                    node.network_status = "DISCONNECTED"
                    offline_nodes.append(nid)
        return offline_nodes

    def get_node(self, node_id: str) -> Optional[WorkerNodeProfile]:
        return self._nodes.get(node_id)

    def list_nodes(self, state_filter: Optional[NodeState] = None) -> List[WorkerNodeProfile]:
        if state_filter:
            return [n for n in self._nodes.values() if n.state == state_filter]
        return list(self._nodes.values())

    def find_eligible_nodes(
        self,
        capability_id: str,
        platform: Optional[NodePlatform] = None,
        requires_gpu: bool = False,
        requires_display: bool = False,
        tenant_id: str = "tnt_primary"
    ) -> List[WorkerNodeProfile]:
        """Finds active, authorized, healthy nodes matching capability & physical constraints."""
        eligible = []
        self.check_health_and_expire()

        for node in self._nodes.values():
            if node.state not in [NodeState.HEALTHY, NodeState.AUTHORIZED]:
                continue
            if node.tenant_scope not in ["*", tenant_id]:
                continue
            if platform and node.platform != platform:
                continue
            if requires_gpu and not node.gpu_availability:
                continue
            if requires_display and not node.display_availability:
                continue
            if capability_id in node.capabilities or "*" in node.capabilities:
                eligible.append(node)
        return eligible
