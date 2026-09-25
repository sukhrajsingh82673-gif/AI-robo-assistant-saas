"""
RoboAssistant Company OS 1.0 — Company Truth & Knowledge Graph Engine
Honest Epistemic States: MEASURED, CALCULATED, ESTIMATED, AI_INFERRED, UNAVAILABLE, NOT_VERIFIED, CONFLICTED.
Rule: Unknown must remain unknown. Never fabricate missing company data.
"""

from typing import List, Dict, Any, Optional
import time
import uuid
from .db import db

class TruthState:
    MEASURED = "MEASURED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    AI_INFERRED = "AI_INFERRED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_VERIFIED = "NOT_VERIFIED"
    CONFLICTED = "CONFLICTED"

class CompanyKnowledgeGraph:
    @staticmethod
    def assert_fact(
        tenant_id: str,
        company_id: str,
        category: str,
        subject: str,
        predicate: str,
        object_val: Any,
        truth_state: str = TruthState.MEASURED,
        provenance_source: str = "SYSTEM",
        confidence: float = 1.0
    ) -> str:
        fact_id = f"fact_{uuid.uuid4().hex[:8]}"
        now = time.time()
        val_str = str(object_val)
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO company_knowledge (
                    fact_id, company_id, tenant_id, category, subject, predicate,
                    object_val, truth_state, provenance_source, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fact_id, company_id, tenant_id, category, subject, predicate,
                 val_str, truth_state, provenance_source, confidence, now)
            )
            conn.commit()
        return fact_id

    @staticmethod
    def query_facts(
        tenant_id: str,
        company_id: str,
        category: Optional[str] = None,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            sql = "SELECT * FROM company_knowledge WHERE tenant_id = ? AND company_id = ?"
            params = [tenant_id, company_id]
            if category:
                sql += " AND category = ?"
                params.append(category)
            if subject:
                sql += " AND subject = ?"
                params.append(subject)
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_company_baseline(tenant_id: str, company_id: str) -> Dict[str, Any]:
        facts = CompanyKnowledgeGraph.query_facts(tenant_id, company_id)
        measured_facts = [f for f in facts if f["truth_state"] == TruthState.MEASURED]
        conflicted_facts = [f for f in facts if f["truth_state"] == TruthState.CONFLICTED]

        # Check financial truth state
        rev_fact = next((f for f in facts if f["subject"] == "financials" and f["predicate"] == "revenue"), None)
        cost_fact = next((f for f in facts if f["subject"] == "financials" and f["predicate"] == "cost"), None)

        return {
            "total_facts": len(facts),
            "measured_facts_count": len(measured_facts),
            "conflicted_facts_count": len(conflicted_facts),
            "revenue_truth_state": rev_fact["truth_state"] if rev_fact else TruthState.UNAVAILABLE,
            "revenue_value": rev_fact["object_val"] if rev_fact else "UNAVAILABLE",
            "cost_truth_state": cost_fact["truth_state"] if cost_fact else TruthState.UNAVAILABLE,
            "cost_value": cost_fact["object_val"] if cost_fact else "UNAVAILABLE",
            "status": "HEALTHY" if not conflicted_facts else "DATA_CONFLICT"
        }
