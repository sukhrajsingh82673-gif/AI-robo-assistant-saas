"""
ZONATA CEO Decision Records Service
OpenCode Step 2J: Structured, evidence-sealed executive decision records.
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, Any, List, Optional

from core.db import db
from core.evidence_service import evidence_service
from core.executive.types import CEODecisionRecordModel


class CEODecisionService:
    """
    Records and evidence-seals formal executive decisions.
    """

    @classmethod
    def record_decision(
        cls,
        tenant_id: str,
        company_id: str,
        title: str,
        options: List[Dict[str, Any]],
        evidence_ids: List[str],
        chosen_option: str,
        reason: str,
        approver_id: str,
        directive_id: Optional[str] = None,
        outcome_review_date: Optional[str] = None,
    ) -> CEODecisionRecordModel:
        """Records an executive decision and seals it in the Merkle evidence ledger."""
        dec_id = f"dec_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO ceo_decision_records (
                    id, tenant_id, company_id, directive_id, title,
                    options, evidence_ids, chosen_option, reason,
                    approver_id, outcome_review_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dec_id, tenant_id, company_id, directive_id, title,
                    json.dumps(options), json.dumps(evidence_ids), chosen_option,
                    reason, approver_id, outcome_review_date, now
                )
            )
            conn.commit()

        # Seal in Merkle evidence ledger
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="CEO_DECISION_RECORDED",
            payload={
                "decision_id": dec_id,
                "title": title,
                "chosen_option": chosen_option,
                "reason": reason,
                "approver_id": approver_id,
                "evidence_ids": evidence_ids,
            },
            action_id=dec_id,
        )

        return CEODecisionRecordModel(
            id=dec_id,
            tenant_id=tenant_id,
            company_id=company_id,
            directive_id=directive_id,
            title=title,
            options=options,
            evidence_ids=evidence_ids,
            chosen_option=chosen_option,
            reason=reason,
            approver_id=approver_id,
            outcome_review_date=outcome_review_date,
            created_at=now,
        )

    @classmethod
    def get_decision(cls, tenant_id: str, company_id: str, decision_id: str) -> Optional[CEODecisionRecordModel]:
        """Retrieves a decision record by ID."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ceo_decision_records WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (decision_id, tenant_id, company_id)
            ).fetchone()
        if not row:
            return None
        return CEODecisionRecordModel(
            id=row["id"],
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
            directive_id=row["directive_id"],
            title=row["title"],
            options=json.loads(row["options"]) if row["options"] else [],
            evidence_ids=json.loads(row["evidence_ids"]) if row["evidence_ids"] else [],
            chosen_option=row["chosen_option"],
            reason=row["reason"],
            approver_id=row["approver_id"],
            outcome_review_date=row["outcome_review_date"],
            created_at=row["created_at"],
        )
