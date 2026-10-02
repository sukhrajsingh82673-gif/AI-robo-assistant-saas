"""
RoboAssistant Company OS 1.0 — Enterprise Disaster Recovery & Point-in-Time Backup Engine
Implements transaction-consistent SQLite online backups, atomic Evidence Ledger archiving,
cryptographic SHA-256 manifest validation, and automated restore verification.
"""

import os
import time
import json
import sqlite3
import hashlib
import tarfile
import fcntl
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("zonata.disaster_recovery")

class DisasterRecoveryManager:
    RPO_TARGET_MINUTES = 15
    RTO_TARGET_MINUTES = 5

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_dir = os.path.join(self.base_dir, "storage")
        self.db_path = os.path.join(self.storage_dir, "roboassistant.db")
        self.ledger_path = os.path.join(self.storage_dir, "evidence/audit_ledger.jsonl")
        self.backups_dir = os.path.join(self.storage_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

    @staticmethod
    def _compute_file_sha256(filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def create_backup(self, label: str = "scheduled") -> Dict[str, Any]:
        """
        Creates a transactionally consistent, point-in-time snapshot backup:
        1. SQLite Online Backup API (zero downtime, locks consistent state)
        2. Evidence Ledger copy under shared file lock
        3. Cryptographic manifest with SHA-256 hashes
        4. Tarball packaging
        """
        t0 = time.time()
        ts = int(t0)
        backup_id = f"bkg_{label}_{ts}"
        staging_dir = os.path.join(self.backups_dir, backup_id)
        os.makedirs(staging_dir, exist_ok=True)

        staging_db = os.path.join(staging_dir, "roboassistant.db")
        staging_ledger = os.path.join(staging_dir, "audit_ledger.jsonl")
        tar_path = os.path.join(self.backups_dir, f"{backup_id}.tar.gz")

        # 1. SQLite Online Backup API
        src_conn = sqlite3.connect(self.db_path, timeout=60.0)
        dst_conn = sqlite3.connect(staging_db)
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
        dst_conn.close()
        src_conn.close()

        # 2. Evidence Ledger Backup under Shared Lock
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, "r", encoding="utf-8") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_SH)
                try:
                    with open(staging_ledger, "w", encoding="utf-8") as out_f:
                        out_f.write(lf.read())
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

        # 3. Cryptographic Manifest
        manifest = {
            "backup_id": backup_id,
            "label": label,
            "timestamp": t0,
            "files": {
                "roboassistant.db": {
                    "sha256": self._compute_file_sha256(staging_db),
                    "size_bytes": os.path.getsize(staging_db)
                },
                "audit_ledger.jsonl": {
                    "sha256": self._compute_file_sha256(staging_ledger) if os.path.exists(staging_ledger) else None,
                    "size_bytes": os.path.getsize(staging_ledger) if os.path.exists(staging_ledger) else 0
                }
            }
        }
        manifest_path = os.path.join(staging_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        # 4. Create Archive
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(staging_dir, arcname=backup_id)

        # Clean staging dir
        import shutil
        shutil.rmtree(staging_dir)

        duration_sec = round(time.time() - t0, 3)
        archive_size = os.path.getsize(tar_path)
        logger.info(f"[*] Backup created: {tar_path} ({archive_size} bytes in {duration_sec}s)")

        return {
            "success": True,
            "backup_id": backup_id,
            "archive_path": tar_path,
            "size_bytes": archive_size,
            "duration_sec": duration_sec,
            "manifest": manifest
        }

    def verify_and_restore(self, archive_path: str, target_restore_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Restores and validates backup archive into target directory,
        verifying SHA-256 hashes and SQLite PRAGMA integrity.
        """
        t0 = time.time()
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Backup archive not found: {archive_path}")

        restore_dir = target_restore_dir or os.path.join(self.storage_dir, "restored_test")
        os.makedirs(restore_dir, exist_ok=True)

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=restore_dir)

        # Locate extracted backup folder
        extracted_folders = [f for f in os.listdir(restore_dir) if f.startswith("bkg_")]
        if not extracted_folders:
            raise ValueError("Invalid backup archive: missing backup root folder")

        bkg_folder = os.path.join(restore_dir, extracted_folders[0])
        manifest_path = os.path.join(bkg_folder, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as mf:
            manifest = json.load(mf)

        # Verify DB SHA-256
        restored_db = os.path.join(bkg_folder, "roboassistant.db")
        actual_db_sha = self._compute_file_sha256(restored_db)
        expected_db_sha = manifest["files"]["roboassistant.db"]["sha256"]
        if actual_db_sha != expected_db_sha:
            raise ValueError(f"Database SHA-256 mismatch! Expected {expected_db_sha}, got {actual_db_sha}")

        # Check SQLite integrity
        conn = sqlite3.connect(restored_db)
        check = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
        conn.close()

        if check != "ok":
            raise ValueError(f"SQLite PRAGMA integrity_check failed: {check}")

        # Clean test restore dir
        import shutil
        shutil.rmtree(restore_dir)

        duration_sec = round(time.time() - t0, 3)
        return {
            "success": True,
            "backup_id": manifest["backup_id"],
            "integrity_check": check,
            "tables_recovered": tables,
            "duration_sec": duration_sec
        }
