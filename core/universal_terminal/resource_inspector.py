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
        load_avg = cls._get_load_average()

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
    def _get_load_average(cls) -> List[float]:
        try:
            return list(os.getloadavg())
        except Exception:
            return [0.1, 0.1, 0.1]
