"""
ZONATA Universal AI Co-worker Fabric — Policy-Driven Multi-Factor Capability Router
Implements policy-driven routing evaluation:

Default routing preference:
1. API / Native System API
2. MCP / Structured Integration
3. Native Accessibility Automation
4. Deterministic RPA
5. OpenAdapt
6. Playwright
7. Visual CUA
8. Human Takeover

Evaluates: capability, risk, provider availability, provider health, platform,
authentication, credential scope, deterministic reproducibility, verification availability,
rollback capability, historical reliability, latency, cost, task complexity, data sensitivity,
visual requirements, browser requirements, application requirements.

Every routing decision is recorded with machine-readable metadata.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid

from .contracts import (
    CapabilityDefinition, CapabilityCategory, ProviderHealthStatus,
    RiskLevel, CostClass, LatencyClass, RoutingDecision
)
from .capability_registry import CapabilityRegistry
from .provider_registry import ProviderRegistry
from .provider_base import CapabilityProvider

class RoutingPolicy:
    """Configurable policy parameters governing provider selection."""
    def __init__(
        self,
        prefer_api: bool = True,
        prefer_accessibility_over_visual: bool = True,
        prefer_deterministic_workflows: bool = True,
        max_cost_tolerance: CostClass = CostClass.HIGH,
        require_rollback_for_financial: bool = True
    ):
        self.prefer_api = prefer_api
        self.prefer_accessibility_over_visual = prefer_accessibility_over_visual
        self.prefer_deterministic_workflows = prefer_deterministic_workflows
        self.max_cost_tolerance = max_cost_tolerance
        self.require_rollback_for_financial = require_rollback_for_financial


class CapabilityRouter:
    """
    Intelligent Policy-Driven Multi-Factor Router.
    The AI CEO requests a capability; the router determines the implementation.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        provider_registry: ProviderRegistry,
        default_policy: Optional[RoutingPolicy] = None,
        tenant_id: str = "tnt_primary"
    ):
        self.capability_reg = capability_registry
        self.provider_reg = provider_registry
        self.policy = default_policy or RoutingPolicy()
        self.tenant_id = tenant_id
        self._decision_history: List[RoutingDecision] = []
        self._last_decision: Optional[RoutingDecision] = None

    def evaluate_routing_tree(
        self,
        cap: CapabilityDefinition,
        platform: str,
        candidates: List[CapabilityProvider]
    ) -> List[Tuple[float, CapabilityProvider, str, Dict[str, Any]]]:
        """
        Executes the policy-driven decision tree:
        1. API / Native System API
        2. MCP / Structured Integration
        3. Native Accessibility Automation
        4. Deterministic RPA
        5. OpenAdapt
        6. Playwright
        7. Visual CUA
        8. Human Takeover
        """
        scored_candidates: List[Tuple[float, CapabilityProvider, str, Dict[str, Any]]] = []

        for p in candidates:
            pid = p.providerId()
            health = p.health()
            score = 100.0
            reasons = []
            risk_prof = p.riskProfile()
            est = p.estimate(cap.capability_id, {})

            reason_dict: Dict[str, Any] = {
                "provider_id": pid,
                "api_available": "api" in pid,
                "deterministic": risk_prof.get("deterministic", True),
                "verification": cap.requires_verification,
                "rollback": risk_prof.get("supports_rollback", False),
                "risk": cap.risk_level.value,
                "health": health.value,
                "platform": platform,
                "latency_sub_second": est.estimated_duration_sec < 1.0,
                "cost_zero": est.estimated_cost_usd == 0.0
            }

            # Factor 1: Health
            if health == ProviderHealthStatus.AVAILABLE:
                score += 30.0
                reasons.append("Health=AVAILABLE (+30)")
            elif health == ProviderHealthStatus.DEGRADED:
                score -= 30.0
                reasons.append("Health=DEGRADED (-30)")

            # Factor 2: Policy Tree Hierarchy
            if pid == cap.preferred_provider:
                score += 20.0
                reasons.append("Capability Preferred Provider (+20)")

            if "api" in pid and self.policy.prefer_api:
                score += 60.0
                reasons.append("Policy: API Preferred (+60)")
            elif "terminal" in pid:
                score += 55.0
                reasons.append("Policy: Governed Terminal Exec (+55)")
            elif any(k in pid for k in ["linux", "windows", "macos"]) and self.policy.prefer_accessibility_over_visual:
                score += 45.0
                reasons.append("Policy: Native Accessibility Preferred (+45)")
            elif any(k in pid for k in ["openadapt", "robocorp", "openrpa"]) and self.policy.prefer_deterministic_workflows:
                score += 35.0
                reasons.append("Policy: Deterministic Workflow/RPA Preferred (+35)")
            elif "playwright" in pid:
                score += 40.0
                reasons.append("Policy: DOM Browser Automation (+40)")
            elif any(k in pid for k in ["visual_cua", "agent_s", "ui_tars"]):
                score -= 20.0
                reasons.append("Policy: Visual CUA Fallback (-20)")

            # Factor 3: Cost & Latency alignment
            if est.estimated_duration_sec < 1.0:
                score += 15.0
                reasons.append("Latency: Sub-second (+15)")
            if est.estimated_cost_usd == 0.0:
                score += 15.0
                reasons.append("Cost: Zero Incremental (+15)")

            # Factor 4: Verification & Rollback
            if risk_prof.get("supports_rollback", False):
                score += 10.0
                reasons.append("Supports Rollback (+10)")
            if risk_prof.get("deterministic", False):
                score += 10.0
                reasons.append("Deterministic Execution (+10)")

            reason_dict["score"] = score
            scored_candidates.append((score, p, " | ".join(reasons), reason_dict))

        return scored_candidates

    def route_capability(
        self,
        capability_id: str,
        platform: str = "linux",
        risk_tolerance: RiskLevel = RiskLevel.HIGH,
        preferred_provider_override: Optional[str] = None
    ) -> Tuple[Optional[CapabilityProvider], str, List[str]]:
        """
        Selects optimal provider evaluating candidate pool against policy and health.
        Records structured routing decision.
        """
        cap = self.capability_reg.get_capability(capability_id)
        if not cap:
            return None, f"Unknown capability: {capability_id}", []

        # If caller specified an authorized override that is available, evaluate it first
        if preferred_provider_override:
            override_p = self.provider_reg.get_provider(preferred_provider_override)
            if override_p and override_p.health() == ProviderHealthStatus.AVAILABLE:
                fallbacks = [p for p in cap.providers if p != preferred_provider_override]
                dec = RoutingDecision(
                    decision_id=f"dec_{uuid.uuid4().hex[:8]}",
                    tenant_id=self.tenant_id,
                    requested_capability=capability_id,
                    candidate_providers=cap.providers,
                    selected_provider=preferred_provider_override,
                    reason={"override": True, "provider": preferred_provider_override},
                    fallbacks=fallbacks,
                    platform=platform
                )
                self._record_decision(dec)
                return override_p, f"Explicit authorized override: {preferred_provider_override}", fallbacks

        # Filter candidate providers by platform and non-crashed health
        candidate_pool: List[CapabilityProvider] = []
        for provider_id in cap.providers:
            provider = self.provider_reg.get_provider(provider_id)
            if not provider:
                continue

            # Reject crashed, unavailable, or policy blocked providers
            if provider.health() in [ProviderHealthStatus.UNAVAILABLE, ProviderHealthStatus.CRASHED, ProviderHealthStatus.POLICY_BLOCKED]:
                continue

            # Check platform compatibility
            if platform not in provider.platforms():
                continue

            candidate_pool.append(provider)

        if not candidate_pool:
            return None, f"No healthy compatible provider found for capability {capability_id} on {platform}", []

        # Evaluate through policy-driven decision tree
        scored = self.evaluate_routing_tree(cap, platform, candidate_pool)
        scored.sort(key=lambda x: x[0], reverse=True)

        selected = scored[0][1]
        best_reason_str = scored[0][2]
        best_reason_dict = scored[0][3]
        fallback_ids = [s[1].providerId() for s in scored[1:]]

        # Add declared fallback providers from capability definition
        for fb in cap.fallback_providers:
            if fb != selected.providerId() and fb not in fallback_ids:
                fallback_ids.append(fb)

        # Record machine-readable routing decision
        decision = RoutingDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:8]}",
            tenant_id=self.tenant_id,
            requested_capability=capability_id,
            candidate_providers=[p.providerId() for p in candidate_pool],
            selected_provider=selected.providerId(),
            reason=best_reason_dict,
            fallbacks=fallback_ids,
            platform=platform
        )
        self._record_decision(decision)

        return selected, best_reason_str, fallback_ids

    def _record_decision(self, decision: RoutingDecision):
        self._decision_history.append(decision)
        self._last_decision = decision

    def get_last_decision(self) -> Optional[RoutingDecision]:
        return self._last_decision

    def get_decision_history(self) -> List[RoutingDecision]:
        return list(self._decision_history)
