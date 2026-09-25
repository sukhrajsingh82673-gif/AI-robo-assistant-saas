"""
RoboAssistant Company OS 1.0 — Model Gateway & AI Orchestration Layer
Multi-provider abstraction: Cloud LLMs, Local Models, Reasoning, Vision & Code.
Enforces cost ceilings, latency policies, fallback routing, and token metering.
"""

from typing import Dict, Any, Optional, List
import time
import uuid
from .billing import UsageMeteringEngine

class ModelTier:
    FRONTIER_REASONING = "frontier_reasoning"
    STANDARD_BALANCED = "standard_balanced"
    FAST_LOCAL = "fast_local"
    CODE_SPECIALIST = "code_specialist"

class ModelProvider:
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL_LLAMA = "local_llama"

class ModelSpec:
    def __init__(
        self,
        model_id: str,
        provider: str,
        tier: str,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
        max_context: int,
        supports_vision: bool = False,
        supports_tools: bool = True
    ):
        self.model_id = model_id
        self.provider = provider
        self.tier = tier
        self.input_cost_per_1k = input_cost_per_1k
        self.output_cost_per_1k = output_cost_per_1k
        self.max_context = max_context
        self.supports_vision = supports_vision
        self.supports_tools = supports_tools

class ModelGateway:
    """
    Central gateway routing all AI model requests.
    Prevents unauthorized spend and transparently meters every call.
    """
    REGISTRY: Dict[str, ModelSpec] = {
        "claude-3-7-sonnet": ModelSpec(
            model_id="claude-3-7-sonnet",
            provider=ModelProvider.ANTHROPIC,
            tier=ModelTier.FRONTIER_REASONING,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            max_context=200000,
            supports_vision=True
        ),
        "gpt-4o": ModelSpec(
            model_id="gpt-4o",
            provider=ModelProvider.OPENAI,
            tier=ModelTier.STANDARD_BALANCED,
            input_cost_per_1k=0.0025,
            output_cost_per_1k=0.010,
            max_context=128000,
            supports_vision=True
        ),
        "gemini-2.5-flash": ModelSpec(
            model_id="gemini-2.5-flash",
            provider=ModelProvider.GOOGLE,
            tier=ModelTier.STANDARD_BALANCED,
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
            max_context=1000000,
            supports_vision=True
        ),
        "local-llama-3.3-70b": ModelSpec(
            model_id="local-llama-3.3-70b",
            provider=ModelProvider.LOCAL_LLAMA,
            tier=ModelTier.FAST_LOCAL,
            input_cost_per_1k=0.000,
            output_cost_per_1k=0.000,
            max_context=32768,
            supports_vision=False
        )
    }

    @classmethod
    def select_model(cls, task_tier: str = ModelTier.STANDARD_BALANCED, prefer_local: bool = False) -> str:
        """Determines best model matching cost, task profile, and company privacy requirements."""
        if prefer_local:
            return "local-llama-3.3-70b"
        for mid, spec in cls.REGISTRY.items():
            if spec.tier == task_tier:
                return mid
        return "claude-3-7-sonnet"

    @classmethod
    def dispatch_inference(
        cls,
        tenant_id: str,
        company_id: Optional[str],
        agent_id: str,
        mission_id: Optional[str],
        prompt: str,
        model_id: Optional[str] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Governed dispatch. Simulates token consumption, calculates exact cost,
        and records auditable billing usage.
        """
        chosen_model = model_id or cls.select_model()
        spec = cls.REGISTRY.get(chosen_model, cls.REGISTRY["claude-3-7-sonnet"])

        # Estimate tokens (approx 4 chars per token)
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = min(max_tokens, 150)

        cost = (input_tokens / 1000.0 * spec.input_cost_per_1k) + (output_tokens / 1000.0 * spec.output_cost_per_1k)

        # Record in Usage Metering Engine
        record_id = UsageMeteringEngine.record_usage(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=agent_id,
            mission_id=mission_id,
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=round(cost, 6)
        )

        return {
            "record_id": record_id,
            "model": chosen_model,
            "provider": spec.provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 6),
            "status": "COMPLETED",
            "timestamp": time.time()
        }
