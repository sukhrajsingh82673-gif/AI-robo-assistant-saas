"""ZONATA Sovereign Core — Document Versioning & Integrity Verification.

Implements OpenCode Step 1E:
- Immutable document versions (document_versions).
- Content-addressed blobs deduplicated per tenant.
- Verify-on-read option comparing payload hash with blob record.
- Scheduled integrity sweep checking all stored blobs for corruption or bit rot.
"""

from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.db import db, tenant_scoped
from core.evidence_ledger import EvidenceLedger
from core.documents.errors import EncryptionUnavailableError
from core.documents.evidence import seal_document_event
from core.ports.base import PortStatus
from core.ports.kms import resolve_kms_provider
from core.ports.storage import resolve_storage_provider
from core.documents.schema import VersionStatus


class BlobCorruptionError(Exception):
    """Raised when blob SHA-256 does not match stored bytes."""
    pass


@tenant_scoped
def create_document_version(
    document_id: str,
    new_payload: bytes,
    author_id: str,
    change_reason: str,
    ledger: Optional[EvidenceLedger] = None,
    tenant_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Tuple[str, str]:
    """Creates a new immutable version of a document without modifying previous versions.

    Returns (version_id, blob_id).
    """
    ledger = ledger or EvidenceLedger()
    sha256_hash = hashlib.sha256(new_payload).hexdigest()
    byte_size = len(new_payload)
    now = time.time()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT tenant_id, company_id, name FROM documents WHERE id = ?", (document_id,))
        doc_row = cur.fetchone()
        if not doc_row:
            raise ValueError(f"Document {document_id} not found")
        doc_tenant_id, doc_company_id, doc_name = doc_row[0], doc_row[1], doc_row[2]
        if tenant_id is not None and doc_tenant_id != tenant_id:
            raise ValueError(f"Document {document_id} does not belong to tenant {tenant_id}")
        if company_id is not None and doc_company_id != company_id:
            raise ValueError(f"Document {document_id} does not belong to company {company_id}")
        tenant_id, company_id = doc_tenant_id, doc_company_id

        cur.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM document_versions WHERE document_id = ?",
            (document_id,)
        )
        current_max_ver = cur.fetchone()[0]
        next_ver = current_max_ver + 1

        # Check deduplication for blob (scoped to tenant + company)
        cur.execute(
            "SELECT id FROM blobs WHERE tenant_id = ? AND company_id = ? AND sha256 = ?",
            (tenant_id, company_id, sha256_hash)
        )
        blob_row = cur.fetchone()
        if blob_row:
            blob_id = blob_row[0]
            conn.execute("UPDATE blobs SET ref_count = ref_count + 1 WHERE id = ?", (blob_id,))
        else:
            # Store new blob
            blob_id = f"blb_{uuid.uuid4().hex[:16]}"
            kms_port = resolve_kms_provider()
            storage_port = resolve_storage_provider()
            key_context = {"tenant_id": tenant_id, "company_id": company_id, "sha256": sha256_hash}
            kms_res, ciphertext = kms_port.encrypt(new_payload, context=key_context)
            if kms_res.status not in (PortStatus.OK, PortStatus.SANDBOX, PortStatus.DEGRADED):
                raise EncryptionUnavailableError(
                    f"KMS port returned {kms_res.status.value}; refusing to store plaintext as encrypted content"
                )

            storage_path = f"tenants/{tenant_id}/blobs/{sha256_hash[:2]}/{sha256_hash}"
            bucket = os.environ.get("S3_BUCKET", "zonata-documents")
            st_res = storage_port.put(bucket, storage_path, ciphertext)
            if st_res.status not in (PortStatus.OK, PortStatus.ACCEPTED_BY_PROVIDER, PortStatus.SANDBOX):
                raise RuntimeError(f"StoragePort.put failed: {st_res.error}")

            conn.execute(
                """
                INSERT INTO blobs (
                    id, tenant_id, company_id, sha256, byte_size,
                    mime_type, storage_path, storage_provider, encrypted,
                    dek_wrapped, encryption_iv, ref_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, NULL, 1, ?)
                """,
                (
                    blob_id, tenant_id, company_id, sha256_hash, byte_size,
                    "application/octet-stream", storage_path, st_res.provider,
                    kms_res.provider_ref or "local_envelope_dek", now
                )
            )

        # Mark previous active version as SUPERSEDED
        conn.execute(
            "UPDATE document_versions SET status = ? WHERE document_id = ? AND status = ?",
            (VersionStatus.SUPERSEDED.value, document_id, VersionStatus.ACTIVE.value)
        )

        version_id = f"ver_{uuid.uuid4().hex[:16]}"
        conn.execute(
            """
            INSERT INTO document_versions (
                id, document_id, version_number, blob_id,
                author_id, change_reason, status, evidence_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id, document_id, next_ver, blob_id,
                author_id, change_reason, VersionStatus.ACTIVE.value, None, now
            )
        )
        conn.execute(
            "UPDATE documents SET current_version_id = ?, updated_at = ? WHERE id = ?",
            (version_id, now, document_id)
        )

    # Record evidence
    seal_document_event(
        ledger=ledger,
        event_type="DOCUMENT_VERSION_CREATED",
        actor_id=author_id,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={
            "document_id": document_id,
            "version_number": next_ver,
            "version_id": version_id,
            "blob_id": blob_id,
            "sha256": sha256_hash,
            "change_reason": change_reason,
        }
    )

    return version_id, blob_id


@tenant_scoped
def get_document_version_payload(
    document_id: str,
    version_number: Optional[int] = None,
    verify_on_read: bool = True,
    tenant_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], bytes]:
    """Retrieves document version record and decrypted payload bytes.

    Optionally verifies payload integrity against blob's recorded SHA-256.
    """
    with db.get_connection() as conn:
        cur = conn.cursor()
        if version_number is not None:
            cur.execute(
                """
                SELECT v.id, v.version_number, v.blob_id, v.author_id, v.status,
                       b.sha256, b.byte_size, b.mime_type, b.storage_path, b.tenant_id, b.company_id
                FROM document_versions v
                JOIN blobs b ON v.blob_id = b.id
                WHERE v.document_id = ? AND v.version_number = ?
                """,
                (document_id, version_number)
            )
        else:
            cur.execute(
                """
                SELECT v.id, v.version_number, v.blob_id, v.author_id, v.status,
                       b.sha256, b.byte_size, b.mime_type, b.storage_path, b.tenant_id, b.company_id
                FROM documents d
                JOIN document_versions v ON d.current_version_id = v.id
                JOIN blobs b ON v.blob_id = b.id
                WHERE d.id = ?
                """,
                (document_id,)
            )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Version not found for document {document_id}")

    meta = {
        "version_id": row[0],
        "version_number": row[1],
        "blob_id": row[2],
        "author_id": row[3],
        "status": row[4],
        "sha256": row[5],
        "byte_size": row[6],
        "mime_type": row[7],
        "storage_path": row[8],
        "tenant_id": row[9],
        "company_id": row[10],
    }

    if tenant_id is not None and meta["tenant_id"] != tenant_id:
        raise ValueError(f"Document {document_id} does not belong to tenant {tenant_id}")
    if company_id is not None and meta["company_id"] != company_id:
        raise ValueError(f"Document {document_id} does not belong to company {company_id}")

    storage_port = resolve_storage_provider()
    bucket = os.environ.get("S3_BUCKET", "zonata-documents")
    st_res, ciphertext = storage_port.get(bucket, meta["storage_path"])
    if st_res.status not in (PortStatus.OK, PortStatus.SANDBOX):
        raise RuntimeError(f"StoragePort.get failed: {st_res.error}")

    kms_port = resolve_kms_provider()
    key_context = {
        "tenant_id": meta["tenant_id"],
        "company_id": meta["company_id"],
        "sha256": meta["sha256"],
    }
    kms_res, plaintext = kms_port.decrypt(ciphertext, context=key_context)
    if kms_res.status not in (PortStatus.OK, PortStatus.SANDBOX, PortStatus.DEGRADED):
        if verify_on_read and kms_res.status == PortStatus.FAILED:
            raise BlobCorruptionError(
                f"Integrity check failed on read for blob {meta['blob_id']}: ciphertext corrupted or tampered ({kms_res.error})"
            )
        raise EncryptionUnavailableError(
            f"KMS port returned {kms_res.status.value}; refusing to treat ciphertext as plaintext"
        )

    if verify_on_read:
        computed_sha = hashlib.sha256(plaintext).hexdigest()
        if computed_sha != meta["sha256"]:
            raise BlobCorruptionError(
                f"Integrity check failed on read for blob {meta['blob_id']}: expected {meta['sha256']}, got {computed_sha}"
            )

    return meta, plaintext


@tenant_scoped
def run_integrity_sweep(
    tenant_id: str,
    ledger: Optional[EvidenceLedger] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Sweeps all blobs for a tenant, validating cryptographic SHA-256 integrity against storage.

    Reports bit rot / corruption incidents and logs tamper records in evidence ledger.
    """
    ledger = ledger or EvidenceLedger()
    storage_port = resolve_storage_provider()
    kms_port = resolve_kms_provider()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sha256, byte_size, storage_path, company_id
            FROM blobs
            WHERE tenant_id = ?
            """,
            (tenant_id,)
        )
        blobs = cur.fetchall()

    checked = 0
    corrupted: List[Dict[str, Any]] = []

    for b in blobs:
        blob_id, expected_sha, byte_size, storage_path, company_id = b[0], b[1], b[2], b[3], b[4]
        checked += 1
        try:
            bucket = os.environ.get("S3_BUCKET", "zonata-documents")
            st_res, ciphertext = storage_port.get(bucket, storage_path)
            if st_res.status not in (PortStatus.OK, PortStatus.SANDBOX):
                corrupted.append({"blob_id": blob_id, "error": f"Storage read failed: {st_res.error}"})
                continue

            key_context = {"tenant_id": tenant_id, "company_id": company_id, "sha256": expected_sha}
            kms_res, plaintext = kms_port.decrypt(ciphertext, context=key_context)
            if kms_res.status not in (PortStatus.OK, PortStatus.SANDBOX, PortStatus.DEGRADED):
                corrupted.append({
                    "blob_id": blob_id,
                    "error": f"KMS unavailable: {kms_res.status.value}",
                })
                continue

            computed_sha = hashlib.sha256(plaintext).hexdigest()
            if computed_sha != expected_sha:
                corrupted.append({
                    "blob_id": blob_id,
                    "expected_sha": expected_sha,
                    "computed_sha": computed_sha,
                    "storage_path": storage_path,
                })
                # Log tamper incident
                seal_document_event(
                    ledger=ledger,
                    event_type="INTEGRITY_SWEEP_CORRUPTION_DETECTED",
                    actor_id="system_integrity_sweep",
                    tenant_id=tenant_id,
                    company_id=company_id,
                    payload={
                        "blob_id": blob_id,
                        "expected_sha": expected_sha,
                        "computed_sha": computed_sha,
                    }
                )
        except Exception as e:
            corrupted.append({"blob_id": blob_id, "error": str(e)})

    return {
        "tenant_id": tenant_id,
        "blobs_checked": checked,
        "corrupted_count": len(corrupted),
        "corrupted_blobs": corrupted,
        "status": "TAMPER_DETECTED" if corrupted else "CLEAN",
    }
