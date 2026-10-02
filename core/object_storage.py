"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Object Storage & Artifact Lifecycle Manager
Provides S3-compatible blob storage abstraction, tenant isolation prefixes,
SHA-256 checksum integrity, and strict legal-hold retention governance.
"""

import os
import time
import json
import hashlib
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("zonata.storage.objects")

class ArtifactLifecycleState:
    TEMPORARY = "TEMPORARY"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    LEGAL_HOLD = "LEGAL_HOLD"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"

@dataclass
class ArtifactReference:
    artifact_id: str
    tenant_id: str
    filename: str
    storage_path: str
    sha256_hash: str
    size_bytes: int
    lifecycle_state: str
    retention_until: Optional[float]
    legal_hold: bool
    created_at: float
    metadata: Dict[str, Any]

class ObjectStorageService:
    """
    Production-grade object storage manager with S3-compatible path partitioning:
    {storage_root}/{tenant_id}/{lifecycle_state}/{sha256[:2]}/{sha256}_{filename}
    """
    def __init__(self, storage_root: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_root = storage_root or os.path.join(base_dir, "storage/object_store")
        os.makedirs(self.storage_root, exist_ok=True)
        self._registry_file = os.path.join(self.storage_root, "artifact_manifest.jsonl")
        self._lock = threading.RLock()

    def store_artifact(
        self,
        tenant_id: str,
        filename: str,
        data: bytes,
        lifecycle_state: str = ArtifactLifecycleState.ACTIVE,
        retention_days: int = 90,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ArtifactReference:
        """
        Store binary artifact with cryptographic checksum, tenant isolation, and lifecycle tagging.
        """
        sha256_hash = hashlib.sha256(data).hexdigest()
        now = time.time()
        retention_until = now + (retention_days * 86400.0) if retention_days > 0 else None

        # Build tenant-partitioned physical path
        prefix_dir = os.path.join(self.storage_root, tenant_id, lifecycle_state, sha256_hash[:2])
        os.makedirs(prefix_dir, exist_ok=True)
        file_path = os.path.join(prefix_dir, f"{sha256_hash}_{filename}")

        with open(file_path, "wb") as f:
            f.write(data)

        artifact_id = f"art_{sha256_hash[:16]}"
        ref = ArtifactReference(
            artifact_id=artifact_id,
            tenant_id=tenant_id,
            filename=filename,
            storage_path=file_path,
            sha256_hash=sha256_hash,
            size_bytes=len(data),
            lifecycle_state=lifecycle_state,
            retention_until=retention_until,
            legal_hold=(lifecycle_state == ArtifactLifecycleState.LEGAL_HOLD),
            created_at=now,
            metadata=metadata or {}
        )

        with self._lock:
            with open(self._registry_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(ref)) + "\n")

        return ref

    def retrieve_artifact(self, storage_path: str, expected_hash: Optional[str] = None) -> bytes:
        """Retrieve artifact bytes and verify cryptographic integrity."""
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"Artifact not found at {storage_path}")

        with open(storage_path, "rb") as f:
            data = f.read()

        if expected_hash:
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected_hash:
                raise ValueError(f"Artifact integrity compromised! Expected {expected_hash}, got {actual}")

        return data

    def prune_expired_artifacts(self) -> int:
        """
        Prune expired temporary artifacts while strictly preserving ACTIVE, ARCHIVED, and LEGAL_HOLD artifacts.
        """
        now = time.time()
        pruned_count = 0
        if not os.path.exists(self._registry_file):
            return 0

        kept_records = []
        with self._lock:
            with open(self._registry_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        is_legal_hold = record.get("legal_hold", False)
                        state = record.get("lifecycle_state")
                        retention = record.get("retention_until")
                        path = record.get("storage_path")

                        # Invariant: Never delete items under legal hold or archived
                        if is_legal_hold or state in (ArtifactLifecycleState.LEGAL_HOLD, ArtifactLifecycleState.ARCHIVED):
                            kept_records.append(record)
                            continue

                        # Check expiration
                        if retention and now > retention and state == ArtifactLifecycleState.TEMPORARY:
                            if os.path.exists(path):
                                try:
                                    os.remove(path)
                                    pruned_count += 1
                                except Exception:
                                    pass
                            record["lifecycle_state"] = ArtifactLifecycleState.DELETED
                            kept_records.append(record)
                        else:
                            kept_records.append(record)
                    except Exception:
                        pass

            # Rewrite updated manifest
            with open(self._registry_file, "w", encoding="utf-8") as f:
                for r in kept_records:
                    f.write(json.dumps(r) + "\n")

        return pruned_count

# Global object storage instance
object_store = ObjectStorageService()
