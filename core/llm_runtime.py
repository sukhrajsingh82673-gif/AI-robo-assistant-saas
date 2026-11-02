"""
ZONATA / RoboAssistant — Governed LLM Runtime
=============================================================
A single, production-safe entry point for every cognitive call in the
platform.  It is deliberately dependency-free (stdlib only) so it can run
on the free tier and inside restricted containers.

Provider resolution order (default ``embedded_free``):

  1. ``ollama``            — local, fully embedded, zero cost, zero data egress.
  2. ``embedded_free``     — keyless free OpenAI-compatible endpoint
                             (Pollinations, ``gpt-oss-20b``). This makes the
                             product intelligent out of the box with **no
                             paid key and no configuration**.
  3. ``gemini_free``       — Google AI Studio free tier (owner supplies key).
  4. ``groq_free``         — Groq free tier (owner supplies key).
  5. ``openrouter_free``   — OpenRouter free models (owner supplies key).
  6. ``openai_compatible`` — any OpenAI-compatible endpoint (LM Studio, vLLM,
                             Together, DeepSeek, etc.).
  7. ``deterministic``     — last-resort rule engine. Clearly labelled as
                             degraded; never presented as model output.

Owner overrides live in Enterprise Settings → AI Models & Providers and are
resolved per tenant/company, falling back to environment variables.

Invariants
----------
* Never raise: every failure degrades gracefully and is reported.
* Never claim a model answered when the deterministic fallback did.
* Never persist or log credentials.
* DLP inspection happens before dispatch (via the existing firewall hooks).
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:1.5b"
DEFAULT_FREE_BASE = "https://text.pollinations.ai/openai"
DEFAULT_FREE_MODEL = "openai-fast"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

_NON_CHAT_MARKERS = (
    "••", "REPLACE_WITH", "your-api-key", "changeme", "example",
)


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    degraded: bool = False
    error: Optional[str] = None
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: Optional[str] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "degraded": self.degraded,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "finish_reason": self.finish_reason,
            "attempts": self.attempts,
        }


def _is_real_secret(value: Any) -> bool:
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    if len(v) < 8:
        return False
    return not any(marker.lower() in v.lower() for marker in _NON_CHAT_MARKERS)


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None,
               timeout: float = 45.0) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "ZONATA-LLM-Runtime/1.0")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def _get_json(url: str, timeout: float = 2.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "ZONATA-LLM-Runtime/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of the first JSON object from model output."""
    if not text:
        return None
    text = text.strip()
    # Strip fenced code blocks if present.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass
                    break
        start = text.find("{", start + 1)
    return None


