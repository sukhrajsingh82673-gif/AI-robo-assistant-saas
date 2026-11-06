"""
ZONATA Autonomous Coworker 2.0 — 5-Level Intelligent Execution Decision Engine
Ladder of Execution:
  Level 1: Native Desktop / POSIX Tools (git, curl, jq, tar, etc.)
  Level 2: Sovereign ZONATA Registered Capabilities (Registry, MCP, DB)
  Level 3: External Open-Source Discovery, AST Security Audit & License Screening
  Level 4: Isolated Virtualenv Sandbox Installation & Smoke Testing
  Level 5: Governed Execution, Independent Verification & Rollback
"""

from __future__ import annotations
import os
import sys
import ast
import json
import time
import uuid
import shutil
import hashlib
import subprocess
import venv
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable

from .contracts_v2 import (
    CleanupManifestRecord, CleanupResourceType, CleanupStatus,
    TaskLifecycleState, CoworkerV2Task
)
from .db_store_v2 import CoworkerDbStoreV2


class ExecutionLadderLevel(int, Enum):
    LEVEL_1_POSIX = 1
    LEVEL_1_DESKTOP = 1
    LEVEL_2_ZONATA = 2
    LEVEL_3_DISCOVERY = 3
    LEVEL_4_SANDBOX = 4
    LEVEL_5_EXECUTION_ROLLBACK = 5


@dataclass
class DecisionEvaluationResult:
    level: ExecutionLadderLevel
    resolved: bool
    capability_name: str
    execution_plan: Dict[str, Any]
    reasoning: str
    security_score: float = 1.0
    license_status: str = "APPROVED"
    sandbox_path: Optional[str] = None
    manifest_id: Optional[str] = None
    error: Optional[str] = None

    @property
    def available(self) -> bool:
        return self.resolved

    @property
    def ladder_level(self) -> ExecutionLadderLevel:
        return self.level


@dataclass
class ExecutionOutput:
    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    output_hash: str
    rollback_applied: bool = False
    verification_passed: bool = False
    evidence: Dict[str, Any] = field(default_factory=dict)


