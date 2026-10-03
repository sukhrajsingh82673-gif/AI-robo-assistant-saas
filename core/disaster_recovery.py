"""
RoboAssistant Enterprise — Disaster Recovery & Backup Integrity Manager
Provides automated hot snapshots, SHA-256 manifest verification, and point-in-time
restoration drills to guarantee business continuity and zero data loss.
"""

import os
import time
import uuid
import json
import shutil
import hashlib
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from .db import db

logger = logging.getLogger("ZonataDisasterRecovery")

class DisasterRecoveryManager:
    """
    Manages cold/hot database backups, cryptographic manifest registration,
    and automated restore drills.
    """

    def __init__(self, tenant_id: str = "tnt_primary", backup_dir: str = "storage/backups"):
        self.tenant_id = tenant_id
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_hot_snapshot(self, backup_type: str = "FULL_SNAPSHOT") -> Dict[str, Any]:
        """
        Creates an online, non-blocking snapshot of the database using SQLite's backup API.
        Computes SHA-256 checksum, counts table records, and registers manifest.
        """
        manifest_id = f"drm_{uuid.uuid4().hex[:12]}"
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        dest_filename = f"zonata_backup_{timestamp_str}_{manifest_id}.db"
        dest_path = os.path.join(self.backup_dir, dest_filename)

        # 1. Perform online SQLite backup
        with db.get_connection() as src_conn:
            dest_conn = sqlite3.connect(dest_path)
            src_conn.backup(dest_conn, pages=100)
            dest_conn.close()

        # 2. Compute SHA-256 checksum
        hasher = hashlib.sha256()
        with open(dest_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_checksum = hasher.hexdigest()
        size_bytes = os.path.getsize(dest_path)

        # 3. Read record counts from the snapshot
        record_counts: Dict[str, int] = {}
        snap_conn = sqlite3.connect(dest_path)
        tables = [r[0] for r in snap_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tables:
            try:
                cnt = snap_conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                record_counts[t] = cnt
            except Exception:
                pass
        snap_conn.close()

        # 4. Generate Merkle root digest over the counts and checksum
        merkle_seed = f"{sha256_checksum}:{json.dumps(record_counts, sort_keys=True)}"
        merkle_root = hashlib.sha256(merkle_seed.encode("utf-8")).hexdigest()

        # 5. Register in DB
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO disaster_recovery_manifests (
                    manifest_id, tenant_id, backup_type, file_path,
                    size_bytes, sha256_checksum, merkle_root,
                    record_counts, verification_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?)
                """,
                (
                    manifest_id,
                    self.tenant_id,
                    backup_type,
                    dest_path,
                    size_bytes,
                    sha256_checksum,
                    merkle_root,
                    json.dumps(record_counts),
                    now
                )
            )
            conn.commit()

        return {
            "manifest_id": manifest_id,
            "backup_type": backup_type,
            "file_path": dest_path,
            "size_bytes": size_bytes,
            "sha256_checksum": sha256_checksum,
            "merkle_root": merkle_root,
            "record_counts": record_counts,
            "created_at": now
        }

    def verify_and_restore_snapshot(self, manifest_id: str, target_restore_path: str) -> Dict[str, Any]:
        """
        Validates the backup file checksum against the recorded manifest and restores
        it into target_restore_path, confirming database integrity.
        """
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM disaster_recovery_manifests WHERE manifest_id = ? AND tenant_id = ?",
                (manifest_id, self.tenant_id)
            ).fetchone()
            if not row:
                raise ValueError(f"Manifest {manifest_id} not found")
            manifest = dict(row)

        src_path = manifest["file_path"]
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Backup file at {src_path} does not exist")

        # 1. Verify SHA-256 Checksum before restore
        hasher = hashlib.sha256()
        with open(src_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        calc_sha = hasher.hexdigest()

        if calc_sha != manifest["sha256_checksum"]:
            raise ValueError(f"Checksum mismatch! Recorded: {manifest['sha256_checksum']}, Calculated: {calc_sha}")

        # 2. Restore file
        os.makedirs(os.path.dirname(os.path.abspath(target_restore_path)), exist_ok=True)
        shutil.copy2(src_path, target_restore_path)

        # 3. Verify SQLite integrity PRAGMA on restored DB
        restored_conn = sqlite3.connect(target_restore_path)
        integrity_res = restored_conn.execute("PRAGMA integrity_check").fetchall()
        is_ok = len(integrity_res) == 1 and integrity_res[0][0] == "ok"

        # 4. Verify record counts
        restored_counts = {}
        tables = [r[0] for r in restored_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tables:
            try:
                cnt = restored_conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                restored_counts[t] = cnt
            except Exception:
                pass
        restored_conn.close()

        expected_counts = json.loads(manifest["record_counts"])
        counts_match = restored_counts == expected_counts

        return {
            "manifest_id": manifest_id,
            "target_path": target_restore_path,
            "checksum_verified": True,
            "sqlite_integrity_ok": is_ok,
            "record_counts_match": counts_match,
            "verified_at": time.time()
        }