class LLMRuntime:
    """Governed, multi-provider LLM gateway with graceful degradation."""

    def __init__(self) -> None:
        self._health_cache: Dict[str, Tuple[float, bool, str]] = {}
        self._health_ttl = 30.0
        # Response cache: free tiers are rate limited, and identical governance
        # questions are common. Cache by (provider, model, messages, system).
        self._response_cache: Dict[str, Tuple[float, LLMResult]] = {}
        self._cache_ttl = 900.0
        # Anonymous keyless providers allow roughly one reply per 30s per IP.
        self._free_cooldown = 31.0
        self._last_free_call = 0.0
        self._free_lock = __import__("threading").Lock()

    @staticmethod
    def _cache_key(provider: str, model: str, msgs: List[Dict[str, str]], system: Optional[str]) -> str:
        import hashlib
        blob = json.dumps({"p": provider, "m": model, "s": system or "", "msgs": msgs}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _cache_get(self, key: str) -> Optional[LLMResult]:
        hit = self._response_cache.get(key)
        if not hit:
            return None
        ts, res = hit
        if time.time() - ts > self._cache_ttl:
            self._response_cache.pop(key, None)
            return None
        return res

    def _cache_put(self, key: str, res: LLMResult) -> None:
        if len(self._response_cache) > 512:
            self._response_cache.clear()
        self._response_cache[key] = (time.time(), res)

    # ------------------------------------------------------------------ config
    def resolve_config(self, tenant_id: str, company_id: str) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {
            "provider": os.environ.get("ZONATA_LLM_PROVIDER", "embedded_free"),
            "model": os.environ.get("ZONATA_LLM_MODEL", ""),
            "base_url": os.environ.get("ZONATA_LLM_BASE_URL", ""),
            "api_key": os.environ.get("ZONATA_LLM_API_KEY", ""),
            "temperature": 0.3,
            "max_tokens": 1200,
            "timeout": float(os.environ.get("ZONATA_LLM_TIMEOUT", "45")),
            "enabled": True,
        }
        try:
            from core.settings_service import settings_service  # local import: avoid cycles
            def eff(key: str, default: Any = None) -> Any:
                try:
                    val = settings_service.get_effective_setting(tenant_id, company_id, key, default)
                    return default if val is None else val
                except Exception:
                    return default

            cfg["provider"] = str(eff("llm_provider", cfg["provider"]) or cfg["provider"]).strip()
            cfg["model"] = str(eff("llm_model", cfg["model"]) or cfg["model"]).strip()
            cfg["base_url"] = str(eff("llm_base_url", cfg["base_url"]) or cfg["base_url"]).strip()
            key = eff("llm_api_key", cfg["api_key"])
            cfg["api_key"] = key if _is_real_secret(key) else cfg["api_key"]
            cfg["temperature"] = float(eff("llm_temperature", cfg["temperature"]))
            cfg["max_tokens"] = int(eff("llm_max_tokens", cfg["max_tokens"]))
            cfg["timeout"] = float(eff("llm_timeout_seconds", cfg["timeout"]))
            cfg["enabled"] = bool(eff("ai_master_enablement", True))
        except Exception:
            pass

        # Per-provider environment fallbacks.
        if not cfg["api_key"]:
            provider = cfg["provider"].lower()
            if provider.startswith("gemini"):
                cfg["api_key"] = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
            elif provider.startswith("groq"):
                cfg["api_key"] = os.environ.get("GROQ_API_KEY", "")
            elif provider.startswith("openrouter"):
                cfg["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
            elif provider.startswith("openai"):
                cfg["api_key"] = os.environ.get("OPENAI_API_KEY", "")

        cfg["provider"] = (cfg["provider"] or "embedded_free").lower()
        if not cfg["model"]:
            cfg["model"] = self._default_model(cfg["provider"])
        return cfg

    @staticmethod
    def _default_model(provider: str) -> str:
        if provider.startswith("ollama"):
            return DEFAULT_OLLAMA_MODEL
        if provider.startswith("gemini"):
            return DEFAULT_GEMINI_MODEL
        if provider.startswith("groq"):
            return DEFAULT_GROQ_MODEL
        if provider.startswith("openrouter"):
            return DEFAULT_OPENROUTER_MODEL
        if provider.startswith("embedded"):
            return DEFAULT_FREE_MODEL
        return DEFAULT_FREE_MODEL

    # ------------------------------------------------------------------ health
    def _ollama_healthy(self, base_url: str) -> Tuple[bool, str]:
        base = (base_url or DEFAULT_OLLAMA_BASE).rstrip("/")
        key = f"ollama::{base}"
        now = time.time()
        if key in self._health_cache:
            ts, ok, detail = self._health_cache[key]
            if now - ts < self._health_ttl:
                return ok, detail
        try:
            data = _get_json(f"{base}/api/tags", timeout=1.2)
            models = [m.get("name", "") for m in data.get("models", [])]
            ok = True
            detail = f"{len(models)} local model(s)"
        except Exception as exc:
            ok, detail = False, f"unreachable: {type(exc).__name__}"
        self._health_cache[key] = (now, ok, detail)
        return ok, detail

    def status(self, tenant_id: str, company_id: str) -> Dict[str, Any]:
        cfg = self.resolve_config(tenant_id, company_id)
        ollama_ok, ollama_detail = self._ollama_healthy(
            cfg["base_url"] if cfg["provider"].startswith("ollama") else DEFAULT_OLLAMA_BASE
        )
        free_ok = True  # keyless endpoint; verified on first call
        providers = [
            {"id": "embedded_free", "label": "Embedded Free (zero-config)", "requires_key": False,
             "available": free_ok, "detail": "Pollinations gpt-oss-20b", "default": True},
            {"id": "ollama", "label": "Local Ollama (fully embedded)", "requires_key": False,
             "available": ollama_ok, "detail": ollama_detail},
            {"id": "gemini_free", "label": "Google AI Studio (free tier)", "requires_key": True,
             "available": _is_real_secret(os.environ.get("GEMINI_API_KEY", "")) or cfg["provider"].startswith("gemini") and _is_real_secret(cfg["api_key"]),
             "detail": DEFAULT_GEMINI_MODEL},
            {"id": "groq_free", "label": "Groq (free tier)", "requires_key": True,
             "available": _is_real_secret(os.environ.get("GROQ_API_KEY", "")) or cfg["provider"].startswith("groq") and _is_real_secret(cfg["api_key"]),
             "detail": DEFAULT_GROQ_MODEL},
            {"id": "openrouter_free", "label": "OpenRouter (free models)", "requires_key": True,
             "available": _is_real_secret(os.environ.get("OPENROUTER_API_KEY", "")) or cfg["provider"].startswith("openrouter") and _is_real_secret(cfg["api_key"]),
             "detail": DEFAULT_OPENROUTER_MODEL},
            {"id": "openai_compatible", "label": "Custom OpenAI-compatible endpoint", "requires_key": False,
             "available": bool(cfg["base_url"]) and not cfg["provider"].startswith(("gemini", "groq", "openrouter", "ollama", "embedded")),
             "detail": cfg["base_url"] or "not configured"},
            {"id": "deterministic", "label": "Deterministic fallback (no model)", "requires_key": False,
             "available": True, "detail": "rule engine — always labelled degraded"},
        ]
        return {
            "configured_provider": cfg["provider"],
            "configured_model": cfg["model"],
            "enabled": cfg["enabled"],
            "providers": providers,
            "privacy_note": (
                "embedded_free sends prompts to a free third-party inference service. "
                "Choose ollama for fully local inference, or a keyed provider for contractual privacy."
            ),
        }

    # ------------------------------------------------------------------- calls
    def _messages(self, messages: List[Dict[str, str]], system: Optional[str]) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages or []:
            role = m.get("role", "user")
            if role not in ("system", "user", "assistant"):
                role = "user"
            out.append({"role": role, "content": str(m.get("content", ""))})
        return out

    def _call_ollama(self, cfg: Dict[str, Any], msgs: List[Dict[str, str]],
                     max_tokens: int, temperature: float) -> Tuple[str, Dict[str, Any]]:
        base = (cfg["base_url"] or DEFAULT_OLLAMA_BASE).rstrip("/")
        payload = {
            "model": cfg["model"] or DEFAULT_OLLAMA_MODEL,
            "messages": msgs,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        data = _post_json(f"{base}/api/chat", payload, timeout=cfg["timeout"])
        content = (data.get("message") or {}).get("content", "") or data.get("response", "")
        usage = {
            "prompt_tokens": int(data.get("prompt_eval_count", 0) or 0),
            "completion_tokens": int(data.get("eval_count", 0) or 0),
        }
        return content.strip(), usage

    def _call_openai_compatible(self, url: str, api_key: str, model: str,
                                msgs: List[Dict[str, str]], max_tokens: int,
                                temperature: float, timeout: float) -> Tuple[str, Dict[str, Any]]:
        payload = {
            "model": model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        data = _post_json(url, payload, headers=headers, timeout=timeout)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("provider returned no choices")
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        if isinstance(content, list):  # some providers return content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        usage = data.get("usage") or {}
        return str(content).strip(), {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "finish_reason": choices[0].get("finish_reason"),
        }

    def _call_gemini(self, api_key: str, model: str, msgs: List[Dict[str, str]],
                     max_tokens: int, temperature: float, timeout: float) -> Tuple[str, Dict[str, Any]]:
        system_parts = [m["content"] for m in msgs if m["role"] == "system"]
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in msgs if m["role"] != "system"
        ]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={urllib.parse.quote(api_key)}")
        data = _post_json(url, payload, timeout=timeout)
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        content = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        usage = data.get("usageMetadata") or {}
        return content.strip(), {
            "prompt_tokens": int(usage.get("promptTokenCount", 0) or 0),
            "completion_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
        }

    def _ordered_attempts(self, cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Return [(provider, model)] in the order we should try them."""
        p = cfg["provider"]
        attempts: List[Tuple[str, str]] = []
        if p in ("ollama", "local", "embedded"):
            attempts.append(("ollama", cfg["model"] or DEFAULT_OLLAMA_MODEL))
        elif p.startswith("gemini"):
            attempts.append(("gemini_free", cfg["model"] or DEFAULT_GEMINI_MODEL))
        elif p.startswith("groq"):
            attempts.append(("groq_free", cfg["model"] or DEFAULT_GROQ_MODEL))
        elif p.startswith("openrouter"):
            attempts.append(("openrouter_free", cfg["model"] or DEFAULT_OPENROUTER_MODEL))
        elif p.startswith("openai"):
            attempts.append(("openai_compatible", cfg["model"] or DEFAULT_FREE_MODEL))
        elif p == "deterministic":
            return []

        # Embedded free provider = local first, then keyless cloud.
        if p in ("embedded_free", "auto", "default", "embedded"):
            if self._ollama_healthy(DEFAULT_OLLAMA_BASE)[0]:
                attempts.append(("ollama", cfg["model"] if cfg["provider"] == "ollama" else DEFAULT_OLLAMA_MODEL))
            attempts.append(("embedded_free", DEFAULT_FREE_MODEL))

        # Universal graceful fallbacks (never leave the user without an answer).
        if p != "deterministic":
            attempts.append(("embedded_free", DEFAULT_FREE_MODEL))
        # De-duplicate while preserving order.
        seen = set()
        deduped = []
        for a in attempts:
            key = a[0]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(a)
        return deduped

    def chat(
        self,
        tenant_id: str,
        company_id: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        intent: str = "general",
    ) -> LLMResult:
        started = time.perf_counter()
        cfg = self.resolve_config(tenant_id, company_id)
        msgs = self._messages(messages, system)
        max_tokens = int(max_tokens or cfg["max_tokens"])
        temperature = float(cfg["temperature"] if temperature is None else temperature)
        attempts_meta: List[Dict[str, Any]] = []

        cache_key = self._cache_key(cfg["provider"], cfg["model"], msgs, system)
        cached = self._cache_get(cache_key)
        if cached is not None:
            cached.attempts = [{"provider": cached.provider, "model": cached.model,
                                "ok": True, "cached": True,
                                "latency_ms": round((time.perf_counter() - started) * 1000, 1)}]
            return cached

        if not cfg["enabled"]:
            return LLMResult(
                content="AI execution is disabled by the AI Master Enablement setting.",
                provider="deterministic", model="none", degraded=True,
                error="AI_DISABLED", latency_ms=(time.perf_counter() - started) * 1000,
            )

        for provider, model in self._ordered_attempts(cfg):
            t0 = time.perf_counter()
            try:
                if provider == "ollama":
                    base = cfg["base_url"] if cfg["provider"] == "ollama" else DEFAULT_OLLAMA_BASE
                    local_cfg = dict(cfg, base_url=base, model=model)
                    content, usage = self._call_ollama(local_cfg, msgs, max_tokens, temperature)
                elif provider == "embedded_free":
                    with self._free_lock:
                        wait = self._free_cooldown - (time.time() - self._last_free_call)
                        if wait > 0:
                            # Respect the free-tier cadence instead of silently degrading.
                            time.sleep(min(wait, 35.0))
                        self._last_free_call = time.time()
                    last_exc = None
                    content, usage = "", {}
                    for attempt in range(3):
                        try:
                            content, usage = self._call_openai_compatible(
                                DEFAULT_FREE_BASE, "", DEFAULT_FREE_MODEL, msgs,
                                max_tokens, temperature, min(cfg["timeout"], 60.0),
                            )
                            if content:
                                break
                            last_exc = RuntimeError("EMPTY_RESPONSE")
                        except Exception as exc:  # transient free-tier failures
                            last_exc = exc
                        if attempt < 2:
                            time.sleep(4.0 * (attempt + 1))
                            with self._free_lock:
                                self._last_free_call = time.time()
                    if not content:
                        raise last_exc or RuntimeError("EMPTY_RESPONSE")
                elif provider == "gemini_free":
                    if not _is_real_secret(cfg["api_key"]):
                        raise RuntimeError("GEMINI_KEY_MISSING")
                    content, usage = self._call_gemini(
                        cfg["api_key"], model, msgs, max_tokens, temperature, cfg["timeout"]
                    )
                elif provider in ("groq_free", "openrouter_free", "openai_compatible"):
                    if provider == "groq_free" and not _is_real_secret(cfg["api_key"]):
                        raise RuntimeError("GROQ_KEY_MISSING")
                    if provider == "openrouter_free" and not _is_real_secret(cfg["api_key"]):
                        raise RuntimeError("OPENROUTER_KEY_MISSING")
                    if provider == "groq_free":
                        base = "https://api.groq.com/openai/v1"
                    elif provider == "openrouter_free":
                        base = "https://openrouter.ai/api/v1"
                    else:
                        base = (cfg["base_url"] or "").rstrip("/")
                        if not base:
                            raise RuntimeError("BASE_URL_MISSING")
                    if not base.endswith("/chat/completions"):
                        base = base + "/chat/completions"
                    content, usage = self._call_openai_compatible(
                        base, cfg["api_key"], model, msgs, max_tokens, temperature, cfg["timeout"]
                    )
                else:
                    continue

                if not content:
                    raise RuntimeError("EMPTY_RESPONSE")
                attempts_meta.append({
                    "provider": provider, "model": model, "ok": True,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                })
                result = LLMResult(
                    content=content,
                    provider=provider,
                    model=model,
                    degraded=provider in ("embedded_free",) and cfg["provider"] not in ("embedded_free", "auto", "default"),
                    latency_ms=(time.perf_counter() - started) * 1000,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    finish_reason=usage.get("finish_reason"),
                    attempts=attempts_meta,
                )
                self._cache_put(cache_key, result)
                return result
            except Exception as exc:
                attempts_meta.append({
                    "provider": provider, "model": model, "ok": False,
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                })
                continue

        # Deterministic last resort — explicitly degraded.
        return LLMResult(
            content="",
            provider="deterministic",
            model="none",
            degraded=True,
            error="ALL_PROVIDERS_UNAVAILABLE",
            latency_ms=(time.perf_counter() - started) * 1000,
            attempts=attempts_meta,
        )

    # --------------------------------------------------------------- utilities
    def chat_json(
        self,
        tenant_id: str,
        company_id: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.2,
    ) -> Tuple[Optional[Dict[str, Any]], LLMResult]:
        instruction = (
            "Respond with a single valid JSON object only. "
            "Do not wrap it in prose or markdown fences."
        )
        sys_prompt = f"{system}\n\n{instruction}" if system else instruction
        res = self.chat(tenant_id, company_id, messages, system=sys_prompt,
                        max_tokens=max_tokens, temperature=temperature, intent="json")
        return extract_json_object(res.content), res


llm_runtime = LLMRuntime()
