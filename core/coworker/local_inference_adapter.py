"""
ZONATA Autonomous Executive Coworker — Local Inference Adapter

Provides hardware-budget-aware inference probing and deterministic tool
routing for the Hermes agent and the ZONATA Coworker.

Two very different things live in this module and must never be confused:

- A **rule engine** (`LocalModelEngine`) that matches keywords and emits
  structured tool calls. It is deterministic, it is useful, and it is not a
  language model. It does not analyse, summarise or verify anything.
- A **language-model endpoint** (a local OpenAI-compatible server, Ollama, or
  the platform `llm_runtime`). Only these count as inference.

`LocalInferenceStatus.available` therefore means "a language model is
reachable". When only the rule engine is present, the status is
`RULE_ENGINE_ONLY`, `available` is False, and `is_language_model` is False.
"""

from __future__ import annotations
import os
import sys
import json
import time
import uuid
import socket
import resource
import threading
import subprocess
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class HardwareBudget:
    """Enforces ARM64 / Container RAM limits to prevent process eviction."""
    max_process_ram_mb: float = 512.0
    total_system_ram_mb: float = 3587.0
    architecture: str = "aarch64"

    def __post_init__(self):
        # Dynamically measure real hardware memory if psutil is available
        if psutil:
            try:
                vm = psutil.virtual_memory()
                self.total_system_ram_mb = round(vm.total / (1024.0 * 1024.0), 1)
            except Exception:
                pass

    @classmethod
    def get_current_ram_mb(cls) -> float:
        """Reads resident memory usage via resource.getrusage."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            return usage.ru_maxrss / (1024.0 * 1024.0)
        return usage.ru_maxrss / 1024.0

    @classmethod
    def get_available_system_ram_mb(cls) -> float:
        """Reads available system memory in MB."""
        if psutil:
            try:
                return round(psutil.virtual_memory().available / (1024.0 * 1024.0), 1)
            except Exception:
                pass
        return 750.0

    def is_constrained(self) -> bool:
        return self.get_current_ram_mb() > self.max_process_ram_mb

    def get_memory_status(self) -> Dict[str, Any]:
        cur = self.get_current_ram_mb()
        avail = self.get_available_system_ram_mb()
        return {
            "architecture": self.architecture,
            "max_process_ram_mb": self.max_process_ram_mb,
            "total_system_ram_mb": self.total_system_ram_mb,
            "available_system_ram_mb": avail,
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
    capabilities: List[str] = field(default_factory=lambda: ["tool_calling"])
    # `available` means "a language model is reachable". A rule engine can route
    # tools but is not inference; it reports is_language_model=False.
    is_language_model: bool = False
    engine_kind: str = "LLM"          # "LLM" or "RULES"
    rule_engine_available: bool = False

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
            "capabilities": self.capabilities,
            "is_language_model": self.is_language_model,
            "engine_kind": self.engine_kind,
            "rule_engine_available": self.rule_engine_available,
        }


# =============================================================================
# 1. LOCAL MODEL & REASONING ENGINE
# =============================================================================

class LocalModelEngine:
    """
    Deterministic keyword router that emits structured tool calls.

    This is **not** a language model. It has no weights, no tokenizer and no
    generation. It matches a handful of keywords to a small set of allowed
    tools, and it returns a factual digest of tool results. Naming it a model
    would be a fabrication, so `IS_LANGUAGE_MODEL` is False and the id says
    `rules`.
    """

    ENGINE_ID = "zonata-rules-v1"
    IS_LANGUAGE_MODEL = False
    # Backwards-compatible attribute name. The value is an engine id, not a model.
    DEFAULT_MODEL = ENGINE_ID

    def __init__(self, model_name: str = ENGINE_ID):
        self.model_name = model_name
        self._execution_history: List[Dict[str, Any]] = []

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        Executes one router turn.
        If tools are registered and the prompt matches a keyword rule, emits structured tool_calls.
        If tool outputs are provided in history, synthesizes final executive conclusion.
        """
        target_model = model or self.model_name
        user_prompt = ""
        has_tool_results = False
        tool_results_data = []

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                user_prompt = content
            elif role in ("tool", "function"):
                has_tool_results = True
                tool_results_data.append(content)
            elif role == "assistant" and m.get("tool_calls"):
                has_tool_results = True
                for tc in m.get("tool_calls", []):
                    if isinstance(tc, dict) and "result" in tc:
                        tool_results_data.append(str(tc["result"]))

        # Case 1: Post-tool turn. Report only what the tools actually returned.
        # There is no model here, so there is no assessment to report.
        if has_tool_results and tool_results_data:
            names = []
            for m in messages:
                for tc in m.get("tool_calls", []) if isinstance(m.get("tool_calls"), list) else []:
                    if isinstance(tc, dict):
                        name = (tc.get("function") or {}).get("name") or tc.get("name")
                        if name:
                            names.append(name)
            summary_content = (
                f"RULE_ENGINE_DIGEST: {len(tool_results_data)} tool result(s) received"
                + (f" ({', '.join(names)})" if names else "")
                + ". No language-model analysis was performed; the raw tool output is "
                  "the authoritative result."
            )
            return {
                "id": f"cmpl_{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": target_model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": summary_content,
                        "tool_calls": []
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(user_prompt.split()) + 50,
                    "completion_tokens": len(summary_content.split()),
                    "total_tokens": len(user_prompt.split()) + len(summary_content.split()) + 50
                }
            }

        # Case 2: Tool calling evaluation
        tool_calls = []
        if tools:
            prompt_lower = user_prompt.lower()
            for tool_spec in tools:
                func = tool_spec.get("function", {})
                name = func.get("name", "")
                params = func.get("parameters", {}).get("properties", {})

                # Check if prompt triggers this tool
                if name == "terminal_exec" and any(k in prompt_lower for k in ["run", "command", "exec", "ls", "git", "scan", "netstat", "ps"]):
                    # Extract suggested command
                    cmd = "ls -la"
                    if "netstat" in prompt_lower or "port" in prompt_lower:
                        cmd = "netstat -tuln"
                    elif "git" in prompt_lower:
                        cmd = "git status"
                    elif "ps" in prompt_lower:
                        cmd = "ps aux"
                    elif "uname" in prompt_lower:
                        cmd = "uname -m"

                    tool_calls.append({
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": "terminal_exec",
                            "arguments": json.dumps({"command": cmd})
                        }
                    })
                    break

                elif name == "subagent_delegate" and any(k in prompt_lower for k in ["delegate", "specialist", "subagent", "assign", "team"]):
                    archetype = "QA_TESTER"
                    if "security" in prompt_lower or "audit" in prompt_lower:
                        archetype = "SECURITY_ANALYST"
                    elif "code" in prompt_lower or "dev" in prompt_lower:
                        archetype = "CODER"
                    elif "architect" in prompt_lower or "design" in prompt_lower:
                        archetype = "ARCHITECT"

                    tool_calls.append({
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": "subagent_delegate",
                            "arguments": json.dumps({"archetype": archetype, "objective": user_prompt})
                        }
                    })
                    break

        if tool_calls:
            assistant_msg = (
                "RULE_ENGINE_ONLY: matched tool schema "
                + tool_calls[0]["function"]["name"]
                + "; no language-model reasoning was performed."
            )
            finish_reason = "tool_calls"
        else:
            # No model is present. Say so, and say what the router did.
            matched = [k for k in ("run", "command", "exec", "ls", "git", "scan",
                                   "netstat", "ps", "delegate", "specialist",
                                   "subagent", "assign", "team")
                       if k in user_prompt.lower()]
            if matched:
                assistant_msg = (
                    "RULE_ENGINE_ONLY: matched keyword(s) "
                    + ", ".join(matched)
                    + " but no tool schema was supplied, so no tool call was emitted. "
                      "No language-model analysis was performed."
                )
            else:
                assistant_msg = (
                    "RULE_ENGINE_ONLY: the deterministic rule engine has no rule for "
                    "this prompt. No language model is available, so no answer was "
                    "generated."
                )
            finish_reason = "stop"

        return {
            "id": f"cmpl_{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": target_model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": assistant_msg,
                    "tool_calls": tool_calls
                },
                "finish_reason": finish_reason
            }],
            "usage": {
                "prompt_tokens": len(user_prompt.split()) + 20,
                "completion_tokens": len(assistant_msg.split()),
                "total_tokens": len(user_prompt.split()) + len(assistant_msg.split()) + 20
            }
        }


