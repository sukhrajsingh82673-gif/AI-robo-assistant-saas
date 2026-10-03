"""
ZONATA Universal AI Co-worker Fabric — Worker Runtime Router
Dynamically routes capability requests to the optimal specialized worker runtime
(Hermes, OpenHands, OpenClaw, Browser, Computer Use, Terminal, or API/MCP).
Enforces explainable selection criteria based on capability schemas, platform constraints,
node health, license compliance, risk levels, and historical reliability.
The AI CEO requests a capability; the router determines the runtime.
"""

from typing import Dict, List, Optional, Any
import time
from dataclasses import dataclass, field

from .base_runtime import WorkerRuntime
from .hermes_runtime import HermesWorkerRuntime
from .openhands_runtime import OpenHandsWorkerRuntime
from .openclaw_runtime import OpenClawWorkerRuntime
from .browser_runtime import BrowserWorkerRuntime
from .computer_use_runtime import ComputerUseWorkerRuntime
from ..contracts import RiskLevel

@dataclass
class RoutingDecision:
    capability_id: str
    selected_runtime_id: str
    selected_runtime_type: str
    score: float
    reason: str
    node_requirements: Dict[str, Any]
    fallback_runtimes: List[str]
    timestamp: float = field(default_factory=time.time)

class WorkerRuntimeRouter:
    """
    Intelligent, governed router for specialized AI Co-Worker runtimes.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._runtimes: Dict[str, WorkerRuntime] = {}
        self._history: List[RoutingDecision] = []

        # Register standard runtimes
        self.register_runtime(HermesWorkerRuntime(tenant_id))
        self.register_runtime(OpenHandsWorkerRuntime(tenant_id))
        self.register_runtime(OpenClawWorkerRuntime(tenant_id))
        self.register_runtime(BrowserWorkerRuntime(tenant_id))
        self.register_runtime(ComputerUseWorkerRuntime(tenant_id))

    def register_runtime(self, runtime: WorkerRuntime):
        self._runtimes[runtime.runtime_id()] = runtime

    def get_runtime(self, runtime_id: str) -> Optional[WorkerRuntime]:
        return self._runtimes.get(runtime_id)

    def list_runtimes(self) -> List[WorkerRuntime]:
        return list(self._runtimes.values())

    def route_capability(
        self,
        capability_id: str,
        platform: str = "linux",
        risk_level: RiskLevel = RiskLevel.LOW,
        preferred_runtime_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Calculates optimal runtime match for the given capability.
        Produces an explainable audit record.
        """
        candidates: List[Tuple[WorkerRuntime, float, str]] = []

        for r in self._runtimes.values():
            caps = r.supported_capabilities()
            score = 0.0
            reasons = []

            # 1. Exact or prefix capability match
            if capability_id in caps:
                score += 50.0
                reasons.append("Exact capability match")
            elif any(c.startswith(capability_id.split(".")[0]) for c in caps):
                score += 25.0
                reasons.append("Domain namespace match")

            # 2. Specialized Domain Affinity
            cap_prefix = capability_id.split(".")[0]
            rtype = r.runtime_type()

            if cap_prefix == "engineering" and rtype == "OPENHANDS":
                score += 40.0
                reasons.append("Specialized software engineering runtime")
            elif cap_prefix in ["browser", "crawl"] and rtype in ["BROWSER", "OPENCLAW"]:
                score += 35.0
                reasons.append("Specialized browser/web crawl runtime")
            elif cap_prefix in ["computer", "desktop"] and rtype == "COMPUTER_USE":
                score += 40.0
                reasons.append("Specialized computer-use CUA runtime")
            elif cap_prefix in ["hermes", "reasoning", "general"] and rtype == "HERMES":
                score += 40.0
                reasons.append("Specialized autonomous reasoning and background runtime")

            # 3. Preference alignment
            if preferred_runtime_type and rtype == preferred_runtime_type:
                score += 20.0
                reasons.append(f"Aligned with preferred runtime {preferred_runtime_type}")

            if score > 0.0:
                candidates.append((r, score, "; ".join(reasons)))

        # Sort candidates descending by score
        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates:
            # Fallback to Hermes as the general-purpose reasoner
            hermes_rt = self._runtimes.get("runtime_hermes_agent") or list(self._runtimes.values())[0]
            decision = RoutingDecision(
                capability_id=capability_id,
                selected_runtime_id=hermes_rt.runtime_id(),
                selected_runtime_type=hermes_rt.runtime_type(),
                score=10.0,
                reason="Default fallback to general-purpose reasoning runtime",
                node_requirements={"platform": platform},
                fallback_runtimes=[]
            )
        else:
            best_rt, best_score, best_reason = candidates[0]
            fallbacks = [c[0].runtime_id() for c in candidates[1:]]

            node_reqs = {"platform": platform}
            if best_rt.runtime_type() == "COMPUTER_USE":
                node_reqs["requires_display"] = True
            elif best_rt.runtime_type() == "BROWSER":
                node_reqs["requires_browser"] = True

            decision = RoutingDecision(
                capability_id=capability_id,
                selected_runtime_id=best_rt.runtime_id(),
                selected_runtime_type=best_rt.runtime_type(),
                score=best_score,
                reason=best_reason,
                node_requirements=node_reqs,
                fallback_runtimes=fallbacks
            )

        self._history.append(decision)
        return decision

    def get_routing_history(self) -> List[RoutingDecision]:
        return list(self._history)
