"""
RoboAssistant Company OS 2.0 — CEO Learning Engine & Strategic Memory
Records prediction vs reality variance, analyzes root causes of failures,
and converts verified outcomes into organizational lessons.
"""

from typing import Dict, Any, List, Optional
import time
import uuid

class CEOLearningEngine:
    """
    Maintains long-term strategic and failure memory to ensure the AI CEO continuously improves.
    """
    _LEARNING_RECORDS: List[Dict[str, Any]] = []

    @classmethod
    def record_learning_event(
        cls,
        tenant_id: str,
        company_id: str,
        decision_id: str,
        predicted_outcome: str,
        actual_outcome: str,
        variance_summary: str,
        root_cause: str,
        strategic_lesson: str,
        updated_policy_rule: Optional[str] = None
    ) -> Dict[str, Any]:
        event_id = f"lrn_{uuid.uuid4().hex[:8]}"
        record = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "decision_id": decision_id,
            "predicted_outcome": predicted_outcome,
            "actual_outcome": actual_outcome,
            "variance_summary": variance_summary,
            "root_cause": root_cause,
            "strategic_lesson": strategic_lesson,
            "updated_policy_rule": updated_policy_rule,
            "recorded_at": time.time()
        }
        cls._LEARNING_RECORDS.append(record)
        return record

    @classmethod
    def query_lessons(
        cls,
        tenant_id: str,
        company_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        results = [
            r for r in cls._LEARNING_RECORDS
            if r["tenant_id"] == tenant_id and (not company_id or r["company_id"] == company_id)
        ]
        return sorted(results, key=lambda x: x["recorded_at"], reverse=True)[:limit]
