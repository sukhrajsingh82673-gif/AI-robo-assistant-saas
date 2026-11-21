"""ZONATA Sovereign Core — AST Truth & Reality Linter.

Implements OpenCode Step 1C.4:
AST-based linter that fails the build if:
1. Any adapter method returns success (OK, ACCEPTED_BY_PROVIDER, DELIVERED, SENT, STORED, POSTED)
   without setting a non-empty provider_ref.
2. Any adapter method returns DELIVERED, SENT, STORED, or POSTED without a live verification check.
"""

from __future__ import annotations
import ast
import os
from typing import Any, List, Optional, Set, Tuple


SUCCESS_STATUS_NAMES = {
    "OK",
    "ACCEPTED_BY_PROVIDER",
    "DELIVERED",
    "SENT",
    "STORED",
    "POSTED",
}

RIGOROUS_STATUS_NAMES = {
    "DELIVERED",
    "SENT",
    "STORED",
    "POSTED",
}

LIVE_CHECK_KEYWORDS = {
    "read", "read_back", "sha256", "hexdigest", "status", "status_code",
    "code", "execute", "commit", "cursor", "recv", "request", "urlopen",
    "sendmail", "post", "get", "fetch", "poll", "verify", "check",
    "ping", "get_connection", "receipt", "ack", "hashlib", "resp"
}


def _extract_status_string(node: ast.AST) -> Optional[str]:
    """Extract string status name from AST node (Constant or Attribute)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_empty_or_none(node: ast.AST) -> bool:
    """Check if AST node represents None or empty string/falsy value."""
    if isinstance(node, ast.Constant):
        return node.value is None or node.value == ""
    if isinstance(node, ast.Name) and node.id in ("None", ""):
        return True
    return False


def _has_live_check(fn_node: ast.FunctionDef) -> bool:
    """Inspect function AST body for indicators of live verification calls or checks."""
    for child in ast.walk(fn_node):
        # Check call names or attribute calls
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name) and any(k in func.id.lower() for k in LIVE_CHECK_KEYWORDS):
                return True
            if isinstance(func, ast.Attribute) and any(k in func.attr.lower() for k in LIVE_CHECK_KEYWORDS):
                return True
        # Check comparisons (e.g. status == 200, digest == expected)
        if isinstance(child, ast.Compare):
            return True
        # Check try-except network / database blocks
        if isinstance(child, ast.Try):
            return True
    return False


class TruthASTVisitor(ast.NodeVisitor):
    def __init__(self, filename: str = "<unknown>"):
        self.filename = filename
        self.violations: List[str] = []
        self._current_function: Optional[ast.FunctionDef] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        prev = self._current_function
        self._current_function = node
        self.generic_visit(node)
        self._current_function = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        # Treat async functions identically
        prev = self._current_function
        self._current_function = node  # type: ignore[assignment]
        self.generic_visit(node)
        self._current_function = prev

    def visit_Call(self, node: ast.Call) -> Any:
        # Check if call is ProviderResult(...) or creates a provider result dict
        is_provider_result = False
        if isinstance(node.func, ast.Name) and node.func.id == "ProviderResult":
            is_provider_result = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "ProviderResult":
            is_provider_result = True

        if is_provider_result:
            self._validate_provider_result_call(node)

        self.generic_visit(node)

    def _validate_provider_result_call(self, node: ast.Call) -> None:
        status_val: Optional[str] = None
        provider_ref_node: Optional[ast.AST] = None
        has_provider_ref_kw = False

        # Extract arguments
        # ProviderResult(status, provider, provider_ref, ...)
        if node.args:
            status_val = _extract_status_string(node.args[0])
            if len(node.args) >= 3:
                has_provider_ref_kw = True
                provider_ref_node = node.args[2]

        for kw in node.keywords:
            if kw.arg == "status":
                status_val = _extract_status_string(kw.value)
            elif kw.arg == "provider_ref":
                has_provider_ref_kw = True
                provider_ref_node = kw.value

        func_name = self._current_function.name if self._current_function else "<module>"
        line = getattr(node, "lineno", "?")

        if status_val and status_val.upper() in SUCCESS_STATUS_NAMES:
            # Rule 1: Must set non-empty provider_ref
            if not has_provider_ref_kw or provider_ref_node is None or _is_empty_or_none(provider_ref_node):
                self.violations.append(
                    f"{self.filename}:{line}: Method '{func_name}' returns success status '{status_val}' "
                    f"without setting a non-empty provider_ref."
                )

            # Rule 2: Rigorous status requires live check
            if status_val.upper() in RIGOROUS_STATUS_NAMES:
                if self._current_function and not _has_live_check(self._current_function):
                    self.violations.append(
                        f"{self.filename}:{line}: Method '{func_name}' claims '{status_val}' "
                        f"without performing a live verification check."
                    )


def lint_code_string(code: str, filename: str = "<string>") -> List[str]:
    """Lint raw Python code string and return list of violations."""
    tree = ast.parse(code, filename=filename)
    visitor = TruthASTVisitor(filename)
    visitor.visit(tree)
    return visitor.violations


def lint_file(filepath: str) -> List[str]:
    """Lint a Python source file and return list of violations."""
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    return lint_code_string(code, filepath)


def lint_directory(dirpath: str) -> List[str]:
    """Recursively lint all python files in directory."""
    violations: List[str] = []
    for root, _, files in os.walk(dirpath):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                violations.extend(lint_file(path))
    return violations
