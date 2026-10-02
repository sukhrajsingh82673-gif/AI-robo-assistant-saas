"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Phase 16 — Policy-Driven Multi-Model Dynamic Routing Engine
Routes inference requests dynamically across approved providers based on:
  - Task type
  - Data classification level
  - Latency requirement
  - Cost ceiling
  - Provider circuit health
  - Tenant sovereignty rules

Constitutional Invariant:
  MODEL_CANNOT_SELECT_ITS_OWN_PROVIDER_WITHOUT_POLICY_AUTHORIZATION
  HIGHLY_RESTRICTED_DATA_ROUTED_ONLY_TO_SOVEREIGN_ENDPOINTS
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.model_data_firewall import model_data_firewall
from core.model_gateway_v4 import model_gateway_v4, ModelSecurityException

logger = logging.getLogger("zonata.model.router.v6")

class RoutingViolationError(PermissionError):
    """Raised when routing constraints cannot be satisfied securely."""
    pass

@dataclass
class ModelRouteDecision:
    selected_provider: str
    selected_model: str
    routing_reason: str
    is_sovereign: bool
    estimated_cost_usd: float

class MultiModelRouterV6:
    """
    Policy-driven routing gate connecting AI Employees to optimal model backends.
    """
    PROVIDER_CATALOG = {
        "ANTHROPIC": {
            "model": "claude-3-7-sonnet",
            "allowed_classifications": {"PUBLIC", "INTERNAL"},
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "is_sovereign": False,
            "latency_tier": "FAST"
        },
        "OPENAI": {
            "model": "gpt-4o",
            "allowed_classifications": {"PUBLIC", "INTERNAL"},
            "cost_per_1k_input": 0.0025,
            "cost_per_1k_output": 0.010,
            "is_sovereign": False,
            "latency_tier": "FAST"
        },
        "SOVEREIGN_LOCAL": {
            "model": "llama-3.3-70b-instruct",
            "allowed_classifications": {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "HIGHLY_RESTRICTED"},
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "is_sovereign": True,
            "latency_tier": "NORMAL"
        },
        "MOCK_DETERMINISTIC": {
            "model": "zonata-deterministic-v6",
            "allowed_classifications": {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "HIGHLY_RESTRICTED"},
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "is_sovereign": True,
            "latency_tier": "REALTIME"
        }
    }

    def route_request(
        self,
        tenant_id: str,
        task_type: str,
        data_classification: str,
        prompt_token_count: int,
        max_cost_usd: float = 1.0,
        preferred_provider: Optional[str] = None,
        require_sovereign: bool = False
    ) -> ModelRouteDecision:
        """
        Determines the authorized, optimal model provider and endpoint.
        """
        # 1. Classification Sovereignty Gate
        if data_classification in ("RESTRICTED", "HIGHLY_RESTRICTED") or require_sovereign:
            # Must route strictly to local sovereign endpoints
            return ModelRouteDecision(
                selected_provider="SOVEREIGN_LOCAL",
                selected_model="llama-3.3-70b-instruct",
                routing_reason="Classification level requires 100% on-premise sovereign isolation.",
                is_sovereign=True,
                estimated_cost_usd=0.0
            )

        # 2. Preferred Provider evaluation
        if preferred_provider and preferred_provider in self.PROVIDER_CATALOG:
            spec = self.PROVIDER_CATALOG[preferred_provider]
            if data_classification in spec["allowed_classifications"]:
                est_cost = (prompt_token_count / 1000.0) * spec["cost_per_1k_input"]
                if est_cost <= max_cost_usd:
                    return ModelRouteDecision(
                        selected_provider=preferred_provider,
                        selected_model=spec["model"],
                        routing_reason=f"Preferred provider '{preferred_provider}' meets policy and budget constraints.",
                        is_sovereign=spec["is_sovereign"],
                        estimated_cost_usd=est_cost
                    )

        # 3. Dynamic Fallback to Fast Cloud Provider
        for prov_name in ("OPENAI", "ANTHROPIC"):
            spec = self.PROVIDER_CATALOG[prov_name]
            if data_classification in spec["allowed_classifications"]:
                est_cost = (prompt_token_count / 1000.0) * spec["cost_per_1k_input"]
                if est_cost <= max_cost_usd:
                    return ModelRouteDecision(
                        selected_provider=prov_name,
                        selected_model=spec["model"],
                        routing_reason=f"Dynamic routing selected '{prov_name}' for speed and classification clearance.",
                        is_sovereign=False,
                        estimated_cost_usd=est_cost
                    )

        # 4. Fallback to Local Sovereign
        return ModelRouteDecision(
            selected_provider="SOVEREIGN_LOCAL",
            selected_model="llama-3.3-70b-instruct",
            routing_reason="Default sovereign fallback engaged.",
            is_sovereign=True,
            estimated_cost_usd=0.0
        )

model_router_v6 = MultiModelRouterV6()
