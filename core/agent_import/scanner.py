"""
ZONATA Agent Factory — Static Security & Malware Scanner (Rule 25, Rule 32).

Quarantines imported code, scans with ClamAV antivirus, and executes AST checks
for dangerous calls (eval, exec, unrestricted subprocess, anti-evasion patterns).
"""

from __future__ import annotations

import ast
import hashlib
import os
from typing import Any, Dict, List, Tuple

from core.agent_import.types import (
    DangerousCodeRejectedError,
    MalwareDetectedError,
)
from core.ports.antivirus import resolve_antivirus_provider
from core.security.anti_evasion import scan_python_code


class DangerousASTInspector(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        # Check eval() / exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "__import__"):
                self.violations.append(
                    f"{self.filename}:{node.lineno}: Prohibited dynamic execution function '{node.func.id}' detected."
                )

        # Check os.system, subprocess calls
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in ("system", "popen", "spawn"):
                self.violations.append(
                    f"{self.filename}:{node.lineno}: Prohibited system execution call '{node.func.attr}' detected."
                )

        self.generic_visit(node)


class SkillImportScanner:
    """
    Performs comprehensive ClamAV and AST security audits on imported packages.
    """

    @classmethod
    def scan_code_bytes(
        cls,
        code_bytes: bytes,
        filename: str = "imported_skill.py",
    ) -> Dict[str, Any]:
        sha256 = hashlib.sha256(code_bytes).hexdigest()

        # 1. Antivirus Scan via ClamAV Port (Rule 32)
        av_prov = resolve_antivirus_provider()
        av_res = av_prov.scan_bytes(code_bytes, filename=filename)
        if getattr(av_res, "infected", False):
            raise MalwareDetectedError(
                f"ClamAV detected malware in imported package '{filename}': {getattr(av_res, 'virus_name', 'UNKNOWN')}"
            )

        # 2. Rule 25 Anti-Evasion AST Scan
        code_str = code_bytes.decode("utf-8", errors="replace")
        evasion_violations = scan_python_code(code_str, filename=filename)
        if evasion_violations:
            raise DangerousCodeRejectedError(
                f"Rule 25 violation in '{filename}': {evasion_violations[0].description}"
            )

        # 3. Static AST analysis for dangerous execution functions
        try:
            tree = ast.parse(code_str, filename=filename)
            inspector = DangerousASTInspector(filename=filename)
            inspector.visit(tree)
            if inspector.violations:
                raise DangerousCodeRejectedError(inspector.violations[0])
        except SyntaxError as exc:
            raise DangerousCodeRejectedError(
                f"Imported code could not be parsed for security review: {exc}"
            ) from exc

        return {
            "clean": True,
            "sha256": sha256,
            "clamav_passed": True,
            "ast_security_passed": True,
        }
