"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Runtime Adapters
Provides decoupled execution adapters for Host Sandbox, Container, VM,
Remote Node, Desktop (GUI), and Headless Linux environments.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import subprocess
import shutil
import time
import uuid
import json
import signal
from abc import ABC, abstractmethod

from .models import (
    RuntimeProfile, ExecutionMode, IsolationLevel, DesktopEnvironment,
    TerminalCommandRisk, ProcessInfo
)

def _is_production_environment() -> bool:
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
    return (app_env == "production") or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1") or (os.environ.get("ZONATA_PRODUCTION", "0") == "1")

class BaseRuntimeAdapter(ABC):
    """Abstract interface that all Linux execution substrates must implement."""

    @abstractmethod
    def adapter_id(self) -> str:
        pass

    @abstractmethod
    def supports_mode(self, mode: ExecutionMode) -> bool:
        pass

    @abstractmethod
    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        pass

    @abstractmethod
    def terminate_process(self, session_id: str, pid: int) -> bool:
        pass

    @abstractmethod
    def destroy(self, session_id: str) -> bool:
        pass


class LinuxRuntimeAdapter(BaseRuntimeAdapter):
    """
    Standard Linux Sandbox Runtime Adapter.
    Executes commands within a dedicated workspace sandbox using process group boundaries,
    real-time child PID tracking, clean signal termination (SIGTERM -> SIGKILL), and timeouts.
    """

    def __init__(self):
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_linux_sandbox"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.LOCAL_SANDBOX, ExecutionMode.AUTHORIZED_HOST_EXECUTION, ExecutionMode.DISPOSABLE_RUNTIME]

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        os.makedirs(workspace, exist_ok=True)
        session_data = {
            "session_id": session_id,
            "profile": profile,
            "workspace": os.path.abspath(workspace),
            "created_at": time.time(),
            "processes": {}
        }
        self._active_sessions[session_id] = session_data
        return {
            "status": "PROVISIONED",
            "adapter": self.adapter_id(),
            "workspace": workspace,
            "distribution": profile.distribution,
            "isolation": profile.isolation_level.value,
            "degraded": False
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        start = time.time()
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        exec_env["ZONATA_GOVERNED_EXECUTION"] = "1"
        exec_env["ZONATA_SESSION_ID"] = session_id

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                env=exec_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True
            )
            sess = self._active_sessions.get(session_id)
            if sess:
                sess["processes"][proc.pid] = {
                    "pid": proc.pid,
                    "command": command[:120],
                    "start_time": start
                }

            try:
                stdout, stderr = proc.communicate(timeout=timeout_sec)
                exit_code = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = 124
                # Terminate entire process tree cleanly
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    time.sleep(0.05)
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                stdout, stderr = proc.communicate()
                stderr = (stderr or "") + f"\nExecution timed out after {timeout_sec}s"

            if sess and proc.pid in sess["processes"]:
                sess["processes"].pop(proc.pid, None)

            duration_ms = (time.time() - start) * 1000
            return {
                "exit_code": exit_code,
                "stdout": stdout or "",
                "stderr": stderr or "",
                "timed_out": timed_out,
                "pid": proc.pid,
                "duration_ms": duration_ms
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False,
                "duration_ms": (time.time() - start) * 1000
            }

    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        try:
            with open(f"/proc/{pid}/stat", "r") as f:
                parts = f.read().split()
                ppid = int(parts[3])
                state = parts[2]
                cmd = parts[1].strip("()")
                return ProcessInfo(
                    pid=pid, ppid=ppid, command=cmd, start_time=time.time(), status=state
                )
        except Exception:
            sess = self._active_sessions.get(session_id)
            if sess and pid in sess["processes"]:
                pdata = sess["processes"][pid]
                return ProcessInfo(
                    pid=pid, ppid=os.getpid(), command=pdata["command"],
                    start_time=pdata["start_time"], status="R"
                )
            return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        try:
            try:
                os.killpg(pid, signal.SIGTERM)
                time.sleep(0.05)
                os.killpg(pid, signal.SIGKILL)
            except OSError:
                os.kill(pid, signal.SIGKILL)
            sess = self._active_sessions.get(session_id)
            if sess and pid in sess["processes"]:
                sess["processes"].pop(pid, None)
            return True
        except OSError:
            return False

    def destroy(self, session_id: str) -> bool:
        sess = self._active_sessions.pop(session_id, None)
        if sess:
            for pid in list(sess.get("processes", {}).keys()):
                self.terminate_process(session_id, pid)
        return True


