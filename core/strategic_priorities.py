"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Strategic Priority Engine
Maintains structural corporate priorities (P0, P1, P2, P3) backed by ExecutiveDecisionRecords.

Constitutional Invariants:
  NO_ARBITRARY_PRIORITY_MUTATION (Priority changes strictly require an immutable ExecutiveDecisionRecord)
  STRUCTURED_PRIORITY_TAXONOMY (P0 Critical, P1 Strategic, P2 Operational, P3 Opportunistic)
  AUDITED_DECISION_RECEIPT (Every priority shift records evidence, affected departments, and budget impact)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class PriorityLevel:
    P0 = "P0"  # Critical (Urgent threat, system outage, existential margin collapse)
    P1 = "P1"  # Strategic (Core quarterly goals, primary revenue drivers)
    P2 = "P2"  # Operational (Routine optimization, secondary tasks)
    P3 = "P3"  # Opportunistic (Discovered opportunities, nice-to-haves)

class ItemType:
    OBJECTIVE = "OBJECTIVE"
    STRATEGY = "STRATEGY"
    MISSION = "MISSION"
    DEPARTMENT = "DEPARTMENT"

@dataclass
class StrategicPriorityEntry:
    priority_id: str
    tenant_id: str
    company_id: str
    item_type: str
    item_id: str
    priority_level: str
    reason: str
    evidence_ref: Optional[str] = None
    decision_record_id: Optional[str] = None
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class StrategicPriorityEngine:
    """
    Governs strategic prioritization across corporate objectives, strategies, and missions.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def set_priority(
        self,
        item_type: str,
        item_id: str,
        new_priority: str,
        reason: str,
        evidence_ref: str,
        affected_departments: Optional[List[str]] = None,
        affected_missions: Optional[List[str]] = None,
        affected_budgets: Optional[Dict[str, float]] = None,
        authority: str = "AI_CEO_GOVERNED"
    ) -> Dict[str, Any]:
        """
        Sets or updates priority. Automatically creates an ExecutiveDecisionRecord
        and links it in database.
        """
        valid_priorities = [PriorityLevel.P0, PriorityLevel.P1, PriorityLevel.P2, PriorityLevel.P3]
        if new_priority not in valid_priorities:
            raise ValueError(f"Invalid priority level {new_priority}. Must be one of {valid_priorities}")

        now = time.time()
        with db.get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM strategic_priorities WHERE tenant_id = ? AND company_id = ? AND item_type = ? AND item_id = ?",
                (self.tenant_id, self.company_id, item_type, item_id)
            ).fetchone()

            prev_priority = existing["priority_level"] if existing else "P2"
            priority_id = existing["priority_id"] if existing else f"prio_{uuid.uuid4().hex[:10]}"

            # Generate immutable ExecutiveDecisionRecord in executive_decisions
            decision_id = f"dec_prio_{uuid.uuid4().hex[:10]}"
            conn.execute("""
                INSERT INTO executive_decisions (
                    decision_id, tenant_id, company_id, title, decision_type,
                    problem_statement, alternatives_considered, selected_option,
                    rationale, constraints, authority_required, approval_status,
                    evidence_refs, outcome, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id, self.tenant_id, self.company_id,
                f"Priority shift for {item_type}:{item_id} ({prev_priority} -> {new_priority})",
                "PRIORITY_UPDATE",
                f"Evaluation of operational importance for {item_type} {item_id}",
                json.dumps([prev_priority, new_priority]),
                new_priority,
                reason,
                json.dumps({"affected_departments": affected_departments or [], "affected_missions": affected_missions or []}),
                authority,
                "APPROVED",  # Internal CEO prioritization within granted operational authority
                json.dumps([evidence_ref] if evidence_ref else []),
                json.dumps({"previous_priority": prev_priority, "new_priority": new_priority, "budget_impact": affected_budgets or {}}),
                now, now
            ))

            # Upsert strategic_priorities
            conn.execute("""
                INSERT INTO strategic_priorities (
                    priority_id, tenant_id, company_id, item_type, item_id,
                    priority_level, reason, evidence_ref, decision_record_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(priority_id) DO UPDATE SET
                    priority_level=excluded.priority_level,
                    reason=excluded.reason,
                    evidence_ref=excluded.evidence_ref,
                    decision_record_id=excluded.decision_record_id,
                    updated_at=excluded.updated_at
            """, (
                priority_id, self.tenant_id, self.company_id, item_type, item_id,
                new_priority, reason, evidence_ref, decision_id, now
            ))
            conn.commit()

        create_executive_event(
            event_type="PriorityChanged",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "priority_id": priority_id,
                "item_type": item_type,
                "item_id": item_id,
                "previous_priority": prev_priority,
                "new_priority": new_priority,
                "decision_record_id": decision_id,
                "reason": reason
            }
        )

        return {
            "priority_id": priority_id,
            "item_type": item_type,
            "item_id": item_id,
            "previous_priority": prev_priority,
            "new_priority": new_priority,
            "decision_record_id": decision_id,
            "updated_at": now
        }

    def get_priority(self, item_type: str, item_id: str) -> Optional[StrategicPriorityEntry]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM strategic_priorities WHERE tenant_id = ? AND company_id = ? AND item_type = ? AND item_id = ?",
                (self.tenant_id, self.company_id, item_type, item_id)
            ).fetchone()
            if not r:
                return None
            return StrategicPriorityEntry(
                priority_id=r["priority_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                item_type=r["item_type"],
                item_id=r["item_id"],
                priority_level=r["priority_level"],
                reason=r["reason"],
                evidence_ref=r["evidence_ref"],
                decision_record_id=r["decision_record_id"],
                updated_at=r["updated_at"]
            )

    def list_priorities(self, priority_level: Optional[str] = None) -> List[StrategicPriorityEntry]:
        with db.get_connection() as conn:
            if priority_level:
                rows = conn.execute(
                    "SELECT * FROM strategic_priorities WHERE tenant_id = ? AND company_id = ? AND priority_level = ? ORDER BY updated_at DESC",
                    (self.tenant_id, self.company_id, priority_level)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM strategic_priorities WHERE tenant_id = ? AND company_id = ? ORDER BY priority_level ASC, updated_at DESC",
                    (self.tenant_id, self.company_id)
                ).fetchall()

            return [
                StrategicPriorityEntry(
                    priority_id=r["priority_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    item_type=r["item_type"],
                    item_id=r["item_id"],
                    priority_level=r["priority_level"],
                    reason=r["reason"],
                    evidence_ref=r["evidence_ref"],
                    decision_record_id=r["decision_record_id"],
                    updated_at=r["updated_at"]
                ) for r in rows
            ]
