"""
ZONATA / URA Universal Linux Terminal Execution Fabric
AICU-Governed Dynamic Runtime, Tool, Desktop and Execution System.
"""

from .models import (
    ExecutionMode, IsolationLevel, DesktopEnvironment, NetworkMode,
    TerminalStatus, TerminalCommandRisk, SemanticExecutionState,
    FailureClassification, RuntimeProfile, CommandPlan, TerminalSession,
    TerminalResult, ProcessInfo, FileSnapshot, VerificationPostcondition,
    AICeoTerminalInstruction, AICeoTerminalResult
)
from .capability_registry import EnvironmentCapabilityRegistry
from .resource_inspector import ResourceInspector
from .runtime_adapters import (
    BaseRuntimeAdapter, LinuxRuntimeAdapter, ContainerRuntimeAdapter,
    VMRuntimeAdapter, DesktopRuntimeAdapter, RemoteLinuxRuntimeAdapter,
    HeadlessRuntimeAdapter
)
from .runtime_router import UniversalRuntimeRouter, EnvironmentSelectionDecision
from .security_gateway import TerminalSecurityGateway
from .execution_gateway import TerminalExecutionGateway
from .verification_engine import TerminalVerificationEngine
from .failure_recovery import TerminalFailureRecoveryEngine
from .tool_integration import TerminalToolIntegrationEngine
from .security_agent import SecurityGovernanceAgent
from .reversibility_engine import ReversibilityAndCheckpointEngine, TerminalOperationRecord, TerminalCheckpoint
from .knowledge_evolution import AICeoKnowledgeEvolutionEngine, AICeoKnowledgeEntry
from .terminal_agent import TerminalHandlingAgent
from .universal_terminal import UniversalTerminal
from .health_service import TerminalHealthService

__all__ = [
    "ExecutionMode",
    "IsolationLevel",
    "DesktopEnvironment",
    "NetworkMode",
    "TerminalStatus",
    "TerminalCommandRisk",
    "SemanticExecutionState",
    "FailureClassification",
    "RuntimeProfile",
    "CommandPlan",
    "TerminalSession",
    "TerminalResult",
    "ProcessInfo",
    "FileSnapshot",
    "VerificationPostcondition",
    "AICeoTerminalInstruction",
    "AICeoTerminalResult",
    "EnvironmentCapabilityRegistry",
    "ResourceInspector",
    "BaseRuntimeAdapter",
    "LinuxRuntimeAdapter",
    "ContainerRuntimeAdapter",
    "VMRuntimeAdapter",
    "DesktopRuntimeAdapter",
    "RemoteLinuxRuntimeAdapter",
    "HeadlessRuntimeAdapter",
    "UniversalRuntimeRouter",
    "EnvironmentSelectionDecision",
    "TerminalSecurityGateway",
    "TerminalExecutionGateway",
    "TerminalVerificationEngine",
    "TerminalFailureRecoveryEngine",
    "TerminalToolIntegrationEngine",
    "SecurityGovernanceAgent",
    "ReversibilityAndCheckpointEngine",
    "TerminalOperationRecord",
    "TerminalCheckpoint",
    "AICeoKnowledgeEvolutionEngine",
    "AICeoKnowledgeEntry",
    "TerminalHandlingAgent",
    "UniversalTerminal",
    "TerminalHealthService"
]
