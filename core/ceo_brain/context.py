"""
RoboAssistant Company OS 2.0 — CEO Context Engine
Builds minimal, relevant, fresh, source-attributed, permission-filtered,
and company-isolated context packages for executive decision making.
Rule: Never send the entire database to an LLM context window.
"""

from typing import Dict, Any, List, Optional
import time
from .state import CEOCompanyState, CEOStateEngine
from ..intelligence import RiskEngine, OpportunityEngine
from ..memory import OrganizationalMemory

class CEOContextEngine:
    """
    Constructs bounded, epistemic context packages for CEO decisions.
    """

    @classmethod
    def assemble_context_package(
        cls,
        tenant_id: str,
        company_id: str,
        intent: str,
        domain_focus: Optional[str] = None
    ) -> Dict[str, Any]:
        state = CEOStateEngine.get_or_build_state(tenant_id, company_id)
        now = time.time()

        # 1. Financial Context (filtered)
        financial_summary = {
            "gross_revenue": f"₹ {state.gross_revenue:,.2f}",
            "operating_cost": f"₹ {state.operating_cost:,.2f}",
            "net_contribution": f"₹ {state.contribution_margin:,.2f}",
            "margin_pct": f"{(state.contribution_margin / state.gross_revenue * 100):.1f}%" if state.gross_revenue > 0 else "0.0%",
            "discretionary_budget_available": f"₹ {max(0.0, state.discretionary_budget_limit - state.discretionary_budget_spent):,.2f}"
        }

        # 2. Epistemic Facts (source-attributed with freshness)
        epistemic_facts = []
        for k, f in state.facts.items():
            freshness_sec = int(now - f["timestamp"])
            freshness_label = f"{freshness_sec}s ago" if freshness_sec < 60 else f"{freshness_sec // 60}m ago"
            epistemic_facts.append({
                "metric": k,
                "value": f["value"],
                "source": f["source"],
                "truth_state": f["truth_state"],
                "freshness": freshness_label,
                "confidence": f["confidence"]
            })

        # 3. Active Risks & Opportunities
        risks = RiskEngine.list_intelligence_items(tenant_id, company_id)
        active_risks = [r for r in risks if r.get("item_type") == "RISK"][:5]
        active_opportunities = [r for r in risks if r.get("item_type") == "OPPORTUNITY"][:5]

        # 4. Relevant Policies & Memory
        memories = OrganizationalMemory.query_memory(tenant_id, company_id=company_id)[:5]

        return {
            "context_id": f"ctx_{int(now * 1000)}",
            "company_name": state.name,
            "industry": state.industry,
            "business_model": state.business_model,
            "intent": intent,
            "domain_focus": domain_focus or "GENERAL_EXECUTIVE",
            "financial_state": financial_summary,
            "epistemic_facts": epistemic_facts,
            "workforce_departments": state.departments,
            "active_risks": [{"title": r["title"], "impact": r.get("potential_impact"), "evidence": r.get("evidence")} for r in active_risks],
            "active_opportunities": [{"title": o["title"], "impact": o.get("potential_impact")} for o in active_opportunities],
            "relevant_policies": state.operating_rules,
            "owner_preferences": state.owner_preferences,
            "relevant_memory": [m["content"] for m in memories],
            "generated_at": now
        }
