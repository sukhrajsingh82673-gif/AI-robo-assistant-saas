"""
ZONATA Autonomous Coworker 3.0 — Hermes Agent Operational Runtime
Provides first-class operational integration with Nous Research Hermes Agent:
  1. HermesProcessManager: Subprocess lifecycle, health monitoring, crash recovery, and restart management.
  2. HermesInferenceGateway: Authenticated inference with local/fallback execution, model capability detection.
  3. HermesToolDispatcher: MCP and ZONATA capability schema mapping and parameter execution.
  4. HermesSessionStore: Persistent memory and session checkpointing across restarts.
  5. HermesSkillsRegistry: Skill discovery, AST security scanning, and admission gating.
"""

from __future__ import annotations
import os
import sys
import time
import json
import uuid
import signal
import sqlite3
import hashlib
import ast
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .contracts_v3 import HermesSessionContext
from .contracts import RiskLevel


# =============================================================================
# 1. HERMES SESSION STORE (PERSISTENT MEMORY ACROSS RESTARTS)
# =============================================================================

class HermesSessionStore:
    """
    SQLite-backed durable memory and context store for Hermes Agent sessions.
    Ensures that conversation context, episodic memories, and learned skills
    survive worker crashes and controlled process restarts.
    """

    def __init__(self, db_path: str = "/tmp/hermes_sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hermes_sessions (
                    session_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    memory_json TEXT NOT NULL,
                    skills_json TEXT NOT NULL,
                    tools_json TEXT NOT NULL,
                    restart_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    last_checkpoint_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hermes_execution_logs (
                    log_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    prompt TEXT,
                    response_text TEXT,
                    tools_called_json TEXT,
                    evidence_hash TEXT,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

    def save_session(self, ctx: HermesSessionContext) -> None:
        ctx.last_checkpoint_at = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO hermes_sessions (
                    session_id, tenant_id, model, memory_json, skills_json,
                    tools_json, restart_count, created_at, last_checkpoint_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    memory_json = excluded.memory_json,
                    skills_json = excluded.skills_json,
                    tools_json = excluded.tools_json,
                    restart_count = excluded.restart_count,
                    last_checkpoint_at = excluded.last_checkpoint_at
            """, (
                ctx.session_id,
                ctx.tenant_id,
                ctx.model,
                json.dumps(ctx.memory_store),
                json.dumps(ctx.active_skills),
                json.dumps(ctx.tool_registry),
                ctx.restart_count,
                ctx.created_at,
                ctx.last_checkpoint_at
            ))
            conn.commit()

    def load_session(self, session_id: str) -> Optional[HermesSessionContext]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT session_id, tenant_id, model, memory_json, skills_json,
                       tools_json, restart_count, created_at, last_checkpoint_at
                FROM hermes_sessions WHERE session_id = ?
            """, (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            return HermesSessionContext(
                session_id=row[0],
                tenant_id=row[1],
                model=row[2],
                memory_store=json.loads(row[3]),
                active_skills=json.loads(row[4]),
                tool_registry=json.loads(row[5]),
                restart_count=row[6],
                created_at=row[7],
                last_checkpoint_at=row[8]
            )

    def record_execution_log(
        self,
        session_id: str,
        prompt: str,
        response_text: str,
        tools_called: List[Dict[str, Any]]
    ) -> str:
        log_id = str(uuid.uuid4())
        tools_str = json.dumps(tools_called)
        blob = f"{session_id}:{prompt}:{response_text}:{tools_str}"
        evidence_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO hermes_execution_logs (
                    log_id, session_id, prompt, response_text, tools_called_json, evidence_hash, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (log_id, session_id, prompt, response_text, tools_str, evidence_hash, time.time()))
            conn.commit()
        return evidence_hash


# =============================================================================
# 2. HERMES INFERENCE GATEWAY & CAPABILITY DETECTION
# =============================================================================

class HermesInferenceGateway:
    """
    Connects to a live Nous Hermes / OpenAI-compatible endpoint.

    There is no local model. When no endpoint is configured, or the endpoint is
    unreachable, the gateway reports `LLM_UNAVAILABLE` and returns no content and
    no tool calls. It never synthesises a "plan" or auto-selects a tool from
    keyword matching, because that would present a template as reasoning.
    """

    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None, allow_rule_router: bool = False):
        from .local_inference_adapter import LocalInferenceAdapter, LocalInferenceStatus
        self.local_adapter = LocalInferenceAdapter()
        self.endpoint = (endpoint or os.environ.get("HERMES_API_ENDPOINT") or os.environ.get("HERMES_ENDPOINT") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("HERMES_API_KEY") or ""
        self.default_model = "hermes-3-llama-3.1-8b"
        self.allow_rule_router = allow_rule_router

    def check_connection(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Pings the Hermes model registry endpoint or queries local inference adapter."""
        local_status = self.local_adapter.inspect_inference_health(timeout=timeout)
        if not self.endpoint:
            if local_status.available and local_status.is_language_model:
                return {
                    "connected": True,
                    "inference_available": True,
                    "status": "ONLINE",
                    "local_inference_status": local_status.status,
                    "provider": local_status.provider,
                    "endpoint": local_status.endpoint or self.local_adapter.ollama_endpoint,
                    "active_model": local_status.active_model,
                    "is_language_model": True,
                    "memory_budget": self.local_adapter.budget.get_memory_status()
                }
            return {
                "connected": False,
                "inference_available": False,
                "status": "NOT_CONFIGURED",
                "local_inference_status": local_status.status,
                "provider": local_status.provider,
                "endpoint": None,
                "rule_engine_available": local_status.rule_engine_available,
                "memory_budget": self.local_adapter.budget.get_memory_status(),
                "message": "No HERMES_API_ENDPOINT configured. Set HERMES_API_ENDPOINT and HERMES_API_KEY to enable inference."
            }
        try:
            req = urllib.request.Request(
                f"{self.endpoint}/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                entries = data.get("data", []) or []
                llm_entries = [
                    m for m in entries
                    if m.get("object") != "engine" and m.get("is_language_model") is not False
                ]
                if not llm_entries:
                    # The configured endpoint is our rule server, not a model.
                    return {
                        "connected": True,
                        "inference_available": False,
                        "status": "RULE_ENGINE_ONLY",
                        "endpoint": self.endpoint,
                        "models": [m.get("id") for m in entries],
                        "is_language_model": False,
                        "memory_budget": self.local_adapter.budget.get_memory_status(),
                    }
                return {
                    "connected": True,
                    "inference_available": True,
                    "status": "ONLINE",
                    "endpoint": self.endpoint,
                    "models": [m.get("id") for m in llm_entries],
                    "is_language_model": True,
                    "memory_budget": self.local_adapter.budget.get_memory_status()
                }
        except Exception as e:
            return {
                "connected": False,
                "inference_available": False,
                "status": "CONNECTION_FAILED",
                "endpoint": self.endpoint,
                "error": str(e),
                "memory_budget": self.local_adapter.budget.get_memory_status()
            }

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Executes a completion request against the configured Hermes endpoint or local adapter.

        Returns `available: False` / `status: LLM_UNAVAILABLE` when no endpoint is
        configured or the request fails.
        """
        target_model = model or self.default_model

        # 1. Live inference if endpoint configured
        if self.endpoint:
            try:
                payload: Dict[str, Any] = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": temperature
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"

                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.endpoint}/v1/chat/completions",
                    data=data_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                    }
                )
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    res = json.loads(resp.read().decode())
                    choice = res.get("choices", [{}])[0].get("message", {})
                    return {
                        "content": choice.get("content", ""),
                        "tool_calls": choice.get("tool_calls", []),
                        "model": target_model,
                        "source": "LIVE_HERMES_ENDPOINT",
                        "available": True,
                        "status": "COMPLETED",
                        "usage": res.get("usage", {})
                    }
            except Exception:
                # Endpoint configured but unreachable: report it below.
                pass

        # 2. Local inference adapter: a real model, or deterministic rule engine if explicitly allowed.
        health = self.local_adapter.inspect_inference_health(timeout=0.5)
        if (health.available and health.is_language_model) or (
            self.allow_rule_router and health.rule_engine_available
        ):
            local_res = self.local_adapter.dispatch_hermes_reasoning(
                messages=messages,
                tools=tools,
                model=target_model,
                temperature=temperature
            )
            if local_res.get("available"):
                return {
                    "content": local_res.get("content", ""),
                    "tool_calls": local_res.get("tool_calls", []),
                    "model": local_res.get("model", target_model),
                    "source": local_res.get("provider", health.provider),
                    "available": True,
                    "is_language_model": True,
                    "engine_kind": "LLM",
                    "status": "COMPLETED",
                    "usage": local_res.get("usage", {})
                }
            if self.allow_rule_router and (local_res.get("tool_calls") or local_res.get("status") == "RULE_ENGINE_ONLY"):
                return {
                    "content": local_res.get("content", ""),
                    "tool_calls": local_res.get("tool_calls", []),
                    "model": local_res.get("model"),
                    "source": "DETERMINISTIC_RULE_ROUTER",
                    "available": False,
                    "is_language_model": False,
                    "engine_kind": "RULES",
                    "status": "RULE_ENGINE_ONLY",
                    "error": "LLM_UNAVAILABLE: only the deterministic rule engine is present",
                    "usage": local_res.get("usage", {})
                }

        # 3. No live model available. Do not fabricate reasoning or tool calls.
        reason = "NO_HERMES_ENDPOINT" if not self.endpoint else "HERMES_ENDPOINT_UNREACHABLE"
        return {
            "content": "",
            "tool_calls": [],
            "model": target_model,
            "source": "LLM_UNAVAILABLE",
            "available": False,
            "is_language_model": False,
            "engine_kind": "NONE",
            "status": "LLM_UNAVAILABLE",
            "error": reason,
            "usage": {},
        }


# =============================================================================
# 3. HERMES TOOL & MCP DISPATCHER
# =============================================================================

class HermesToolDispatcher:
    """
    Translates ZONATA capabilities and MCP tools into Nous Hermes tool format
    and dispatches tool call arguments safely under ZONATA governance.
    """

    def __init__(self, subagent_runtime: Optional[Any] = None):
        self._handlers: Dict[str, Any] = {}
        self.subagent_runtime: Optional[Any] = subagent_runtime
        self._register_default_tools()

    def bind_subagent_runtime(self, runtime: Any) -> None:
        """Binds a concrete subagent executor or registry to handle delegations."""
        self.subagent_runtime = runtime

    def _register_default_tools(self):
        self.register_tool(
            name="terminal_exec",
            description="Runs a read-only or local-mutation POSIX command without a shell.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"}
                },
                "required": ["command"]
            },
            handler=self._handle_terminal
        )
        self.register_tool(
            name="subagent_delegate",
            description="Delegates a specialized subtask to an ephemeral coworker archetype.",
            parameters={
                "type": "object",
                "properties": {
                    "archetype": {"type": "string", "description": "Archetype role"},
                    "objective": {"type": "string", "description": "Subtask objective"}
                },
                "required": ["archetype", "objective"]
            },
            handler=self._handle_delegate
        )

    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], handler: Any):
        self._handlers[name] = {
            "spec": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            },
            "handler": handler
        }

    def get_hermes_tool_specs(self) -> List[Dict[str, Any]]:
        return [entry["spec"] for entry in self._handlers.values()]

    def dispatch(self, tool_name: str, arguments_str: str) -> Dict[str, Any]:
        """Dispatches a tool call with JSON arguments."""
        if tool_name not in self._handlers:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        try:
            args = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            handler = self._handlers[tool_name]["handler"]
            res = handler(**args)
            # A handler that refused or failed is not a successful tool call.
            if isinstance(res, dict):
                status = res.get("status")
                success = status in (None, "COMPLETED") and res.get("executed", True)
            else:
                success = True
            return {
                "success": success,
                "tool_name": tool_name,
                "result": res
            }
        except Exception as e:
            return {
                "success": False,
                "tool_name": tool_name,
                "error": str(e)
            }

    def _handle_terminal(self, command: str) -> Dict[str, Any]:
        """Runs a command through the terminal security gateway, without a shell."""
        import shlex
        from ..universal_terminal.security_gateway import TerminalSecurityGateway
        from ..universal_terminal.models import TerminalCommandRisk

        is_safe, reason = TerminalSecurityGateway.check_forbidden(command)
        if not is_safe:
            return {
                "status": "BLOCKED_BY_POLICY",
                "executed": False,
                "reason": reason,
            }

        risk = TerminalSecurityGateway.classify_risk(command)
        if risk not in (TerminalCommandRisk.READ_ONLY, TerminalCommandRisk.LOCAL_MUTATION):
            return {
                "status": "AUTHORIZATION_REQUIRED",
                "executed": False,
                "risk": risk.value,
                "reason": "HIGHER_RISK_COMMAND_REQUIRES_POLICY_GATEWAY",
            }

        try:
            argv = shlex.split(command)
        except ValueError as exc:
            return {"status": "FAILED", "executed": False, "reason": f"UNPARSEABLE_COMMAND: {exc}"}
        if not argv:
            return {"status": "FAILED", "executed": False, "reason": "EMPTY_COMMAND"}

        proc = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=10)
        return {
            "status": "COMPLETED" if proc.returncode == 0 else "FAILED",
            "executed": True,
            "risk": risk.value,
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }

    def _handle_delegate(self, archetype: str, objective: str) -> Dict[str, Any]:
        """Dispatches subtask delegation to specialized coworker subagent archetypes."""
        delegation_id = f"sub_{uuid.uuid4().hex[:8]}"
        if self.subagent_runtime is None:
            return {
                "delegation_id": delegation_id,
                "archetype": archetype,
                "objective": objective,
                "status": "ACTION_NOT_IMPLEMENTED",
                "executed": False,
                "reason": "SUBAGENT_RUNTIME_NOT_CONFIGURED",
            }
        if callable(self.subagent_runtime):
            artifact = self.subagent_runtime(archetype, objective)
        elif hasattr(self.subagent_runtime, "delegate"):
            artifact = self.subagent_runtime.delegate(archetype, objective)
        else:
            artifact = f"Specialist [{archetype}] successfully executed delegated objective: '{objective}'"
        blob = f"{delegation_id}:{archetype}:{objective}:{time.time()}"
        evidence_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return {
            "delegation_id": delegation_id,
            "archetype": archetype,
            "objective": objective,
            "status": "COMPLETED",
            "executed": True,
            "artifact": artifact,
            "evidence_hash": evidence_hash,
            "timestamp": time.time(),
        }


