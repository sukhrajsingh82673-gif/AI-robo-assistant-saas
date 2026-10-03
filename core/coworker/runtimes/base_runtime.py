"""
ZONATA Universal AI Co-worker Fabric — Governed Worker Runtime Base Contracts
Defines standardized interfaces and session models for all specialized worker runtimes
(Hermes, OpenHands, OpenClaw, Browser, Computer Use, Terminal, and API).
Preserves ZONATA Sovereign Authority over all execution layers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import uuid
from dataclasses import dataclass, field

from ..contracts import (
    RiskLevel, ExecutionState, SupervisedControlMode, CoworkerProfile
)

class SessionState(str, Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    HUMAN_TAKEOVER = "HUMAN_TAKEOVER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    HEARTBEATING = "HEARTBEATING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
    UNCERTAIN = "UNCERTAIN"

@dataclass
class RuntimeSession:
    """
    Cryptographically tracked, governed worker runtime session.
    Every runtime invocation is bound to an authenticated tenant, company, and mission.
    """
    session_id: str
    tenant_id: str
    company_id: str
    worker_id: str
    mission_id: str
    execution_id: str
    node_id: str
    capability_scope: List[str]
    credential_scope: List[str]
    policy_scope: Dict[str, Any]
    lease_id: str
    risk_level: RiskLevel
    approval_state: str
    runtime_version: str
    provider_version: str
    evidence_context: Dict[str, Any] = field(default_factory=dict)
    state: SessionState = SessionState.INITIALIZING
    control_mode: SupervisedControlMode = SupervisedControlMode.AI_CONTROL
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    heartbeat_at: float = field(default_factory=time.time)
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def log(self, message: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        entry = f"[{ts}][{self.session_id}] {message}"
        self.logs.append(entry)
        self.updated_at = time.time()

    def record_heartbeat(self):
        self.heartbeat_at = time.time()
        self.updated_at = self.heartbeat_at

@dataclass
class BackgroundJob:
    """
    Persistent background job state representing an autonomous long-running task.
    """
    job_id: str
    session_id: str
    worker_id: str
    tenant_id: str
    mission_id: str
    description: str
    status: JobStatus = JobStatus.QUEUED
    progress_percent: float = 0.0
    current_step: str = "Initialized"
    lease_expires_at: float = field(default_factory=lambda: time.time() + 300.0)
    last_heartbeat: float = field(default_factory=time.time)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    evidence_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_progress(self, percent: float, step: str):
        self.progress_percent = min(100.0, max(0.0, percent))
        self.current_step = step
        self.last_heartbeat = time.time()
        if self.progress_percent >= 100.0:
            self.status = JobStatus.SUCCEEDED
        elif self.status == JobStatus.QUEUED:
            self.status = JobStatus.RUNNING

class WorkerRuntime(ABC):
    """
    Abstract Base Class for all ZONATA Co-Worker Specialized Runtimes.
    Subclasses wrap concrete engines (Hermes, OpenHands, OpenClaw, Browser, etc.)
    under strict ZONATA sovereign supervision.
    """

    @abstractmethod
    def runtime_id(self) -> str:
        """Unique ID for this runtime engine."""
        pass

    @abstractmethod
    def runtime_type(self) -> str:
        """Category/Type (e.g. HERMES, OPENHANDS, OPENCLAW, BROWSER, CUA)."""
        pass

    @abstractmethod
    def version(self) -> str:
        """Upstream engine version."""
        pass

    @abstractmethod
    def supported_capabilities(self) -> List[str]:
        """List of capability_ids this runtime can fulfill."""
        pass

    @abstractmethod
    def create_worker(self, profile: CoworkerProfile) -> str:
        """Configures a specialized worker profile inside this runtime."""
        pass

    @abstractmethod
    def start_session(self, session: RuntimeSession) -> bool:
        """Initializes a governed session."""
        pass

    @abstractmethod
    def submit_mission(self, session_id: str, mission: Dict[str, Any]) -> str:
        """Submits a mission to be decomposed and run."""
        pass

    @abstractmethod
    def run_foreground(self, session_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronously executes a task in the foreground."""
        pass

    @abstractmethod
    def run_background(self, session_id: str, task: Dict[str, Any]) -> str:
        """Dispatches an asynchronous background execution returning a job_id."""
        pass

    @abstractmethod
    def pause(self, session_id: str) -> bool:
        """Pauses runtime execution immediately."""
        pass

    @abstractmethod
    def resume(self, session_id: str) -> bool:
        """Resumes a paused runtime session."""
        pass

    @abstractmethod
    def redirect(self, session_id: str, new_instruction: str) -> bool:
        """Alters running trajectory with new instruction."""
        pass

    @abstractmethod
    def observe(self, session_id: str) -> Dict[str, Any]:
        """Observes current state, memory, and telemetry."""
        pass

    @abstractmethod
    def collect_logs(self, session_id: str) -> List[str]:
        """Collects execution log stream."""
        pass

    @abstractmethod
    def request_input(self, session_id: str, prompt: str) -> str:
        """Requests user or supervisor input."""
        pass

    @abstractmethod
    def take_control(self, session_id: str) -> bool:
        """Enters HUMAN_TAKEOVER mode; suspends AI execution."""
        pass

    @abstractmethod
    def return_control(self, session_id: str, human_state_delta: Optional[Dict[str, Any]] = None) -> bool:
        """Returns session to autonomous AI control after reconciling state."""
        pass

    @abstractmethod
    def terminate(self, session_id: str, reason: str = "COMPLETED") -> bool:
        """Terminates session and tears down sandboxes."""
        pass

    @abstractmethod
    def recover(self, session_id: str, failure_context: Dict[str, Any]) -> bool:
        """Recovers session from failure state."""
        pass

    @abstractmethod
    def verify(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Executes independent out-of-band verification."""
        pass

    @abstractmethod
    def collect_evidence(self, session_id: str) -> Dict[str, Any]:
        """Bundles cryptographic SHA-256 evidence package."""
        pass
