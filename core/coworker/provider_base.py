"""
ZONATA Universal AI Co-worker Fabric — Capability Provider Abstract Base Class
Defines the strict capability provider contract. All external execution engines,
RPA libraries, visual CUAs, browser engines, and desktop adapters MUST implement
this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from .contracts import (
    ProviderHealthStatus, ProviderEstimate, ExecutionResult,
    VerificationResult, VerificationStatus, RiskLevel
)

class CapabilityProvider(ABC):
    """
    Common abstraction for all execution technologies.
    External open-source systems are replaceable capability providers.
    ZONATA remains the sovereign authority.
    """

    @abstractmethod
    def providerId(self) -> str:
        """Returns the unique identifier of this capability provider."""
        pass

    @abstractmethod
    def capabilities(self) -> List[str]:
        """Returns the list of capability_ids supported by this provider."""
        pass

    @abstractmethod
    def platforms(self) -> List[str]:
        """Returns the supported host platforms ('linux', 'windows', 'darwin')."""
        pass

    @abstractmethod
    def health(self) -> ProviderHealthStatus:
        """Reports the real-time operational health of this provider."""
        pass

    @abstractmethod
    def riskProfile(self) -> Dict[str, Any]:
        """Returns the safety and risk characteristics of this provider."""
        pass

    @abstractmethod
    def estimate(self, capability: str, params: Dict[str, Any]) -> ProviderEstimate:
        """Estimates duration, cost, and confidence for executing this capability."""
        pass

    @abstractmethod
    def prepare(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Prepares environment, verifies prerequisites and locks without side effects."""
        pass

    @abstractmethod
    def execute(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> ExecutionResult:
        """
        Executes the capability under ZONATA supervision.
        Must return structured ExecutionResult with tamper-evident evidence.
        Never treat provider text as proof of success.
        """
        pass

    @abstractmethod
    def observe(self, capability: str, execution_id: str) -> Dict[str, Any]:
        """Observes the resulting environment state after execution."""
        pass

    @abstractmethod
    def verify(self, execution_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        """Performs provider-level verification (supplemented by IndependentVerificationEngine)."""
        pass

    @abstractmethod
    def rollback(self, execution_id: str) -> bool:
        """Rolls back side effects if supported; returns False if irreversible."""
        pass

    @abstractmethod
    def cancel(self, execution_id: str) -> bool:
        """Cancels an ongoing asynchronous execution immediately."""
        pass

    @abstractmethod
    def recover(self, execution_id: str, error: Exception) -> bool:
        """Attempts self-healing or session recovery upon failure."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully halts worker sessions, drivers, or child processes."""
        pass