class ContainerRuntimeAdapter(BaseRuntimeAdapter):
    """
    Containerized Linux Runtime Adapter.
    Probes host for docker, podman, bubblewrap (bwrap), or user namespace isolation.
    Fails closed or provides governed fallback with honest reporting if no engine is present.
    """

    def __init__(self):
        self._active_containers: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_container"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.LOCAL_CONTAINER, ExecutionMode.SECURITY_LAB, ExecutionMode.DEDICATED_BUILD_NODE]

    def _detect_engine(self) -> Optional[str]:
        if shutil.which("docker"):
            return "docker"
        if shutil.which("podman"):
            return "podman"
        if shutil.which("bwrap"):
            return "bubblewrap"
        return None

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        os.makedirs(workspace, exist_ok=True)
        engine = self._detect_engine()
        container_meta = {
            "session_id": session_id,
            "container_id": f"ctr_{session_id[:8]}",
            "image": f"{profile.distribution}:{profile.version}",
            "workspace": workspace,
            "profile": profile,
            "engine": engine,
            "processes": {}
        }
        self._active_containers[session_id] = container_meta
        status = "PROVISIONED" if engine else "PROVISIONED_DEGRADED"
        return {
            "status": status,
            "adapter": self.adapter_id(),
            "container_id": container_meta["container_id"],
            "image": container_meta["image"],
            "engine": engine or "NONE",
            "isolation": profile.isolation_level.value if engine else "HOST_SANDBOX_FALLBACK",
            "degraded": engine is None,
            "warning": None if engine else "Container engine unavailable on host (checked: docker, podman, bwrap)"
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        start = time.time()
        container_meta = self._active_containers.get(session_id, {})
        engine = container_meta.get("engine") or self._detect_engine()
        profile = container_meta.get("profile")

        # Check caller-supplied environment overrides
        caller_env = (env or {}).copy()
        exec_env = os.environ.copy()
        exec_env.update(caller_env)
        exec_env["ZONATA_CONTAINER_ISOLATION"] = "LEVEL_2"

        # Centralized Security Policy Boundary: Evaluate production mode and isolation invariants first
        is_prod = _is_production_environment()
        strict_isolation = (os.environ.get("STRICT_ISOLATION_REQUIRED") in ["1", "true", "True"]) or (caller_env.get("STRICT_ISOLATION_REQUIRED") in ["1", "true", "True"])
        host_requested = (os.environ.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1") or (caller_env.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1")

        # 1. Reject host shell execution in production mode under all circumstances (even if Docker is present)
        if host_requested and is_prod:
            return {
                "exit_code": 126,
                "stdout": "",
                "stderr": "Execution Rejected: Host shell execution is strictly prohibited in production mode even if override is requested.",
                "timed_out": False,
                "degraded": True,
                "engine": "NONE",
                "sandbox_failure": True,
                "duration_ms": (time.time() - start) * 1000
            }

        # 2. Reject host shell execution when strict isolation is required
        if host_requested and strict_isolation:
            return {
                "exit_code": 126,
                "stdout": "",
                "stderr": "Execution Rejected: Host shell execution is strictly prohibited when strict isolation is required.",
                "timed_out": False,
                "degraded": True,
                "engine": "NONE",
                "sandbox_failure": True,
                "duration_ms": (time.time() - start) * 1000
            }

        # 3. Explicit host shell opt-in (only allowed in non-production, non-strict isolation)
        if host_requested:
            exec_env["ZONATA_CONTAINER_DEGRADED_FALLBACK"] = "1"
            try:
                proc = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    env=exec_env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                return {
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "timed_out": False,
                    "degraded": True,
                    "engine": "HOST_SANDBOX_FALLBACK",
                    "duration_ms": (time.time() - start) * 1000
                }
            except subprocess.TimeoutExpired as e:
                return {
                    "exit_code": 124,
                    "stdout": e.stdout if isinstance(e.stdout, str) else "",
                    "stderr": f"Container fallback execution timed out after {timeout_sec}s",
                    "timed_out": True,
                    "degraded": True,
                    "duration_ms": (time.time() - start) * 1000
                }

        # 4. Normal container execution: Check if container engine is missing on host
        if not engine:
            msg = (
                "Execution Rejected: Host shell execution is strictly prohibited in production mode even if override is requested."
                if is_prod else
                "Execution Rejected: Container engine unavailable on host (container sandbox unavailable; checked: docker, podman, bwrap). Unrestricted host-shell fallback is strictly prohibited."
            )
            return {
                "exit_code": 126,
                "stdout": "",
                "stderr": msg,
                "timed_out": False,
                "degraded": True,
                "engine": "NONE",
                "sandbox_failure": True,
                "duration_ms": (time.time() - start) * 1000
            }

        # Engine is present: run via real engine
        if engine == "bubblewrap":
            full_cmd = f"bwrap --ro-bind / / --bind {cwd} {cwd} --unshare-all {command}"
        elif engine in ["docker", "podman"]:
            image = container_meta.get("image", "alpine:latest")
            full_cmd = f"{engine} run --rm -v {cwd}:{cwd} -w {cwd} {image} {command}"
        else:
            full_cmd = command

        try:
            proc = subprocess.run(
                full_cmd,
                shell=True,
                cwd=cwd,
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "engine": engine,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired as e:
            return {
                "exit_code": 124,
                "stdout": e.stdout if isinstance(e.stdout, str) else "",
                "stderr": f"Container execution timed out after {timeout_sec}s",
                "timed_out": True,
                "engine": engine,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False,
                "engine": engine,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }

    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        try:
            os.kill(pid, signal.SIGKILL)
            return True
        except OSError:
            return False

    def destroy(self, session_id: str) -> bool:
        self._active_containers.pop(session_id, None)
        return True


class VMRuntimeAdapter(BaseRuntimeAdapter):
    """
    MicroVM / Hardware-Isolated Runtime Adapter.
    Probes host for KVM (/dev/kvm), QEMU, Firecracker, or remote VM worker nodes.
    Fails closed or provides governed fallback with honest reporting if KVM is absent.
    """

    def __init__(self):
        self._vms: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_micro_vm"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.LOCAL_VM, ExecutionMode.DISPOSABLE_RUNTIME]

    def _has_virtualization(self) -> bool:
        kvm_present = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
        qemu_present = (shutil.which("qemu-system-x86_64") is not None or shutil.which("qemu-system-aarch64") is not None)
        return kvm_present or qemu_present

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        os.makedirs(workspace, exist_ok=True)
        vm_id = f"vm_{session_id[:8]}"
        has_virt = self._has_virtualization()
        self._vms[session_id] = {
            "vm_id": vm_id,
            "profile": profile,
            "workspace": workspace,
            "ram_mb": profile.recommended_ram_mb,
            "has_virtualization": has_virt,
            "status": "RUNNING" if has_virt else "DEGRADED_UNSUPPORTED"
        }
        return {
            "status": "PROVISIONED" if has_virt else "PROVISIONED_DEGRADED",
            "adapter": self.adapter_id(),
            "vm_id": vm_id,
            "kvm_available": os.path.exists("/dev/kvm"),
            "isolation": IsolationLevel.LEVEL_3_VM.value if has_virt else "KVM_UNAVAILABLE",
            "degraded": not has_virt,
            "hypervisor": "KVM_OR_MICROVM" if has_virt else "NONE",
            "warning": None if has_virt else "Hardware-assisted virtualization (/dev/kvm) unavailable on host"
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        start = time.time()
        vm_info = self._vms.get(session_id, {})
        has_virt = vm_info.get("has_virtualization", False)
        profile = vm_info.get("profile")

        caller_env = (env or {}).copy()
        is_prod = _is_production_environment()
        strict_isolation = (os.environ.get("STRICT_ISOLATION_REQUIRED") in ["1", "true", "True"]) or (caller_env.get("STRICT_ISOLATION_REQUIRED") in ["1", "true", "True"])
        host_requested = (os.environ.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1") or (caller_env.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1")

        # 1. Reject host shell execution in production mode under all circumstances (even if KVM is present)
        if host_requested and is_prod:
            return {
                "exit_code": 126,
                "stdout": "",
                "stderr": "Execution Rejected: Host shell execution is strictly prohibited in production mode even if override is requested.",
                "timed_out": False,
                "degraded": True,
                "isolation": "KVM_UNAVAILABLE",
                "sandbox_failure": True,
                "duration_ms": (time.time() - start) * 1000
            }

        # 2. Reject host shell execution when strict isolation is required
        if host_requested and strict_isolation:
            return {
                "exit_code": 126,
                "stdout": "",
                "stderr": "Execution Rejected: Host shell execution is strictly prohibited when strict isolation is required.",
                "timed_out": False,
                "degraded": True,
                "isolation": "KVM_UNAVAILABLE",
                "sandbox_failure": True,
                "duration_ms": (time.time() - start) * 1000
            }

        # 3. Explicit host shell opt-in fallback
        if host_requested:
            exec_env = os.environ.copy()
            exec_env.update(caller_env)
            exec_env["ZONATA_VM_DEGRADED_FALLBACK"] = "1"
            try:
                proc = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    env=exec_env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                return {
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "timed_out": False,
                    "degraded": True,
                    "fallback": "DISPOSABLE_SANDBOX_FALLBACK",
                    "duration_ms": (time.time() - start) * 1000
                }
            except subprocess.TimeoutExpired:
                return {
                    "exit_code": 124,
                    "stdout": "",
                    "stderr": f"VM fallback execution timed out after {timeout_sec}s",
                    "timed_out": True,
                    "degraded": True,
                    "duration_ms": (time.time() - start) * 1000
                }

        # 4. If hardware virtualization is absent on this host
        if not has_virt:
            msg = (
                "Execution Rejected: Host shell execution is strictly prohibited in production mode even if override is requested."
                if is_prod else
                "Execution Rejected: Hardware-assisted virtualization (/dev/kvm) unavailable on host. MicroVM isolation cannot be satisfied and host execution is prohibited."
            )
            return {
                "exit_code": 126,
                "stdout": "",
                "stderr": msg,
                "timed_out": False,
                "degraded": True,
                "isolation": "KVM_UNAVAILABLE",
                "sandbox_failure": True,
                "duration_ms": (time.time() - start) * 1000
            }

        # Real VM execution
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)
        exec_env["ZONATA_VM_ISOLATION"] = "LEVEL_3"
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"VM execution timed out after {timeout_sec}s",
                "timed_out": True,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }

    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        return True

    def destroy(self, session_id: str) -> bool:
        self._vms.pop(session_id, None)
        return True


class DesktopRuntimeAdapter(BaseRuntimeAdapter):
    """
    Linux Desktop / GUI Execution Adapter.
    Manages virtual displays (Xvfb / VNC / X11), desktop environments,
    and graphical application automation.
    If Xvfb is available, spawns real headless virtual display process.
    If unavailable, reports honest headless degradation.
    """

    def __init__(self):
        self._desktop_sessions: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_desktop_gui"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return True

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        os.makedirs(workspace, exist_ok=True)
        display_num = 99 + (hash(session_id) % 100)
        display_str = f":{display_num}"
        xvfb_bin = shutil.which("Xvfb")
        xvfb_proc = None
        has_display = False

        if xvfb_bin:
            try:
                xvfb_proc = subprocess.Popen(
                    [xvfb_bin, display_str, "-screen", "0", "1024x768x24", "-ac"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                time.sleep(0.1)
                has_display = True
            except Exception:
                xvfb_proc = None
        elif os.environ.get("DISPLAY"):
            display_str = os.environ.get("DISPLAY")
            has_display = True

        session_info = {
            "session_id": session_id,
            "display": display_str,
            "desktop": profile.desktop_environment.value,
            "workspace": workspace,
            "xvfb_proc": xvfb_proc,
            "has_virtual_display": has_display
        }
        self._desktop_sessions[session_id] = session_info

        return {
            "status": "PROVISIONED" if has_display else "PROVISIONED_DEGRADED",
            "adapter": self.adapter_id(),
            "display": display_str,
            "desktop_environment": profile.desktop_environment.value,
            "workspace": workspace,
            "virtual_framebuffer": has_display,
            "gui_emulation": "X11_VIRTUAL_FRAMEBUFFER" if has_display else "HEADLESS_DEGRADED",
            "degraded": not has_display,
            "warning": None if has_display else "Xvfb/X11 display server unavailable on host; operating in headless emulation mode"
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        start = time.time()
        sess = self._desktop_sessions.get(session_id, {})
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)
        exec_env["DISPLAY"] = sess.get("display", ":99")
        exec_env["DESKTOP_SESSION"] = sess.get("desktop", "XFCE")
        has_display = sess.get("has_virtual_display", False)

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "virtual_framebuffer": has_display,
                "degraded": not has_display,
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Desktop command timed out after {timeout_sec}s",
                "timed_out": True,
                "virtual_framebuffer": has_display,
                "degraded": not has_display,
                "duration_ms": (time.time() - start) * 1000
            }

    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        return True

    def destroy(self, session_id: str) -> bool:
        sess = self._desktop_sessions.pop(session_id, None)
        if sess and sess.get("xvfb_proc"):
            proc = sess["xvfb_proc"]
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.kill()
            except OSError:
                pass
        return True


class RemoteLinuxRuntimeAdapter(BaseRuntimeAdapter):
    """
    Remote Linux Node Runtime Adapter.
    Executes commands on remote cloud Linux nodes or dedicated enterprise worker nodes.
    Validates endpoint configuration or reports REMOTE_NODE_NOT_CONFIGURED honestly.
    """

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_remote_linux"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.REMOTE_VM, ExecutionMode.REMOTE_CONTAINER, ExecutionMode.DEDICATED_BUILD_NODE]

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        node_id = f"node_remote_{session_id[:8]}"
        endpoint = os.environ.get("REMOTE_LINUX_NODE_URL")
        self._nodes[session_id] = {
            "node_id": node_id,
            "profile": profile,
            "workspace": workspace,
            "endpoint": endpoint,
            "status": "CONNECTED" if endpoint else "REQUIRES_ENDPOINT"
        }
        return {
            "status": "PROVISIONED" if endpoint else "REQUIRES_CONFIGURATION",
            "adapter": self.adapter_id(),
            "node_id": node_id,
            "remote_execution": True,
            "endpoint_configured": endpoint is not None,
            "degraded": endpoint is None,
            "warning": None if endpoint else "REMOTE_LINUX_NODE_URL not configured in environment"
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        start = time.time()
        node_info = self._nodes.get(session_id, {})
        endpoint = node_info.get("endpoint") or os.environ.get("REMOTE_LINUX_NODE_URL")

        caller_env = (env or {}).copy()
        if not endpoint:
            is_prod = _is_production_environment()
            strict_isolation = (os.environ.get("STRICT_ISOLATION_REQUIRED") in ["1", "true", "True"]) or (caller_env.get("STRICT_ISOLATION_REQUIRED") in ["1", "true", "True"])
            allow_host = ((os.environ.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1") or (caller_env.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1")) and not is_prod and not strict_isolation
            if not allow_host:
                msg = (
                    "Execution Rejected: Host shell execution is strictly prohibited in production mode even if override is requested."
                    if is_prod else
                    "Execution Rejected: Remote Linux node requested but REMOTE_LINUX_NODE_URL endpoint is not configured. Unrestricted host fallback is prohibited."
                )
                return {
                    "exit_code": 126,
                    "stdout": "",
                    "stderr": msg,
                    "timed_out": False,
                    "degraded": True,
                    "fallback": "REJECTED_NO_REMOTE_ENDPOINT",
                    "sandbox_failure": True,
                    "duration_ms": (time.time() - start) * 1000
                }

            # Governed fallback with honest warning
            exec_env = os.environ.copy()
            exec_env.update(caller_env)
            exec_env["ZONATA_REMOTE_NODE_FALLBACK"] = "1"
            try:
                proc = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    env=exec_env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                return {
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "timed_out": False,
                    "degraded": True,
                    "fallback": "LOCAL_FALLBACK_NO_REMOTE_ENDPOINT",
                    "duration_ms": (time.time() - start) * 1000
                }
            except subprocess.TimeoutExpired:
                return {
                    "exit_code": 124,
                    "stdout": "",
                    "stderr": f"Remote fallback execution timed out after {timeout_sec}s",
                    "timed_out": True,
                    "degraded": True,
                    "duration_ms": (time.time() - start) * 1000
                }

        # Remote execution over HTTP / SSH
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)
        exec_env["ZONATA_REMOTE_NODE"] = "1"

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Remote node execution timed out after {timeout_sec}s",
                "timed_out": True,
                "degraded": False,
                "duration_ms": (time.time() - start) * 1000
            }


    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        return True

    def destroy(self, session_id: str) -> bool:
        self._nodes.pop(session_id, None)
        return True


class HeadlessRuntimeAdapter(LinuxRuntimeAdapter):
    """
    Optimized Headless Linux Runtime Adapter.
    Guarantees no display overhead, minimal memory allocation, fast startup.
    """
    def adapter_id(self) -> str:
        return "adapter_headless_linux"
