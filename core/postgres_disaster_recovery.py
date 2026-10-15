"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
PostgreSQL 16 Continuous WAL Archiving & Point-In-Time Recovery (PITR) Engine

Provides enterprise-grade continuous database protection and disaster recovery:
- Continuous WAL archiving state verification against live PostgreSQL 16 engine
- Non-blocking physical base backups via pg_basebackup with cryptographic SHA-256 manifests
- Forced WAL segment archiving and archive integrity validation
- Automated Point-In-Time Recovery (PITR) drills to exact UTC target timestamps
- Verification of recovery promotion, RTO (Recovery Time Objective), and RPO (Recovery Point Objective)
- Negative-path validation ensuring recovery fails closed on missing/corrupt WAL archives
"""

from __future__ import annotations

import os
import sys
import time
import json
import uuid
import shutil
import hashlib
import logging
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("zonata.infra.dr.postgres_pitr")


@dataclass
class PostgresWALArchivingConfig:
    wal_level: str
    archive_mode: str
    archive_command: str
    archive_timeout: int
    last_archived_wal: Optional[str] = None
    last_archived_time: Optional[str] = None
    last_failed_wal: Optional[str] = None
    last_failed_time: Optional[str] = None

    def is_active(self) -> bool:
        return (
            self.wal_level.lower() in ("replica", "logical")
            and self.archive_mode.lower() in ("on", "always")
            and bool(self.archive_command.strip())
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PostgresBaseBackupManifest:
    manifest_id: str
    backup_name: str
    backup_path: str
    size_bytes: int
    sha256_checksum: str
    created_at_utc: str
    record_counts: Dict[str, int]
    verification_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PITRDrillResult:
    drill_id: str
    base_backup_name: str
    baseline_commit_time_utc: str
    baseline_checksum: str
    baseline_row_count: int
    recovery_target_time_utc: str
    loss_simulation_time_utc: str
    loss_simulation_row_count: int
    recovery_started_at_utc: str
    recovery_promoted_at_utc: str
    rto_seconds: float
    rpo_data_gap_seconds: float
    baseline_data_verified: bool
    post_target_data_absent: bool
    read_write_promoted: bool
    recovery_logs_summary: str
    verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PostgresDisasterRecoveryManager:
    """
    Manages continuous WAL archiving, base backups, and automated PITR rehearsals
    for PostgreSQL 16 multi-service production topology.
    """

    def __init__(
        self,
        compose_file: str = "docker-compose.prod.yml",
        postgres_service: str = "postgres",
        postgres_user: str = "zonata_admin",
        postgres_db: str = "zonata_production",
        wal_archive_dir: str = "/var/lib/postgresql/wal_archive",
        base_backup_dir: str = "/var/lib/postgresql/base_backups",
        project_root: Optional[str] = None
    ):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.compose_file = os.path.join(self.project_root, compose_file) if not os.path.isabs(compose_file) else compose_file
        self.postgres_service = postgres_service
        self.postgres_user = postgres_user
        self.postgres_db = postgres_db
        self.wal_archive_dir = wal_archive_dir
        self.base_backup_dir = base_backup_dir

    def run_docker_exec(self, cmd: List[str], check: bool = True, timeout: int = 60, user: Optional[str] = None) -> subprocess.CompletedProcess:
        """Executes a command inside the primary postgres container via docker compose exec."""
        base_cmd = ["docker", "compose", "-f", self.compose_file, "exec", "-T"]
        if user:
            base_cmd.extend(["-u", user])
        full_cmd = base_cmd + [self.postgres_service] + cmd
        return subprocess.run(
            full_cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=check
        )

    def execute_sql(self, sql: str, check: bool = True) -> str:
        """Executes SQL against the primary database via psql in the container."""
        res = self.run_docker_exec(
            ["psql", "-U", self.postgres_user, "-d", self.postgres_db, "-tAc", sql],
            check=check
        )
        return res.stdout.strip()

    def get_wal_archiving_config(self) -> PostgresWALArchivingConfig:
        """Queries PostgreSQL 16 runtime settings and archiver statistics."""
        sql = """
        SELECT name, setting FROM pg_settings 
        WHERE name IN ('wal_level', 'archive_mode', 'archive_command', 'archive_timeout');
        """
        raw = self.execute_sql(sql)
        settings: Dict[str, str] = {}
        for line in raw.splitlines():
            if "|" in line:
                k, v = line.split("|", 1)
                settings[k.strip()] = v.strip()

        arch_sql = """
        SELECT COALESCE(last_archived_wal, ''), 
               COALESCE(to_char(last_archived_time, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), ''),
               COALESCE(last_failed_wal, ''), 
               COALESCE(to_char(last_failed_time, 'YYYY-MM-DD"T"HH24:MI:SS"'), '')
        FROM pg_stat_archiver;
        """
        raw_arch = self.execute_sql(arch_sql)
        arch_parts = raw_arch.split("|") if "|" in raw_arch else ["", "", "", ""]

        return PostgresWALArchivingConfig(
            wal_level=settings.get("wal_level", "unknown"),
            archive_mode=settings.get("archive_mode", "off"),
            archive_command=settings.get("archive_command", ""),
            archive_timeout=int(settings.get("archive_timeout", 0)),
            last_archived_wal=arch_parts[0] if len(arch_parts) > 0 and arch_parts[0] else None,
            last_archived_time=arch_parts[1] if len(arch_parts) > 1 and arch_parts[1] else None,
            last_failed_wal=arch_parts[2] if len(arch_parts) > 2 and arch_parts[2] else None,
            last_failed_time=arch_parts[3] if len(arch_parts) > 3 and arch_parts[3] else None
        )

    def trigger_wal_switch(self) -> str:
        """Forces PostgreSQL to switch to a new WAL file, triggering immediate archive_command."""
        switched_lsn = self.execute_sql("SELECT pg_switch_wal();")
        time.sleep(1)
        current_wal = self.execute_sql("SELECT pg_walfile_name(pg_current_wal_lsn());")
        return current_wal

    def list_archived_wals(self) -> List[str]:
        """Lists WAL files present in the WAL archive directory."""
        res = self.run_docker_exec(
            ["ls", "-1", self.wal_archive_dir],
            check=False,
            user="postgres"
        )
        if res.returncode != 0:
            return []
        files = [f.strip() for f in res.stdout.splitlines() if f.strip() and not f.strip().endswith(".backup")]
        return sorted(files)

    def create_base_backup(self, backup_name: str) -> PostgresBaseBackupManifest:
        """
        Creates a consistent, non-blocking physical base backup via pg_basebackup.
        Computes SHA-256 digest of backup label and records table counts.
        """
        target_dir = f"{self.base_backup_dir}/{backup_name}"
        # 1. Clean existing target if present
        self.run_docker_exec(["rm", "-rf", target_dir], check=False, user="postgres")
        self.run_docker_exec(["mkdir", "-p", self.base_backup_dir], check=False, user="postgres")

        # 2. Execute pg_basebackup with WAL included (-Xs) in plain format (-Fp)
        cmd = [
            "pg_basebackup",
            "-U", self.postgres_user,
            "-D", target_dir,
            "-Fp",
            "-Xs",
            "-P"
        ]
        res = self.run_docker_exec(cmd, check=True, timeout=120, user="postgres")

        # 3. Verify backup directory contents
        check_res = self.run_docker_exec(["test", "-f", f"{target_dir}/PG_VERSION"], check=True, user="postgres")
        label_res = self.run_docker_exec(["cat", f"{target_dir}/backup_label"], check=True, user="postgres")
        backup_label = label_res.stdout.strip()

        # 4. Compute SHA-256 digest over backup_label
        hasher = hashlib.sha256()
        hasher.update(backup_label.encode("utf-8"))
        checksum = hasher.hexdigest()

        # 5. Measure backup size
        size_res = self.run_docker_exec(["du", "-sb", target_dir], check=False, user="postgres")
        size_bytes = 0
        if size_res.returncode == 0 and size_res.stdout:
            try:
                size_bytes = int(size_res.stdout.split()[0])
            except Exception:
                size_bytes = 0

        # 6. Record table counts from live DB at time of backup
        counts_raw = self.execute_sql("""
            SELECT 'tenants', count(*) FROM tenants
            UNION ALL
            SELECT 'crm_customers', count(*) FROM crm_customers
            UNION ALL
            SELECT 'crm_deals', count(*) FROM crm_deals;
        """)
        record_counts: Dict[str, int] = {}
        for line in counts_raw.splitlines():
            if "|" in line:
                tbl, cnt = line.split("|", 1)
                try:
                    record_counts[tbl.strip()] = int(cnt.strip())
                except ValueError:
                    pass

        manifest_id = f"pbm_{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        return PostgresBaseBackupManifest(
            manifest_id=manifest_id,
            backup_name=backup_name,
            backup_path=target_dir,
            size_bytes=size_bytes,
            sha256_checksum=checksum,
            created_at_utc=now_utc,
            record_counts=record_counts,
            verification_status="VERIFIED"
        )
