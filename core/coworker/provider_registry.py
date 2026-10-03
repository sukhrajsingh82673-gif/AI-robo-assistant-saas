"""
ZONATA Universal AI Co-worker Fabric — Provider Registry & Health Monitor
Maintains live instances of capability providers and continuously tracks their health.
"""

from typing import Dict, List, Optional, Any
import time
from .provider_base import CapabilityProvider
from .contracts import ProviderHealthStatus
from .providers import (
    OpenAdaptProvider,
    WindowsDesktopProvider, MacOSDesktopProvider, LinuxDesktopProvider,
    ComputerUseMCPProvider, PlaywrightProvider,
    RobocorpProvider, OpenRPAProvider, APIMCPProvider,
    AgentSProvider, UITARSProvider, TerminalProvider
)

class ProviderRegistry:
    """Registry maintaining active CapabilityProvider adapters."""

    def __init__(self):
        self._providers: Dict[str, CapabilityProvider] = {}
        self._initialize_default_providers()

    def _initialize_default_providers(self):
        # Register standard default providers
        providers: List[CapabilityProvider] = [
            APIMCPProvider(),
            TerminalProvider(),
            PlaywrightProvider(),
            OpenAdaptProvider(),
            LinuxDesktopProvider(),
            WindowsDesktopProvider(),
            MacOSDesktopProvider(),
            ComputerUseMCPProvider(),
            RobocorpProvider(),
            OpenRPAProvider(),
            AgentSProvider(),
            UITARSProvider()
        ]
        for p in providers:
            self.register(p)

    def register(self, provider: CapabilityProvider):
        self._providers[provider.providerId()] = provider

    def get_provider(self, provider_id: str) -> Optional[CapabilityProvider]:
        return self._providers.get(provider_id)

    def list_providers(self) -> List[CapabilityProvider]:
        return list(self._providers.values())

    def get_healthy_providers(self) -> List[CapabilityProvider]:
        return [
            p for p in self._providers.values()
            if p.health() in [ProviderHealthStatus.AVAILABLE, ProviderHealthStatus.DEGRADED]
        ]

    def get_health_report(self) -> Dict[str, Any]:
        return ProviderHealthMonitor(self).get_health_report()


class ProviderHealthMonitor:
    """Monitors heartbeat, crash states, and availability of all registered providers."""

    def __init__(self, registry: ProviderRegistry):
        self._registry = registry
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._last_heartbeat: Dict[str, float] = {}

    def record_heartbeat(self, provider_id: str):
        self._last_heartbeat[provider_id] = time.time()

    def record_failure(self, provider_id: str, error_msg: str):
        stats = self._metrics.setdefault(provider_id, {"failures": 0, "successes": 0, "last_error": None})
        stats["failures"] += 1
        stats["last_error"] = error_msg
        if stats["failures"] >= 3:
            provider = self._registry.get_provider(provider_id)
            if provider:
                provider.shutdown()
                # Mark as degraded or crashed
                if hasattr(provider, "set_health"):
                    provider.set_health(ProviderHealthStatus.DEGRADED)

    def record_success(self, provider_id: str):
        stats = self._metrics.setdefault(provider_id, {"failures": 0, "successes": 0, "last_error": None})
        stats["successes"] += 1

    def get_health_report(self) -> Dict[str, Any]:
        report = {}
        for p in self._registry.list_providers():
            pid = p.providerId()
            stats = self._metrics.get(pid, {"failures": 0, "successes": 0, "last_error": None})
            meta = p.get_metadata()
            report[pid] = {
                "health": p.health().value,
                "platforms": p.platforms(),
                "capabilities_count": len(p.capabilities()),
                "repository": meta.get("repository"),
                "commit": meta.get("commit"),
                "license": meta.get("license"),
                "integration_status": meta.get("integration_status"),
                "model_dependencies": meta.get("model_dependencies", []),
                "runtime_dependencies": meta.get("runtime_dependencies", []),
                "failures": stats["failures"],
                "successes": stats["successes"],
                "last_error": stats["last_error"]
            }
        return report
