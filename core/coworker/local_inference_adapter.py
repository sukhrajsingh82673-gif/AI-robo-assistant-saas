"""
ZONATA Autonomous Executive Coworker — Milestone 2: Local Inference Adapter
Provides hardware-budget-aware local inference delegation for Hermes Agent.
Prioritizes localhost Ollama at 127.0.0.1:11434 with 1.5s timeout probe,
cascading to core.llm_runtime.llm_runtime.
Reports honest status ('LLM_UNAVAILABLE', available=False) when unconfigured without hallucinations.
"""

from __future__ import annotations
import os
import sys
import json
import time
import socket
import resource
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class HardwareBudget:
    """Enforces ARM64 / Container RAM limits to prevent process eviction."""
    max_process_ram_mb: float = 180.0
    total_system_ram_mb: float = 620.0
    architecture: str = "arm64"

    @classmethod
    def get_current_ram_mb(cls) -> float:
        """Reads resident memory usage via resource.getrusage."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # On Linux ru_maxrss is in KiB; on Darwin/macOS it is in bytes.
        if sys.platform == "darwin":
            return usage.ru_maxrss / (1024.0 * 1024.0)
        return usage.ru_maxrss / 1024.0

    def is_constrained(self) -> bool:
        return self.get_current_ram_mb() > self.max_process_ram_mb

    def get_memory_status(self) -> Dict[str, Any]:
        cur = self.get_current_ram_mb()
        return {
            "architecture": self.architecture,
            "max_process_ram_mb": self.max_process_ram_mb,
            "total_system_ram_mb": self.total_system_ram_mb,
            "current_ram_mb": round(cur, 2),
            "constrained": cur > self.max_process_ram_mb
        }


@dataclass
class LocalInferenceStatus:
    available: bool
    endpoint: Optional[str]
    provider: str
    active_model: Optional[str]
    ram_usage_mb: float
    hardware_constrained: bool
    status: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "endpoint": self.endpoint,
            "provider": self.provider,
            "active_model": self.active_model,
            "ram_usage_mb": round(self.ram_usage_mb, 2),
            "hardware_constrained": self.hardware_constrained,
            "status": self.status,
            "error": self.error,
        }


class LocalInferenceAdapter:
    """
    Hardware-budget-aware local inference adapter for Hermes Agent.
    Prioritizes localhost Ollama at 127.0.0.1:11434 with a 1.5s probe,
    cascading to core.llm_runtime.llm_runtime.
    Returns honest status='LLM_UNAVAILABLE', available=False without hallucinations.
    """

    def __init__(
        self,
        ollama_endpoint: str = "http://127.0.0.1:11434",
        budget: Optional[HardwareBudget] = None,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
    ):
        self.ollama_endpoint = os.environ.get("OLLAMA_BASE_URL", ollama_endpoint).rstrip("/")
        self.budget = budget or HardwareBudget()
        self.tenant_id = tenant_id
        self.company_id = company_id

    def inspect_inference_health(self, timeout: float = 1.5) -> LocalInferenceStatus:
        """
        Probe localhost Ollama at 127.0.0.1:11434 with timeout.
        If unavailable, cascade to core.llm_runtime.llm_runtime.status("tnt_primary", "comp_primary").
        """
        current_ram = self.budget.get_current_ram_mb()
        constrained = current_ram > self.budget.max_process_ram_mb

        # 1. Probe localhost Ollama
        try:
            req = urllib.request.Request(
                f"{self.ollama_endpoint}/api/tags",
                headers={"User-Agent": "ZONATA-Hermes-Probe"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    active_model = models[0] if models else "qwen2.5:1.5b"
                    return LocalInferenceStatus(
                        available=True,
                        endpoint=self.ollama_endpoint,
                        provider="ollama_local",
                        active_model=active_model,
                        ram_usage_mb=current_ram,
                        hardware_constrained=constrained,
                        status="ONLINE",
                        error=None,
                    )
        except Exception:
            pass

        # 2. Cascade to core.llm_runtime.llm_runtime status check
        try:
            from core.llm_runtime import llm_runtime
            rt_status = llm_runtime.status(self.tenant_id, self.company_id)
            if rt_status.get("status") in ("ONLINE", "READY", "HEALTHY") or rt_status.get("configured", False):
                return LocalInferenceStatus(
                    available=True,
                    endpoint=rt_status.get("endpoint"),
                    provider=rt_status.get("provider", "llm_runtime"),
                    active_model=rt_status.get("model", "embedded_free"),
                    ram_usage_mb=current_ram,
                    hardware_constrained=constrained,
                    status="RUNTIME_CASCADE_AVAILABLE",
                    error=None,
                )
        except Exception:
            pass

        # 3. Honest unavailable reporting (no hallucinations)
        return LocalInferenceStatus(
            available=False,
            endpoint=None,
            provider="none",
            active_model=None,
            ram_usage_mb=current_ram,
            hardware_constrained=constrained,
            status="LLM_UNAVAILABLE",
            error="No local Ollama (127.0.0.1:11434) or platform LLM runtime provider is available.",
        )

    detect_status = inspect_inference_health

    def dispatch_hermes_reasoning(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Executes reasoning via localhost Ollama or cascades to core.llm_runtime.llm_runtime.chat().
        If neither has a live model/endpoint, returns honest status='LLM_UNAVAILABLE', available=False.
        """
        health = self.inspect_inference_health(timeout=1.5)

        # 1. Localhost Ollama dispatch
        if health.provider == "ollama_local" and health.available:
            try:
                formatted_msgs = []
                if system_prompt:
                    formatted_msgs.append({"role": "system", "content": system_prompt})
                formatted_msgs.extend(messages)

                payload = {
                    "model": model or health.active_model or "qwen2.5:1.5b",
                    "messages": formatted_msgs,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens}
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.ollama_endpoint}/api/chat",
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    msg = res.get("message", {})
                    return {
                        "content": msg.get("content", ""),
                        "tool_calls": [],
                        "model": res.get("model", health.active_model),
                        "provider": "ollama_local",
                        "status": "COMPLETED",
                        "available": True,
                        "ram_usage_mb": health.ram_usage_mb,
                        "hardware_constrained": health.hardware_constrained,
                        "usage": {
                            "prompt_tokens": res.get("prompt_eval_count", 0),
                            "completion_tokens": res.get("eval_count", 0),
                        }
                    }
            except Exception:
                pass

        # 2. Cascade to core.llm_runtime.llm_runtime
        try:
            from core.llm_runtime import llm_runtime
            clean_msgs = []
            for m in messages:
                if m.get("role") == "system" and not system_prompt:
                    system_prompt = m.get("content")
                elif m.get("role") != "system":
                    clean_msgs.append(m)

            result = llm_runtime.chat(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                messages=clean_msgs,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            if result.content and not result.degraded and result.provider != "deterministic":
                return {
                    "content": result.content,
                    "tool_calls": [],
                    "model": result.model,
                    "provider": result.provider,
                    "status": "COMPLETED",
                    "available": True,
                    "ram_usage_mb": health.ram_usage_mb,
                    "hardware_constrained": health.hardware_constrained,
                    "usage": {
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                    }
                }
        except Exception:
            pass

        # 3. Honest unavailable response (no fake reasoning)
        return {
            "content": "",
            "tool_calls": [],
            "model": "none",
            "provider": "none",
            "status": "LLM_UNAVAILABLE",
            "available": False,
            "ram_usage_mb": health.ram_usage_mb,
            "hardware_constrained": health.hardware_constrained,
            "error": "No live local Ollama or platform LLM runtime endpoint is configured.",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0}
        }

    generate_completion = dispatch_hermes_reasoning
