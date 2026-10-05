"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Executive Attention & Event Priority Manager

Implements Section 12 of the Gemma 4 Master Specification:
- Continuously ranks executive events and operational variances across 10 dimensions:
    1. Urgency
    2. Financial Impact
    3. Customer Impact
    4. Operational Impact
    5. Security Impact
    6. Legal / Compliance Impact
    7. Strategic Importance
    8. Deadline Proximity
    9. Dependency Blocking
    10. Failure Severity
- Gemma 4 cognitive model recommends priority; deterministic ZONATA policy validates.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.executive.attention")

@dataclass
class ExecutiveAttentionItem:
    item_id: str
    tenant_id: str
    company_id: str
    title: str
    category: str                      # APPROVAL, INCIDENT, DRIFT, DEADLINE, RISK, OPPORTUNITY
    source_department: str
    description: str
    urgency_score: float               # 0.0 - 10.0
    financial_impact_inr: float
    customer_impact_score: float       # 0.0 - 10.0
    operational_impact_score: float    # 0.0 - 10.0
    security_impact_score: float       # 0.0 - 10.0
    compliance_impact_score: float     # 0.0 - 10.0
    failure_severity: str              # NONE, LOW, MEDIUM, HIGH, CRITICAL
    model_recommended_priority: str    # P0, P1, P2, P3
    validated_priority: str            # Validated by deterministic policy
    requires_human_owner: bool
    status: str = "OPEN"               # OPEN, IN_REVIEW, RESOLVED, DISMISSED
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutiveAttentionManager:
    """
    Ranks and manages executive attention to prevent CEO cognitive overload.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._items: Dict[str, ExecutiveAttentionItem] = {}

    def register_event(
        self,
        item_id: str,
        title: str,
        category: str,
        source_department: str,
        description: str,
        financial_impact_inr: float = 0.0,
        security_score: float = 0.0,
        urgency_score: float = 5.0,
        customer_score: float = 5.0,
        operational_score: float = 5.0,
        compliance_score: float = 0.0,
        failure_severity: str = "LOW",
        model_recommended_prio: str = "P2"
    ) -> ExecutiveAttentionItem:
        # Deterministic Policy Validation
        validated_prio = model_recommended_prio
        requires_owner = False

        # Rule 1: High financial impact (> 50,000 INR) or critical security/compliance is P0/P1
        if financial_impact_inr > 100000.0 or security_score >= 8.0 or failure_severity == "CRITICAL":
            validated_prio = "P0"
            requires_owner = True
        elif financial_impact_inr > 50000.0 or urgency_score >= 8.0 or compliance_score >= 7.0:
            if validated_prio not in ("P0", "P1"):
                validated_prio = "P1"
            requires_owner = True

        itm = ExecutiveAttentionItem(
            item_id=item_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title=title,
            category=category,
            source_department=source_department,
            description=description,
            urgency_score=urgency_score,
            financial_impact_inr=financial_impact_inr,
            customer_impact_score=customer_score,
            operational_impact_score=operational_score,
            security_impact_score=security_score,
            compliance_impact_score=compliance_score,
            failure_severity=failure_severity,
            model_recommended_priority=model_recommended_prio,
            validated_priority=validated_prio,
            requires_human_owner=requires_owner,
            created_at=time.time()
        )
        self._items[item_id] = itm
        return itm

    def get_ranked_attention_queue(self) -> List[ExecutiveAttentionItem]:
        """
        Ranks items by deterministic priority (P0 > P1 > P2 > P3) then composite impact.
        """
        prio_weights = {"P0": 1000, "P1": 500, "P2": 100, "P3": 10}

        def score_func(i: ExecutiveAttentionItem):
            base = prio_weights.get(i.validated_priority, 0)
            impact = (i.urgency_score * 2.0) + (i.security_impact_score * 3.0) + (i.customer_impact_score * 1.5)
            fin = min(100.0, i.financial_impact_inr / 1000.0)
            return base + impact + fin

        open_items = [itm for itm in self._items.values() if itm.status == "OPEN"]
        return sorted(open_items, key=score_func, reverse=True)
