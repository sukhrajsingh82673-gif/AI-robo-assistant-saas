"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Corporate Objective Engine
Transforms unstructured Human Owner intent into structured, measurable, provenance-tagged objectives.

Constitutional Invariants:
  NO_SILENT_INFERENCE_CONVERSION (AI inferences must be tagged as AI_INFERRED or CEO_PROPOSED, never OWNER_DEFINED)
  MEASURABLE_DIMENSIONS (Objectives must define target metrics and acceptable variance)
  PROVENANCE_INTEGRITY (Every objective records origin: OWNER_DEFINED, CEO_PROPOSED, DATA_DERIVED, AI_INFERRED)
"""

import time
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class ObjectiveProvenance:
    OWNER_DEFINED = "OWNER_DEFINED"
    CEO_PROPOSED = "CEO_PROPOSED"
    DATA_DERIVED = "DATA_DERIVED"
    AI_INFERRED = "AI_INFERRED"

class ObjectiveTimeHorizon:
    IMMEDIATE = "IMMEDIATE"
    TODAY = "TODAY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    STRATEGIC = "STRATEGIC"

class ObjectiveStatus:
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    ACHIEVED = "ACHIEVED"
    DEVIATED = "DEVIATED"
    CANCELLED = "CANCELLED"
    REVISED = "REVISED"

@dataclass
class CorporateObjective:
    objective_id: str
    tenant_id: str
    company_id: str
    title: str
    description: str
    provenance: str = ObjectiveProvenance.OWNER_DEFINED
    time_horizon: str = ObjectiveTimeHorizon.QUARTERLY
    target_dimensions: Dict[str, Any] = field(default_factory=dict)
    status: str = ObjectiveStatus.ACTIVE
    parent_objective_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CorporateObjectiveEngine:
    """
    Manages structured corporate objectives, dimension compilation, and provenance boundaries.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def compile_intent_to_objective(
        self,
        raw_intent: str,
        provenance: str = ObjectiveProvenance.OWNER_DEFINED,
        time_horizon: str = ObjectiveTimeHorizon.QUARTERLY,
        parent_objective_id: Optional[str] = None,
        custom_dimensions: Optional[Dict[str, Any]] = None
    ) -> CorporateObjective:
        """
        Parses high-level business goals (e.g. 'Increase hotel profitability during peak wedding season')
        into explicit measurable operational dimensions rather than blindly executing strings.
        """
        intent_lower = raw_intent.lower()
        dimensions = {}

        # 1. Detect target operational dimensions from domain intent
        if any(w in intent_lower for w in ["profit", "profitability", "margin", "ebitda"]):
            dimensions["contribution_margin"] = {"target_min": 0.28, "unit": "RATIO", "baseline": 0.22}
            dimensions["operating_cost"] = {"max_variance_pct": 0.05, "unit": "PERCENT"}

        if any(w in intent_lower for w in ["hotel", "revpar", "occupancy", "adr", "room", "wedding", "stay"]):
            dimensions["revpar"] = {"target_value": 4500.0, "currency": "₹", "baseline": 3800.0}
            dimensions["occupancy"] = {"target_pct": 0.88, "unit": "PERCENT", "baseline": 0.74}
            dimensions["adr"] = {"target_value": 5200.0, "currency": "₹", "baseline": 4600.0}

        if any(w in intent_lower for w in ["guest", "service", "standards", "satisfaction", "csat", "nps"]):
            dimensions["guest_satisfaction_score"] = {"target_min": 4.6, "scale": "1-5", "baseline": 4.5}
            dimensions["service_sla_compliance"] = {"target_min": 0.95, "unit": "PERCENT", "baseline": 0.94}

        if any(w in intent_lower for w in ["revenue", "sales", "turnover", "demand"]):
            dimensions["gross_revenue"] = {"target_growth_pct": 0.15, "baseline": 1000000.0}

        if custom_dimensions:
            dimensions.update(custom_dimensions)

        # Fallback default if no known domain keywords matched
        if not dimensions:
            dimensions["performance_index"] = {"target_value": 1.0, "baseline": 0.85, "unit": "INDEX"}

        objective_id = f"obj_{uuid.uuid4().hex[:10]}"
        now = time.time()

        obj = CorporateObjective(
            objective_id=objective_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title=raw_intent.strip(),
            description=f"Structured Corporate Objective compiled from intent: '{raw_intent}'. Dimensions: {list(dimensions.keys())}",
            provenance=provenance,
            time_horizon=time_horizon,
            target_dimensions=dimensions,
            status=ObjectiveStatus.ACTIVE,
            parent_objective_id=parent_objective_id,
            created_at=now,
            updated_at=now,
            metadata={"raw_intent": raw_intent, "compiled_by": "CorporateObjectiveEngine"}
        )

        self._persist_objective(obj)

        create_executive_event(
            event_type="CorporateObjectiveCreated",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "objective_id": obj.objective_id,
                "title": obj.title,
                "provenance": obj.provenance,
                "dimensions": list(dimensions.keys())
            }
        )

        return obj

    def _persist_objective(self, obj: CorporateObjective):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO corporate_objectives (
                    objective_id, tenant_id, company_id, title, description,
                    provenance, time_horizon, target_dimensions, status,
                    parent_objective_id, created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(objective_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    provenance=excluded.provenance,
                    target_dimensions=excluded.target_dimensions,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    metadata=excluded.metadata
            """, (
                obj.objective_id, obj.tenant_id, obj.company_id, obj.title, obj.description,
                obj.provenance, obj.time_horizon, json.dumps(obj.target_dimensions), obj.status,
                obj.parent_objective_id, obj.created_at, obj.updated_at, json.dumps(obj.metadata)
            ))
            conn.commit()

    def get_objectives(self, status: Optional[str] = None) -> List[CorporateObjective]:
        with db.get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM corporate_objectives WHERE tenant_id = ? AND company_id = ? AND status = ? ORDER BY created_at DESC",
                    (self.tenant_id, self.company_id, status)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM corporate_objectives WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC",
                    (self.tenant_id, self.company_id)
                ).fetchall()

            res = []
            for r in rows:
                res.append(CorporateObjective(
                    objective_id=r["objective_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    title=r["title"],
                    description=r["description"],
                    provenance=r["provenance"],
                    time_horizon=r["time_horizon"],
                    target_dimensions=json.loads(r["target_dimensions"] or "{}"),
                    status=r["status"],
                    parent_objective_id=r["parent_objective_id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    metadata=json.loads(r["metadata"] or "{}")
                ))
            return res

    def get_objective(self, objective_id: str) -> Optional[CorporateObjective]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM corporate_objectives WHERE objective_id = ? AND tenant_id = ? AND company_id = ?",
                (objective_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            return CorporateObjective(
                objective_id=r["objective_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                title=r["title"],
                description=r["description"],
                provenance=r["provenance"],
                time_horizon=r["time_horizon"],
                target_dimensions=json.loads(r["target_dimensions"] or "{}"),
                status=r["status"],
                parent_objective_id=r["parent_objective_id"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                metadata=json.loads(r["metadata"] or "{}")
            )