# =============================================================================
# 2. LOCAL OPENAI-COMPATIBLE HTTP SERVER
# =============================================================================

class _OpenAIHTTPHandler(BaseHTTPRequestHandler):
    """Handles /v1/chat/completions and /v1/models."""

    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging
        pass

    def do_GET(self):
        if self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "object": "list",
                "data": [{
                    "id": LocalModelEngine.ENGINE_ID,
                    "object": "engine",
                    "is_language_model": LocalModelEngine.IS_LANGUAGE_MODEL,
                    "owned_by": "zonata",
                }],
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif self.path in ("/health", "/api/tags"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "status": "RULE_ENGINE_ONLY",
                "is_language_model": LocalModelEngine.IS_LANGUAGE_MODEL,
                "engine": LocalModelEngine.ENGINE_ID,
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                req_json = json.loads(body.decode("utf-8"))
                engine = getattr(self.server, "engine", LocalModelEngine())
                resp = engine.chat_completion(
                    messages=req_json.get("messages", []),
                    tools=req_json.get("tools"),
                    model=req_json.get("model"),
                    temperature=req_json.get("temperature", 0.2),
                    max_tokens=req_json.get("max_tokens", 1024)
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class LocalOpenAIServer:
    """
    Serves the deterministic rule engine over the OpenAI wire format.

    Useful because any OpenAI client can connect, but it is **not** inference:
    `/v1/models` reports an `engine` with `is_language_model: false`, and
    `/health` reports `RULE_ENGINE_ONLY`.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8088):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.engine = LocalModelEngine()
        self.is_running = False
        self.start_error: Optional[str] = None

    def start(self) -> bool:
        if self.is_running:
            return True
        self.start_error = None
        # Another process (or an earlier run) may already serve this port. If it
        # is our rule server, the endpoint is usable even though we did not bind.
        if self._existing_rule_server():
            self.is_running = True
            return True
        last_exc: Optional[BaseException] = None
        for _attempt in range(5):
            try:
                self.server = HTTPServer((self.host, self.port), _OpenAIHTTPHandler)
                setattr(self.server, "engine", self.engine)
                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.thread.start()
                self.is_running = True
                time.sleep(0.1)
                return True
            except OSError as exc:
                last_exc = exc
                time.sleep(0.2)
        self.start_error = f"{type(last_exc).__name__}: {last_exc}" if last_exc else "UNKNOWN_BIND_FAILURE"
        return False

    def _existing_rule_server(self) -> bool:
        try:
            with urllib.request.urlopen(
                f"http://{self.host}:{self.port}/v1/models", timeout=1.0
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return False
        for entry in data.get("data", []) or []:
            if entry.get("id") == LocalModelEngine.ENGINE_ID and entry.get("is_language_model") is False:
                return True
        return False

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.is_running = False


# Global singleton instance of LocalOpenAIServer
_GLOBAL_LOCAL_SERVER: Optional[LocalOpenAIServer] = None
_SERVER_LOCK = threading.Lock()


def get_or_start_local_server(port: int = 8088) -> LocalOpenAIServer:
    """Returns or boots the global local OpenAI server."""
    global _GLOBAL_LOCAL_SERVER
    with _SERVER_LOCK:
        if _GLOBAL_LOCAL_SERVER is None:
            _GLOBAL_LOCAL_SERVER = LocalOpenAIServer(port=port)
            _GLOBAL_LOCAL_SERVER.start()
        elif not _GLOBAL_LOCAL_SERVER.is_running:
            _GLOBAL_LOCAL_SERVER.start()
        return _GLOBAL_LOCAL_SERVER


# =============================================================================
# 3. LOCAL INFERENCE ADAPTER
# =============================================================================

class LocalInferenceAdapter:
    """
    Hardware-budget-aware inference adapter for the Hermes agent.

    Probe order, first reachable wins:

    1. An OpenAI-compatible server on 127.0.0.1:8088. If it only serves the
       deterministic rule engine, the result is `RULE_ENGINE_ONLY`.
    2. A localhost Ollama daemon on 127.0.0.1:11434 (a real language model).
    3. The platform `llm_runtime`, when configured.
    4. Otherwise `LLM_UNAVAILABLE`, `available=False`, no fabricated output.

    The rule engine is not a fallback for inference. It is reported separately
    via `rule_engine_available`, and any tool calls it produces are labelled
    `RULE_ENGINE_ONLY` rather than `COMPLETED`.
    """

    def __init__(
        self,
        ollama_endpoint: str = "http://127.0.0.1:11434",
        local_server_endpoint: str = "http://127.0.0.1:8088",
        budget: Optional[HardwareBudget] = None,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        enable_rule_engine: Optional[bool] = None,
        enable_embedded_engine: Optional[bool] = None,  # deprecated alias
    ):
        self.ollama_endpoint = os.environ.get("OLLAMA_BASE_URL", ollama_endpoint).rstrip("/")
        self.local_server_endpoint = os.environ.get("LOCAL_OPENAI_ENDPOINT", local_server_endpoint).rstrip("/")
        self.budget = budget or HardwareBudget()
        self.tenant_id = tenant_id
        self.company_id = company_id
        if enable_rule_engine is None:
            if enable_embedded_engine is not None:
                enable_rule_engine = enable_embedded_engine
            else:
                enable_rule_engine = os.environ.get("ZONATA_ENABLE_RULE_ENGINE", "1") not in ("0", "false", "False", "")
        self.enable_rule_engine = enable_rule_engine
        self.enable_embedded_engine = enable_rule_engine  # deprecated alias
        self.engine = LocalModelEngine()

    def inspect_inference_health(self, timeout: float = 1.5) -> LocalInferenceStatus:
        """
        Probe local endpoints (8088 or 11434).
        If offline, probe embedded local engine or report honest unavailable.
        """
        current_ram = self.budget.get_current_ram_mb()
        constrained = current_ram > self.budget.max_process_ram_mb

        # 1. Probe local OpenAI server at 127.0.0.1:8088
        try:
            req = urllib.request.Request(
                f"{self.local_server_endpoint}/v1/models",
                headers={"User-Agent": "ZONATA-Local-Probe"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    entries = data.get("data", []) or []
                    # Our own rule server marks entries with object="engine" /
                    # is_language_model=false. A standard OpenAI-compatible
                    # server (Ollama, vLLM, LM Studio) does neither, so it is
                    # treated as a model endpoint.
                    llm_entries = [
                        m for m in entries
                        if m.get("object") != "engine" and m.get("is_language_model") is not False
                    ]
                    if not llm_entries:
                        # The endpoint answered, but it serves a rule engine, not a model.
                        return LocalInferenceStatus(
                            available=False,
                            endpoint=self.local_server_endpoint,
                            provider="zonata_rule_server",
                            active_model=None,
                            ram_usage_mb=current_ram,
                            hardware_constrained=constrained,
                            status="RULE_ENGINE_ONLY",
                            error=None,
                            is_language_model=False,
                            engine_kind="RULES",
                            rule_engine_available=bool(entries),
                            capabilities=["tool_routing"],
                        )
                    active_model = llm_entries[0].get("id")
                    return LocalInferenceStatus(
                        available=True,
                        endpoint=self.local_server_endpoint,
                        provider="zonata_local_server",
                        active_model=active_model,
                        ram_usage_mb=current_ram,
                        hardware_constrained=constrained,
                        status="ONLINE",
                        error=None,
                        is_language_model=True,
                        engine_kind="LLM",
                        capabilities=["tool_calling", "multi_step_planning"],
                    )
        except Exception:
            pass

        # 2. Probe localhost Ollama at 127.0.0.1:11434
        try:
            req = urllib.request.Request(
                f"{self.ollama_endpoint}/api/tags",
                headers={"User-Agent": "ZONATA-Hermes-Probe"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    if not models:
                        # The daemon is up but has no model pulled. That is not
                        # an available model, and we do not invent a name.
                        raise RuntimeError("OLLAMA_NO_MODELS")
                    active_model = models[0]
                    return LocalInferenceStatus(
                        available=True,
                        endpoint=self.ollama_endpoint,
                        provider="ollama_local",
                        active_model=active_model,
                        ram_usage_mb=current_ram,
                        hardware_constrained=constrained,
                        status="ONLINE",
                        error=None,
                        is_language_model=True,
                        engine_kind="LLM",
                        capabilities=["tool_calling", "multi_step_planning"],
                    )
        except Exception:
            pass

        # 3. The deterministic rule engine. Useful for tool routing, but it is
        #    not inference and must not be reported as an available model.
        if self.enable_rule_engine and not constrained:
            return LocalInferenceStatus(
                available=False,
                endpoint="embedded://rule_engine",
                provider="zonata_rule_engine",
                active_model=None,
                ram_usage_mb=current_ram,
                hardware_constrained=False,
                status="RULE_ENGINE_ONLY",
                error=None,
                is_language_model=False,
                engine_kind="RULES",
                rule_engine_available=True,
                capabilities=["tool_routing"],
            )

        # 4. Cascade to platform llm_runtime if configured
        try:
            from core.llm_runtime import llm_runtime
            rt_status = llm_runtime.status(self.tenant_id, self.company_id)
            if rt_status.get("status") in ("ONLINE", "READY", "HEALTHY") or rt_status.get("configured", False):
                return LocalInferenceStatus(
                    available=True,
                    endpoint=rt_status.get("endpoint"),
                    provider=rt_status.get("provider", "llm_runtime"),
                    active_model=rt_status.get("model"),
                    ram_usage_mb=current_ram,
                    hardware_constrained=constrained,
                    status="RUNTIME_CASCADE_AVAILABLE",
                    error=None,
                    is_language_model=True,
                    engine_kind="LLM",
                    capabilities=["tool_calling", "multi_step_planning"],
                )
        except Exception:
            pass

        # 5. Honest unavailable reporting (zero hallucinations)
        return LocalInferenceStatus(
            available=False,
            endpoint=None,
            provider="none",
            active_model=None,
            ram_usage_mb=current_ram,
            hardware_constrained=constrained,
            status="LLM_UNAVAILABLE",
            error="No local OpenAI server, Ollama, or platform LLM runtime endpoint is available.",
            is_language_model=False,
            engine_kind="NONE",
            rule_engine_available=False,
            capabilities=[],
        )

    detect_status = inspect_inference_health

    def dispatch_hermes_reasoning(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        One reasoning turn.

        - With a reachable language model: returns the endpoint's completion,
          `available=True`, `status=COMPLETED`.
        - With only the rule engine: returns deterministic tool calls, but
          `available=False`, `status=RULE_ENGINE_ONLY`, `is_language_model=False`.
          The content is a factual digest, never an invented assessment.
        - With nothing: returns `LLM_UNAVAILABLE` and no content or tool calls.
        """
        health = self.inspect_inference_health(timeout=1.0)
        formatted_msgs: List[Dict[str, Any]] = []
        if system_prompt:
            formatted_msgs.append({"role": "system", "content": system_prompt})
        formatted_msgs.extend(messages)

        # 1. A real language model.
        if health.available and health.is_language_model:
            endpoint = health.endpoint or self.ollama_endpoint
            payload = {
                "model": model or health.active_model,
                "messages": formatted_msgs,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = tools
            try:
                req = urllib.request.Request(
                    f"{endpoint}/v1/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                choice = res.get("choices", [{}])[0].get("message", {})
                return {
                    "content": choice.get("content", ""),
                    "tool_calls": choice.get("tool_calls", []),
                    "model": res.get("model") or health.active_model,
                    "provider": health.provider,
                    "status": "COMPLETED",
                    "available": True,
                    "is_language_model": True,
                    "engine_kind": "LLM",
                    "ram_usage_mb": health.ram_usage_mb,
                    "hardware_constrained": health.hardware_constrained,
                    "usage": res.get("usage", {}),
                }
            except Exception as exc:
                return {
                    "content": "",
                    "tool_calls": [],
                    "model": health.active_model or "none",
                    "provider": health.provider,
                    "status": "LLM_UNAVAILABLE",
                    "available": False,
                    "is_language_model": False,
                    "engine_kind": "LLM",
                    "error": f"INFERENCE_ENDPOINT_FAILED: {exc}",
                    "ram_usage_mb": health.ram_usage_mb,
                    "hardware_constrained": health.hardware_constrained,
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                }

        # 2. Deterministic rule engine. Tool routing only; no inference claim.
        if health.rule_engine_available or (self.enable_rule_engine and not health.hardware_constrained):
            res = self.engine.chat_completion(
                messages=formatted_msgs,
                tools=tools,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = res.get("choices", [{}])[0].get("message", {})
            return {
                "content": choice.get("content", ""),
                "tool_calls": choice.get("tool_calls", []),
                "model": LocalModelEngine.ENGINE_ID,
                "provider": "zonata_rule_engine",
                "status": "RULE_ENGINE_ONLY",
                "available": False,
                "is_language_model": False,
                "engine_kind": "RULES",
                "rule_engine_available": True,
                "capabilities": ["tool_routing"],
                "ram_usage_mb": health.ram_usage_mb,
                "hardware_constrained": health.hardware_constrained,
                "usage": res.get("usage", {}),
            }

        # 3. Nothing at all.
        return {
            "content": "",
            "tool_calls": [],
            "model": "none",
            "provider": "none",
            "status": "LLM_UNAVAILABLE",
            "available": False,
            "is_language_model": False,
            "engine_kind": "NONE",
            "ram_usage_mb": health.ram_usage_mb,
            "hardware_constrained": health.hardware_constrained,
            "error": health.error,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    generate_completion = dispatch_hermes_reasoning
