"""
URA / ZONATA Universal Automation Fabric
========================================
Production enterprise automation package for the ZONATA / URA
Universal AI Company Operating System.
"""

from core.automation_fabric.contracts import (
    ExecutionStatus, TerminalOutcome, ActionRiskLevel,
    ApprovalStatus, LicenseType, CircuitState, ExecutionLease,
    ConnectorDefinition, WorkflowTemplate, StepResult,
    IndependentVerificationResult
)
from core.automation_fabric.license_validator import (
    AutomationLicenseValidator, license_validator, LicenseValidationError
)
from core.automation_fabric.kestra_adapter import (
    KestraFlowAdapter, kestra_adapter, KestraFlowValidationError
)
from core.automation_fabric.connector_registry import (
    GovernedConnectorRegistry, connector_registry,
    ConnectorSecurityError, CircuitBreakerTrippedError
)
from core.automation_fabric.specialized_agents import (
    SpecializedAgentRegistry, specialized_agent_registry,
    AgentDelegationTask
)
from core.automation_fabric.templates import (
    TemplateCatalog, template_catalog
)
from core.automation_fabric.fabric import (
    UniversalAutomationFabric, universal_automation_fabric,
    AutomationSecurityException
)

__all__ = [
    "ExecutionStatus",
    "TerminalOutcome",
    "ActionRiskLevel",
    "ApprovalStatus",
    "LicenseType",
    "CircuitState",
    "ExecutionLease",
    "ConnectorDefinition",
    "WorkflowTemplate",
    "StepResult",
    "IndependentVerificationResult",
    "AutomationLicenseValidator",
    "license_validator",
    "LicenseValidationError",
    "KestraFlowAdapter",
    "kestra_adapter",
    "KestraFlowValidationError",
    "GovernedConnectorRegistry",
    "connector_registry",
    "ConnectorSecurityError",
    "CircuitBreakerTrippedError",
    "SpecializedAgentRegistry",
    "specialized_agent_registry",
    "AgentDelegationTask",
    "TemplateCatalog",
    "template_catalog",
    "UniversalAutomationFabric",
    "universal_automation_fabric",
    "AutomationSecurityException"
]
