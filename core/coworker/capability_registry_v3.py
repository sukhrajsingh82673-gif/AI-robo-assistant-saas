"""
ZONATA Autonomous Executive Coworker — Capability Registry V3 & 10-Stage Lifecycle
Enforces AST security screening, approved enterprise license verification,
and the complete autonomous self-expanding capability lifecycle:
  Discover -> Evaluate -> Approve -> Install -> Integrate -> Test -> Register -> Execute -> Monitor -> Decommission.
"""

from __future__ import annotations
import ast
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import hashlib
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Callable
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
    version: str = "1.0.0"
    sandbox_path: Optional[str] = None
    execution_count: int = 0
    lifecycle_stage: str = "DISCOVERED"


class CapabilityRegistryV3:
    """
    Governed Capability Registry V3 enforcing AST screening, enterprise license approval,
    and the full 10-stage autonomous capability expansion lifecycle.
    """

    APPROVED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Python-2.0", "MPL-2.0"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile"}
    FORBIDDEN_ATTRS = {"system", "popen", "spawn", "execve"}
    DANGEROUS_TARGETS = {"/etc/shadow", "/root/.ssh", "id_rsa", "bearer ", "zonata_master_key"}

    def __init__(self):
        self._registry: Dict[str, RegisteredCapabilityV3] = {}
        # Capability id -> sandbox module/runner. Capabilities are executed in a
        # separate Python process, never in this one.
        self._sandboxed: Dict[str, Dict[str, str]] = {}

    def scan_and_register(
        self,
        name: str,
        category: str,
        license_str: str,
        source_code: str,
        version: str = "1.0.0"
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
                        if alias.name in ("pty", "shelve", "ctypes"):
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
            violations=violations,
            version=version,
            lifecycle_stage="REGISTERED" if is_admitted else "REJECTED"
        )
        self._registry[cap_id] = entry
        return entry

    # =========================================================================
    # 10-STAGE AUTONOMOUS CAPABILITY LIFECYCLE
    # =========================================================================

    def detect_capability_gap(self, required_feature: str) -> Dict[str, Any]:
        """Stage 1: DISCOVER/DETECT — detects that a required tool is missing."""
        gap_id = f"gap_{uuid.uuid4().hex[:8]}"
        is_missing = True
        for cap in self._registry.values():
            if cap.name == required_feature and cap.is_admitted:
                is_missing = False
                break
        return {
            "gap_id": gap_id,
            "required_feature": required_feature,
            "is_missing": is_missing,
            "detected_at": time.time()
        }

    def discover_candidate(
        self,
        gap_info: Dict[str, Any],
        candidate_catalog: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Stage 2: DISCOVER — looks up a candidate in a supplied catalogue.

        There is no web or GitHub search here, and unknown features are not
        synthesised. A missing candidate is reported as missing.
        """
        feature = gap_info.get("required_feature", "unknown")
        catalog = candidate_catalog or {
            "json_schema_validator": {
                "name": "json_schema_validator",
                "category": "validation",
                "version": "1.2.0",
                "license": "MIT",
                "source": "def validate_schema(data, schema):\n    return isinstance(data, dict) and all(k in data for k in schema.get('required', []))\n"
            },
            "entropy_calculator": {
                "name": "entropy_calculator",
                "category": "cryptography",
                "version": "1.0.0",
                "license": "MIT",
                "source": "import math\ndef compute_shannon_entropy(data_bytes: bytes) -> float:\n    if not data_bytes: return 0.0\n    freq = [float(data_bytes.count(b))/len(data_bytes) for b in set(data_bytes)]\n    return -sum([p * math.log2(p) for p in freq])\n"
            }
        }
        candidate = catalog.get(feature)
        if candidate is None:
            return {
                "found": False,
                "name": feature,
                "reason": "NO_CANDIDATE_IN_CATALOG",
                "catalog_size": len(catalog),
            }
        return {**candidate, "found": True}

    def evaluate_candidate(self, candidate: Dict[str, Any]) -> RegisteredCapabilityV3:
        """Stage 3: EVALUATE — runs AST security and license compliance checks."""
        entry = self.scan_and_register(
            name=candidate.get("name", "candidate"),
            category=candidate.get("category", "utility"),
            license_str=candidate.get("license", "UNKNOWN"),
            source_code=candidate.get("source", ""),
            version=candidate.get("version", "1.0.0")
        )
        entry.lifecycle_stage = "EVALUATED"
        return entry

    def request_approval(
        self,
        capability: RegisteredCapabilityV3,
        requested_by: str = "AutonomousCoworker"
    ) -> Dict[str, Any]:
        """
        Stage 4: APPROVE — local admission gate.

        This is a security-score threshold, not a PolicyEngine decision. A real
        deployment must route the request through the policy gateway and record
        an approval id; `approval_basis` makes the difference explicit.
        """
        approved = capability.is_admitted and capability.security_score >= 0.75
        capability.lifecycle_stage = "APPROVED" if approved else "APPROVAL_DENIED"
        return {
            "capability_id": capability.capability_id,
            "approved": approved,
            "approval_basis": "SECURITY_SCORE_THRESHOLD",
            "requested_by": requested_by,
            "security_score": capability.security_score,
            "violations": capability.violations
        }

    def install_in_sandbox(self, capability: RegisteredCapabilityV3, source_code: str) -> str:
        """Stage 5: INSTALL — provisions extension in an isolated directory."""
        sandbox_dir = tempfile.mkdtemp(prefix=f"cap_sandbox_{capability.name}_")
        py_file = os.path.join(sandbox_dir, f"{capability.name}.py")
        with open(py_file, "w", encoding="utf-8") as fp:
            fp.write(source_code)
        capability.sandbox_path = sandbox_dir
        capability.lifecycle_stage = "INSTALLED"
        return sandbox_dir

    # Written into each sandbox and executed as a separate process. The module
    # is imported by path, one function is called, and the result is printed as
    # tagged JSON. Nothing from the capability runs inside the main process.
    _RUNNER_SOURCE = """\
import importlib.util, json, pickle, sys

def main():
    payload_path, module_path, func_name = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(payload_path, "rb") as fh:
        payload = pickle.load(fh)
    spec = importlib.util.spec_from_file_location("sandbox_capability", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        print("__CAP_ERROR__NOT_CALLABLE")
        return 2
    result = fn(*payload.get("args", []), **payload.get("kwargs", {}))
    print("__CAP_RESULT__" + json.dumps(result, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""

    SANDBOX_TIMEOUT_SEC = 10.0

    def _sandbox_paths(self, capability: RegisteredCapabilityV3) -> Dict[str, str]:
        sandbox_dir = capability.sandbox_path
        if not sandbox_dir:
            sandbox_dir = tempfile.mkdtemp(prefix=f"cap_sandbox_{capability.name}_")
            capability.sandbox_path = sandbox_dir
        return {
            "dir": sandbox_dir,
            "module": os.path.join(sandbox_dir, f"{capability.name}.py"),
            "runner": os.path.join(sandbox_dir, "_runner.py"),
        }

    def integrate_capability(self, capability: RegisteredCapabilityV3, source_code: str) -> bool:
        """
        Stage 6: INTEGRATE — writes the module and its runner into the sandbox.

        The module is syntax-checked with `py_compile` and inspected with AST.
        It is *not* executed here; `exec` of untrusted source in the host process
        would defeat the sandbox. Execution happens in `test_capability` and
        `execute_capability` as a subprocess.
        """
        paths = self._sandbox_paths(capability)
        with open(paths["module"], "w", encoding="utf-8") as fp:
            fp.write(source_code)
        with open(paths["runner"], "w", encoding="utf-8") as fp:
            fp.write(self._RUNNER_SOURCE)

        compiled = subprocess.run(
            [sys.executable, "-m", "py_compile", paths["module"]],
            capture_output=True, text=True, timeout=self.SANDBOX_TIMEOUT_SEC,
        )
        if compiled.returncode != 0:
            capability.lifecycle_stage = "INTEGRATE_FAILED"
            return False

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            capability.lifecycle_stage = "INTEGRATE_FAILED"
            return False
        functions = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not functions:
            capability.lifecycle_stage = "INTEGRATE_FAILED"
            return False
        # Prefer the capability name; otherwise bind the first top-level function
        # and record which one, so callers know what will be invoked.
        func_name = capability.name if capability.name in functions else functions[0]

        self._sandboxed[capability.capability_id] = {
            "module": paths["module"],
            "runner": paths["runner"],
            "func": func_name,
        }
        capability.lifecycle_stage = "INTEGRATED"
        return True

    def _run_in_sandbox(
        self,
        capability_id: str,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Any, str]:
        """Runs one call in a subprocess. Returns (ok, result, detail)."""
        entry = self._sandboxed.get(capability_id)
        if not entry:
            return False, None, "CAPABILITY_NOT_INTEGRATED"
        # Unique payload per call: two concurrent calls on the same capability
        # must not share a pickle file.
        fd, payload = tempfile.mkstemp(
            prefix="_payload_", suffix=".pkl", dir=os.path.dirname(entry["module"])
        )
        os.close(fd)
        try:
            with open(payload, "wb") as fh:
                pickle.dump({"args": list(args), "kwargs": kwargs or {}}, fh)
            proc = subprocess.run(
                [sys.executable, entry["runner"], payload, entry["module"], entry["func"]],
                capture_output=True, text=True, timeout=self.SANDBOX_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired:
            return False, None, "SANDBOX_TIMEOUT"
        except Exception as exc:
            return False, None, f"SANDBOX_ERROR: {exc}"
        finally:
            try:
                os.remove(payload)
            except OSError:
                pass

        if proc.returncode != 0:
            return False, None, f"SANDBOX_EXIT_{proc.returncode}"
        for line in proc.stdout.splitlines():
            if line.startswith("__CAP_RESULT__"):
                try:
                    return True, json.loads(line[len("__CAP_RESULT__"):]), "OK"
                except json.JSONDecodeError:
                    return False, None, "UNPARSEABLE_RESULT"
        return False, None, "NO_RESULT_EMITTED"

    def test_capability(
        self,
        capability: RegisteredCapabilityV3,
        test_args: Tuple = (),
        test_kwargs: Optional[Dict[str, Any]] = None,
        expected_predicate: Optional[Callable[[Any], bool]] = None
    ) -> bool:
        """Stage 7: TEST — runs the capability once in its sandbox and checks the output."""
        ok, out, _detail = self._run_in_sandbox(
            capability.capability_id, args=test_args, kwargs=test_kwargs
        )
        if not ok:
            capability.lifecycle_stage = "TEST_FAILED"
            return False
        passed = bool(expected_predicate(out)) if expected_predicate else (out is not None)
        capability.lifecycle_stage = "TESTED" if passed else "TEST_FAILED"
        return passed

    def register_capability(self, capability: RegisteredCapabilityV3) -> str:
        """Stage 8: REGISTER — registers into permanent registry and seals evidence token."""
        capability.lifecycle_stage = "REGISTERED"
        token = hashlib.sha256(f"{capability.capability_id}:{capability.source_digest}".encode()).hexdigest()
        return token

    def execute_capability(self, capability_id: str, *args, **kwargs) -> Any:
        """Stage 9: EXECUTE — runs the admitted capability in its sandbox."""
        cap = self._registry.get(capability_id)
        if not cap or not cap.is_admitted:
            raise RuntimeError(f"Capability '{capability_id}' is not admitted or available.")
        ok, out, detail = self._run_in_sandbox(capability_id, args=args, kwargs=kwargs)
        if not ok:
            raise RuntimeError(f"Capability '{capability_id}' failed in sandbox: {detail}")
        cap.execution_count += 1
        cap.lifecycle_stage = "EXECUTED"
        return out

    def monitor_and_decommission(self, capability_id: str) -> bool:
        """Stage 10: MONITOR & DECOMMISSION — safely unloads capability and purges sandbox."""
        cap = self._registry.get(capability_id)
        if not cap:
            return False
        if cap.sandbox_path and os.path.exists(cap.sandbox_path):
            shutil.rmtree(cap.sandbox_path, ignore_errors=True)
            cap.sandbox_path = None
        self._sandboxed.pop(capability_id, None)
        cap.lifecycle_stage = "DECOMMISSIONED"
        return True

    def run_full_lifecycle(
        self,
        required_feature: str,
        test_args: Tuple = (),
        expected_predicate: Optional[Callable[[Any], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes all 10 stages of the capability lifecycle in sequence.
        """
        # 1. Detect Gap
        gap = self.detect_capability_gap(required_feature)

        # 2. Discover Candidate
        candidate = self.discover_candidate(gap)
        if not candidate.get("found", True):
            return {
                "success": False,
                "stage": "DISCOVER",
                "reason": candidate.get("reason", "NO_CANDIDATE_FOUND"),
            }

        # 3. Evaluate AST & License
        cap_entry = self.evaluate_candidate(candidate)
        if not cap_entry.is_admitted:
            return {"success": False, "stage": "EVALUATE", "violations": cap_entry.violations}

        # 4. Request Approval
        appr = self.request_approval(cap_entry)
        if not appr.get("approved"):
            return {"success": False, "stage": "APPROVE"}

        # 5. Install in Sandbox
        sandbox = self.install_in_sandbox(cap_entry, candidate["source"])

        # 6. Integrate
        integrated = self.integrate_capability(cap_entry, candidate["source"])
        if not integrated:
            return {"success": False, "stage": "INTEGRATE"}

        # 7. Test
        test_ok = self.test_capability(cap_entry, test_args=test_args, expected_predicate=expected_predicate)
        if not test_ok:
            return {"success": False, "stage": "TEST"}

        # 8. Register
        token = self.register_capability(cap_entry)

        # 9. Execute
        exec_res = self.execute_capability(cap_entry.capability_id, *test_args)

        # 10. Monitor & Decommission
        decom_ok = self.monitor_and_decommission(cap_entry.capability_id)

        return {
            "success": True,
            "capability_id": cap_entry.capability_id,
            "evidence_token": token,
            "execution_result": exec_res,
            "decommissioned": decom_ok,
            "lifecycle_stages_completed": 10
        }

    def get_capability(self, capability_id: str) -> Optional[RegisteredCapabilityV3]:
        return self._registry.get(capability_id)

    def list_capabilities(self) -> List[RegisteredCapabilityV3]:
        return list(self._registry.values())
