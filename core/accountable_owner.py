"""ZONATA Sovereign Core — Accountable Owner Record.

Implements Law L5 & L7 of ZONATA Master Architecture:
- Every action, process, agent, and Work Item must trace to a verified Accountable Owner.
- An Accountable Owner is a legal or designated executive principal with non-delegable responsibility.
- Rejects execution of any un-owned work item or unassigned process.
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.db import db
from agent_factory.ports import EvidenceEvent
from agent_factory.adapters.zonata import ZonataEvidenceAdapter


class AccountableOwnerError(Exception):
    pass


class UnaccountableWorkItemError(AccountableOwnerError):
    pass


@dataclass
class AccountableOwnerRecord:
    id: str
    tenant_id: str
    company_id: str
    subject_kind: str  # company, department, process, agent, work_item
    subject_id: str
    owner_principal_id: str
    owner_name: str
    owner_email: str
    legal_jurisdiction: str
    created_at: float
    verified_at: Optional[float] = None
    status: str = "ACTIVE"  # ACTIVE, VACANT, TRANSFERRED


class AccountableOwnerRegistry:
    def __init__(self, db_conn_factory=None, evidence_port=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self.evidence = evidence_port or ZonataEvidenceAdapter()
        self._ensure_table()

    def _get_connection(self):
        return self.db_conn_factory()

    def _ensure_table(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS af_accountable_owner (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    subject_kind TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    owner_principal_id TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    owner_email TEXT NOT NULL,
                    legal_jurisdiction TEXT NOT NULL DEFAULT 'GLOBAL',
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at REAL NOT NULL,
                    verified_at REAL,
                    UNIQUE (tenant_id, subject_kind, subject_id)
                )
            """)
            conn.commit()

    def register_owner(
        self,
        tenant_id: str,
        company_id: str,
        subject_kind: str,
        subject_id: str,
        owner_principal_id: str,
        owner_name: str,
        owner_email: str,
        legal_jurisdiction: str = "GLOBAL"
    ) -> AccountableOwnerRecord:
        """Register a verified accountable owner for a system subject."""
        now = time.time()
        record_id = f"own_{uuid.uuid4().hex[:12]}"

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO af_accountable_owner (
                    id, tenant_id, company_id, subject_kind, subject_id,
                    owner_principal_id, owner_name, owner_email,
                    legal_jurisdiction, status, created_at, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                ON CONFLICT (tenant_id, subject_kind, subject_id) DO UPDATE SET
                    id = excluded.id,
                    company_id = excluded.company_id,
                    owner_principal_id = excluded.owner_principal_id,
                    owner_name = excluded.owner_name,
                    owner_email = excluded.owner_email,
                    legal_jurisdiction = excluded.legal_jurisdiction,
                    status = 'ACTIVE',
                    verified_at = excluded.verified_at
            """, (
                record_id, tenant_id, company_id, subject_kind, subject_id,
                owner_principal_id, owner_name, owner_email,
                legal_jurisdiction, now, now
            ))
            conn.commit()

        # Log to tamper-evident ledger
        self.evidence.append_event(EvidenceEvent(
            subject_kind="accountable_owner",
            subject_id=record_id,
            event_type="accountable_owner.registered",
            actor=owner_principal_id,
            payload_hashes={
                "record_id": record_id,
                "tenant_id": tenant_id,
                "subject": f"{subject_kind}:{subject_id}",
                "owner": owner_principal_id
            },
            timestamp=now,
            tenant_id=tenant_id
        ))

        return AccountableOwnerRecord(
            id=record_id,
            tenant_id=tenant_id,
            company_id=company_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            owner_principal_id=owner_principal_id,
            owner_name=owner_name,
            owner_email=owner_email,
            legal_jurisdiction=legal_jurisdiction,
            created_at=now,
            verified_at=now,
            status="ACTIVE"
        )

    def get_owner(
        self,
        tenant_id: str,
        subject_kind: str,
        subject_id: str
    ) -> Optional[AccountableOwnerRecord]:
        """Lookup accountable owner for a subject with company-level fallback."""
        with self._get_connection() as conn:
            # 1. Exact subject lookup
            cur = conn.execute("""
                SELECT id, tenant_id, company_id, subject_kind, subject_id,
                       owner_principal_id, owner_name, owner_email,
                       legal_jurisdiction, created_at, verified_at, status
                FROM af_accountable_owner
                WHERE tenant_id = ? AND subject_kind = ? AND subject_id = ? AND status = 'ACTIVE'
            """, (tenant_id, subject_kind, subject_id))
            row = cur.fetchone()
            if row:
                return AccountableOwnerRecord(*row)

            # 2. Fallback to company-level owner
            cur = conn.execute("""
                SELECT id, tenant_id, company_id, subject_kind, subject_id,
                       owner_principal_id, owner_name, owner_email,
                       legal_jurisdiction, created_at, verified_at, status
                FROM af_accountable_owner
                WHERE tenant_id = ? AND subject_kind = 'company' AND status = 'ACTIVE'
                LIMIT 1
            """, (tenant_id,))
            row = cur.fetchone()
            if row:
                return AccountableOwnerRecord(*row)

            return None

    def assert_accountable_owner(
        self,
        tenant_id: str,
        subject_kind: str,
        subject_id: str
    ) -> AccountableOwnerRecord:
        """Enforces that an accountable owner exists. Raises error if vacant."""
        owner = self.get_owner(tenant_id, subject_kind, subject_id)
        if not owner:
            raise UnaccountableWorkItemError(
                f"UNACCOUNTABLE_SUBJECT: Subject {subject_kind}:{subject_id} in tenant {tenant_id} has no registered Accountable Owner!"
            )
        return owner
