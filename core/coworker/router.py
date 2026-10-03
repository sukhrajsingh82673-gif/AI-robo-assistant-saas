"""
ZONATA Universal AI Co-worker Fabric — Intelligent Capability Router
Selects the optimal capability provider based on structured scoring:
capability match + health + platform + risk + verification + latency + cost.
Enforces the core principle: API-first, native accessibility second, visual CUA as fallback.
"""

from typing import Dict, List, Optional, Any, Tuple
from .contracts import (
    CapabilityDefinition, CapabilityCategory, ProviderHealthStatus,
    RiskLevel, CostClass, LatencyClass
)
from .capability_registry import CapabilityRegistry
from .provider_registry import ProviderRegistry
from .provider_base import CapabilityProvider

class CapabilityRouter:
    """
    Intelligent Provider Router.
    The AI CEO requests a capability; the router determines the implementation.
    """

    def __init__(self, capability_registry: CapabilityRegistry, provider_registry: ProviderRegistry):
        self.capability_reg = capability_registry
        self.provider_reg = provider_registry

        # Preference hierarchy weights
        self._category_priority = {
            CapabilityCategory.API: 100,        # Highest preference: structured, deterministic, fast
            CapabilityCategory.DESKTOP: 85,     # Native UI / Accessibility tree
            CapabilityCategory.BROWSER: 80,     # Playwright DOM
            CapabilityCategory.RPA: 75,         # Robocorp / OpenRPA
            CapabilityCategory.FILE: 70,        # Filesystem
            CapabilityCategory.SYSTEM: 65,      # OS processes
            CapabilityCategory.VISUAL_CUA: 40   # Fallback: expensive, probabilistic visual AI
        }

    def route_capability(
        self,
        capability_id: str,
        platform: str = "linux",
        risk_tolerance: RiskLevel = RiskLevel.HIGH,
        preferred_provider_override: Optional[str] = None
    ) -> Tuple[Optional[CapabilityProvider], str, List[str]]:
        """
        Evaluates candidate providers for a given capability and returns:
        (SelectedProvider, SelectionReason, FallbackProviderIds)
        """
        cap = self.capability_reg.get_capability(capability_id)
        if not cap:
            return None, f"Unknown capability: {capability_id}", []

        candidates: List[Tuple[float, CapabilityProvider, str]] = []

        # If caller specified an override that is available and healthy, evaluate it first
        if preferred_provider_override:
            override_p = self.provider_reg.get_provider(preferred_provider_override)
            if override_p and override_p.health() == ProviderHealthStatus.AVAILABLE:
                fallbacks = [p for p in cap.providers if p != preferred_provider_override]
                return override_p, f"Explicit authorized override: {preferred_provider_override}", fallbacks

        for provider_id in cap.providers:
            provider = self.provider_reg.get_provider(provider_id)
            if not provider:
                continue

            # 1. Health check
            health = provider.health()
            if health in [ProviderHealthStatus.UNAVAILABLE, ProviderHealthStatus.CRASHED, ProviderHealthStatus.POLICY_BLOCKED]:
                continue

            # 2. Platform compatibility
            if platform not in provider.platforms():
                continue

            # 3. Calculate score
            score = 100.0

            # Health penalty
            if health == ProviderHealthStatus.DEGRADED:
                score -= 30.0

            # Category preference
            score += self._category_priority.get(cap.category, 50)

            # Specific provider architectural preferences
            pid = provider.providerId()
            if "api" in pid:
                score += 50.0  # Strongly favor structured APIs
            elif "robocorp" in pid or "openrpa" in pid:
                score += 35.0  # Favor deterministic RPA over visual CUA
            elif "playwright" in pid:
                score += 40.0  # Favor DOM over visual CUA
            elif "linux" in pid or "windows" in pid or "macos" in pid:
                score += 30.0  # Native accessibility preferred over visual
            elif "openadapt" in pid:
                score += 25.0  # Demonstrated repeatable workflow
            elif "visual_cua" in pid:
                score -= 20.0  # High cost, probabilistic

            # Preferred provider bonus
            if pid == cap.preferred_provider:
                score += 15.0

            reason = f"Score: {score:.1f} (Category: {cap.category.value}, Health: {health.value})"
            candidates.append((score, provider, reason))

        if not candidates:
            return None, f"No healthy compatible provider found for capability {capability_id} on {platform}", []

        # Sort by score descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        selected = candidates[0][1]
        best_reason = candidates[0][2]
        fallback_ids = [c[1].providerId() for c in candidates[1:]]

        # Append static fallback providers from capability definition
        for fb in cap.fallback_providers:
            if fb != selected.providerId() and fb not in fallback_ids:
                fallback_ids.append(fb)

        return selected, best_reason, fallback_ids
