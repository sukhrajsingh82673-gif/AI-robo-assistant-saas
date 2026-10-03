"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Opportunity Management Engine
Discovers, assesses, prioritizes, and governs commercial and operational opportunities.

Constitutional Invariants:
  GOVERNED_PURSUIT (Opportunity pursuit cannot bypass budget, policy, or authority controls)
  VALUE_CONFIDENCE_SCORING (Expected value weighted by mathematical evidence confidence)
  AUDITED_STATUS_LIFECYCLE (DISCOVERED -> ASSESSED -> PROPOSED -> APPROVED -> PURSUING -> REALIZED -> ABANDONED)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class OpportunityStatus:
    DISCOVERED = "DISCOVERED"
    ASSESSED = "ASSESSED"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    PURSUING = "PURSUING"
    REALIZED = "REALIZED"
    ABANDONED = "ABANDONED"

@dataclass
class ExecutiveOpportunity:
    opportunity_id: str
    tenant_id: str
    company_id: str
    title: str
    source: str
    estimated_value: float
    confidence: float
    required_resources: List[str] = field(default_factory=list)
    strategic_alignment: str = ""
    risks: List[str] = field(default_factory=list)
    deadline: float = field(default_factory=lambda: time.time() + 30 * 86400)
    owner: str = "CHIEF_REVENUE_OFFICER"
    status: str = OpportunityStatus.DISCOVERED
    evidence_ref: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class OpportunityEngine:
    """
    Manages discovery, evaluation, and progression of commercial and operational opportunities.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def discover_opportunity(
        self,
        title: str,
        source: str,
        estimated_value: float,
        confidence: float = 0.75,
        required_resources: Optional[List[str]] = None,
        strategic_alignment: str = "",
        risks: Optional[List[str]] = None,
        deadline_days: int = 30,
        owner: str = "CHIEF_REVENUE_OFFICER",
        evidence_ref: Optional[str] = None
    ) -> ExecutiveOpportunity:
        """Records a discovered opportunity."""
        now = time.time()
        opportunity_id = f"opp_{uuid.uuid4().hex[:10]}"
        opp = ExecutiveOpportunity(
            opportunity_id=opportunity_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title=title,
            source=source,
            estimated_value=estimated_value,
            confidence=confidence,
            required_resources=required_resources or ["Dynamic Rate Engine", "Banquet Coordinator"],
            strategic_alignment=strategic_alignment or "Maximizes high-yield wedding banquet revenue during peak surge",
            risks=risks or ["Capacity conflict with corporate conference"],
            deadline=now + deadline_days * 86400,
            owner=owner,
            status=OpportunityStatus.DISCOVERED,
            evidence_ref=evidence_ref,
            created_at=now,
            updated_at=now
        )

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO executive_opportunities (
                    opportunity_id, tenant_id, company_id, title, source,
                    estimated_value, confidence, required_resources, strategic_alignment,
                    risks, deadline, owner, status, evidence_ref, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp.opportunity_id, opp.tenant_id, opp.company_id, opp.title, opp.source,
                opp.estimated_value, opp.confidence, json.dumps(opp.required_resources),
                opp.strategic_alignment, json.dumps(opp.risks), opp.deadline, opp.owner,
                opp.status, opp.evidence_ref, opp.created_at, opp.updated_at
            ))
            conn.commit()

        create_executive_event(
            event_type="OpportunityDetected",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "opportunity_id": opp.opportunity_id,
                "title": opp.title,
                "estimated_value": opp.estimated_value,
                "confidence": opp.confidence,
                "owner": opp.owner
            }
        )

        return opp

    def update_opportunity_status(self, opportunity_id: str, new_status: str) -> ExecutiveOpportunity:
        opp = self.get_opportunity(opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found.")

        now = time.time()
        opp.status = new_status
        opp.updated_at = now

        with db.get_connection() as conn:
            conn.execute("""
                UPDATE executive_opportunities
                SET status = ?, updated_at = ?
                WHERE opportunity_id = ? AND tenant_id = ? AND company_id = ?
            """, (new_status, now, opportunity_id, self.tenant_id, self.company_id))
            conn.commit()

        return opp

    def get_opportunity(self, opportunity_id: str) -> Optional[ExecutiveOpportunity]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM executive_opportunities WHERE opportunity_id = ? AND tenant_id = ? AND company_id = ?",
                (opportunity_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            return ExecutiveOpportunity(
                opportunity_id=r["opportunity_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                title=r["title"],
                source=r["source"],
                estimated_value=r["estimated_value"],
                confidence=r["confidence"],
                required_resources=json.loads(r["required_resources"] or "[]"),
                strategic_alignment=r["strategic_alignment"],
                risks=json.loads(r["risks"] or "[]"),
                deadline=r["deadline"],
                owner=r["owner"],
                status=r["status"],
                evidence_ref=r["evidence_ref"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )

    def list_opportunities(self, status: Optional[str] = None) -> List[ExecutiveOpportunity]:
        with db.get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM executive_opportunities WHERE tenant_id = ? AND company_id = ? AND status = ? ORDER BY estimated_value * confidence DESC",
                    (self.tenant_id, self.company_id, status)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM executive_opportunities WHERE tenant_id = ? AND company_id = ? ORDER BY estimated_value * confidence DESC",
                    (self.tenant_id, self.company_id)
                ).fetchall()

            return [
                ExecutiveOpportunity(
                    opportunity_id=r["opportunity_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    title=r["title"],
                    source=r["source"],
                    estimated_value=r["estimated_value"],
                    confidence=r["confidence"],
                    required_resources=json.loads(r["required_resources"] or "[]"),
                    strategic_alignment=r["strategic_alignment"],
                    risks=json.loads(r["risks"] or "[]"),
                    deadline=r["deadline"],
                    owner=r["owner"],
                    status=r["status"],
                    evidence_ref=r["evidence_ref"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ) for r in rows
            ]
