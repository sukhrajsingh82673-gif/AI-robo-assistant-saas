"""
ZONATA Sovereign Core — LLMGateway Port & Multi-Tier Sovereign Adapters
Implements OpenCode Step 2B: Tiers, budgets, schemas, circuit breakers, and honest tracing.
"""

import os
import time
import json
import uuid
import random
import hashlib
import logging
import urllib.request
import urllib.error

logger = logging.getLogger("zonata.ports.llm")
from typing import Dict, Any, Optional, List, Tuple, Type, TypeVar
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel

from core.db import db, tenant_scoped, tenant_scope
from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
    port_registry,
)
from core.llm.budget import llm_budget_manager, BudgetExhaustionError
from core.llm.policy import tenant_model_policy, DataPolicyViolationError
from core.llm.prompts import prompt_registry, wrap_untrusted_content
from core.llm.typed_output import parse_and_validate, LLMOutputValidationError

T = TypeVar("T", bound=BaseModel)


class ModelTier(str, Enum):
    PLANNER = "PLANNER"
    WORKER = "WORKER"
    FAST = "FAST"
    VISION = "VISION"
    EMBEDDING = "EMBEDDING"


@dataclass
class LLMGenerationResult:
    status: PortStatus
    provider: str
    model: str
    tier: ModelTier
    text: str
    input_tokens: int
    output_tokens: int
    cost_micro_usd: int
    latency_ms: float
    trace_id: str
    sandbox: bool
    fallback_used: bool = False
    error: Optional[str] = None


