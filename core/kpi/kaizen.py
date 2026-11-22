"""
ZONATA Kaizen Continuous Improvement Engine
OpenCode Step 2I: Defect logging, clustering, coaching prompts, and SOP revision proposals.
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from collections import defaultdict

from core.db import db, tenant_scope
from core.evidence_service import evidence_service
from core.kpi.types import (
    DefectType,
    KaizenProposalType,
    KaizenDefectRecordModel,
    KaizenProposalModel,
)


class KaizenEngine:
    """
    Continuous improvement feedback loop: records verification defects,
    clusters recurring errors, and synthesizes coaching prompts & SOP revision proposals.
    """

    @classmethod
    def record_defect(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        defect_type: DefectType,
        details: Optional[Dict[str, Any]] = None,
        position_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        sop_id: Optional[str] = None,
    ) -> KaizenDefectRecordModel:
        """Records a defect when a task verification fails."""
        defect_id = f"kzd_{uuid.uuid4().hex[:12]}"
        now = time.time()
        details = details or {}

        with tenant_scope(tenant_id, company_id):
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO kaizen_defect_records (
                        id, tenant_id, company_id, task_id, position_id, employee_id,
                        sop_id, defect_type, details, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        defect_id, tenant_id, company_id, task_id, position_id, employee_id,
                        sop_id, defect_type.value, json.dumps(details), now
                    )
                )
                conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="KAIZEN_DEFECT_RECORDED",
            payload={"defect_id": defect_id, "task_id": task_id, "defect_type": defect_type.value},
            action_id=defect_id,
        )

        return KaizenDefectRecordModel(
            id=defect_id,
            tenant_id=tenant_id,
            company_id=company_id,
            task_id=task_id,
            position_id=position_id,
            employee_id=employee_id,
            sop_id=sop_id,
            defect_type=defect_type,
            details=details,
            recorded_at=now,
        )

    @classmethod
    def analyze_defects_and_cluster(
        cls,
        tenant_id: str,
        company_id: str,
        position_id: Optional[str] = None,
        sop_id: Optional[str] = None,
        threshold_count: int = 3,
    ) -> List[KaizenProposalModel]:
        """
        Analyzes defect clusters. When defects exceed threshold_count,
        generates an SOP revision proposal or coaching prompt in DRAFT status.
        """
        with tenant_scope(tenant_id, company_id):
            query = "SELECT * FROM kaizen_defect_records WHERE tenant_id = ? AND company_id = ?"
            params = [tenant_id, company_id]
            if position_id:
                query += " AND position_id = ?"
                params.append(position_id)
            if sop_id:
                query += " AND sop_id = ?"
                params.append(sop_id)

            with db.get_connection() as conn:
                rows = conn.execute(query, tuple(params)).fetchall()

            if not rows:
                return []

            # Cluster by (target_type, target_id, defect_type)
            clusters = defaultdict(list)
            for r in rows:
                d_type = DefectType(r["defect_type"])
                if r["sop_id"]:
                    clusters[("SOP", r["sop_id"], d_type)].append(r)
                elif r["position_id"]:
                    clusters[("POSITION", r["position_id"], d_type)].append(r)
                elif r["employee_id"]:
                    clusters[("EMPLOYEE", r["employee_id"], d_type)].append(r)

            generated_proposals: List[KaizenProposalModel] = []
            now = time.time()

            for (target_type, target_id, d_type), defect_list in clusters.items():
                count = len(defect_list)
                if count >= threshold_count:
                    prop_id = f"kzp_{uuid.uuid4().hex[:12]}"
                    if target_type == "SOP":
                        prop_type = KaizenProposalType.SOP_REVISION_PROPOSAL
                        title = f"Kaizen Proposed Revision for SOP {target_id} ({d_type.value} clustering)"
                        content = {
                            "sop_id": target_id,
                            "cluster_defect_type": d_type.value,
                            "defect_occurrences": count,
                            "suggested_actions": [
                                f"Add strict pre-validation rule for {d_type.value}",
                                "Insert automated check step before final deliverable submission",
                            ],
                            "review_required": True,
                        }
                    else:
                        prop_type = KaizenProposalType.COACHING_PROMPT
                        title = f"Kaizen Coaching Guidance for {target_type} {target_id}"
                        content = {
                            "target_id": target_id,
                            "cluster_defect_type": d_type.value,
                            "defect_occurrences": count,
                            "coaching_guidance": f"High defect concentration in {d_type.value}. Review instructions and tool schemas.",
                        }

                    with db.get_connection() as conn:
                        conn.execute(
                            """
                            INSERT INTO kaizen_proposals (
                                id, tenant_id, company_id, proposal_type, target_type,
                                target_id, cluster_defect_type, cluster_count, title,
                                content, status, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?)
                            """,
                            (
                                prop_id, tenant_id, company_id, prop_type.value, target_type,
                                target_id, d_type.value, count, title, json.dumps(content), now
                            )
                        )
                        conn.commit()

                    proposal = KaizenProposalModel(
                        id=prop_id,
                        tenant_id=tenant_id,
                        company_id=company_id,
                        proposal_type=prop_type,
                        target_type=target_type,
                        target_id=target_id,
                        cluster_defect_type=d_type,
                        cluster_count=count,
                        title=title,
                        content=content,
                        status="DRAFT",
                        created_at=now,
                    )
                    generated_proposals.append(proposal)

            return generated_proposals


kaizen_engine = KaizenEngine()