class ExecutionDecisionEngine:
    """
    Evaluates actions through the 5-Level Decision Ladder to find the safest,
    most deterministic, and lowest-cost execution pathway.
    """

    APPROVED_LICENSES = {
        "MIT", "Apache-2.0", "Apache 2.0", "BSD-2-Clause", "BSD-3-Clause",
        "ISC", "Python-2.0", "BSD", "MIT License", "Apache Software License"
    }
    QUARANTINED_LICENSES = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "SSPL", "Commons-Clause", "Proprietary", "Unknown"}

    FORBIDDEN_AST_CALLS = {"eval", "exec", "__import__", "compile"}
    FORBIDDEN_AST_ATTRS = {"system", "popen", "spawn", "execve"}
    SENSITIVE_TARGETS = {"/etc/shadow", "/root/.ssh", "id_rsa", "bearer ", "sk-", "zonata_master_key"}

    COMMON_POSIX_TOOLS = [
        "git", "curl", "wget", "jq", "python3", "tar", "gzip", "unzip",
        "grep", "awk", "sed", "find", "cut", "sort", "uniq", "wc", "cat",
        "head", "tail", "diff", "ffmpeg", "sqlite3"
    ]

    def __init__(
        self,
        db_store: Optional[CoworkerDbStoreV2] = None,
        capability_registry: Optional[Any] = None,
        workspaces_root: str = "/tmp/zonata_workspaces",
        store: Optional[CoworkerDbStoreV2] = None,
        scan_root: Optional[str] = None
    ):
        self.db = store or db_store or CoworkerDbStoreV2.get_instance()
        self.capability_registry = capability_registry
        self.workspaces_root = workspaces_root
        self.scan_root = scan_root or workspaces_root
        os.makedirs(self.workspaces_root, exist_ok=True)

    def evaluate_level_1_desktop(self, tool_command: str) -> DecisionEvaluationResult:
        res = self.evaluate_level_1_posix(tool_command)
        if res:
            return res
        return DecisionEvaluationResult(
            level=ExecutionLadderLevel.LEVEL_1_POSIX,
            resolved=False,
            capability_name="unknown_command",
            execution_plan={},
            reasoning=f"Command '{tool_command}' not found in POSIX PATH.",
            security_score=0.0
        )

    def screen_license(self, license_name: str) -> bool:
        lic = (license_name or "").strip()
        return lic in self.APPROVED_LICENSES

    def ast_screen_code(self, source_code: str) -> Dict[str, Any]:
        violations: List[str] = []
        is_safe = True
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_AST_CALLS:
                        violations.append(f"Forbidden call: {node.func.id}")
                        is_safe = False
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in self.FORBIDDEN_AST_ATTRS:
                        violations.append(f"Forbidden attribute: {node.func.attr}")
                        is_safe = False
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val_lower = node.value.lower()
                    if any(t in val_lower for t in self.SENSITIVE_TARGETS):
                        violations.append("Sensitive token/credential detected in literal")
                        is_safe = False
        except Exception as e:
            violations.append(f"AST parse error: {str(e)}")
            is_safe = False
        return {"is_safe": is_safe, "violations": violations}

    def execute_and_verify(
        self,
        command: str,
        expected_output_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        timeout_sec: float = 60.0
    ) -> ExecutionOutput:
        cmd_list = ["bash", "-c", command] if isinstance(command, str) else command
        def _verify(stdout, stderr):
            if expected_output_path:
                return os.path.exists(expected_output_path) and os.path.getsize(expected_output_path) > 0
            return True
        return self.execute_with_verification_and_rollback(
            command=cmd_list,
            cwd=workspace_dir,
            timeout_sec=timeout_sec,
            verify_fn=_verify
        )

    # =========================================================================
    # Level 1: Native Desktop / POSIX Tools
    # =========================================================================

    def evaluate_level_1_posix(self, tool_command: str) -> Optional[DecisionEvaluationResult]:
        """
        Detects if the requested utility is present natively in system PATH.
        If available, constructs a direct zero-overhead native execution plan.
        """
        executable = tool_command.strip().split()[0] if tool_command.strip() else ""
        if not executable:
            return None

        tool_path = shutil.which(executable)
        if tool_path and executable in self.COMMON_POSIX_TOOLS:
            return DecisionEvaluationResult(
                level=ExecutionLadderLevel.LEVEL_1_POSIX,
                resolved=True,
                capability_name=f"posix_{executable}",
                execution_plan={
                    "type": "POSIX_CLI",
                    "executable": tool_path,
                    "command": tool_command,
                    "isolation": "HOST_SUBPROCESS"
                },
                reasoning=f"Resolved via native POSIX executable: {tool_path}",
                security_score=1.0,
                license_status="SYSTEM_NATIVE"
            )
        return None

    # =========================================================================
    # Level 2: Sovereign ZONATA Capabilities
    # =========================================================================

    KNOWN_ZONATA_CAPABILITIES = {
        "terminal.file_operation", "terminal.command_execution",
        "browser.navigate", "browser.extract", "mcp.call_tool",
        "rpa.desktop_control", "api.http_request"
    }

    def evaluate_level_2_zonata(self, capability_id: str) -> Optional[DecisionEvaluationResult]:
        """
        Checks internal ZONATA capability catalog, MCP servers, and registered providers.
        """
        if capability_id in self.KNOWN_ZONATA_CAPABILITIES:
            return DecisionEvaluationResult(
                level=ExecutionLadderLevel.LEVEL_2_ZONATA,
                resolved=True,
                capability_name=capability_id,
                execution_plan={
                    "type": "ZONATA_CAPABILITY",
                    "capability_id": capability_id,
                    "preferred_provider": "local_engine"
                },
                reasoning=f"Found existing verified ZONATA capability: {capability_id}",
                security_score=1.0,
                license_status="Apache-2.0"
            )

        if self.capability_registry:
            try:
                cap = self.capability_registry.get_capability(capability_id)
                if cap and getattr(cap, "availability_status", "AVAILABLE") == "AVAILABLE":
                    return DecisionEvaluationResult(
                        level=ExecutionLadderLevel.LEVEL_2_ZONATA,
                        resolved=True,
                        capability_name=capability_id,
                        execution_plan={
                            "type": "ZONATA_CAPABILITY",
                            "capability_id": capability_id,
                            "preferred_provider": getattr(cap, "preferred_provider", "local_engine")
                        },
                        reasoning=f"Found existing verified ZONATA capability: {capability_id}",
                        security_score=1.0,
                        license_status=getattr(cap, "license", "Apache-2.0")
                    )
            except Exception:
                pass
        return None

    # =========================================================================
    # Level 3: External Open-Source Discovery, AST Screening & License Audit
    # =========================================================================

    def evaluate_level_3_discovery(
        self,
        package_name: str,
        package_license: str,
        source_code: Optional[str] = None
    ) -> DecisionEvaluationResult:
        """
        Audits an external open-source candidate:
        1. License approval check.
        2. AST security screening (flags eval, exec, credential patterns).
        3. Security score computation (0.0 to 1.0; must be >= 0.70 to admit).
        """
        # 1. License Check
        lic = package_license.strip()
        is_approved_lic = lic in self.APPROVED_LICENSES
        if not is_approved_lic:
            return DecisionEvaluationResult(
                level=ExecutionLadderLevel.LEVEL_3_DISCOVERY,
                resolved=False,
                capability_name=package_name,
                execution_plan={},
                reasoning=f"License '{lic}' is not approved for sovereign enterprise runtime.",
                security_score=0.0,
                license_status="REJECTED_OR_QUARANTINED",
                error=f"License rejection: {lic}"
            )

        # 2. AST Security Screening
        ast_clean = True
        ast_issues: List[str] = []
        if source_code:
            try:
                tree = ast.parse(source_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_AST_CALLS:
                            ast_issues.append(f"Forbidden call: {node.func.id}")
                            ast_clean = False
                        elif isinstance(node.func, ast.Attribute) and node.func.attr in self.FORBIDDEN_AST_ATTRS:
                            ast_issues.append(f"Suspicious attribute call: {node.func.attr}")
                            ast_clean = False
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        s_val = node.value.lower()
                        if any(target in s_val for target in self.SENSITIVE_TARGETS):
                            ast_issues.append(f"Sensitive credential string detected in literal")
                            ast_clean = False
            except Exception as e:
                ast_issues.append(f"AST parse failure: {str(e)}")
                ast_clean = False

        # 3. Composite Score Calculation
        score = 0.50 if is_approved_lic else 0.0
        if ast_clean:
            score += 0.50
        else:
            score = max(0.0, score - 0.30)

        if score < 0.70:
            return DecisionEvaluationResult(
                level=ExecutionLadderLevel.LEVEL_3_DISCOVERY,
                resolved=False,
                capability_name=package_name,
                execution_plan={},
                reasoning=f"AST screening failed with score {score:.2f}: {'; '.join(ast_issues)}",
                security_score=score,
                license_status="LICENSE_APPROVED_BUT_AST_FAILED",
                error=f"AST security audit failed: {ast_issues}"
            )

        return DecisionEvaluationResult(
            level=ExecutionLadderLevel.LEVEL_3_DISCOVERY,
            resolved=True,
            capability_name=package_name,
            execution_plan={
                "type": "EXTERNAL_PACKAGE_QUALIFIED",
                "package_name": package_name,
                "license": lic,
                "ast_clean": True
            },
            reasoning=f"Package '{package_name}' passed license and AST audit with score {score:.2f}.",
            security_score=score,
            license_status="APPROVED"
        )

    def discover_external_package(
        self,
        package_name: str,
        task_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        allow_download: bool = True
    ) -> Dict[str, Any]:
        """
        Executes genuine Level 3 package provenance and Level 4 isolated installation:
        1. Queries official PyPI JSON API: https://pypi.org/pypi/{package_name}/json
        2. Validates package license against approved open-source licenses.
        3. Extracts release version, distribution URLs, and SHA-256 cryptographic digests.
        4. Downloads the distribution archive to /tmp/zonata_workspaces/<mission_id>/downloads/.
        5. Computes and asserts SHA-256 cryptographic integrity matches PyPI metadata.
        6. Provisions isolated sandbox venv and smoke-tests import.
        7. Registers sandbox cleanup manifest.
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        mission_id = mission_id or f"msn_{uuid.uuid4().hex[:8]}"

        # 1. Query PyPI JSON API
        pypi_url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            req = urllib.request.Request(pypi_url, headers={"User-Agent": "ZONATA-Coworker/2.0"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                pypi_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {
                "success": False,
                "status": "PACKAGE_NOT_FOUND" if e.code == 404 else "PYPI_HTTP_ERROR",
                "package_name": package_name,
                "error": f"PyPI responded with status {e.code}: {e.reason}",
                "provenance": None
            }
        except Exception as e:
            return {
                "success": False,
                "status": "PYPI_NETWORK_ERROR",
                "package_name": package_name,
                "error": str(e),
                "provenance": None
            }

        info = pypi_data.get("info", {})
        version = info.get("version", "unknown")
        declared_license = (info.get("license") or "").strip()
        classifiers = info.get("classifiers", [])

        # License screening (check declared license and OSI classifiers)
        license_approved = False
        effective_license = declared_license or "Unknown"
        for lic in self.APPROVED_LICENSES:
            if lic.lower() in declared_license.lower():
                license_approved = True
                effective_license = lic
                break
        if not license_approved:
            for cls in classifiers:
                if "License :: OSI Approved ::" in cls:
                    for lic in self.APPROVED_LICENSES:
                        if lic.lower() in cls.lower():
                            license_approved = True
                            effective_license = lic
                            break
                    if license_approved:
                        break

        if not license_approved:
            return {
                "success": False,
                "status": "LICENSE_REJECTED",
                "package_name": package_name,
                "version": version,
                "license": effective_license,
                "error": f"License '{effective_license}' is not in approved sovereign runtime licenses.",
                "provenance": {"version": version, "license": effective_license}
            }

        # Find best release distribution (prefer bdist_wheel or sdist)
        urls = pypi_data.get("urls", [])
        chosen_dist = None
        for u in urls:
            if u.get("packagetype") == "bdist_wheel":
                chosen_dist = u
                break
        if not chosen_dist and urls:
            chosen_dist = urls[0]

        if not chosen_dist:
            return {
                "success": False,
                "status": "NO_DISTRIBUTION_FOUND",
                "package_name": package_name,
                "version": version,
                "error": "No downloadable release archives available on PyPI."
            }

        download_url = chosen_dist.get("url")
        pypi_sha256 = chosen_dist.get("digests", {}).get("sha256")
        filename = chosen_dist.get("filename", f"{package_name}-{version}.tar.gz")

        download_dir = os.path.join(self.workspaces_root, mission_id, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        local_file_path = os.path.join(download_dir, filename)

        local_sha256 = None
        integrity_verified = False

        if allow_download:
            try:
                urllib.request.urlretrieve(download_url, local_file_path)
                with open(local_file_path, "rb") as f:
                    local_sha256 = hashlib.sha256(f.read()).hexdigest()

                integrity_verified = (local_sha256.lower() == pypi_sha256.lower()) if pypi_sha256 else True
                if not integrity_verified:
                    return {
                        "success": False,
                        "status": "INTEGRITY_CHECK_FAILED",
                        "package_name": package_name,
                        "version": version,
                        "pypi_sha256": pypi_sha256,
                        "local_sha256": local_sha256,
                        "error": "Local file SHA-256 does not match PyPI published digest!"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "status": "DOWNLOAD_FAILED",
                    "package_name": package_name,
                    "error": str(e)
                }

        # Provision Level 4 isolated sandbox venv
        install_target = local_file_path if (allow_download and os.path.exists(local_file_path)) else package_name
        sandbox_result = self.provision_level_4_sandbox(
            mission_id=mission_id,
            task_id=task_id,
            package_name=install_target
        )

        return {
            "success": sandbox_result.resolved,
            "status": "QUALIFIED_AND_PROVISIONED" if sandbox_result.resolved else "SANDBOX_FAILED",
            "package_name": package_name,
            "version": version,
            "license": effective_license,
            "license_approved": True,
            "pypi_sha256": pypi_sha256,
            "local_sha256": local_sha256,
            "integrity_verified": integrity_verified,
            "download_path": local_file_path if os.path.exists(local_file_path) else None,
            "sandbox_path": sandbox_result.sandbox_path,
            "manifest_id": sandbox_result.manifest_id,
            "execution_plan": sandbox_result.execution_plan,
            "error": sandbox_result.error
        }

    # =========================================================================
    # Level 4: Isolated Virtualenv Sandbox Installation & Smoke Testing
    # =========================================================================

    def provision_level_4_sandbox(
        self,
        mission_id: str,
        task_id: str,
        package_name: str,
        pip_args: Optional[List[str]] = None
    ) -> DecisionEvaluationResult:
        """
        Creates an isolated virtual environment at /tmp/zonata_workspaces/<mission_id>/.venv,
        installs the package, runs a real import smoke test, and registers cleanup manifest.
        """
        workspace_dir = os.path.join(self.workspaces_root, mission_id)
        venv_dir = os.path.join(workspace_dir, ".venv")
        os.makedirs(workspace_dir, exist_ok=True)

        manifest_id = f"mf_{uuid.uuid4().hex[:8]}"

        try:
            # 1. Build virtual environment (with graceful ensurepip fallback on Debian/Ubuntu)
            if not os.path.exists(venv_dir):
                has_ensurepip = False
                try:
                    import ensurepip
                    has_ensurepip = True
                except ImportError:
                    has_ensurepip = False

                if has_ensurepip:
                    try:
                        venv.EnvBuilder(with_pip=True, symlinks=True).create(venv_dir)
                    except (Exception, SystemExit):
                        shutil.rmtree(venv_dir, ignore_errors=True)
                        venv.EnvBuilder(with_pip=False, symlinks=True).create(venv_dir)
                else:
                    venv.EnvBuilder(with_pip=False, symlinks=True).create(venv_dir)

            py_exec = os.path.join(venv_dir, "bin", "python3")
            if not os.path.exists(py_exec):
                py_exec = os.path.join(venv_dir, "bin", "python")

            # Register cleanup manifest record for isolated venv
            cleanup_rec = CleanupManifestRecord(
                manifest_id=manifest_id,
                task_id=task_id,
                mission_id=mission_id,
                resource_type=CleanupResourceType.VENV,
                resource_path=workspace_dir,
                status=CleanupStatus.PENDING
            )
            self.db.add_cleanup_record(cleanup_rec)

            # 2. Governed pip install
            # Test if py_exec has pip; if not, use host pip targeted with --prefix
            has_internal_pip = False
            try:
                chk = subprocess.run([py_exec, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                has_internal_pip = (chk.returncode == 0)
            except Exception:
                has_internal_pip = False

            if has_internal_pip:
                cmd = [py_exec, "-m", "pip", "install", "--no-warn-script-location", package_name]
            else:
                cmd = [sys.executable, "-m", "pip", "install", "--prefix", venv_dir, "--no-warn-script-location", package_name]

            if pip_args:
                cmd.extend(pip_args)

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
            if proc.returncode != 0:
                return DecisionEvaluationResult(
                    level=ExecutionLadderLevel.LEVEL_4_SANDBOX,
                    resolved=False,
                    capability_name=package_name,
                    execution_plan={},
                    reasoning=f"Pip installation failed: {proc.stderr[:300]}",
                    security_score=0.5,
                    sandbox_path=venv_dir,
                    manifest_id=manifest_id,
                    error=proc.stderr
                )

            # 3. Real Import Smoke Test
            raw_pkg = os.path.basename(package_name).split("-")[0] if os.path.sep in package_name else package_name
            module_name = raw_pkg.split("==")[0].split(">=")[0].replace("-", "_")
            smoke_cmd = [py_exec, "-c", f"import {module_name}; print('SMOKE_OK')"]
            smoke_proc = subprocess.run(smoke_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)

            if smoke_proc.returncode != 0 or "SMOKE_OK" not in smoke_proc.stdout:
                return DecisionEvaluationResult(
                    level=ExecutionLadderLevel.LEVEL_4_SANDBOX,
                    resolved=False,
                    capability_name=package_name,
                    execution_plan={},
                    reasoning=f"Smoke import test failed for module '{module_name}': {smoke_proc.stderr[:200]}",
                    security_score=0.4,
                    sandbox_path=venv_dir,
                    manifest_id=manifest_id,
                    error=smoke_proc.stderr
                )

            return DecisionEvaluationResult(
                level=ExecutionLadderLevel.LEVEL_4_SANDBOX,
                resolved=True,
                capability_name=package_name,
                execution_plan={
                    "type": "SANDBOX_VENV",
                    "python_executable": py_exec,
                    "workspace_dir": workspace_dir,
                    "venv_dir": venv_dir,
                    "module_name": module_name
                },
                reasoning=f"Successfully built sandbox venv and smoke tested '{package_name}'.",
                security_score=1.0,
                sandbox_path=venv_dir,
                manifest_id=manifest_id
            )

        except Exception as e:
            return DecisionEvaluationResult(
                level=ExecutionLadderLevel.LEVEL_4_SANDBOX,
                resolved=False,
                capability_name=package_name,
                execution_plan={},
                reasoning=f"Sandbox provisioning exception: {str(e)}",
                security_score=0.0,
                error=str(e)
            )

    # =========================================================================
    # Level 5: Execution, Independent Verification & Rollback
    # =========================================================================

    def execute_with_verification_and_rollback(
        self,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout_sec: float = 60.0,
        verify_fn: Optional[Callable[[str, str], bool]] = None,
        rollback_fn: Optional[Callable[[], bool]] = None
    ) -> ExecutionOutput:
        """
        Executes an action in the designated environment, calculates cryptographic
        output digest, independently verifies the output, and triggers rollback upon failure.
        """
        t0 = time.time()
        try:
            proc = subprocess.run(
                command,
                env=env,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec
            )
            duration_ms = (time.time() - t0) * 1000.0
            out = proc.stdout
            err = proc.stderr
            ret = proc.returncode

            out_hash = hashlib.sha256(out.encode("utf-8", errors="replace")).hexdigest()

            # Independent verification
            verification_passed = (ret == 0)
            if verification_passed and verify_fn:
                try:
                    verification_passed = verify_fn(out, err)
                except Exception:
                    verification_passed = False

            rollback_applied = False
            if not verification_passed or ret != 0:
                if rollback_fn:
                    try:
                        rollback_applied = rollback_fn()
                    except Exception:
                        rollback_applied = False

            return ExecutionOutput(
                success=(ret == 0 and verification_passed),
                returncode=ret,
                stdout=out,
                stderr=err,
                duration_ms=duration_ms,
                output_hash=out_hash,
                rollback_applied=rollback_applied,
                verification_passed=verification_passed,
                evidence={
                    "command": command,
                    "returncode": ret,
                    "duration_ms": duration_ms,
                    "sha256": out_hash
                }
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - t0) * 1000.0
            rollback_applied = False
            if rollback_fn:
                try:
                    rollback_applied = rollback_fn()
                except Exception:
                    pass
            return ExecutionOutput(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout_sec}s",
                duration_ms=duration_ms,
                output_hash="",
                rollback_applied=rollback_applied,
                verification_passed=False
            )
        except Exception as e:
            duration_ms = (time.time() - t0) * 1000.0
            rollback_applied = False
            if rollback_fn:
                try:
                    rollback_applied = rollback_fn()
                except Exception:
                    pass
            return ExecutionOutput(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                output_hash="",
                rollback_applied=rollback_applied,
                verification_passed=False
            )