class CircuitBreaker:
    """Per-provider circuit breaker guarding against cascading outages."""
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def is_available(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN allows probe


# Default price catalog (integer micro-USD per 1,000 tokens)
# 1 USD = 1,000,000 micro-USD
PRICE_CATALOG_MICRO_USD: Dict[str, Tuple[int, int]] = {
    # model: (input_micro_per_1k, output_micro_per_1k)
    "claude-3-7-sonnet": (3000, 15000),       # $3 / $15
    "claude-3-5-sonnet": (3000, 15000),
    "claude-3-5-haiku": (800, 4000),          # $0.80 / $4
    "gpt-4o": (2500, 10000),                  # $2.50 / $10
    "gpt-4o-mini": (150, 600),                # $0.15 / $0.60
    "gemini-2.5-flash": (150, 600),           # $0.15 / $0.60
    "gemini-1.5-pro": (1250, 5000),
    "text-embedding-3-small": (20, 0),        # $0.02
    "sandbox-stub": (1500, 6000),             # Test mode simulated rates ($1.50 / $6.00)
    "embedded_free": (0, 0),
}


class LLMGatewayPort(Port):
    """Sovereign Multi-Tier LLM Gateway Port."""

    def __init__(self):
        super().__init__("llm")
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._ensure_tables()

    def _ensure_tables(self):
        with db.get_connection() as conn:
            if db.pg_tables_ready(conn, "model_calls"):
                return
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS model_calls (
                call_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                correlation_id TEXT,
                tier TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_micro_usd INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                latency_ms REAL NOT NULL,
                outcome TEXT NOT NULL,
                evidence_id TEXT,
                prompt_stored TEXT,
                response_stored TEXT,
                created_at REAL NOT NULL
            );
            """)
            conn.commit()

    def _get_circuit(self, provider: str) -> CircuitBreaker:
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = CircuitBreaker()
        return self._circuit_breakers[provider]

    def _resolve_tier_config(self, tier: ModelTier) -> List[Tuple[str, str]]:
        """Resolves ordered (provider, model) fallback chain for the requested tier.
        
        Reads from environment variables (never hardcoded), with sensible defaults.
        """
        env_key = f"ZONATA_LLM_TIER_{tier.value}"
        env_val = os.environ.get(env_key)

        defaults: Dict[ModelTier, List[Tuple[str, str]]] = {
            ModelTier.PLANNER: [("anthropic", "claude-3-7-sonnet"), ("openai", "gpt-4o")],
            ModelTier.WORKER: [("openai", "gpt-4o"), ("anthropic", "claude-3-5-sonnet")],
            ModelTier.FAST: [("google", "gemini-2.5-flash"), ("openai", "gpt-4o-mini")],
            ModelTier.VISION: [("google", "gemini-2.5-flash"), ("anthropic", "claude-3-7-sonnet")],
            ModelTier.EMBEDDING: [("openai", "text-embedding-3-small"), ("google", "gemini-2.5-flash")],
        }

        if env_val:
            chain = []
            for item in env_val.split(","):
                if ":" in item:
                    p, m = item.strip().split(":", 1)
                    chain.append((p.lower(), m))
            if chain:
                return chain

        return defaults.get(tier, [("sandbox", "sandbox-stub")])

    def calculate_cost_micro_usd(self, model: str, input_tokens: int, output_tokens: int) -> int:
        """Calculate cost in integer micro-USD."""
        rates = PRICE_CATALOG_MICRO_USD.get(model, (3000, 15000))  # fallback to conservative max
        in_cost = (input_tokens * rates[0]) // 1000
        out_cost = (output_tokens * rates[1]) // 1000
        return max(0, in_cost + out_cost)

    def _dispatch_raw(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.0,
        timeout: float = 30.0
    ) -> Tuple[str, int, int]:
        """Low-level dispatch to individual provider endpoints.
        
        Returns (response_text, input_tokens, output_tokens).
        """
        is_test_mode = os.environ.get("ZONATA_TEST_MODE") == "1"
        provider_clean = provider.lower()

        # Deterministic Sandbox / Stub Provider
        if is_test_mode or provider_clean.startswith("sandbox") or provider_clean in ("stub",):
            if "concurrent" in prompt:
                time.sleep(0.05)
            tokens_in = max(1, len(prompt) // 4)
            tokens_out = 30
            # Return predictable responses for testing
            if "fail_primary" in prompt and provider_clean in ("sandbox", "sandbox_primary"):
                raise RuntimeError(f"Simulated outage for provider {provider}")
            return f'{{"result": "sandbox_confirmed", "provider": "{provider}", "model": "{model}"}}', tokens_in, tokens_out

        # Real Anthropic REST API
        if provider_clean == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not configured")
            url = "https://api.anthropic.com/v1/messages"
            payload: Dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                payload["system"] = system_prompt
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"]
                usage = data.get("usage", {})
                return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)

        # Real OpenAI / OpenAI-compatible REST API
        if provider_clean in ("openai", "vllm", "ollama", "local"):
            api_key = os.environ.get("OPENAI_API_KEY", "ollama-local-key")
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            if provider_clean == "ollama":
                base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
            url = f"{base_url}/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

        # Real Google Gemini REST API
        if provider_clean == "google":
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY not configured")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if system_prompt:
                payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
            headers = {"Content-Type": "application/json"}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                return text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)

        raise RuntimeError(f"Unsupported or unconfigured LLM provider '{provider}'")

    @tenant_scoped
    def generate(
        self,
        tenant_id: str,
        company_id: str,
        tier: ModelTier,
        prompt: str,
        system_prompt: Optional[str] = None,
        entity_chain: Optional[List[Tuple[str, str]]] = None,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        document_sensitivities: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.0,
    ) -> LLMGenerationResult:
        """Execute a budgeted, traced, and policy-checked LLM generation turn.
        
        Enforces reserve-then-settle budgeting, circuit breakers, and automatic fallbacks.
        """
        start_time = time.time()
        trace_id = f"tr_llm_{uuid.uuid4().hex[:12]}"
        is_test_mode = os.environ.get("ZONATA_TEST_MODE") == "1"

        # 1. Resolve Tier Provider Chain
        chain = self._resolve_tier_config(tier)
        primary_provider, primary_model = chain[0]
        est_input_tokens = max(1, len(prompt) // 4)
        max_cost_micro_usd = self.calculate_cost_micro_usd(primary_model, est_input_tokens, max_tokens)

        if is_test_mode:
            chain = [("sandbox_primary", "sandbox-stub"), ("sandbox_fallback", "sandbox-stub")]

        # Build hierarchy chain: tenant -> company -> dept -> position -> mission -> task
        chain_levels = entity_chain or [("TENANT", tenant_id), ("COMPANY", company_id)]
        if mission_id and ("MISSION", mission_id) not in chain_levels:
            chain_levels.append(("MISSION", mission_id))
        if task_id and ("TASK", task_id) not in chain_levels:
            chain_levels.append(("TASK", task_id))

        # 3. Reserve Budget (atomic row lock)
        reservation_id = llm_budget_manager.reserve(
            tenant_id=tenant_id,
            company_id=company_id,
            entity_chain=chain_levels,
            max_cost_micro_usd=max_cost_micro_usd,
            mission_id=mission_id,
            task_id=task_id,
        )

        last_error = None
        fallback_used = False

        for idx, (provider, model) in enumerate(chain):
            cb = self._get_circuit(provider)
            if not cb.is_available():
                logger.warning(f"Circuit breaker OPEN for provider '{provider}'; failing over to next in tier.")
                fallback_used = True
                continue

            try:
                # 4. Check Tenant Data Policy & Document Sensitivity
                tenant_model_policy.validate_dispatch(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    provider=provider,
                    document_sensitivities=document_sensitivities,
                )

                # 5. Dispatch
                t0 = time.perf_counter()
                text, in_tok, out_tok = self._dispatch_raw(
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0

                actual_cost_micro_usd = self.calculate_cost_micro_usd(model, in_tok, out_tok)
                cb.record_success()

                # 6. Settle Budget
                llm_budget_manager.settle(
                    reservation_id=reservation_id,
                    actual_cost_micro_usd=actual_cost_micro_usd,
                    entity_chain=chain_levels,
                    tenant_id=tenant_id,
                    company_id=company_id,
                )

                # 7. Record Auditable Trace (Rule 10: Zero secrets stored)
                self._record_trace(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    tier=tier.value,
                    provider=provider,
                    model=model,
                    prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_micro_usd=actual_cost_micro_usd,
                    latency_ms=latency_ms,
                    outcome="OK",
                    evidence_id=evidence_id,
                )

                return LLMGenerationResult(
                    status=PortStatus.OK,
                    provider=provider,
                    model=model,
                    tier=tier,
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_micro_usd=actual_cost_micro_usd,
                    latency_ms=latency_ms,
                    trace_id=trace_id,
                    sandbox=is_test_mode or provider == "sandbox",
                    fallback_used=fallback_used or (idx > 0)
                )

            except Exception as e:
                cb.record_failure()
                last_error = str(e)
                fallback_used = True
                logger.warning(f"LLM dispatch failed on provider '{provider}': {e}. Attempting fallback...")

        # If all providers fail, release reserved budget
        llm_budget_manager.release(
            reservation_id,
            entity_chain=chain_levels,
            tenant_id=tenant_id,
            company_id=company_id,
        )
        latency_ms = (time.time() - start_time) * 1000.0

        self._record_trace(
            tenant_id=tenant_id,
            company_id=company_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            tier=tier.value,
            provider="none",
            model="none",
            prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            input_tokens=0,
            output_tokens=0,
            cost_micro_usd=0,
            latency_ms=latency_ms,
            outcome="FAILED",
            evidence_id=evidence_id,
        )

        return LLMGenerationResult(
            status=PortStatus.FAILED,
            provider="all_failed",
            model="none",
            tier=tier,
            text="",
            input_tokens=0,
            output_tokens=0,
            cost_micro_usd=0,
            latency_ms=latency_ms,
            trace_id=trace_id,
            sandbox=is_test_mode,
            fallback_used=True,
            error=last_error or "All providers in tier fallback chain failed."
        )

    @tenant_scoped
    def generate_structured(
        self,
        tenant_id: str,
        company_id: str,
        tier: ModelTier,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        entity_chain: Optional[List[Tuple[str, str]]] = None,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        document_sensitivities: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> Tuple[T, LLMGenerationResult]:
        """Generate typed, schema-validated proposal with exactly ONE self-correction retry.
        
        Enforces Rule 16: If validation fails twice, fails closed with LLMOutputValidationError.
        """
        schema_json = json.dumps(schema.schema())
        typed_prompt = (
            f"{prompt}\n\n"
            f"You MUST output strictly a JSON object conforming to this JSON Schema:\n"
            f"{schema_json}\n"
            f"Output JSON only. Do not wrap in markdown or add conversational filler."
        )

        # First Attempt
        res = self.generate(
            tenant_id=tenant_id,
            company_id=company_id,
            tier=tier,
            prompt=typed_prompt,
            system_prompt=system_prompt,
            entity_chain=entity_chain,
            mission_id=mission_id,
            task_id=task_id,
            document_sensitivities=document_sensitivities,
            correlation_id=correlation_id,
            evidence_id=evidence_id,
            max_tokens=max_tokens,
        )

        if res.status != PortStatus.OK:
            raise LLMOutputValidationError(
                schema_name=schema.__name__,
                raw_output=res.text,
                validation_error=res.error or "Underlying model generation failed."
            )

        parsed, error = parse_and_validate(res.text, schema)
        if parsed is not None:
            return parsed, res

        # Single Self-Correction Retry with Validation Error
        logger.info(f"Schema validation failed on attempt 1: {error}. Retrying once...")
        retry_prompt = (
            f"{typed_prompt}\n\n"
            f"[PREVIOUS ATTEMPT FAILED SCHEMA VALIDATION]\n"
            f"Your previous output was:\n{res.text}\n"
            f"Validation error:\n{error}\n"
            f"Please correct the errors and return ONLY the valid JSON object."
        )

        retry_res = self.generate(
            tenant_id=tenant_id,
            company_id=company_id,
            tier=tier,
            prompt=retry_prompt,
            system_prompt=system_prompt,
            entity_chain=entity_chain,
            mission_id=mission_id,
            task_id=task_id,
            document_sensitivities=document_sensitivities,
            correlation_id=correlation_id,
            evidence_id=evidence_id,
            max_tokens=max_tokens,
        )

        if retry_res.status != PortStatus.OK:
            raise LLMOutputValidationError(
                schema_name=schema.__name__,
                raw_output=retry_res.text,
                validation_error=retry_res.error or "Retry model generation failed."
            )

        retry_parsed, retry_error = parse_and_validate(retry_res.text, schema)
        if retry_parsed is not None:
            return retry_parsed, retry_res

        # Fail closed
        raise LLMOutputValidationError(
            schema_name=schema.__name__,
            raw_output=retry_res.text,
            validation_error=retry_error or "Output failed schema validation after retry."
        )

    @tenant_scoped
    def _record_trace(
        self,
        tenant_id: str,
        company_id: str,
        trace_id: str,
        correlation_id: Optional[str],
        tier: str,
        provider: str,
        model: str,
        prompt_hash: str,
        input_tokens: int,
        output_tokens: int,
        cost_micro_usd: int,
        latency_ms: float,
        outcome: str,
        evidence_id: Optional[str],
    ):
        """Record model call trace strictly avoiding secret leakage (Rule 10)."""
        now = time.time()
        call_id = f"mc_{uuid.uuid4().hex[:12]}"
        prompt_id = "prompt.unregistered"

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO model_calls (
                call_id, tenant_id, company_id, trace_id, correlation_id, tier,
                provider, model, prompt_id, prompt_hash, input_tokens, output_tokens,
                cost_micro_usd, currency, latency_ms, outcome, evidence_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?, ?)
            """, (
                call_id, tenant_id, company_id, trace_id, correlation_id, tier,
                provider, model, prompt_id, prompt_hash, input_tokens, output_tokens,
                cost_micro_usd, latency_ms, outcome, evidence_id, now
            ))
            conn.commit()

    def probe(self) -> ProviderResult:
        """Harmless capability truth probe reporting active providers, tiers, and fallback health."""
        t0 = time.perf_counter()
        is_test_mode = os.environ.get("ZONATA_TEST_MODE") == "1"
        is_prod = os.environ.get("APP_ENV") == "production"
        allow_degraded = os.environ.get("ZONATA_ALLOW_DEGRADED") == "1"

        explicit_provider = os.environ.get("ZONATA_LLM_PROVIDER", "").strip().lower()
        if explicit_provider:
            key_map = {
                "openai": os.environ.get("OPENAI_API_KEY"),
                "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
                "gemini": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
                "google": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
            }
            if explicit_provider in ("ollama", "local", "vllm", "embedded_free"):
                pass
            elif explicit_provider in key_map and key_map[explicit_provider]:
                pass
            else:
                return NotConfiguredProvider(
                    "llm",
                    f"No API key or verified endpoint configured for LLM provider '{explicit_provider}'"
                ).probe()

        planner_chain = self._resolve_tier_config(ModelTier.PLANNER)
        primary_p, primary_m = planner_chain[0]

        if is_test_mode:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider="sandbox_llm_gateway",
                provider_ref="sandbox_tiers_active",
                sandbox=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                cost=0.0,
                metadata={
                    "tiers": [t.value for t in ModelTier],
                    "primary_provider": primary_p,
                    "primary_model": primary_m,
                    "sandbox": True
                }
            )

        if primary_p == "embedded_free":
            status = PortStatus.DEGRADED if (is_prod and allow_degraded) else PortStatus.DEGRADED
            return ProviderResult(
                status=status,
                provider="embedded_free",
                provider_ref="heuristic_rule_engine",
                sandbox=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                cost=0.0,
                metadata={"degraded": True, "note": "Embedded free rule engine active"}
            )

        # Check API key configuration
        has_key = False
        if primary_p == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            has_key = True
        elif primary_p == "openai" and os.environ.get("OPENAI_API_KEY"):
            has_key = True
        elif primary_p == "google" and (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            has_key = True
        elif primary_p in ("ollama", "local", "vllm"):
            has_key = True

        if not has_key:
            return NotConfiguredProvider("llm", f"API keys not configured for primary provider '{primary_p}'").probe()

        return ProviderResult(
            status=PortStatus.OK,
            provider=primary_p,
            provider_ref=f"llm_{primary_p}_{primary_m}",
            sandbox=False,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            cost="UNMEASURED",
            metadata={
                "primary_model": primary_m,
                "tiers": [t.value for t in ModelTier],
                "circuit_status": self._get_circuit(primary_p).state
            }
        )


# Global instance & registration
llm_gateway = LLMGatewayPort()
port_registry.register("llm", llm_gateway)
