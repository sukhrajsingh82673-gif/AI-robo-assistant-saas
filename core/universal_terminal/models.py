"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Data Models
Defines stable architectural abstractions, session contracts, command plans,
runtime profiles, isolation levels, execution modes, and structured results.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

class ExecutionMode(str, Enum):
    LOCAL_SANDBOX = "LOCAL_SANDBOX"
    LOCAL_VM = "LOCAL_VM"
    LOCAL_CONTAINER = "LOCAL_CONTAINER"
    REMOTE_VM = "REMOTE_VM"
    REMOTE_CONTAINER = "REMOTE_CONTAINER"
    DEDICATED_BUILD_NODE = "DEDICATED_BUILD_NODE"
    SECURITY_LAB = "SECURITY_LAB"
    DISPOSABLE_RUNTIME = "DISPOSABLE_RUNTIME"
    AUTHORIZED_HOST_EXECUTION = "AUTHORIZED_HOST_EXECUTION"
    PRODUCTION_EXECUTION = "PRODUCTION_EXECUTION"

class IsolationLevel(str, Enum):
    LEVEL_0_OBSERVE = "LEVEL_0"           # Observe / inspect only
    LEVEL_1_SANDBOX = "LEVEL_1"           # Restricted sandbox (cwd, non-root, tempfs)
    LEVEL_2_CONTAINER = "LEVEL_2"         # Isolated container / cgroups / namespaces
    LEVEL_3_VM = "LEVEL_3"                # Isolated microVM (hardware virtualization)
    LEVEL_4_HOST = "LEVEL_4"              # Controlled host execution with lease
    LEVEL_5_PRODUCTION = "LEVEL_5"        # Production execution with cryptographic gates

class DesktopEnvironment(str, Enum):
    HEADLESS = "HEADLESS"                 # Zero-GUI headless execution (default)
    XFCE = "XFCE"                         # Lightweight desktop
    LXQT = "LXQT"                         # Ultra-lightweight Qt desktop
    GNOME = "GNOME"                       # Full-featured modern desktop
    KDE_PLASMA = "KDE_PLASMA"             # Feature-rich modular desktop
    VIRTUAL_DISPLAY = "VIRTUAL_DISPLAY"   # Xvfb / headless display buffer

class NetworkMode(str, Enum):
    OFFLINE = "OFFLINE"
    RESTRICTED_NETWORK = "RESTRICTED_NETWORK"
    ALLOWLIST_DOMAINS = "ALLOWLIST_DOMAINS"
    PACKAGE_REPOSITORIES_ONLY = "PACKAGE_REPOSITORIES_ONLY"
    INTERNAL_NETWORK = "INTERNAL_NETWORK"
    INTERNET_ENABLED_SANDBOX = "INTERNET_ENABLED_SANDBOX"
    PRODUCTION_NETWORK = "PRODUCTION_NETWORK"

class TerminalStatus(str, Enum):
    DISCOVERING = "DISCOVERING"
    SELECTING_RUNTIME = "SELECTING_RUNTIME"
    PROVISIONING = "PROVISIONING"
    PREPARING = "PREPARING"
    WAITING_AUTHORIZATION = "WAITING_AUTHORIZATION"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    STOPPED = "STOPPED"

