"""ZONATA Sovereign Core — Anti-Bypass AST Security Policy (Standing Rule 34).

Enforces Standing Rule 34:
"No framework reaches a model, tool, network or datastore except through ZONATA ports
(LLMGateway, ToolRegistry -> ActionGateway, document, folio and ledger ports).
A framework-native model client, built-in tool or code executor is disabled unless
wrapped. Enforce with an AST lint and a network policy that blocks direct egress
from agent workers."

Scans codebase for:
1. Direct imports of model providers (openai, anthropic, google.generativeai, cohere)
   outside core/ports/llm.
2. Direct raw network sockets or HTTP requests (requests, httpx, aiohttp, urllib.request)
   inside agent workers or framework adapters bypassing ZONATA ports.
3. Direct OS command execution (subprocess, os.system) outside TerminalPort.
"""

from __future__ import annotations
import ast
from dataclasses import dataclass
import os
import sys
from typing import List, Optional, Set


class AntiBypassViolationError(Exception):
    """Raised when an anti-bypass policy violation is detected."""
    pass


@dataclass(frozen=True)
class AntiBypassViolation:
    file_path: str
    line_number: Optional[int]
    violation_type: str
    description: str
    offending_symbol: str


BANNED_DIRECT_MODEL_IMPORTS: Set[str] = {
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "mistralai",
    "cohere",
}

ALLOWLISTED_MODEL_IMPORT_PATHS: Set[str] = {
    "core/ports/llm.py",
    "core/ports/llm/",
    "core/llm_gateway.py",
    "tests/test_ports_contracts.py",
    "tests/test_llm_gateway.py",
}

FRAMEWORK_RUNTIME_MODULES: Set[str] = {
    "core/ports/agent_runtime.py",
    "core/agent_spec/",
    "core/agents/",
    "zonata/langgraph_adapter.py",
    "core/temporal_durable_execution_runtime.py",
    "core/langgraph/",
    "core/temporal/",
    "core/adk/",
    "agent_factory/build/",
}

BANNED_FRAMEWORK_PROCESS_EXECUTORS: Set[str] = {
    "subprocess.Popen",
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "os.system",
    "os.popen",
}

BANNED_FRAMEWORK_RAW_NETWORKS: Set[str] = {
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
    "httpx.get",
    "httpx.post",
    "aiohttp.ClientSession",
    "urllib.request.urlopen",
}

ALLOWLISTED_PROCESS_PATHS: Set[str] = {
    "core/ports/terminal.py",
    "core/terminal/",
    "core/host/",
    "core/agent_import/sandbox_runner.py",
    "tests/",
    "scripts/",
}

TARGET_SCAN_DIRECTORIES = ["core", "zonata", "agent_factory", "src"]


class AntiBypassASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path.replace("\\", "/")
        self.violations: List[AntiBypassViolation] = []
        self._is_framework_runtime = any(
            mod in self.file_path for mod in FRAMEWORK_RUNTIME_MODULES
        )

    def _is_allowlisted(self, allowlist: Set[str]) -> bool:
        for prefix in allowlist:
            if prefix in self.file_path:
                return True
        return False

    def visit_Import(self, node: ast.Import) -> None:
        if not self._is_allowlisted(ALLOWLISTED_MODEL_IMPORT_PATHS):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg in BANNED_DIRECT_MODEL_IMPORTS or alias.name in BANNED_DIRECT_MODEL_IMPORTS:
                    self.violations.append(
                        AntiBypassViolation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            violation_type="RULE_34_DIRECT_MODEL_IMPORT",
                            description=(
                                f"Direct model SDK import '{alias.name}' is prohibited by Rule 34. "
                                f"All model invocations must route through LLMGateway."
                            ),
                            offending_symbol=alias.name,
                        )
                    )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not self._is_allowlisted(ALLOWLISTED_MODEL_IMPORT_PATHS):
            if node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg in BANNED_DIRECT_MODEL_IMPORTS or node.module in BANNED_DIRECT_MODEL_IMPORTS:
                    self.violations.append(
                        AntiBypassViolation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            violation_type="RULE_34_DIRECT_MODEL_IMPORT",
                            description=(
                                f"Direct model SDK import 'from {node.module} import ...' is prohibited by Rule 34. "
                                f"All model invocations must route through LLMGateway."
                            ),
                            offending_symbol=node.module,
                        )
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check for un-governed process execution or raw network calls inside framework runtimes
        if self._is_framework_runtime and not self._is_allowlisted(ALLOWLISTED_PROCESS_PATHS):
            call_str = self._resolve_call_name(node.func)
            if call_str in BANNED_FRAMEWORK_PROCESS_EXECUTORS:
                self.violations.append(
                    AntiBypassViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="RULE_34_UNGOVERNED_SUBPROCESS",
                        description=(
                            f"Direct execution of '{call_str}' in agent runtime code is prohibited by Rule 34. "
                            f"OS execution must route through TerminalPort and ActionGateway."
                        ),
                        offending_symbol=call_str,
                    )
                )
            elif call_str in BANNED_FRAMEWORK_RAW_NETWORKS:
                self.violations.append(
                    AntiBypassViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="RULE_34_DIRECT_NETWORK_EGRESS",
                        description=(
                            f"Direct network call '{call_str}' in agent runtime code is prohibited by Rule 34. "
                            f"Network egress must route through ZONATA ports (BrowserPort, SearchPort)."
                        ),
                        offending_symbol=call_str,
                    )
                )
        self.generic_visit(node)

    def _resolve_call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""


def scan_python_code(code: str, file_path: str = "snippet.py") -> List[AntiBypassViolation]:
    """Scans Python source string for Rule 34 anti-bypass violations."""
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError:
        return []
    visitor = AntiBypassASTVisitor(file_path)
    visitor.visit(tree)
    return visitor.violations


def scan_repository_anti_bypass(repo_root: str) -> List[AntiBypassViolation]:
    """Recursively audits repo Python files for Rule 34 bypass violations."""
    violations: List[AntiBypassViolation] = []
    for dir_name in TARGET_SCAN_DIRECTORIES:
        scan_dir = os.path.join(repo_root, dir_name)
        if not os.path.isdir(scan_dir):
            continue

        for root, _, files in os.walk(scan_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_root)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    file_violations = scan_python_code(content, rel_path)
                    violations.extend(file_violations)
                except Exception:
                    pass

    return violations