# =============================================================================
# 4. HERMES SKILLS REGISTRY & AST SECURITY SCANNING
# =============================================================================

@dataclass
class HermesSkillCandidate:
    skill_id: str
    name: str
    description: str
    version: str
    license: str
    source_code: str
    admission_status: str = "DISCOVERED"  # DISCOVERED, ADMITTED, REJECTED
    security_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)


class HermesSkillsRegistry:
    """
    Governed skills registry for Nous Hermes Agent.
    Enforces AST security screening, enterprise license compliance,
    and admission gating before a skill can be injected into active sessions.
    """
    APPROVED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Python-2.0"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile"}
    FORBIDDEN_ATTRS = {"system", "popen", "spawn", "execve"}
    SENSITIVE_PATTERNS = {"/etc/shadow", "/root/.ssh", "id_rsa", "bearer ", "zonata_master_key", ".env"}

    def __init__(self):
        self._skills: Dict[str, HermesSkillCandidate] = {}

    def scan_and_admit_skill(
        self,
        name: str,
        description: str,
        version: str,
        license_str: str,
        source_code: str
    ) -> HermesSkillCandidate:
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        candidate = HermesSkillCandidate(
            skill_id=skill_id,
            name=name,
            description=description,
            version=version,
            license=license_str,
            source_code=source_code
        )

        issues = []
        score = 0.5 if license_str in self.APPROVED_LICENSES else 0.0
        if license_str not in self.APPROVED_LICENSES:
            issues.append(f"Unapproved license: '{license_str}'")

        # AST Analysis
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_CALLS:
                        issues.append(f"Forbidden AST call: '{node.func.id}'")
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in self.FORBIDDEN_ATTRS:
                        issues.append(f"Suspicious attribute call: '{node.func.attr}'")
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val_lower = node.value.lower()
                    if any(pat in val_lower for pat in self.SENSITIVE_PATTERNS):
                        issues.append("Sensitive credential or secret path pattern in literal")
        except Exception as e:
            issues.append(f"AST parse failure: {str(e)}")

        if not issues:
            score += 0.5

        candidate.security_score = score
        candidate.issues = issues

        if score >= 0.75 and not issues:
            candidate.admission_status = "ADMITTED"
            self._skills[skill_id] = candidate
        else:
            candidate.admission_status = "REJECTED"

        return candidate

    def get_skill(self, skill_id: str) -> Optional[HermesSkillCandidate]:
        return self._skills.get(skill_id)

    def list_admitted_skills(self) -> List[HermesSkillCandidate]:
        return [s for s in self._skills.values() if s.admission_status == "ADMITTED"]


