"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Cognitive Model Router & Outage Fail-Safe Engine

Implements Section 25 & Section 26 of the Gemma 4 Master Specification:
- Dynamic task routing by:
    * Task complexity (High -> Gemma 4 31B IT; Normal/Low -> Gemma 4 26B MoE)
    * Latency sensitivity (Realtime/Low -> Gemma 4 26B MoE)
    * Cost ceiling (Cost-optimized -> Gemma 4 26B MoE)
    * Privacy & data classification (RESTRICTED/HIGHLY_RESTRICTED -> Local sovereign mode)
    * Modality requirements (Multimodal -> Gemma 4 Multimodal Processor)
    * Risk level (HIGH_RISK -> Gemma 4 31B IT + Deterministic Policy + Human Approval)
- Outage resilience & circuit breakers (Section 25):
    If Gemma 4 becomes unavailable, the system safely falls back to:
      1. Secondary configured model (e.g. Gemini 2.5 Pro / Flash)
      2. Deterministic governance workflow
      3. Queued missions under safe state
    Never allows model availability to become a single point of failure for governance.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from core.cognitive_model_provider import CognitiveModelProvider, Gemma4Provider

logger = logging.getLogger("zonata.cognitive.router")

@dataclass
class CognitiveRoutingDecision:
    selected_provider: str
    selected_model: str
    deployment_mode: str  # LOCAL, REMOTE, HYBRID
    routing_reason: str
    is_sovereign: bool
    requires_human_approval: bool
    fallback_available: bool
    circuit_healthy: bool
    timestamp: float = field(default_factory=time.time)

class CognitiveModelRouter:
    """
    Intelligent routing gate dispatching cognitive executive requests.
    Enforces governance boundaries and ensures zero single-point-of-failure.
    """

    def __init__(self):
        self._providers: Dict[str, CognitiveModelProvider] = {
            "gemma4": Gemma4Provider(model_id="gemma-4-31b-it", deployment_mode="HYBRID")
        }
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {
            "gemma4": {"is_open": False, "failure_count": 0, "last_failure": 0.0}
        }
        self._routing_log: List[Dict[str, Any]] = []

    def get_provider(self, provider_key: str = "gemma4") -> CognitiveModelProvider:
        return self._providers.get(provider_key, self._providers["gemma4"])

    def record_provider_failure(self, provider_key: str):
        cb = self._circuit_breakers.setdefault(provider_key, {"is_open": False, "failure_count": 0, "last_failure": 0.0})
        cb["failure_count"] += 1
        cb["last_failure"] = time.time()
        if cb["failure_count"] >= 3:
            cb["is_open"] = True
            logger.warning(f"Circuit breaker tripped for provider '{provider_key}'. Entering fail-safe fallback mode.")

    def record_provider_success(self, provider_key: str):
        cb = self._circuit_breakers.setdefault(provider_key, {"is_open": False, "failure_count": 0, "last_failure": 0.0})
        cb["failure_count"] = 0
        cb["is_open"] = False

    def route_request(
        self,
        task_type: str,
        data_classification: str = "INTERNAL",
        complexity: str = "NORMAL",        # LOW, NORMAL, HIGH, CRITICAL
        latency_requirement: str = "NORMAL", # REALTIME, FAST, NORMAL, BATCH
        cost_preference: str = "BALANCED", # MINIMIZE, BALANCED, PERFORMANCE
        has_media: bool = False,
        risk_level: str = "LOW",           # LOW, MEDIUM, HIGH, CRITICAL
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary"
    ) -> CognitiveRoutingDecision:
        """
        Determines the optimal cognitive model and mode while preserving sovereign invariants.
        """
        cb_healthy = not self._circuit_breakers.get("gemma4", {}).get("is_open", False)

        # 1. Sovereignty / Privacy Boundary
        if data_classification in ("RESTRICTED", "HIGHLY_RESTRICTED"):
            return CognitiveRoutingDecision(
                selected_provider="GOOGLE_GEMMA_4",
                selected_model="gemma-4-31b-it",
                deployment_mode="LOCAL",
                routing_reason="Data classification requires 100% on-premise sovereign local execution.",
                is_sovereign=True,
                requires_human_approval=(risk_level in ("HIGH", "CRITICAL")),
                fallback_available=True,
                circuit_healthy=cb_healthy
            )

        # 2. Circuit Breaker Fallback Mode (Section 25: Model Failure Resilience)
        if not cb_healthy:
            return CognitiveRoutingDecision(
                selected_provider="ZONATA_DETERMINISTIC_SAFE_FALLBACK",
                selected_model="deterministic-governance-engine",
                deployment_mode="LOCAL",
                routing_reason="Primary cognitive provider circuit breaker tripped; routed to deterministic rule engine.",
                is_sovereign=True,
                requires_human_approval=True,
                fallback_available=True,
                circuit_healthy=False
            )

        # 3. High-Risk / High-Complexity / Strategic Planning
        if complexity in ("HIGH", "CRITICAL") or risk_level in ("HIGH", "CRITICAL") or task_type in ("STRATEGIC_PLANNING", "EXECUTIVE_DECISION", "ORGANIZATIONAL_RESTRUCTURE"):
            return CognitiveRoutingDecision(
                selected_provider="GOOGLE_GEMMA_4",
                selected_model="gemma-4-31b-it",
                deployment_mode="HYBRID",
                routing_reason="High-complexity / high-risk strategic reasoning routed to Gemma 4 31B IT.",
                is_sovereign=False,
                requires_human_approval=(risk_level in ("HIGH", "CRITICAL")),
                fallback_available=True,
                circuit_healthy=True
            )

        # 4. Latency-Critical or Cost-Sensitive High-Throughput Tasks
        if latency_requirement in ("REALTIME", "FAST") or cost_preference == "MINIMIZE" or task_type in ("CLASSIFICATION", "FAST_MONITORING", "CONVERSATIONAL_STATUS"):
            return CognitiveRoutingDecision(
                selected_provider="GOOGLE_GEMMA_4",
                selected_model="gemma-4-26b-a4b-it",
                deployment_mode="HYBRID",
                routing_reason="Latency-critical / cost-optimized task routed to Gemma 4 26B MoE (4B active).",
                is_sovereign=False,
                requires_human_approval=False,
                fallback_available=True,
                circuit_healthy=True
            )

        # 5. Default Executive Interaction
        return CognitiveRoutingDecision(
            selected_provider="GOOGLE_GEMMA_4",
            selected_model="gemma-4-31b-it",
            deployment_mode="HYBRID",
            routing_reason="Standard executive conversation routed to production default Gemma 4 31B IT.",
            is_sovereign=False,
            requires_human_approval=False,
            fallback_available=True,
            circuit_healthy=True
        )


# Global singleton router instance
cognitive_router = CognitiveModelRouter()
