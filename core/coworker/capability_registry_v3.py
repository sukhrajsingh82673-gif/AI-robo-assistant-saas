"""
ZONATA Autonomous Executive Coworker — Milestone 5: Capability Registry V3
Enforces AST security screening (blocking eval, exec, dynamic import, un-sanitized os.system),
approved enterprise license verification, and cryptographic SHA-256 fingerprinting.
"""

from __future__ import annotations
import ast
import hashlib
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class RegisteredCapabilityV3:
    capability_id: str
    name: str
    category: str
    license_str: str
    source_digest: str
    is_admitted: bool
    security_score: float
    violations: List[str] = field(default_factory=list)
    admitted_at: float = field(default_factory=time.time)


class CapabilityRegistryV3:
    """Governed Capability Registry V3 enforcing AST screening and enterprise license approval."""

    APPROVED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Python-2.0"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile"}
    FORBIDDEN_ATTRS = {"system", "popen", "spawn", "execve"}
    DANGEROUS_TARGETS = {"/etc/shadow", "/root/.ssh", "id_rsa", "bearer ", "zonata_master_key"}

    def __init__(self):
        self._registry: Dict[str, RegisteredCapabilityV3] = {}

    def scan_and_register(
        self,
        name: str,
        category: str,
        license_str: str,
        source_code: str
    ) -> RegisteredCapabilityV3:
        """
        Screens capability source code for dangerous AST nodes and validates license.
        Computes cryptographic SHA-256 fingerprint.
        """
        cap_id = f"cap_v3_{uuid.uuid4().hex[:8]}"
        violations = []
        score = 0.5 if license_str in self.APPROVED_LICENSES else 0.0

        if license_str not in self.APPROVED_LICENSES:
            violations.append(f"Prohibited license: '{license_str}'. Must be approved enterprise license (MIT, Apache-2.0, BSD, etc.).")

        # AST Security Screening
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                # 1. Block dangerous call invocations
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_CALLS:
                        violations.append(f"Forbidden AST call: '{node.func.id}'")
                    elif isinstance(node.func, ast.Attribute):
                        if node.func.attr in self.FORBIDDEN_ATTRS:
                            violations.append(f"Suspicious un-sanitized call: '{node.func.attr}'")

                # 2. Block dynamic imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("pty", "shelve"):
                            violations.append(f"Prohibited module import: '{alias.name}'")

                # 3. Detect sensitive string literals
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value.lower()
                    if any(t in val for t in self.DANGEROUS_TARGETS):
                        violations.append("Sensitive file or secret pattern detected in string literal")

        except Exception as e:
            violations.append(f"AST parse failure: {str(e)}")

        if not violations:
            score += 0.5

        is_admitted = (score >= 0.75 and len(violations) == 0)
        digest = hashlib.sha256(source_code.encode("utf-8")).hexdigest()

        entry = RegisteredCapabilityV3(
            capability_id=cap_id,
            name=name,
            category=category,
            license_str=license_str,
            source_digest=digest,
            is_admitted=is_admitted,
            security_score=score,
            violations=violations
        )

        if is_admitted:
            self._registry[cap_id] = entry
        return entry

    def get_capability(self, cap_id: str) -> Optional[RegisteredCapabilityV3]:
        return self._registry.get(cap_id)

    def list_admitted(self) -> List[RegisteredCapabilityV3]:
        return list(self._registry.values())
