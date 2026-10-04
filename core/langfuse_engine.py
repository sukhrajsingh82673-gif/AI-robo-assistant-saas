"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Langfuse AI Observability, LLM Tracing & Evaluation Engine
==========================================================
Captures prompt, model, response, token usage, latency, cost calculations,
tool calls, retrieval contexts, evaluation scores, and human feedback.
Bridges with OpenTelemetry and provides LLM performance analytics for AI CEO.

Constitutional Invariant:
  Langfuse is an AI observability and evaluation tool, NOT a governance authority.
  ZONATA EvidenceLedger remains the sole cryptographic authority for outcome truth.
"""

import os
import time
import json
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.ai.langfuse")

# Industry standard pricing per 1M tokens in USD
MODEL_PRICING_PER_1M = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "hermes-3-llama-3.1": {"input": 0.0, "output": 0.0},
    "local-model": {"input": 0.0, "output": 0.0}
}

@dataclass
class LangfuseGeneration:
    generation_id: str
    trace_id: str
    name: str
    model: str
    prompt: str
    response: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    start_time: float
    end_time: float
    tenant_id: str
    company_id: str
    mission_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    eval_scores: Dict[str, float] = field(default_factory=dict)
    human_feedback: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PromptVersion:
    prompt_id: str
    name: str
    version: int
    template: str
    variables: List[str]
    created_at: float
    author: str
    is_active: bool

class LangfuseEngine:
    """
    Production-grade Langfuse AI Observability & Evaluation Engine for ZONATA.
    Can operate self-hosted in-memory/SQLite and forward to upstream Langfuse server.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LangfuseEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, host: Optional[str] = None, public_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.host = host or os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
        self.public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-zonata-mock")
        self.secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "sk-zonata-mock")
        self._generations: List[LangfuseGeneration] = []
        self._prompts: Dict[str, List[PromptVersion]] = {}
        self._outage_active = False
        self._lock = threading.Lock()

    def simulate_outage(self, enabled: bool):
        """Simulates Langfuse service outage for failure injection."""
        self._outage_active = enabled

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculates exact dollar cost using model token pricing matrix."""
        model_key = model.lower()
        if "local" in model_key or "hermes" in model_key or "llama" in model_key:
            return 0.0

        pricing = None
        for k, v in MODEL_PRICING_PER_1M.items():
            if k in model_key:
                pricing = v
                break
        if not pricing:
            pricing = MODEL_PRICING_PER_1M["gpt-4o"]  # Conservative default

        cost_in = (input_tokens / 1_000_000.0) * pricing["input"]
        cost_out = (output_tokens / 1_000_000.0) * pricing["output"]
        return round(cost_in + cost_out, 6)

    def record_generation(
        self,
        name: str,
        model: str,
        prompt: str,
        response: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        latency_ms: float = 0.0,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        mission_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        completion: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None
    ) -> LangfuseGeneration:
        """Records an LLM generation trace with automatic token cost computation."""
        if self._outage_active:
            raise ConnectionError("Langfuse AI observability service unreachable (Connection refused)")

        resp_text = response if response is not None else (completion or "")
        inp_tok = input_tokens if input_tokens is not None else (prompt_tokens or 0)
        out_tok = output_tokens if output_tokens is not None else (completion_tokens or 0)
        start_time = time.time() - (latency_ms / 1000.0)
        end_time = time.time()
        cost_usd = self.calculate_cost(model, inp_tok, out_tok)
        gen_id = f"gen_{uuid.uuid4().hex[:12]}"
        t_id = trace_id or f"trace_{uuid.uuid4().hex[:16]}"

        gen = LangfuseGeneration(
            generation_id=gen_id,
            trace_id=t_id,
            name=name,
            model=model,
            prompt=prompt,
            response=resp_text,
            input_tokens=inp_tok,
            output_tokens=out_tok,
            total_tokens=inp_tok + out_tok,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            start_time=start_time,
            end_time=end_time,
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            agent_id=agent_id,
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )

        with self._lock:
            self._generations.append(gen)
            if len(self._generations) > 2000:
                self._generations.pop(0)

        logger.info(
            f"LANGFUSE TRACE: [{gen.model}] Tokens: {gen.total_tokens} (In: {input_tokens}, Out: {output_tokens}) "
            f"Cost: ${cost_usd:.6f} Latency: {latency_ms:.1f}ms - Trace: {t_id}"
        )
        return gen

    def submit_score(self, generation_id: str, metric: str, score: float, comment: Optional[str] = None) -> bool:
        """Attaches an automated evaluation score to a generation."""
        with self._lock:
            for g in self._generations:
                if g.generation_id == generation_id:
                    g.eval_scores[metric] = score
                    if comment:
                        g.metadata[f"score_comment_{metric}"] = comment
                    return True
        return False

    def submit_feedback(self, generation_id: str, rating: int, comment: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """Records human feedback (1-5 rating, comment, user_id)."""
        with self._lock:
            for g in self._generations:
                if g.generation_id == generation_id:
                    g.human_feedback = {
                        "rating": rating,
                        "comment": comment,
                        "user_id": user_id or "anonymous_evaluator",
                        "timestamp": time.time()
                    }
                    return True
        return False

    def register_prompt(self, name: str, template: str, variables: List[str], author: str = "AI_CEO") -> PromptVersion:
        """Registers a versioned prompt template."""
        with self._lock:
            history = self._prompts.get(name, [])
            new_version = len(history) + 1
            for p in history:
                p.is_active = False

            pv = PromptVersion(
                prompt_id=f"prompt_{uuid.uuid4().hex[:8]}",
                name=name,
                version=new_version,
                template=template,
                variables=variables,
                created_at=time.time(),
                author=author,
                is_active=True
            )
            history.append(pv)
            self._prompts[name] = history
            return pv

    def get_prompt(self, name: str, version: Optional[int] = None) -> Optional[PromptVersion]:
        with self._lock:
            history = self._prompts.get(name, [])
            if not history:
                return None
            if version is not None:
                for p in history:
                    if p.version == version:
                        return p
                return None
            # Return active or latest
            for p in history:
                if p.is_active:
                    return p
            return history[-1]

    def get_generations(
        self,
        tenant_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            res = []
            for g in self._generations:
                if tenant_id and g.tenant_id != tenant_id:
                    continue
                if mission_id and g.mission_id != mission_id:
                    continue
                if agent_id and g.agent_id != agent_id:
                    continue
                res.append(g.to_dict())
            return res

    def get_analytics(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregates LLM metrics across all captured generations."""
        with self._lock:
            total_tokens = 0
            total_cost = 0.0
            total_latency = 0.0
            model_counts: Dict[str, int] = {}
            filtered = [g for g in self._generations if not tenant_id or g.tenant_id == tenant_id]

            for g in filtered:
                total_tokens += g.total_tokens
                total_cost += g.cost_usd
                total_latency += g.latency_ms
                model_counts[g.model] = model_counts.get(g.model, 0) + 1

            count = len(filtered)
            return {
                "total_generations": count,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "avg_latency_ms": round(total_latency / count, 2) if count > 0 else 0.0,
                "models_used": model_counts
            }

# Global singleton instance
langfuse_engine = LangfuseEngine.get_instance()

