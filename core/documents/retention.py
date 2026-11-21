"""ZONATA Sovereign Core — Document Retention, Legal Holds & Crypto-Shred Disposal.

Implements OpenCode Step 1E:
- Legal hold blocks any disposal, tombstoning, or retention reduction.
- Retention policy objects (retention_days, trigger_event, jurisdiction, worm_required).
- Disposal executes crypto-shred (destroys DEK wrapped material) + tombstone + sealed evidence entry.
- Deletion conflicting with hold or active retention is refused with explicit reason.
"""

from __future__ import annotations
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from core.db import db, tenant_scoped
from core.evidence_ledger import EvidenceLedger
from core.documents.errors import StorageDeletionFailedError
from core.documents.evidence import seal_document_event
from core.ports.base import PortStatus
from core.ports.storage import resolve_storage_provider


class LegalHoldEnforcedError(Exception):
    """Raised when disposal or deletion is attempted on a document under active legal hold."""
    pass


class RetentionPeriodActiveError(Exception):
    """Raised when disposal is attempted before retention period expiration."""
    pass


@tenant_scoped
def apply_legal_hold(
    document_id: str,
    reason: str,
    matter_id: Optional[str],
    applied_by: str,
    ledger: Optional[EvidenceLedger] = None,
    tenant_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> str:
    """Applies an active legal hold to a document, preventing disposal or mutation."""
    ledger = ledger or EvidenceLedger()
    hold_id = f"hold_{uuid.uuid4().hex[:16]}"
    now = time.time()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, company_id FROM documents WHERE id = ?",
            (document_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Document {document_id} not found")
        doc_tenant_id, doc_company_id = row[0], row[1]
        if tenant_id is not None and doc_tenant_id != tenant_id:
            raise ValueError(f"Document {document_id} does not belong to tenant {tenant_id}")
        if company_id is not None and doc_company_id != company_id:
            raise ValueError(f"Document {document_id} does not belong to company {company_id}")
        tenant_id, company_id = doc_tenant_id, doc_company_id

        conn.execute(
            """
            INSERT INTO legal_holds (
                id, tenant_id, company_id, document_id, reason,
                matter_id, applied_by, active, applied_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (hold_id, tenant_id, company_id, document_id, reason, matter_id, applied_by, now)
        )
        conn.execute(
            "UPDATE documents SET legal_hold = 1, updated_at = ? WHERE id = ?",
            (now, document_id)
        )
        conn.execute(
            """
            INSERT INTO document_events (
                id, document_id, tenant_id, company_id, event_type,
                payload, actor_id, evidence_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evt_{uuid.uuid4().hex[:16]}", document_id, tenant_id, company_id,
                "LEGAL_HOLD_APPLIED",
                json.dumps({"hold_id": hold_id, "reason": reason, "matter_id": matter_id}),
                applied_by, None, now
            )
        )

    seal_document_event(
        ledger=ledger,
        event_type="DOCUMENT_LEGAL_HOLD_APPLIED",
        actor_id=applied_by,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={"document_id": document_id, "hold_id": hold_id, "reason": reason}
    )

    return hold_id


@tenant_scoped
def release_legal_hold(
    document_id: str,
    hold_id: str,
    released_by: str,
    ledger: Optional[EvidenceLedger] = None,
    tenant_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> None:
    """Releases a specific legal hold. If no active holds remain, clears document's hold flag."""
    ledger = ledger or EvidenceLedger()
    now = time.time()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, company_id FROM documents WHERE id = ?",
            (document_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Document {document_id} not found")
        doc_tenant_id, doc_company_id = row[0], row[1]
        if tenant_id is not None and doc_tenant_id != tenant_id:
            raise ValueError(f"Document {document_id} does not belong to tenant {tenant_id}")
        if company_id is not None and doc_company_id != company_id:
            raise ValueError(f"Document {document_id} does not belong to company {company_id}")
        tenant_id, company_id = doc_tenant_id, doc_company_id

        conn.execute(
            "UPDATE legal_holds SET active = 0, released_at = ?, released_by = ? WHERE id = ?",
            (now, released_by, hold_id)
        )
        cur.execute(
            "SELECT COUNT(*) FROM legal_holds WHERE document_id = ? AND active = 1",
            (document_id,)
        )
        remaining_holds = cur.fetchone()[0]
        if remaining_holds == 0:
            conn.execute("UPDATE documents SET legal_hold = 0, updated_at = ? WHERE id = ?", (now, document_id))

        conn.execute(
            """
            INSERT INTO document_events (
                id, document_id, tenant_id, company_id, event_type,
                payload, actor_id, evidence_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evt_{uuid.uuid4().hex[:16]}", document_id, tenant_id, company_id,
                "LEGAL_HOLD_RELEASED",
                json.dumps({"hold_id": hold_id, "remaining_holds": remaining_holds}),
                released_by, None, now
            )
        )

    seal_document_event(
        ledger=ledger,
        event_type="DOCUMENT_LEGAL_HOLD_RELEASED",
        actor_id=released_by,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={"document_id": document_id, "hold_id": hold_id}
    )


@tenant_scoped
def dispose_document(
    document_id: str,
    actor_id: str,
    force: bool = False,
    ledger: Optional[EvidenceLedger] = None,
    tenant_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Disposes a document via crypto-shredding and tombstoning.

    Refuses disposal if document is under active legal hold or within active retention period.
    """
    ledger = ledger or EvidenceLedger()
    now = time.time()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tenant_id, company_id, name, legal_hold, retention_until, tombstone, current_version_id
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Document {document_id} not found")

        doc_tenant_id, doc_company_id, name, legal_hold, retention_until, tombstone, current_ver_id = row
        if tenant_id is not None and doc_tenant_id != tenant_id:
            raise ValueError(f"Document {document_id} does not belong to tenant {tenant_id}")
        if company_id is not None and doc_company_id != company_id:
            raise ValueError(f"Document {document_id} does not belong to company {company_id}")
        tenant_id, company_id = doc_tenant_id, doc_company_id

        # Invariant 1: Active legal hold blocks disposal. Query the authoritative
        # hold rows rather than trusting a potentially stale denormalized flag.
        cur.execute("SELECT id, reason FROM legal_holds WHERE document_id = ? AND active = 1", (document_id,))
        active_holds = cur.fetchall()
        if active_holds:
            reasons = [h[1] for h in active_holds]
            err_msg = f"Cannot dispose document {document_id}: active legal hold enforced ({'; '.join(reasons)})"
            # Record tamper attempt in ledger
            seal_document_event(
                ledger=ledger,
                event_type="DISPOSAL_BLOCKED_BY_LEGAL_HOLD",
                actor_id=actor_id,
                tenant_id=tenant_id,
                company_id=company_id,
                payload={"document_id": document_id, "active_holds": reasons}
            )
            raise LegalHoldEnforcedError(err_msg)

        # Invariant 2: Active retention period blocks disposal unless forced
        if retention_until and now < retention_until and not force:
            remaining_secs = int(retention_until - now)
            raise RetentionPeriodActiveError(
                f"Cannot dispose document {document_id}: active retention period until timestamp {retention_until} ({remaining_secs}s remaining)"
            )

        if tombstone:
            return {"status": "ALREADY_DISPOSED", "document_id": document_id}

        # Retrieve associated blob to crypto-shred and decrement ref_count
        cur.execute(
            """
            SELECT b.id, b.storage_path, b.ref_count
            FROM document_versions v
            JOIN blobs b ON v.blob_id = b.id
            WHERE v.document_id = ?
            """,
            (document_id,)
        )
        associated_blobs = cur.fetchall()

        storage_port = resolve_storage_provider()
        shredded_count = 0
        for b_id, s_path, ref_cnt in associated_blobs:
            if ref_cnt <= 1:
                # Last reference: delete ciphertext first and honour the result
                # before destroying the DEK. Reporting DISPOSED on a failed
                # delete would violate the Truth Rule.
                bucket = os.environ.get("S3_BUCKET", "zonata-documents")
                del_res = storage_port.delete(bucket, s_path)
                if del_res.status not in (PortStatus.OK, PortStatus.ACCEPTED_BY_PROVIDER, PortStatus.SANDBOX):
                    raise StorageDeletionFailedError(
                        f"Storage delete failed for blob {b_id}: {del_res.error}"
                    )
                # Overwrite DEK in database (crypto-shred)
                conn.execute(
                    "UPDATE blobs SET dek_wrapped = 'CRYPTO_SHREDDED_NULLIFIED', ref_count = 0 WHERE id = ?",
                    (b_id,)
                )
                shredded_count += 1
            else:
                # Other documents still reference this blob: only release our
                # reference. Shredding the DEK here would destroy their data.
                conn.execute(
                    "UPDATE blobs SET ref_count = ref_count - 1 WHERE id = ?",
                    (b_id,)
                )

        # Tombstone document record
        conn.execute(
            """
            UPDATE documents
            SET tombstone = 1, status = 'DISPOSED', disposed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, document_id)
        )
        conn.execute(
            """
            INSERT INTO document_events (
                id, document_id, tenant_id, company_id, event_type,
                payload, actor_id, evidence_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evt_{uuid.uuid4().hex[:16]}", document_id, tenant_id, company_id,
                "DOCUMENT_CRYPTO_SHREDDED_DISPOSED",
                json.dumps({
                    "disposed_by": actor_id,
                    "blobs_shredded": shredded_count,
                    "blobs_referenced": len(associated_blobs) - shredded_count,
                }),
                actor_id, None, now
            )
        )

    # Record sealed disposal in evidence ledger
    evidence_id = seal_document_event(
        ledger=ledger,
        event_type="DOCUMENT_CRYPTO_SHREDDED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={
            "document_id": document_id,
            "disposed_at": now,
            "blobs_shredded": shredded_count,
            "blobs_referenced": len(associated_blobs) - shredded_count,
        }
    )

    return {
        "status": "DISPOSED",
        "document_id": document_id,
        "disposed_at": now,
        "tombstone": True,
        "evidence_id": evidence_id,
    }
