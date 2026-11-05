"""
ZONATA Autonomous Coworker 2.0 — Storage and Resource Management Engine (Milestone 5)
Enforces:
  1. Pre-flight checks (CPU < 85%, RAM >= 512MB, Disk >= 1.0GB).
  2. Temporary workspace directory tracking and isolation under /tmp/zonata_workspaces/<mission_id>/.
  3. Strict asset preservation invariant:
     NEVER automatically delete user documents, company records, databases,
     evidence, backups, credentials, or unknown files.
  4. Cleanup manifest execution: safely purging temporary installation artifacts.
"""

from __future__ import annotations
import os
import sys
import shutil
import time
import uuid
import signal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .contracts_v2 import (
    CleanupManifestRecord, CleanupResourceType, CleanupStatus
)
from .db_store_v2 import CoworkerDbStoreV2


@dataclass
class HostResourceMetrics:
    cpu_percent: float
    free_ram_mb: float
    free_disk_gb: float
    cpu_healthy: bool
    ram_healthy: bool
    disk_healthy: bool
    all_healthy: bool
    details: Dict[str, Any] = field(default_factory=dict)


class ResourceGuardEngine:
    """
    Intelligent Storage and Resource Management Subsystem.
    Guards host hardware, monitors disk space, creates isolated workspaces,
    and enforces safe cleanup policies without deleting company deliverables.
    """

    PROTECTED_DIRECTORIES = {
        "/root/roboassistant/storage",
        "/root/roboassistant/storage/evidence",
        "/root/roboassistant/storage/database",
        "/root/roboassistant/core",
        "/root/roboassistant/web",
        "/root/roboassistant/tests",
        "/root/roboassistant/docs",
        "/etc",
        "/root/.ssh",
    }

    PROTECTED_FILE_EXTENSIONS = {
        ".db", ".sqlite", ".sqlite3", ".jsonl", ".key", ".pem", ".env", ".bak"
    }

    _instance: Optional[ResourceGuardEngine] = None

    @classmethod
    def get_instance(
        cls,
        db_store: Optional[CoworkerDbStoreV2] = None,
        store: Optional[CoworkerDbStoreV2] = None,
        workspaces_root: str = "/tmp/zonata_workspaces",
        base_workspace_dir: Optional[str] = None
    ) -> ResourceGuardEngine:
        if cls._instance is None:
            cls._instance = cls(
                db_store=db_store,
                store=store,
                workspaces_root=base_workspace_dir or workspaces_root
            )
        return cls._instance

    def __init__(
        self,
        db_store: Optional[CoworkerDbStoreV2] = None,
        workspaces_root: str = "/tmp/zonata_workspaces",
        min_free_ram_mb: float = 512.0,
        min_free_disk_gb: float = 1.0,
        max_cpu_percent: float = 85.0,
        store: Optional[CoworkerDbStoreV2] = None,
        base_workspace_dir: Optional[str] = None
    ):
        self.db = store or db_store or CoworkerDbStoreV2.get_instance()
        self.workspaces_root = base_workspace_dir or workspaces_root
        self.min_free_ram_mb = min_free_ram_mb
        self.min_free_disk_gb = min_free_disk_gb
        self.max_cpu_percent = max_cpu_percent
        os.makedirs(self.workspaces_root, exist_ok=True)

    def is_path_protected(self, target_path: str) -> bool:
        return self.is_protected_path(target_path)

    def assert_path_unprotected(self, target_path: str) -> None:
        if self.is_protected_path(target_path):
            raise PermissionError(f"Target path is sovereign protected asset: {target_path}")

    def check_storage_and_memory(self) -> Dict[str, Any]:
        m = self.check_host_resources()
        return {
            "sufficient": (m.ram_healthy and m.disk_healthy),
            "disk_free_gb": m.free_disk_gb,
            "ram_free_mb": m.free_ram_mb,
            "cpu_percent": m.cpu_percent,
            "healthy": m.all_healthy
        }

    def provision_task_workspace(self, task_id: str, mission_id: Optional[str] = None) -> Dict[str, Any]:
        msn_id = mission_id or f"msn_{uuid.uuid4().hex[:6]}"
        ws_dir = self.provision_mission_workspace(msn_id, task_id)
        return {"workspace_dir": ws_dir, "mission_id": msn_id, "task_id": task_id}

    def register_cleanup_resource(
        self,
        task_id: str,
        resource_type: CleanupResourceType,
        resource_path: str,
        mission_id: Optional[str] = None
    ) -> CleanupManifestRecord:
        rec = CleanupManifestRecord(
            manifest_id=f"man_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            mission_id=mission_id or f"msn_{uuid.uuid4().hex[:6]}",
            resource_type=resource_type,
            resource_path=resource_path,
            status=CleanupStatus.PENDING
        )
        self.db.add_cleanup_record(rec)
        return rec

    def execute_task_cleanup(self, task_id: str) -> Dict[str, Any]:
        records = self.db.list_pending_cleanups(task_id=task_id)
        cleaned = 0
        for r in records:
            ok, _ = self.safe_reclaim_resource(r)
            if ok:
                cleaned += 1
        return {"cleaned_count": cleaned}

    def check_host_resources(self) -> HostResourceMetrics:
        """
        Reads system resource stats using POSIX primitives (/proc or os.statvfs).
        Zero external dependencies (Ponytail native standard library).
        """
        free_ram_mb = 1024.0
        cpu_percent = 10.0

        # Read memory from /proc/meminfo if available (Linux)
        if os.path.exists("/proc/meminfo"):
            try:
                meminfo = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            meminfo[parts[0].strip()] = parts[1].strip()
                mem_avail_kb = int(meminfo.get("MemAvailable", "1048576 kB").split()[0])
                free_ram_mb = mem_avail_kb / 1024.0
            except Exception:
                pass

        # Read disk space via os.statvfs
        try:
            stat = os.statvfs(self.workspaces_root)
            free_disk_bytes = stat.f_bavail * stat.f_frsize
            free_disk_gb = free_disk_bytes / (1024.0 ** 3)
        except Exception:
            free_disk_gb = 10.0

        # Read 1-min load average to estimate CPU usage
        try:
            load1, _, _ = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            cpu_percent = min(100.0, (load1 / cpu_count) * 100.0)
        except Exception:
            cpu_percent = 15.0

        cpu_ok = cpu_percent < self.max_cpu_percent
        ram_ok = free_ram_mb >= self.min_free_ram_mb
        disk_ok = free_disk_gb >= self.min_free_disk_gb

        return HostResourceMetrics(
            cpu_percent=round(cpu_percent, 2),
            free_ram_mb=round(free_ram_mb, 2),
            free_disk_gb=round(free_disk_gb, 2),
            cpu_healthy=cpu_ok,
            ram_healthy=ram_ok,
            disk_healthy=disk_ok,
            all_healthy=(cpu_ok and ram_ok and disk_ok),
            details={
                "max_cpu_threshold": self.max_cpu_percent,
                "min_ram_threshold_mb": self.min_free_ram_mb,
                "min_disk_threshold_gb": self.min_free_disk_gb,
            }
        )

    def provision_mission_workspace(self, mission_id: str, task_id: str) -> str:
        """
        Creates an isolated temporary workspace directory for a task.
        Registers the workspace in the cleanup manifest.
        """
        metrics = self.check_host_resources()
        if not (metrics.disk_healthy and metrics.ram_healthy):
            raise RuntimeError(
                f"Insufficient host resources for new workspace: "
                f"RAM={metrics.free_ram_mb}MB (min {self.min_free_ram_mb}MB), "
                f"Disk={metrics.free_disk_gb}GB (min {self.min_free_disk_gb}GB)"
            )

        ws_path = os.path.join(self.workspaces_root, mission_id, task_id)
        os.makedirs(ws_path, exist_ok=True)

        # Register cleanup manifest record
        rec = CleanupManifestRecord(
            manifest_id=f"man_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            mission_id=mission_id,
            resource_type=CleanupResourceType.DIRECTORY,
            resource_path=ws_path,
            status=CleanupStatus.PENDING
        )
        self.db.add_cleanup_record(rec)
        return ws_path

    def is_protected_path(self, target_path: str) -> bool:
        """
        Asserts whether a file or directory is protected from deletion.
        """
        norm = os.path.abspath(target_path)

        # Check protected directory trees
        for p_dir in self.PROTECTED_DIRECTORIES:
            norm_p = os.path.abspath(p_dir)
            if norm == norm_p or norm.startswith(norm_p + os.sep):
                return True

        # Check sensitive extensions
        ext = os.path.splitext(norm)[1].lower()
        if ext in self.PROTECTED_FILE_EXTENSIONS:
            return True

        # Check root workspace safety
        if norm in ("/", "/root", "/root/roboassistant", "/tmp"):
            return True

        # Check repository source files (e.g. api_server.py, README.md)
        if norm.startswith("/root/roboassistant") and not norm.startswith("/tmp"):
            return True

        return False

    def safe_reclaim_resource(self, record: CleanupManifestRecord) -> Tuple[bool, Optional[str]]:
        """
        Safely deletes or terminates a registered temporary resource.
        Refuses to delete protected files, company databases, or parent codebases.
        """
        target = record.resource_path
        if self.is_protected_path(target):
            err = f"BLOCKED: Attempted cleanup of sovereign protected asset: {target}"
            self.db.mark_cleaned(record.manifest_id, success=False, error=err)
            return False, err

        try:
            if record.resource_type in (CleanupResourceType.DIRECTORY, CleanupResourceType.VENV):
                if os.path.exists(target) and os.path.isdir(target):
                    shutil.rmtree(target, ignore_errors=True)
            elif record.resource_type == CleanupResourceType.TEMP_FILE:
                if os.path.exists(target) and os.path.isfile(target):
                    os.remove(target)
            elif record.resource_type == CleanupResourceType.PROCESS:
                pid = int(target)
                os.kill(pid, signal.SIGTERM)

            self.db.mark_cleaned(record.manifest_id, success=True)
            return True, None
        except Exception as e:
            self.db.mark_cleaned(record.manifest_id, success=False, error=str(e))
            return False, str(e)
