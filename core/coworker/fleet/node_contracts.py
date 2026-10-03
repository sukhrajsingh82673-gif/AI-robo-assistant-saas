"""
ZONATA Universal AI Co-worker Fabric — Distributed Worker Fleet Contracts
Defines node types, platforms, registration tokens, capabilities, and node lifecycle states.
Distinguishes ZONATA Control Plane from Distributed Execution Plane.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import uuid

class NodePlatform(str, Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "darwin"
    ANDROID_PROOT = "android_proot"
    CLOUD_CONTAINER = "cloud_container"

class NodeType(str, Enum):
    LINUX_NODE = "LINUX_NODE"
    WINDOWS_NODE = "WINDOWS_NODE"
    MACOS_NODE = "MACOS_NODE"
    GPU_NODE = "GPU_NODE"
    BROWSER_NODE = "BROWSER_NODE"
    DESKTOP_NODE = "DESKTOP_NODE"

class NodeState(str, Enum):
    REGISTERED = "REGISTERED"
    AUTHORIZED = "AUTHORIZED"
    HEALTHY = "HEALTHY"
    DRAINING = "DRAINING"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"
    OFFLINE = "OFFLINE"

class SecurityPosture(str, Enum):
    HARDENED_ENTERPRISE = "HARDENED_ENTERPRISE"
    STANDARD_WORKSTATION = "STANDARD_WORKSTATION"
    ISOLATED_SANDBOX = "ISOLATED_SANDBOX"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"

@dataclass
class WorkerNodeRegistrationRequest:
    """Request payload sent by an external node to join the fleet."""
    node_id: str
    tenant_scope: str
    node_type: NodeType
    platform: NodePlatform
    architecture: str
    os_version: str
    runtime_version: str
    capabilities: List[str]
    installed_providers: List[str]
    gpu_availability: bool = False
    display_availability: bool = False
    security_posture: SecurityPosture = SecurityPosture.STANDARD_WORKSTATION
    registration_secret: str = ""

@dataclass
class WorkerNodeProfile:
    """Governed registration record for a worker node in the control plane."""
    node_id: str
    tenant_scope: str
    node_type: NodeType
    platform: NodePlatform
    architecture: str
    os_version: str
    runtime_version: str
    capabilities: List[str]
    installed_providers: List[str]
    gpu_availability: bool
    display_availability: bool
    security_posture: SecurityPosture
    credential_scope: List[str]
    provider_qualification_status: Dict[str, str]
    state: NodeState = NodeState.REGISTERED
    network_status: str = "CONNECTED"
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    lease_state: str = "IDLE"
    active_leases: List[str] = field(default_factory=list)
    auth_token_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "tenant_scope": self.tenant_scope,
            "node_type": self.node_type.value,
            "platform": self.platform.value,
            "architecture": self.architecture,
            "os_version": self.os_version,
            "runtime_version": self.runtime_version,
            "capabilities": self.capabilities,
            "installed_providers": self.installed_providers,
            "gpu_availability": self.gpu_availability,
            "display_availability": self.display_availability,
            "security_posture": self.security_posture.value,
            "credential_scope": self.credential_scope,
            "provider_qualification_status": self.provider_qualification_status,
            "state": self.state.value,
            "network_status": self.network_status,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "lease_state": self.lease_state,
            "active_leases": self.active_leases
        }

@dataclass
class NodeTaskAssignment:
    """Governed task assigned by the control plane to an execution node."""
    assignment_id: str
    node_id: str
    task_id: str
    mission_id: str
    capability_id: str
    provider_id: str
    parameters: Dict[str, Any]
    assigned_at: float = field(default_factory=time.time)
    lease_ttl_sec: float = 300.0
    idempotency_key: Optional[str] = None
    tenant_id: str = "tnt_primary"
    worker_id: str = "wrk_default"

@dataclass
class NodeTaskResult:
    """Execution result returned by an execution node back to the control plane."""
    assignment_id: str
    node_id: str
    task_id: str
    status: str
    output: Dict[str, Any]
    error_message: Optional[str] = None
    pre_state_hash: Optional[str] = None
    post_state_hash: Optional[str] = None
    completed_at: float = field(default_factory=time.time)
    idempotency_key: Optional[str] = None
