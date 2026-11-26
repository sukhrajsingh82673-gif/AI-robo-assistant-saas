"""
ZONATA Company Risk Register Service
OpenCode Step 2J: Deterministic risk triggers creating proposed corrective tasks (never silent actions).
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, Any, List, Optional

from core.db import db
from core.executive.types import (
    RiskTriggerType,
    RiskSeverity,
    RiskRecordModel,
)


class CompanyRiskService:
    """
    Monitors deterministic risk conditions across KPIs, SLAs, verifications, and approvals.
    Creates auditable risk records and drafts proposed corrective tasks.
    """

    @classmethod
    def record_risk_and_propose_task(
        cls,
        tenant_id: str,
        company_id: str,
        trigger_type: RiskTriggerType,
        severity: RiskSeverity,
        details: Dict[str, Any],
        corrective_task_title: Optional[str] = None,
        assigned_position_id: Optional[str] = None,
    ) -> RiskRecordModel:
        """
        Records a risk trigger and creates a proposed corrective task in the Work Kernel.
        """
        now = time.time()
        risk_id = f"rsk_{uuid.uuid4().hex[:12]}"
        task_id = f"tsk_risk_{uuid.uuid4().hex[:10]}"

        # 1. Draft Proposed Corrective Task
        title = corrective_task_title or f"Mitigate Risk: {trigger_type.value} ({severity.value})"
        pos_id = assigned_position_id or "pos_operations_lead"

        with db.get_connection() as conn:
            # Create proposed task in work_tasks
            conn.execute(
                """
                INSERT INTO work_tasks (
                    id, tenant_id, company_id, mission_id, project_id, title,
                    owner_id, assignee_type, assignee_id, status, estimate_minor_units,
                    estimate_seconds, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, NULL, ?,
                    'principal_owner', 'POSITION', ?, 'PROPOSED', 0, 3600, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (task_id, tenant_id, company_id, title, pos_id, now, now)
            )

            # Insert risk register entry linking to the corrective task
            conn.execute(
                """
                INSERT INTO company_risk_register (
                    id, tenant_id, company_id, trigger_type, severity,
                    details, corrective_task_id, status, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """,
                (
                    risk_id, tenant_id, company_id, trigger_type.value,
                    severity.value, json.dumps(details), task_id, now
                )
            )
            conn.commit()

        return RiskRecordModel(
            id=risk_id,
            tenant_id=tenant_id,
            company_id=company_id,
            trigger_type=trigger_type,
            severity=severity,
            details=details,
            corrective_task_id=task_id,
            status="OPEN",
            detected_at=now,
        )

    @classmethod
    def list_open_risks(cls, tenant_id: str, company_id: str) -> List[RiskRecordModel]:
        """Lists active open risk records for a company."""
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM company_risk_register WHERE tenant_id = ? AND company_id = ? AND status = 'OPEN'",
                (tenant_id, company_id)
            ).fetchall()

        results = []
        for r in rows:
            results.append(
                RiskRecordModel(
                    id=r["id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    trigger_type=RiskTriggerType(r["trigger_type"]),
                    severity=RiskSeverity(r["severity"]),
                    details=json.loads(r["details"]) if r["details"] else {},
                    corrective_task_id=r["corrective_task_id"],
                    status=r["status"],
                    detected_at=r["detected_at"],
                    resolved_at=r["resolved_at"],
                )
            )
        return results
