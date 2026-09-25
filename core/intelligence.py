"""
RoboAssistant Company OS 1.0 — Opportunity & Operational Risk Engines
Automated detection of verified operational bottlenecks, financial variances, and strategic opportunities.
"""

from typing import List, Dict, Any, Optional
import time
import uuid
from .db import db

class OpportunityEngine:
    @staticmethod
    def register_opportunity(
        tenant_id: str,
        company_id: str,
        title: str,
        evidence: str,
        potential_impact: str,
        confidence: float = 0.85
    ) -> Dict[str, Any]:
        item_id = f"opp_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO business_intelligence_items (
                    item_id, company_id, tenant_id, item_type, title,
                    evidence, potential_impact, severity_or_confidence, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, company_id, tenant_id, "OPPORTUNITY", title, evidence, potential_impact, confidence, "DISCOVERED", now)
            )
            conn.commit()

        return {
            "item_id": item_id,
            "company_id": company_id,
            "title": title,
            "evidence": evidence,
            "potential_impact": potential_impact,
            "confidence": confidence,
            "status": "DISCOVERED"
        }

class RiskEngine:
    @staticmethod
    def register_risk(
        tenant_id: str,
        company_id: str,
        title: str,
        evidence: str,
        potential_impact: str,
        severity: float = 0.8
    ) -> Dict[str, Any]:
        item_id = f"rsk_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO business_intelligence_items (
                    item_id, company_id, tenant_id, item_type, title,
                    evidence, potential_impact, severity_or_confidence, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, company_id, tenant_id, "RISK", title, evidence, potential_impact, severity, "DISCOVERED", now)
            )
            conn.commit()

        return {
            "item_id": item_id,
            "company_id": company_id,
            "title": title,
            "evidence": evidence,
            "potential_impact": potential_impact,
            "severity": severity,
            "status": "DISCOVERED"
        }

    @staticmethod
    def list_intelligence_items(tenant_id: str, company_id: str, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            sql = "SELECT * FROM business_intelligence_items WHERE tenant_id = ? AND company_id = ?"
            params = [tenant_id, company_id]
            if item_type:
                sql += " AND item_type = ?"
                params.append(item_type)
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
