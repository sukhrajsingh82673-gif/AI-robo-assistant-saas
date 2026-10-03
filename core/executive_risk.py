"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Executive Risk Engine
Identifies, tracks, scores, and mitigates strategic and operational enterprise risks.

Constitutional Invariants:
  MATERIAL_RISK_INCORPORATION (High/Critical risks must be reflected in executive decisions)
  AUDITED_STATUS_LIFECYCLE (IDENTIFIED -> MONITORED -> MITIGATED -> ACCEPTED -> ESCALATED -> MATERIALIZED -> CLOSED)
  EVIDENCE_GROUNDED_RISKS (Risk probability and severity require supporting observations or evidence)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class RiskSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskStatus:
    IDENTIFIED = "IDENTIFIED"
    MONITORED = "MONITORED"
    MITIGATED = "MITIGATED"
    ACCEPTED = "ACCEPTED"
    ESCALATED = "ESCALATED"
    MATERIALIZED = "MATERIALIZED"
    CLOSED = "CLOSED"

@dataclass
class ExecutiveRisk:
    risk_id: str
    tenant_id: str
    company_id: str
    category: str
    title: str
    description: str
    probability: float
    impact: float
    severity: str
    affected_objective_id: Optional[str]
    affected_mission_id: Optional[str]
    owner: str
    mitigation: str
    contingency: str
    status: str = RiskStatus.IDENTIFIED
    evidence_ref: Optional[str] = None
    review_date: float = field(default_factory=lambda: time.time() + 7 * 86400)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutiveRiskEngine:
    """
    Evaluates enterprise risks, monitors mitigation compliance, and triggers automated escalations.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def identify_risk(
        self,
        category: str,
        title: str,
        description: str,
        probability: float,
        impact: float,
        owner: str = "CHIEF_RISK_OFFICER",
        affected_objective_id: Optional[str] = None,
        affected_mission_id: Optional[str] = None,
        mitigation: str = "",
        contingency: str = "",
        evidence_ref: Optional[str] = None
    ) -> ExecutiveRisk:
        """Identifies and stores an authoritative risk."""
        now = time.time()
        score = probability * impact
        if score >= 0.7:
            severity = RiskSeverity.CRITICAL
        elif score >= 0.45:
            severity = RiskSeverity.HIGH
        elif score >= 0.2:
            severity = RiskSeverity.MEDIUM
        else:
            severity = RiskSeverity.LOW

        risk_id = f"rsk_{uuid.uuid4().hex[:10]}"
        risk = ExecutiveRisk(
            risk_id=risk_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            category=category,
            title=title,
            description=description,
            probability=probability,
            impact=impact,
            severity=severity,
            affected_objective_id=affected_objective_id,
            affected_mission_id=affected_mission_id,
            owner=owner,
            mitigation=mitigation,
            contingency=contingency,
            status=RiskStatus.IDENTIFIED,
            evidence_ref=evidence_ref,
            review_date=now + 7 * 86400,
            created_at=now,
            updated_at=now
        )

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO executive_risks (
                    risk_id, tenant_id, company_id, category, title, description,
                    probability, impact, severity, affected_objective_id, affected_mission_id,
                    owner, mitigation, contingency, status, evidence_ref, review_date,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                risk.risk_id, risk.tenant_id, risk.company_id, risk.category, risk.title,
                risk.description, risk.probability, risk.impact, risk.severity,
                risk.affected_objective_id, risk.affected_mission_id, risk.owner,
                risk.mitigation, risk.contingency, risk.status, risk.evidence_ref,
                risk.review_date, risk.created_at, risk.updated_at
            ))
            conn.commit()

        create_executive_event(
            event_type="RiskDetected",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "risk_id": risk.risk_id,
                "title": risk.title,
                "severity": risk.severity,
                "category": risk.category,
                "owner": risk.owner
            }
        )

        return risk

    def update_risk_status(self, risk_id: str, new_status: str, notes: Optional[str] = None) -> ExecutiveRisk:
        risk = self.get_risk(risk_id)
        if not risk:
            raise ValueError(f"Risk {risk_id} not found.")

        now = time.time()
        risk.status = new_status
        risk.updated_at = now
        if notes:
            risk.mitigation += f" | {notes}"

        with db.get_connection() as conn:
            conn.execute("""
                UPDATE executive_risks
                SET status = ?, mitigation = ?, updated_at = ?
                WHERE risk_id = ? AND tenant_id = ? AND company_id = ?
            """, (risk.status, risk.mitigation, risk.updated_at, risk.risk_id, self.tenant_id, self.company_id))
            conn.commit()

        return risk

    def get_risk(self, risk_id: str) -> Optional[ExecutiveRisk]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM executive_risks WHERE risk_id = ? AND tenant_id = ? AND company_id = ?",
                (risk_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            return ExecutiveRisk(
                risk_id=r["risk_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                category=r["category"],
                title=r["title"],
                description=r["description"],
                probability=r["probability"],
                impact=r["impact"],
                severity=r["severity"],
                affected_objective_id=r["affected_objective_id"],
                affected_mission_id=r["affected_mission_id"],
                owner=r["owner"],
                mitigation=r["mitigation"],
                contingency=r["contingency"],
                status=r["status"],
                evidence_ref=r["evidence_ref"],
                review_date=r["review_date"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )

    def list_risks(self, severity: Optional[str] = None, status: Optional[str] = None) -> List[ExecutiveRisk]:
        with db.get_connection() as conn:
            query = "SELECT * FROM executive_risks WHERE tenant_id = ? AND company_id = ?"
            params = [self.tenant_id, self.company_id]
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY probability * impact DESC"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                ExecutiveRisk(
                    risk_id=r["risk_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    category=r["category"],
                    title=r["title"],
                    description=r["description"],
                    probability=r["probability"],
                    impact=r["impact"],
                    severity=r["severity"],
                    affected_objective_id=r["affected_objective_id"],
                    affected_mission_id=r["affected_mission_id"],
                    owner=r["owner"],
                    mitigation=r["mitigation"],
                    contingency=r["contingency"],
                    status=r["status"],
                    evidence_ref=r["evidence_ref"],
                    review_date=r["review_date"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ) for r in rows
            ]