class TerminalCommandRisk(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOCAL_MUTATION = "LOCAL_MUTATION"
    PACKAGE_INSTALL = "PACKAGE_INSTALL"
    PROCESS_CONTROL = "PROCESS_CONTROL"
    NETWORK_ACCESS = "NETWORK_ACCESS"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    ACCOUNT_OPERATION = "ACCOUNT_OPERATION"
    DATA_DELETION = "DATA_DELETION"
    SYSTEM_MUTATION = "SYSTEM_MUTATION"
    PRODUCTION_MUTATION = "PRODUCTION_MUTATION"
    FINANCIAL_ACTION = "FINANCIAL_ACTION"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"

class SemanticExecutionState(str, Enum):
    COMMAND_EXECUTED = "COMMAND_EXECUTED"
    COMMAND_SUCCEEDED = "COMMAND_SUCCEEDED"
    TASK_VERIFIED = "TASK_VERIFIED"
    BUSINESS_OBJECTIVE_ACHIEVED = "BUSINESS_OBJECTIVE_ACHIEVED"

class FailureClassification(str, Enum):
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    PERMISSION_FAILURE = "PERMISSION_FAILURE"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"
    BUILD_FAILURE = "BUILD_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    TIMEOUT = "TIMEOUT"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    SECURITY_DENIAL = "SECURITY_DENIAL"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"

@dataclass
class RuntimeProfile:
    profile_id: str
    distribution: str                     # debian, ubuntu, alpine, fedora, kali, tails, arch
    version: str                          # e.g., 12-bookworm, 3.19, 39, rolling
    architecture: str                     # x86_64, aarch64, armv7l
    desktop_environment: DesktopEnvironment
    execution_mode: ExecutionMode
    isolation_level: IsolationLevel
    network_mode: NetworkMode
    min_ram_mb: int = 512
    recommended_ram_mb: int = 2048
    min_disk_mb: int = 1024
    gpu_required: bool = False
    kernel_requirements: List[str] = field(default_factory=list)
    preinstalled_tools: List[str] = field(default_factory=list)
    license: str = "GPL/Linux Standard"
    trust_level: str = "VERIFIED"         # VERIFIED, EXPERIMENTAL, QUARANTINED
    is_ephemeral: bool = True
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CommandPlan:
    plan_id: str
    objective: str
    environment_profile_id: str
    working_directory: str
    command: str
    arguments: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    network_requirements: NetworkMode = NetworkMode.OFFLINE
    filesystem_impact: str = "LOCAL"      # NONE, LOCAL, SYSTEM, DESTRUCTIVE
    risk_level: TerminalCommandRisk = TerminalCommandRisk.READ_ONLY
    timeout_sec: float = 30.0
    expected_result: str = ""
    verification_method: str = "EXIT_CODE_AND_ARTIFACT"
    rollback_strategy: str = "SNAPSHOT_RESTORE"  # NONE, SNAPSHOT_RESTORE, REVERSE_COMMAND

@dataclass
class ProcessInfo:
    pid: int
    ppid: int
    command: str
    start_time: float
    status: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    children: List[int] = field(default_factory=list)

@dataclass
class FileSnapshot:
    snapshot_id: str
    target_path: str
    pre_sha256: Optional[str]
    backup_path: Optional[str]
    timestamp: float = field(default_factory=time.time)

@dataclass
class VerificationPostcondition:
    name: str
    check_type: str                       # FILE_EXISTS, FILE_SHA256, PROCESS_ALIVE, PORT_LISTENING, COMMAND_OUTPUT_MATCH, FUNCTIONAL_TEST
    expected_value: Any
    actual_value: Optional[Any] = None
    passed: bool = False
    evidence_detail: str = ""

@dataclass
class TerminalSession:
    session_id: str
    tenant_id: str
    company_id: str
    mission_id: str
    task_id: str
    agent_id: str
    environment_id: str
    runtime_id: str
    authorization_context: Dict[str, Any]
    risk_level: TerminalCommandRisk
    workspace: str
    network_policy: NetworkMode
    credential_scope: List[str]
    created_at: float = field(default_factory=time.time)
    status: TerminalStatus = TerminalStatus.PREPARING
    current_command: Optional[str] = None
    current_plan: Optional[CommandPlan] = None
    active_processes: Dict[int, ProcessInfo] = field(default_factory=dict)
    snapshots: Dict[str, FileSnapshot] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)

    def log(self, message: str):
        entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self.logs.append(entry)

@dataclass
class TerminalResult:
    status: str                           # SUCCESS, PARTIAL_SUCCESS, FAILED, BLOCKED, REQUIRES_AUTHORIZATION, REQUIRES_HUMAN_DECISION, VERIFICATION_FAILED
    summary: str
    environment_used: str
    runtime_profile: str
    tools_used: List[str]
    tools_installed: List[str]
    commands_executed: List[str]
    files_changed: List[str]
    artifacts: List[Dict[str, Any]]
    observations: Dict[str, Any]
    verification: Dict[str, Any]
    evidence_id: Optional[str]
    failures: List[Dict[str, Any]]
    recovery_actions: List[str]
    remaining_risks: List[str]
    escalation_required: bool = False
    duration_ms: float = 0.0
