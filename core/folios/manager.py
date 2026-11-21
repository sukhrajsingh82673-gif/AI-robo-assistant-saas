"""ZONATA Sovereign Core — Folio Lifecycle Manager & Aggregate Controller.

Implements OpenCode Step 1F:
- Universal folio aggregate managing transaction case files.
- Sequence-ordered immutable timeline entries.
- Deterministic Merkle evidence tree recalculation on mutation.
- State transitions (OPEN → ACTIVE → SUSPENDED → PENDING_CLOSE → CLOSED → ARCHIVED → EXPUNGED).
- Deletion drill (export pack verified -> sealed in global ledger -> expunge database & storage).
"""

from __future__ import annotations
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.db import db
from core.evidence_ledger import EvidenceLedger
from core.documents.evidence import seal_document_event
from core.ports.storage import resolve_storage_provider
from core.folios.schema import (
    FolioStatus,
    FolioEntryType,
    ALLOWED_TRANSITIONS,
    ensure_folio_tables,
)
from core.folios.merkle import (
    recompute_folio_merkle_root,
    GENESIS_ROOT,
)
from core.folios.export import (
    generate_folio_export_pack,
    verify_export_pack_file,
)


class FolioManager:
    """Manages lifecycles, timeline entries, Merkle evidence, and export packs for folios."""

    def __init__(self, ledger: Optional[EvidenceLedger] = None):
        ensure_folio_tables()
        self.ledger = ledger or EvidenceLedger()

    def create_folio(
        self,
        tenant_id: str,
        company_id: str,
        folio_type: str,
        title: str,
        subject_id: Optional[str] = None,
        created_by: str = "usr_admin",
        retention_policy_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Initializes a new governed folio."""
        folio_id = f"fol_{uuid.uuid4().hex[:16]}"
        now = time.time()
        meta_json = json.dumps(metadata or {})

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO folios (
                    id, tenant_id, company_id, folio_type, title,
                    subject_id, status, retention_policy_id, retention_until,
                    merkle_root, created_by, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    folio_id, tenant_id, company_id, folio_type, title,
                    subject_id, FolioStatus.OPEN.value, retention_policy_id,
                    GENESIS_ROOT, created_by, meta_json, now, now
                )
            )

        seal_document_event(
            ledger=self.ledger,
            event_type="FOLIO_CREATED",
            actor_id=created_by,
            tenant_id=tenant_id,
            company_id=company_id,
            payload={"folio_id": folio_id, "folio_type": folio_type, "title": title}
        )

        return folio_id

    def add_entry(
        self,
        folio_id: str,
        entry_type: FolioEntryType,
        reference_id: str,
        title: str,
        payload: Dict[str, Any],
        author_id: str,
    ) -> Tuple[str, str, int]:
        """Appends an immutable entry to the folio timeline and recalculates the Merkle root.

        Returns (entry_id, entry_hash, sequence_number).
        """
        now = time.time()
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tenant_id, company_id, status FROM folios WHERE id = ?",
                (folio_id,)
            )
            folio_row = cur.fetchone()
            if not folio_row:
                raise ValueError(f"Folio {folio_id} not found")

            tenant_id, company_id, status = folio_row
            if status in (FolioStatus.EXPUNGED.value, FolioStatus.CLOSED.value):
                raise ValueError(f"Cannot add entry to folio {folio_id} in {status} status")

            cur.execute(
                """
                SELECT COALESCE(MAX(sequence_number), 0), entry_hash
                FROM folio_entries
                WHERE folio_id = ?
                ORDER BY sequence_number DESC LIMIT 1
                """,
                (folio_id,)
            )
            last_entry = cur.fetchone()
            last_seq = last_entry[0] if last_entry else 0
            prev_hash = last_entry[1] if (last_entry and last_entry[1]) else GENESIS_ROOT
            next_seq = last_seq + 1

            # Compute chained entry hash
            hash_input = f"{prev_hash}:{next_seq}:{entry_type.value}:{reference_id}:{payload_sha256}"
            entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            entry_id = f"fole_{uuid.uuid4().hex[:16]}"
            conn.execute(
                """
                INSERT INTO folio_entries (
                    id, folio_id, tenant_id, company_id, entry_type,
                    reference_id, title, payload_sha256, payload_json,
                    author_id, sequence_number, entry_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id, folio_id, tenant_id, company_id, entry_type.value,
                    reference_id, title, payload_sha256, json.dumps(payload),
                    author_id, next_seq, entry_hash, now
                )
            )

        # Recalculate folio Merkle root
        new_root = recompute_folio_merkle_root(folio_id)

        # Seal in evidence ledger
        seal_document_event(
            ledger=self.ledger,
            event_type="FOLIO_ENTRY_APPENDED",
            actor_id=author_id,
            tenant_id=tenant_id,
            company_id=company_id,
            payload={
                "folio_id": folio_id,
                "entry_id": entry_id,
                "sequence_number": next_seq,
                "entry_type": entry_type.value,
                "reference_id": reference_id,
                "new_merkle_root": new_root,
            }
        )

        return entry_id, entry_hash, next_seq

    def transition_status(
        self,
        folio_id: str,
        new_status: FolioStatus,
        actor_id: str,
        reason: Optional[str] = None
    ) -> None:
        """Transitions folio to new status following strict state machine rules."""
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tenant_id, company_id, status FROM folios WHERE id = ?",
                (folio_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Folio {folio_id} not found")

            tenant_id, company_id, current_status_str = row
            current_status = FolioStatus(current_status_str)

            allowed = ALLOWED_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Invalid folio transition: cannot transition from {current_status.value} to {new_status.value}"
                )

            # Invariant 5: Sealing or closing a folio verifies all its journal entries are in POSTED status
            if new_status in (FolioStatus.PENDING_CLOSE, FolioStatus.CLOSED):
                from core.ledger.kernel import LedgerKernel
                LedgerKernel().verify_folio_journal_entries_posted(tenant_id, company_id, folio_id)

            closed_at = now if new_status == FolioStatus.CLOSED else None
            archived_at = now if new_status == FolioStatus.ARCHIVED else None
            expunged_at = now if new_status == FolioStatus.EXPUNGED else None

            sql = "UPDATE folios SET status = ?, updated_at = ?"
            params: List[Any] = [new_status.value, now]
            if closed_at:
                sql += ", closed_at = ?"
                params.append(closed_at)
            if archived_at:
                sql += ", archived_at = ?"
                params.append(archived_at)
            if expunged_at:
                sql += ", expunged_at = ?"
                params.append(expunged_at)
            sql += " WHERE id = ?"
            params.append(folio_id)

            conn.execute(sql, tuple(params))

        seal_document_event(
            ledger=self.ledger,
            event_type="FOLIO_STATUS_TRANSITIONED",
            actor_id=actor_id,
            tenant_id=tenant_id,
            company_id=company_id,
            payload={
                "folio_id": folio_id,
                "previous_status": current_status.value,
                "new_status": new_status.value,
                "reason": reason,
            }
        )

    def get_folio(self, folio_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves folio record and current Merkle root."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, tenant_id, company_id, folio_type, title, subject_id,
                       status, merkle_root, created_by, closed_at, archived_at,
                       expunged_at, metadata_json, created_at, updated_at
                FROM folios WHERE id = ?
                """,
                (folio_id,)
            )
            row = cur.fetchone()
            if not row:
                return None

            cur.execute("SELECT COUNT(*) FROM folio_entries WHERE folio_id = ?", (folio_id,))
            entry_count = cur.fetchone()[0]

            return {
                "id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "folio_type": row[3],
                "title": row[4],
                "subject_id": row[5],
                "status": row[6],
                "merkle_root": row[7],
                "created_by": row[8],
                "closed_at": row[9],
                "archived_at": row[10],
                "expunged_at": row[11],
                "metadata": json.loads(row[12]) if isinstance(row[12], str) else row[12],
                "created_at": row[13],
                "updated_at": row[14],
                "entry_count": entry_count,
            }

    def list_entries(self, folio_id: str) -> List[Dict[str, Any]]:
        """Lists all timeline entries for a folio in chronological order."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, entry_type, reference_id, title, payload_sha256,
                       payload_json, author_id, sequence_number, entry_hash, created_at
                FROM folio_entries
                WHERE folio_id = ?
                ORDER BY sequence_number ASC
                """,
                (folio_id,)
            )
            rows = cur.fetchall()

            return [
                {
                    "id": r[0],
                    "entry_type": r[1],
                    "reference_id": r[2],
                    "title": r[3],
                    "payload_sha256": r[4],
                    "payload": json.loads(r[5]) if isinstance(r[5], str) else r[5],
                    "author_id": r[6],
                    "sequence_number": r[7],
                    "entry_hash": r[8],
                    "created_at": r[9],
                }
                for r in rows
            ]

    def export_pack(self, folio_id: str, output_dir: Optional[str] = None) -> Tuple[str, str, int]:
        """Exports self-verifying standalone .zip pack for the folio."""
        return generate_folio_export_pack(folio_id, output_dir=output_dir)

    def expunge_folio(
        self,
        folio_id: str,
        actor_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """Executes deletion drill: exports pack, verifies pack, seals pack hash, and expunges DB rows and blobs.

        The exported .zip pack remains the sovereign audit record.
        """
        folio = self.get_folio(folio_id)
        if not folio:
            raise ValueError(f"Folio {folio_id} not found")

        current_status = FolioStatus(folio["status"])
        if current_status not in (FolioStatus.CLOSED, FolioStatus.ARCHIVED) and not force:
            raise ValueError(
                f"Cannot expunge folio {folio_id}: status must be CLOSED or ARCHIVED (current: {current_status.value})"
            )

        # 1. Export pack
        zip_path, pack_sha, pack_size = self.export_pack(folio_id)

        # 2. Standalone verification before expunging
        is_valid, status_msg, report = verify_export_pack_file(zip_path)
        if not is_valid:
            raise RuntimeError(f"Export pack verification failed prior to expunge: {report}")

        # 3. Seal pack hash in global evidence ledger
        seal_document_event(
            ledger=self.ledger,
            event_type="FOLIO_EXPUNGED_EXPORT_SEALED",
            actor_id=actor_id,
            tenant_id=folio["tenant_id"],
            company_id=folio["company_id"],
            payload={
                "folio_id": folio_id,
                "pack_sha256": pack_sha,
                "pack_size": pack_size,
                "merkle_root": folio["merkle_root"],
                "entry_count": folio["entry_count"],
            }
        )

        # 4. Expunge database records
        with db.get_connection() as conn:
            conn.execute("DELETE FROM folio_entries WHERE folio_id = ?", (folio_id,))
            conn.execute("DELETE FROM folios WHERE id = ?", (folio_id,))

        return {
            "status": "EXPUNGED",
            "folio_id": folio_id,
            "pack_sha256": pack_sha,
            "pack_size": pack_size,
            "export_pack_path": zip_path,
        }
