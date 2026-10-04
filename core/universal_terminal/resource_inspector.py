"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Resource Inspector
Dynamically inspects host hardware, virtualization support, container engines,
memory headroom, CPU architecture, and kernel capabilities to ensure resource-aware routing.
"""

from typing import Dict, List, Optional, Any
import os
import sys
import platform
import shutil
import subprocess
import time

class ResourceInspector:
    """
    Hardware and system capacity inspector.
    Evaluates real machine metrics to determine what execution substrates can be safely provisioned.
    """

    @classmethod
    def inspect_system(cls) -> Dict[str, Any]:
        """Collects complete real-time host hardware & virtualization metrics."""
        uname = platform.uname()
        ram_info = cls._get_ram_info()
        disk_info = cls._get_disk_info()
        cpu_info = cls._get_cpu_info()
        virt_info = cls._get_virtualization_info()
        container_info = cls._get_container_info()
        display_info = cls._get_display_info()
        load_avg = cls._get_load_average()
        substrate_matrix = cls._build_substrate_matrix(virt_info, container_info, display_info)

        return {
            "timestamp": time.time(),
            "hostname": uname.node,
            "architecture": uname.machine,
            "os_system": uname.system,
            "kernel_release": uname.release,
            "cpu": cpu_info,
            "ram": ram_info,
            "disk": disk_info,
            "virtualization": virt_info,
            "containers": container_info,
            "display": display_info,
            "substrate_matrix": substrate_matrix,
            "load_average": load_avg,
            "is_resource_constrained": ram_info["total_mb"] < 2048 or disk_info["free_mb"] < 2048
        }

    @classmethod
    def _get_ram_info(cls) -> Dict[str, int]:
        total_mb = 4096
        available_mb = 3072
        swap_mb = 1024
        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            total_mb = int(line.split()[1]) // 1024
                        elif "MemAvailable" in line:
                            available_mb = int(line.split()[1]) // 1024
                        elif "SwapTotal" in line:
                            swap_mb = int(line.split()[1]) // 1024
        except Exception:
            pass
        return {
            "total_mb": total_mb,
            "available_mb": available_mb,
            "swap_mb": swap_mb
        }

    @classmethod
    def _get_disk_info(cls) -> Dict[str, int]:
        total_mb = 10240
        free_mb = 5120
        try:
            usage = shutil.disk_usage("/")
            total_mb = usage.total // (1024 * 1024)
            free_mb = usage.free // (1024 * 1024)
        except Exception:
            pass
        return {
            "total_mb": total_mb,
            "free_mb": free_mb,
            "used_mb": total_mb - free_mb
        }

    @classmethod
    def _get_cpu_info(cls) -> Dict[str, Any]:
        count = os.cpu_count() or 2
        arch = platform.machine()
        return {
            "cores": count,
            "architecture": arch,
            "is_64bit": sys.maxsize > 2**32
        }

    @classmethod
    def _get_virtualization_info(cls) -> Dict[str, Any]:
        kvm_present = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
        qemu_present = shutil.which("qemu-system-x86_64") is not None or shutil.which("qemu-system-aarch64") is not None
        return {
            "kvm_available": kvm_present,
            "qemu_available": qemu_present,
            "hardware_virtualization_supported": kvm_present or qemu_present
        }

    @classmethod
    def _get_container_info(cls) -> Dict[str, Any]:
        has_docker = shutil.which("docker") is not None
        has_podman = shutil.which("podman") is not None
        has_bwrap = shutil.which("bwrap") is not None
        has_chroot = shutil.which("chroot") is not None
        return {
            "docker": has_docker,
            "podman": has_podman,
            "bubblewrap": has_bwrap,
            "chroot": has_chroot,
            "rootless_container_supported": has_podman or has_bwrap or has_docker
        }

    @classmethod
    def _get_display_info(cls) -> Dict[str, Any]:
        display_env = os.environ.get("DISPLAY")
        wayland_env = os.environ.get("WAYLAND_DISPLAY")
        has_xvfb = shutil.which("Xvfb") is not None
        has_xephyr = shutil.which("Xephyr") is not None
        has_xdotool = shutil.which("xdotool") is not None
        has_scrot = shutil.which("scrot") is not None
        return {
            "display_env": display_env,
            "wayland_env": wayland_env,
            "xvfb_available": has_xvfb,
            "xephyr_available": has_xephyr,
            "xdotool_available": has_xdotool,
            "scrot_available": has_scrot,
            "virtual_display_supported": has_xvfb or display_env is not None or wayland_env is not None
        }

    @classmethod
    def _build_substrate_matrix(cls, virt_info: Dict[str, Any], container_info: Dict[str, Any], display_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "host_sandbox": {
                "available": True,
                "status": "OPERATIONAL",
                "isolation": "PROCESS_WORKSPACE"
            },
            "container": {
                "available": container_info.get("rootless_container_supported", False),
                "status": "OPERATIONAL" if container_info.get("rootless_container_supported", False) else "UNAVAILABLE_FALLBACK_SANDBOX",
                "isolation": "NAMESPACE_OR_ROOTLESS",
                "checked_engines": ["docker", "podman", "bubblewrap"]
            },
            "micro_vm": {
                "available": virt_info.get("kvm_available", False),
                "status": "OPERATIONAL" if virt_info.get("kvm_available", False) else "UNAVAILABLE_NO_KVM",
                "isolation": "HARDWARE_HYPERVISOR",
                "device_kvm": os.path.exists("/dev/kvm")
            },
            "desktop_gui": {
                "available": display_info.get("virtual_display_supported", False),
                "status": "OPERATIONAL" if display_info.get("virtual_display_supported", False) else "HEADLESS_DEGRADED",
                "isolation": "VIRTUAL_DISPLAY_BUFFER"
            },
            "remote_linux": {
                "available": True,
                "status": "REQUIRES_ENDPOINT",
                "isolation": "NETWORK_NODE"
            }
        }

    @classmethod
    def _get_load_average(cls) -> List[float]:
        try:
            return list(os.getloadavg())
        except Exception:
            return [0.1, 0.1, 0.1]

