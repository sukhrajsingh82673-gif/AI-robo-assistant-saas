"""
ZONATA Autonomous Coworker — Resource Manifests & File Ownership

Implements the Coworker 2.0 spec §7 records that were previously missing:

  - Download manifest   : URL, local path, size, SHA-256, when, by whom.
  - Installation manifest: package, version, interpreter, venv, smoke result.
  - File ownership      : which task created a path, so cleanup can refuse to
                          delete something it does not own.

Everything is written to SQLite. Nothing here deletes files; the store only
answers questions that the cleanup path asks.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


def _sha256_file(path: str, chunk: int = 1 << 20) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(chunk), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


@dataclass
class DownloadManifest:
    manifest_id: str
    url: str
    target_path: str
    byte_count: int
    sha256: str
    tenant_id: str
    task_id: Optional[str] = None
    mission_id: Optional[str] = None
    content_type: Optional[str] = None
    requested_by: str = "coworker"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "url": self.url,
            "target_path": self.target_path,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "content_type": self.content_type,
            "requested_by": self.requested_by,
            "timestamp": self.timestamp,
        }


@dataclass
class InstallationManifest:
    manifest_id: str
    package: str
    version: str
    interpreter: str
    venv_path: str
    tenant_id: str
    source: str = "pypi"
    task_id: Optional[str] = None
    mission_id: Optional[str] = None
    smoke_test_passed: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "package": self.package,
            "version": self.version,
            "interpreter": self.interpreter,
            "venv_path": self.venv_path,
            "tenant_id": self.tenant_id,
            "source": self.source,
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "smoke_test_passed": self.smoke_test_passed,
            "timestamp": self.timestamp,
        }


class ResourceManifestStore:
    """SQLite-backed download / installation / ownership records."""

    def __init__(self, db_path: Optional[str] = None, tenant_id: str = "tnt_primary"):
        self.db_path = db_path or os.environ.get(
            "ZONATA_MANIFEST_DB", os.path.join(tempfile.gettempdir(), "zonata_manifests.db")
        )
        self.tenant_id = tenant_id
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_manifests (
                    manifest_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    byte_count INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    task_id TEXT,
                    mission_id TEXT,
                    content_type TEXT,
                    requested_by TEXT,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS installation_manifests (
                    manifest_id TEXT PRIMARY KEY,
                    package TEXT NOT NULL,
                    version TEXT NOT NULL,
                    interpreter TEXT NOT NULL,
                    venv_path TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    source TEXT,
                    task_id TEXT,
                    mission_id TEXT,
                    smoke_test_passed INTEGER NOT NULL DEFAULT 0,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_ownership (
                    path TEXT PRIMARY KEY,
                    owner_task_id TEXT NOT NULL,
                    mission_id TEXT,
                    manifest_id TEXT,
                    kind TEXT NOT NULL,
                    sha256 TEXT,
                    tenant_id TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    # --- Download manifests ---------------------------------------------------

    def record_download(
        self,
        url: str,
        target_path: str,
        content_type: Optional[str] = None,
        task_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        requested_by: str = "coworker",
    ) -> DownloadManifest:
        """Records a completed download by hashing the bytes actually on disk."""
        sha = _sha256_file(target_path) or ""
        size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
        manifest = DownloadManifest(
            manifest_id=f"dl_{uuid.uuid4().hex[:10]}",
            url=url,
            target_path=os.path.abspath(target_path),
            byte_count=size,
            sha256=sha,
            tenant_id=self.tenant_id,
            task_id=task_id,
            mission_id=mission_id,
            content_type=content_type,
            requested_by=requested_by,
        )
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO download_manifests VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    manifest.manifest_id, manifest.url, manifest.target_path,
                    manifest.byte_count, manifest.sha256, manifest.tenant_id,
                    manifest.task_id, manifest.mission_id, manifest.content_type,
                    manifest.requested_by, manifest.timestamp,
                ),
            )
            conn.commit()
        return manifest

    def get_downloads(self, task_id: Optional[str] = None) -> list:
        q = "SELECT * FROM download_manifests"
        params: tuple = ()
        if task_id:
            q += " WHERE task_id = ?"
            params = (task_id,)
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(q + " ORDER BY timestamp DESC", params)]

    def verify_download(self, manifest_id: str) -> Tuple[bool, str]:
        """Re-hashes the file on disk and compares it with the recorded digest."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM download_manifests WHERE manifest_id = ?", (manifest_id,)
            ).fetchone()
        if not row:
            return False, "MANIFEST_NOT_FOUND"
        if not os.path.exists(row["target_path"]):
            return False, "FILE_MISSING"
        current = _sha256_file(row["target_path"])
        if current != row["sha256"]:
            return False, f"DIGEST_MISMATCH: expected {row['sha256']}, found {current}"
        return True, "DIGEST_MATCH"

    # --- Installation manifests ----------------------------------------------

    def record_installation(
        self,
        package: str,
        version: str,
        interpreter: str,
        venv_path: str,
        source: str = "pypi",
        task_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        smoke_test_passed: bool = False,
    ) -> InstallationManifest:
        manifest = InstallationManifest(
            manifest_id=f"in_{uuid.uuid4().hex[:10]}",
            package=package,
            version=version,
            interpreter=interpreter,
            venv_path=os.path.abspath(venv_path),
            tenant_id=self.tenant_id,
            source=source,
            task_id=task_id,
            mission_id=mission_id,
            smoke_test_passed=smoke_test_passed,
        )
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO installation_manifests VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    manifest.manifest_id, manifest.package, manifest.version,
                    manifest.interpreter, manifest.venv_path, manifest.tenant_id,
                    manifest.source, manifest.task_id, manifest.mission_id,
                    1 if manifest.smoke_test_passed else 0, manifest.timestamp,
                ),
            )
            conn.commit()
        return manifest

    def get_installations(self, mission_id: Optional[str] = None) -> list:
        q = "SELECT * FROM installation_manifests"
        params: tuple = ()
        if mission_id:
            q += " WHERE mission_id = ?"
            params = (mission_id,)
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(q + " ORDER BY timestamp DESC", params)]

    # --- File ownership -------------------------------------------------------

    def register_ownership(
        self,
        path: str,
        owner_task_id: str,
        mission_id: Optional[str] = None,
        manifest_id: Optional[str] = None,
        kind: str = "DIRECTORY",
    ) -> Dict[str, Any]:
        ap = os.path.abspath(path)
        sha = _sha256_file(ap) if os.path.isfile(ap) else None
        with self._connect() as conn:
            # Portable upsert: UPDATE-then-INSERT works on both SQLite and
            # PostgreSQL, unlike SQLite's INSERT OR REPLACE.
            updated = conn.execute(
                """UPDATE file_ownership
                   SET owner_task_id = ?, mission_id = ?, manifest_id = ?,
                       kind = ?, sha256 = ?, tenant_id = ?, created_at = ?
                   WHERE path = ?""",
                (owner_task_id, mission_id, manifest_id, kind, sha,
                 self.tenant_id, time.time(), ap),
            )
            if updated.rowcount == 0:
                conn.execute(
                    """INSERT INTO file_ownership
                       (path, owner_task_id, mission_id, manifest_id, kind, sha256, tenant_id, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (ap, owner_task_id, mission_id, manifest_id, kind, sha,
                     self.tenant_id, time.time()),
                )
            conn.commit()
        return {
            "path": ap,
            "owner_task_id": owner_task_id,
            "mission_id": mission_id,
            "manifest_id": manifest_id,
            "kind": kind,
            "sha256": sha,
        }

    def get_owner(self, path: str) -> Optional[Dict[str, Any]]:
        ap = os.path.abspath(path)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM file_ownership WHERE path = ?", (ap,)
            ).fetchone()
            if row:
                return dict(row)
            # A path inside a registered directory is owned by that directory's task.
            rows = conn.execute(
                "SELECT * FROM file_ownership WHERE kind = 'DIRECTORY'"
            ).fetchall()
        for r in rows:
            root = r["path"].rstrip(os.sep) + os.sep
            if ap.startswith(root):
                return dict(r)
        return None

    def can_reclaim(self, path: str, requester_task_id: Optional[str]) -> Tuple[bool, str]:
        """
        Ownership gate for cleanup.

        - Unknown path  -> refused. §7 forbids deleting unknown files.
        - Owned by the requester -> allowed.
        - Owned by a different task -> refused.
        """
        owner = self.get_owner(path)
        if owner is None:
            return False, "NO_OWNERSHIP_RECORD"
        if not requester_task_id:
            return False, "REQUESTER_TASK_ID_REQUIRED"
        if owner["owner_task_id"] != requester_task_id:
            return False, f"OWNED_BY_ANOTHER_TASK: {owner['owner_task_id']}"
        return True, "OWNED_BY_REQUESTER"