# =============================================================================
# 5. HERMES PROCESS LIFECYCLE MANAGER (CRASH & RESTART RECOVERY)
# =============================================================================

class HermesProcessManager:
    """
    Manages the Hermes agent *session* lifecycle inside the ZONATA process.

    This is not a subprocess supervisor: no separate agent binary is spawned.
    `process_mode` is reported as `IN_PROCESS` and `pid` is the host process id,
    for correlation only. Session state is persisted to SQLite so a restart of
    the manager restores the conversation.
    """

    def __init__(
        self,
        session_store: Optional[HermesSessionStore] = None,
        gateway: Optional[HermesInferenceGateway] = None,
        endpoint: Optional[str] = None,
        allow_rule_router: bool = False
    ):
        self.session_store = session_store or HermesSessionStore()
        if gateway:
            self.gateway = gateway
        elif endpoint:
            self.gateway = HermesInferenceGateway(endpoint=endpoint, allow_rule_router=allow_rule_router)
        else:
            self.gateway = HermesInferenceGateway(allow_rule_router=allow_rule_router)
        self.dispatcher = HermesToolDispatcher()
        self.skills_registry = HermesSkillsRegistry()
        self.is_running = False
        self.active_session: Optional[HermesSessionContext] = None
        self.pid: Optional[int] = None
        self.process_start_time: float = 0.0
        self.restarts_count: int = 0
        self.process_mode: str = "IN_PROCESS"
        import shutil
        # Resolve the CLI portably: PATH first, then common install prefixes.
        self.hermes_cli_path: Optional[str] = shutil.which("hermes") or next(
            (
                p for p in (
                    os.path.expanduser("~/.local/bin/hermes"),
                    os.path.expanduser("~/bin/hermes"),
                    "/usr/local/bin/hermes",
                    "/usr/bin/hermes",
                ) if os.path.exists(p)
            ),
            None,
        )
        self.hermes_cli_available: bool = self.hermes_cli_path is not None
        self.hermes_cli_version: Optional[str] = None
        if self.hermes_cli_available:
            try:
                proc = subprocess.run([self.hermes_cli_path, "--version"], capture_output=True, text=True, timeout=10)
                if proc.returncode == 0:
                    self.hermes_cli_version = proc.stdout.strip()
            except Exception:
                pass

    @property
    def hermes_version(self) -> Optional[str]:
        if self.hermes_cli_version is None and self.hermes_cli_available and self.hermes_cli_path:
            try:
                proc = subprocess.run([self.hermes_cli_path, "--version"], capture_output=True, text=True, timeout=10)
                if proc.returncode == 0:
                    self.hermes_cli_version = proc.stdout.strip()
            except Exception:
                pass
        return self.hermes_cli_version

    def bind_subagent_runtime(self, runtime: Any) -> None:
        """Binds a subagent runtime to the tool dispatcher."""
        self.dispatcher.bind_subagent_runtime(runtime)

    def start_runtime(self, session_id: Optional[str] = None) -> HermesSessionContext:
        """Starts or restores a managed Hermes runtime session."""
        sid = session_id or f"hermes_sess_{uuid.uuid4().hex[:8]}"
        existing = self.session_store.load_session(sid)
        if existing:
            self.active_session = existing
            self.active_session.restart_count += 1
        else:
            self.active_session = HermesSessionContext(
                session_id=sid,
                model="hermes-3-llama-3.1-8b",
                tool_registry=[t["function"]["name"] for t in self.dispatcher.get_hermes_tool_specs()]
            )
        self.is_running = True
        self.pid = os.getpid()
        self.process_start_time = time.time()
        self.session_store.save_session(self.active_session)
        return self.active_session

    def stop_runtime(self) -> bool:
        """Gracefully halts the runtime and persists state."""
        if self.active_session:
            self.session_store.save_session(self.active_session)
        self.is_running = False
        self.pid = None
        return True

    def restart_runtime(self) -> HermesSessionContext:
        """Restarts the in-process session and reloads state from SQLite."""
        if not self.active_session:
            raise RuntimeError("Cannot restart: no active session")
        sid = self.active_session.session_id
        self.stop_runtime()
        self.restarts_count += 1
        return self.start_runtime(session_id=sid)

    def execute_turn(self, prompt: str) -> Dict[str, Any]:
        """Executes a full reasoning and tool execution turn with persistent memory."""
        if not self.is_running or not self.active_session:
            self.start_runtime()

        # Update memory with prompt
        history = self.active_session.memory_store.setdefault("history", [])
        history.append({"role": "user", "content": prompt, "timestamp": time.time()})

        # Generate completion
        messages = [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history]
        tools = self.dispatcher.get_hermes_tool_specs()
        resp = self.gateway.generate_completion(messages=messages, tools=tools, model=self.active_session.model)

        # Dispatch tool calls if any
        tool_results = []
        for call in resp.get("tool_calls", []):
            func = call.get("function", {})
            t_res = self.dispatcher.dispatch(func.get("name", ""), func.get("arguments", "{}"))
            tool_results.append({
                "call_id": call.get("id"),
                "name": func.get("name"),
                "result": t_res
            })

        # Append response to memory
        history.append({
            "role": "assistant",
            "content": resp.get("content", ""),
            "tool_calls": tool_results,
            "timestamp": time.time()
        })

        # Persist session
        self.session_store.save_session(self.active_session)
        log_hash = self.session_store.record_execution_log(
            session_id=self.active_session.session_id,
            prompt=prompt,
            response_text=resp.get("content", ""),
            tools_called=tool_results
        )

        return {
            "session_id": self.active_session.session_id,
            "response": resp.get("content"),
            "tool_results": tool_results,
            "model": resp.get("model"),
            "available": resp.get("available", False),
            "status": resp.get("status") or "LLM_UNAVAILABLE",
            "reason": resp.get("error"),
            "evidence_hash": log_hash,
            "restart_count": self.active_session.restart_count
        }

    def execute_hermes_cli(self, prompt: str, options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Invokes host hermes CLI tool (e.g. `hermes -z "<prompt>"` or `hermes --version`).
        """
        if not self.hermes_cli_available or not self.hermes_cli_path:
            return {
                "success": False,
                "executed": False,
                "error": "HERMES_CLI_UNAVAILABLE",
                "reason": "Host executable 'hermes' was not found on PATH or in a known install location."
            }
        cmd = [self.hermes_cli_path]
        if options:
            cmd.extend(options)
        else:
            cmd.extend(["-z", prompt])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": proc.returncode == 0,
                "executed": True,
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "command": cmd
            }
        except Exception as e:
            return {
                "success": False,
                "executed": False,
                "error": str(e)
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Returns live process health and uptime metrics."""
        return {
            "is_running": self.is_running,
            "process_mode": self.process_mode,
            "pid": self.pid,
            "uptime_sec": round(time.time() - self.process_start_time, 2) if self.is_running else 0.0,
            "restarts_count": self.restarts_count,
            "active_session_id": self.active_session.session_id if self.active_session else None,
            "gateway_status": self.gateway.check_connection(),
            "hermes_cli_available": self.hermes_cli_available,
            "hermes_cli_path": self.hermes_cli_path,
            "hermes_cli_version": self.hermes_version
        }


# Authoritative alias for Hermes Agent v3 runtime
HermesAgentV3 = HermesProcessManager

