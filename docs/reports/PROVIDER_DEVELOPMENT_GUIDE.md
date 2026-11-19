# ZONATA PROVIDER DEVELOPMENT GUIDE
## Guidelines for Developing and Integrating Capability Adapters

**Version**: 1.0.0  
**Target Audience**: Platform Integrators, SREs & Automation Engineers  

---

## 1. Provider Design Philosophy

External open-source systems (OpenAdapt, Playwright, Robocorp, Agent S, UI-TARS, MCP servers) are **replaceable capability providers**.
They never possess sovereign authority over ZONATA.
Every provider must implement `CapabilityProvider` from `core.coworker.provider_base`.

---

## 2. Implementing the CapabilityProvider Interface

```python
from typing import Dict, List, Optional, Any
from core.coworker.provider_base import CapabilityProvider
from core.coworker.contracts import (
    ProviderHealthStatus, ProviderEstimate, ExecutionResult,
    VerificationResult, VerificationStatus, RiskLevel
)

class MyCustomProvider(CapabilityProvider):
    def __init__(self):
        self._id = "provider_my_custom"
        self._health = ProviderHealthStatus.AVAILABLE

    def providerId(self) -> str:
        return self._id

    def capabilities(self) -> List[str]:
        return ["desktop.custom_action"]

    def platforms(self) -> List[str]:
        return ["linux", "windows", "darwin"]

    def health(self) -> ProviderHealthStatus:
        return self._health

    def riskProfile(self) -> Dict[str, Any]:
        return {"risk_tier": RiskLevel.LOW, "deterministic": True}

    def estimate(self, capability: str, params: Dict[str, Any]) -> ProviderEstimate:
        return ProviderEstimate(
            provider_id=self._id,
            estimated_duration_sec=1.0,
            estimated_cost_usd=0.0001,
            confidence_score=0.98,
            risk_assessment="Deterministic execution"
        )

    def prepare(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return self._health == ProviderHealthStatus.AVAILABLE

    def execute(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> ExecutionResult:
        # Perform action bounded by ZONATA policies
        return ExecutionResult(
            provider_id=self._id,
            capability_id=capability,
            execution_id="exec_123",
            status="SUCCESS",
            output={"result": "OK"},
            confidence=0.98
        )

    def observe(self, capability: str, execution_id: str) -> Dict[str, Any]:
        return {"status": "ACTIVE"}

    def verify(self, execution_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        return VerificationResult(status=VerificationStatus.VERIFIED, verified_by=self._id)

    def rollback(self, execution_id: str) -> bool:
        return False

    def cancel(self, execution_id: str) -> bool:
        return True

    def recover(self, execution_id: str, error: Exception) -> bool:
        self._health = ProviderHealthStatus.AVAILABLE
        return True

    def shutdown(self) -> None:
        pass
```

---

## 3. Registration & Verification Rules

1. Register your provider in `core.coworker.provider_registry.ProviderRegistry`.
2. Add capability definitions into `core.coworker.capability_registry.CapabilityRegistry`.
3. Never treat a provider's textual statement ("success") as proof. All mutations must produce verifiable physical evidence (DOM trace, file hash, API receipt ID, or accessibility event).
