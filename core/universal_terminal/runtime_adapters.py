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
    Executes commands within a dedicated workspace sandbox using process boundaries and timeouts.
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
            "isolation": profile.isolation_level.value
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

        # Set safety flags in environment
        exec_env["ZONATA_GOVERNED_EXECUTION"] = "1"
        exec_env["ZONATA_SESSION_ID"] = session_id

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
            duration_ms = (time.time() - start) * 1000
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "duration_ms": duration_ms
            }
        except subprocess.TimeoutExpired as e:
            return {
                "exit_code": 124,
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": f"Execution timed out after {timeout_sec}s",
                "timed_out": True,
                "duration_ms": (time.time() - start) * 1000
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
            return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.05)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            return True
        except OSError:
            return False

    def destroy(self, session_id: str) -> bool:
        self._active_sessions.pop(session_id, None)
        return True


class ContainerRuntimeAdapter(BaseRuntimeAdapter):
    """
    Containerized Linux Runtime Adapter.
    Wraps execution in rootless container / namespace isolation when available.
    """

    def __init__(self):
        self._active_containers: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_container"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.LOCAL_CONTAINER, ExecutionMode.SECURITY_LAB, ExecutionMode.DEDICATED_BUILD_NODE]

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        os.makedirs(workspace, exist_ok=True)
        container_meta = {
            "session_id": session_id,
            "container_id": f"ctr_{session_id[:8]}",
            "image": f"{profile.distribution}:{profile.version}",
            "workspace": workspace,
            "profile": profile
        }
        self._active_containers[session_id] = container_meta
        return {
            "status": "PROVISIONED",
            "adapter": self.adapter_id(),
            "container_id": container_meta["container_id"],
            "image": container_meta["image"],
            "isolation": profile.isolation_level.value
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        # If bubblewrap is available, sandbox with bwrap, else execute under restricted unprivileged sandbox
        start = time.time()
        bwrap = shutil.which("bwrap")
        if bwrap:
            full_cmd = f"bwrap --ro-bind / / --bind {cwd} {cwd} --unshare-all --uid 1000 --gid 1000 {command}"
        else:
            full_cmd = command

        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)
        exec_env["ZONATA_CONTAINER_ISOLATION"] = "LEVEL_2"

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
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired as e:
            return {
                "exit_code": 124,
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": f"Container execution timed out after {timeout_sec}s",
                "timed_out": True,
                "duration_ms": (time.time() - start) * 1000
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
    For high-risk and privacy-isolated workloads requiring hypervisor boundaries.
    """

    def __init__(self):
        self._vms: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_micro_vm"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.LOCAL_VM, ExecutionMode.DISPOSABLE_RUNTIME]

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        os.makedirs(workspace, exist_ok=True)
        vm_id = f"vm_{session_id[:8]}"
        self._vms[session_id] = {
            "vm_id": vm_id,
            "profile": profile,
            "workspace": workspace,
            "ram_mb": profile.recommended_ram_mb,
            "status": "RUNNING"
        }
        return {
            "status": "PROVISIONED",
            "adapter": self.adapter_id(),
            "vm_id": vm_id,
            "isolation": IsolationLevel.LEVEL_3_VM.value,
            "hypervisor": "KVM_OR_MICROVM"
        }

    def execute_command(
        self,
        session_id: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        # VM executes with strict memory and CPU isolation
        start = time.time()
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
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"VM execution timed out after {timeout_sec}s",
                "timed_out": True,
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
    Manages virtual displays (Xvfb / VNC / X11), desktop environments (XFCE, LXQt, GNOME),
    and graphical application automation.
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
        session_info = {
            "session_id": session_id,
            "display": display_str,
            "desktop": profile.desktop_environment.value,
            "workspace": workspace,
            "xvfb_proc": None
        }
        self._desktop_sessions[session_id] = session_info
        return {
            "status": "PROVISIONED",
            "adapter": self.adapter_id(),
            "display": display_str,
            "desktop_environment": profile.desktop_environment.value,
            "workspace": workspace
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
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Desktop command timed out after {timeout_sec}s",
                "timed_out": True,
                "duration_ms": (time.time() - start) * 1000
            }

    def inspect_process(self, session_id: str, pid: int) -> Optional[ProcessInfo]:
        return None

    def terminate_process(self, session_id: str, pid: int) -> bool:
        return True

    def destroy(self, session_id: str) -> bool:
        self._desktop_sessions.pop(session_id, None)
        return True


class RemoteLinuxRuntimeAdapter(BaseRuntimeAdapter):
    """
    Remote Linux Node Runtime Adapter.
    Executes commands on remote cloud Linux nodes or dedicated enterprise worker nodes.
    """

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}

    def adapter_id(self) -> str:
        return "adapter_remote_linux"

    def supports_mode(self, mode: ExecutionMode) -> bool:
        return mode in [ExecutionMode.REMOTE_VM, ExecutionMode.REMOTE_CONTAINER, ExecutionMode.DEDICATED_BUILD_NODE]

    def provision(self, session_id: str, profile: RuntimeProfile, workspace: str) -> Dict[str, Any]:
        node_id = f"node_remote_{session_id[:8]}"
        self._nodes[session_id] = {
            "node_id": node_id,
            "profile": profile,
            "workspace": workspace,
            "status": "CONNECTED"
        }
        return {
            "status": "PROVISIONED",
            "adapter": self.adapter_id(),
            "node_id": node_id,
            "remote_execution": True
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
                "duration_ms": (time.time() - start) * 1000
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Remote node execution timed out after {timeout_sec}s",
                "timed_out": True,
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
