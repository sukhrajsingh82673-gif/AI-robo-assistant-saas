"""ZONATA Sovereign Core — Base Port Framework & Typed Provider Contracts.

Implements OpenCode Step 1C:
1. Typed ProviderResult with statuses: OK, ACCEPTED_BY_PROVIDER, FAILED,
   NOT_CONFIGURED, NOT_IMPLEMENTED, SANDBOX, DEGRADED.
2. Port base class with Port -> RealProvider -> default NotConfiguredProvider -> test-only SandboxProvider.
3. Central PortRegistry and provider resolution.
4. Truth Rule: Nothing reports success it did not achieve.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import os
import time
from typing import Any, Dict, List, Literal, Optional, Union


class PortStatus(str, Enum):
    OK = "OK"
    ACCEPTED_BY_PROVIDER = "ACCEPTED_BY_PROVIDER"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    SANDBOX = "SANDBOX"
    DEGRADED = "DEGRADED"


@dataclass
class ProviderResult:
    status: PortStatus
    provider: str
    provider_ref: Optional[str] = None
    sandbox: bool = False
    latency_ms: float = 0.0
    cost: Union[float, Literal["UNMEASURED"]] = "UNMEASURED"
    evidence_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        """Only external confirmation or sandbox qualifies as operational success."""
        return self.status in (PortStatus.OK, PortStatus.ACCEPTED_BY_PROVIDER, PortStatus.SANDBOX)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value if isinstance(self.status, PortStatus) else str(self.status),
            "provider": self.provider,
            "provider_ref": self.provider_ref,
            "sandbox": bool(self.sandbox),
            "latency_ms": round(float(self.latency_ms), 3),
            "cost": self.cost if self.cost == "UNMEASURED" else round(float(self.cost), 6),
            "evidence_id": self.evidence_id,
            "error": self.error,
            "metadata": self.metadata,
        }


class Port(ABC):
    """Abstract port definition."""
    name: str = "base"
    capability: str = "base"

    def __init__(self, provider_name: str = "default", sandbox: bool = False):
        self.provider_name = provider_name
        self.sandbox = sandbox

    @abstractmethod
    def probe(self) -> ProviderResult:
        """Harmless, real health/reality check measuring latency and genuine status."""
        pass


class NotConfiguredProvider(Port):
    """Default provider when no real provider or test sandbox is active."""
    def __init__(self, capability: str, reason: str = "Provider not configured in environment"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.capability = capability
        self.reason = reason

    def probe(self) -> ProviderResult:
        return ProviderResult(
            status=PortStatus.NOT_CONFIGURED,
            provider="not_configured",
            provider_ref=None,
            sandbox=False,
            latency_ms=0.0,
            cost="UNMEASURED",
            error=self.reason
        )


class NotImplementedProvider(Port):
    """Provider for capabilities that are explicitly not implemented (e.g. browser, desktop control)."""
    def __init__(self, capability: str, reason: str = "Capability is not implemented in sovereign runtime"):
        super().__init__(provider_name="none", sandbox=False)
        self.capability = capability
        self.reason = reason

    def probe(self) -> ProviderResult:
        return ProviderResult(
            status=PortStatus.NOT_IMPLEMENTED,
            provider="none",
            provider_ref=None,
            sandbox=False,
            latency_ms=0.0,
            cost="UNMEASURED",
            error=self.reason
        )


class SandboxProvider(Port):
    """Test-only sandbox provider, active strictly when ZONATA_TEST_MODE=1 or test profile."""
    def __init__(self, capability: str, provider_name: str = "sandbox"):
        super().__init__(provider_name=provider_name, sandbox=True)
        self.capability = capability

    def probe(self) -> ProviderResult:
        # Enforce Rule 1: Sandbox only when ZONATA_TEST_MODE=1 or test profile
        is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
        if not is_test:
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                sandbox=False,
                latency_ms=0.0,
                cost="UNMEASURED",
                error="SandboxProvider rejected in non-test mode without ZONATA_TEST_MODE=1"
            )
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=f"sandbox_{self.capability}_{int(time.time())}",
            sandbox=True,
            latency_ms=0.5,
            cost=0.0,
            metadata={"sandbox": True, "note": "Simulation mode"}
        )


class PortRegistry:
    """Registry maintaining active ports per capability."""
    def __init__(self):
        self._ports: Dict[str, Port] = {}

    def register(self, capability: str, port: Port) -> None:
        self._ports[capability] = port

    def get(self, capability: str) -> Port:
        if capability in self._ports:
            return self._ports[capability]
        return NotConfiguredProvider(capability)

    def list_capabilities(self) -> List[str]:
        return sorted(list(self._ports.keys()))


port_registry = PortRegistry()
