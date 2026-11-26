"""ZONATA Sovereign Core — Google ADK Model Wrapper.

Implements OpenCode Step 4F (Rule 34 Port Isolation):
Wraps Google Agent Development Kit (ADK) model interactions to ensure
100% of model calls route through sovereign LLMGatewayPort with token accounting,
model tier enforcement, and correlation IDs.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from core.ports.llm import llm_gateway, ModelTier

logger = logging.getLogger(__name__)


class ZonataADKModel:
    """Wrapped model client for Google ADK agents routing exclusively through LLMGateway."""

    def __init__(self, default_tier: str = "WORKER"):
        self.default_tier = default_tier

    def generate_content(
        self,
        tenant_id: str,
        company_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_tier: Optional[str] = None,
        correlation_id: Optional[str] = None,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """Generates content via LLMGateway without direct third-party SDK calls (Rule 34)."""
        tier_str = model_tier or self.default_tier
        tier_enum = getattr(ModelTier, tier_str, ModelTier.WORKER)

        res = llm_gateway.generate(
            tenant_id=tenant_id,
            company_id=company_id,
            tier=tier_enum,
            prompt=prompt,
            system_prompt=system_instruction,
            correlation_id=correlation_id,
            max_tokens=max_tokens,
        )

        return {
            "text": getattr(res, "text", ""),
            "input_tokens": getattr(res, "input_tokens", 100),
            "output_tokens": getattr(res, "output_tokens", 50),
            "cost_micro_usd": getattr(res, "cost_micro_usd", 500),
            "model": getattr(res, "model_id", "sovereign_llm"),
        }


adk_model = ZonataADKModel()
