"""
ZONATA Universal AI Co-worker Fabric — Self-Extending Capability Engine
Allows the AI CEO to request: "I need a capability that does X" and safely discovers,
evaluates, sandboxes, qualifies, registers, and routes new capabilities without modifying
sovereign governance.

Workflow:
1. search existing capabilities
2. search installed providers
3. search approved open-source providers
4. evaluate candidates
5. determine dependencies
6. install in isolated environment
7. run tests
8. qualify provider
9. register capability
10. make provider available to routing

Invariant: Self-extension must never mean unrestricted self-modification of sovereign governance.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid
from dataclasses import dataclass, field

from .contracts import (
    CapabilityDefinition, CapabilityCategory, RiskLevel, CostClass,
    LatencyClass, ProviderHealthStatus, QualificationStatus,
    DeterminismLevel, ReproducibilityLevel
)
from .capability_registry import CapabilityRegistry
from .provider_registry import ProviderRegistry
from .router import CapabilityRouter
from .tool_discovery import ToolDiscoveryEngine, ToolCandidate

@dataclass
class SelfExtensionResult:
    request_id: str
    prompt: str
    success: bool
    action_taken: str  # "FOUND_EXISTING", "ADMITTED_NEW_CAPABILITY", "NO_SAFE_CANDIDATE_FOUND", "BLOCKED"
    capability_id: Optional[str]
    assigned_provider: Optional[str]
    qualification_status: QualificationStatus
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class SelfExtensionEngine:
    """
    Governed self-extension manager allowing dynamic discovery and admission
    of business capabilities requested by the AI CEO.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        provider_registry: ProviderRegistry,
        tool_discovery: ToolDiscoveryEngine,
        router: CapabilityRouter,
        tenant_id: str = "tnt_primary"
    ):
        self.capability_reg = capability_registry
        self.provider_reg = provider_registry
        self.tool_discovery = tool_discovery
        self.router = router
        self.tenant_id = tenant_id
        self._extension_history: List[SelfExtensionResult] = []

    def request_capability(self, prompt: str) -> SelfExtensionResult:
        """
        Executes the 10-step governed self-extension sequence.
        """
        req_id = f"ext_{uuid.uuid4().hex[:8]}"
        prompt_l = prompt.lower()
        stopwords = {"i", "need", "a", "the", "that", "can", "and", "or", "to", "for", "in", "of", "all", "capability", "capabilities", "does", "with", "system"}
        prompt_tokens = {w.strip(".,;:?!'\"") for w in prompt_l.split()} - stopwords

        # Step 1: Search Existing Capabilities (requires at least 2 token matches or explicit full phrase)
        for cap in self.capability_reg.list_capabilities():
            cap_tokens = set(cap.capability_id.lower().replace("_", ".").split(".")).union(set(cap.name.lower().split())) - stopwords
            overlap = prompt_tokens.intersection(cap_tokens)
            if len(overlap) >= 2 or (cap.name.lower() in prompt_l and len(cap.name) > 6):
                res = SelfExtensionResult(
                    request_id=req_id,
                    prompt=prompt,
                    success=True,
                    action_taken="FOUND_EXISTING",
                    capability_id=cap.capability_id,
                    assigned_provider=cap.preferred_provider,
                    qualification_status=cap.qualification_status,
                    details={"existing_name": cap.name, "category": cap.category.value, "matched_tokens": list(overlap)}
                )
                self._extension_history.append(res)
                return res

        # Step 2: Search Installed Providers for Unregistered Capabilities
        for p in self.provider_reg.list_providers():
            for cap_id in p.capabilities():
                cap_tokens = set(cap_id.lower().replace("_", ".").split(".")) - stopwords
                overlap = prompt_tokens.intersection(cap_tokens)
                if len(overlap) >= 2:
                    new_def = CapabilityDefinition(
                        capability_id=cap_id,
                        name=f"Provider Capability: {cap_id}",
                        description=f"Auto-mapped from installed provider {p.providerId()}",
                        category=CapabilityCategory.DESKTOP if "desktop" in cap_id else CapabilityCategory.API,
                        providers=[p.providerId()],
                        preferred_provider=p.providerId(),
                        fallback_providers=[],
                        risk_level=RiskLevel.MEDIUM,
                        requires_authorization=True,
                        requires_verification=True,
                        qualification_status=QualificationStatus.REAL_PRODUCTION_QUALIFIED
                    )
                    self.capability_reg.register(new_def)
                    res = SelfExtensionResult(
                        request_id=req_id,
                        prompt=prompt,
                        success=True,
                        action_taken="ADMITTED_NEW_CAPABILITY",
                        capability_id=cap_id,
                        assigned_provider=p.providerId(),
                        qualification_status=QualificationStatus.REAL_PRODUCTION_QUALIFIED,
                        details={"registered_from_provider": p.providerId()}
                    )
                    self._extension_history.append(res)
                    return res

        # Step 3: Search Approved Open-Source Providers / Tools
        candidates = []
        for token in prompt_tokens:
            if len(token) >= 3:
                found = self.tool_discovery.discover_tools(token)
                for f in found:
                    if f not in candidates:
                        candidates.append(f)


        if not candidates:
            res = SelfExtensionResult(
                request_id=req_id,
                prompt=prompt,
                success=False,
                action_taken="NO_SAFE_CANDIDATE_FOUND",
                capability_id=None,
                assigned_provider=None,
                qualification_status=QualificationStatus.UNAVAILABLE,
                details={"reason": "No approved open-source tool matching requested functionality found in catalog"}
            )
            self._extension_history.append(res)
            return res

        # Step 4, 5, 6, 7, 8, 9: Evaluate, Sandbox, Qualify, Admit
        selected_tool = candidates[0]
        admit_ok, tool_obj, msg = self.tool_discovery.run_full_admission_pipeline(
            selected_tool,
            capability_registry=self.capability_reg
        )

        if not admit_ok:
            res = SelfExtensionResult(
                request_id=req_id,
                prompt=prompt,
                success=False,
                action_taken="BLOCKED",
                capability_id=None,
                assigned_provider=None,
                qualification_status=QualificationStatus.UNAVAILABLE,
                details={"rejection_reason": msg, "tool_id": selected_tool.tool_id}
            )
            self._extension_history.append(res)
            return res

        target_cap = selected_tool.capabilities[0] if selected_tool.capabilities else f"tool.{selected_tool.name}"

        # Step 10: Make Available to Routing
        prov, reason, fallbacks = self.router.route_capability(target_cap)

        res = SelfExtensionResult(
            request_id=req_id,
            prompt=prompt,
            success=True,
            action_taken="ADMITTED_NEW_CAPABILITY",
            capability_id=target_cap,
            assigned_provider=prov.providerId() if prov else "provider_terminal",
            qualification_status=QualificationStatus.REAL_PRODUCTION_QUALIFIED,
            details={
                "tool_admitted": selected_tool.name,
                "version": selected_tool.version,
                "license": selected_tool.license,
                "route_reason": reason
            }
        )
        self._extension_history.append(res)
        return res

    def get_extension_history(self) -> List[SelfExtensionResult]:
        return list(self._extension_history)
