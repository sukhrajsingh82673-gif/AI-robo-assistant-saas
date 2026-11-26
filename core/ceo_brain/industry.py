"""
ZONATA Universal AI Company OS — Data-Driven Industry Understanding Engine
Strict adherence to Rule 17 & Sub-step 1H: Zero hardcoded branching on industry names.
All industry-specific models, revenue engines, and KPIs are loaded dynamically
from declarative zonata.industry-pack/v1 blueprints and UN ISIC Rev. 4 taxonomy.
"""

from typing import Any, Dict, List, Optional
from core.industry_packs.isic import get_isic_details, validate_isic_code
from core.industry_packs.registry import industry_pack_registry


class IndustryUnderstandingEngine:
    """Discovers industry-specific revenue engines, cost structures, and KPI hierarchies
    purely from declarative industry packs and UN ISIC Rev. 4 taxonomy.
    """

    @classmethod
    def analyze_industry(
        cls, industry_name_or_code: str, business_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyzes an industry using registered declarative packs and UN ISIC taxonomy."""
        target = (industry_name_or_code or "").strip()

        # 1. Lookup in declarative IndustryPackRegistry by ISIC code or pack_id
        matched_pack = industry_pack_registry.find_by_isic(target)
        if not matched_pack:
            # Check by pack_id, name, or declarative aliases in registered packs
            for pack_meta in industry_pack_registry.list_packs():
                p_id = pack_meta["pack_id"]
                p_name = pack_meta["name"].lower()
                aliases = [str(a).lower() for a in pack_meta.get("aliases", [])]
                t = target.lower()
                if t in p_id.lower() or t in p_name or any(a in t or t in a for a in aliases):
                    matched_pack = industry_pack_registry.get_pack(p_id)
                    break

        if matched_pack:
            meta = matched_pack.get("metadata", {})
            coa = matched_pack.get("chart_of_accounts", [])
            revenue_engines = [a["name"] for a in coa if a.get("type") == "REVENUE"]
            cost_drivers = [a["name"] for a in coa if a.get("type") == "EXPENSE"]

            return {
                "industry": meta.get("name", target),
                "isic_code": meta.get("industry_code"),
                "identified_domain": True,
                "pack_id": meta.get("pack_id"),
                "revenue_engines": revenue_engines or ["Subscription Revenue", "Direct Sales"],
                "cost_drivers": cost_drivers or ["Operational Expenses", "COGS"],
                "standard_kpis": meta.get("standard_kpis") or meta.get("kpis") or [
                    {"name": "Gross Contribution Margin", "unit": "%", "benchmark": 30.0},
                    {"name": "Operating Cost Ratio", "unit": "%", "benchmark": 70.0},
                ],
                "common_leakage_vectors": ["Billing delays", "Cost overruns", "Capacity dead time"],
            }

        # 2. Lookup in UN ISIC Rev. 4 taxonomy
        isic_meta = get_isic_details(target)
        if isic_meta:
            return {
                "industry": isic_meta["name"],
                "isic_code": isic_meta["code"],
                "isic_section": isic_meta["section"],
                "identified_domain": True,
                "pack_id": None,
                "revenue_engines": [f"{isic_meta['name']} Sales", "Contract Billings"],
                "cost_drivers": ["Labor", "Direct Operations", "Facility Overhead"],
                "standard_kpis": [
                    {"name": "Operating Margin", "unit": "%", "benchmark": 20.0},
                ],
                "common_leakage_vectors": ["Operational inefficiencies", "Overhead variance"],
            }

        # 3. Dynamic generic fallback when unclassified
        return {
            "industry": target or "Commercial Operations",
            "isic_code": None,
            "identified_domain": False,
            "pack_id": None,
            "revenue_engines": ["Direct Sales", "Client Engagements", "Service Contracts"],
            "cost_drivers": ["Operational Expenses", "Personnel", "Technology / Software", "Marketing"],
            "standard_kpis": [
                {"name": "Gross Contribution Margin", "unit": "%", "benchmark": 25.0},
                {"name": "Revenue Growth MoM", "unit": "%", "benchmark": 10.0},
                {"name": "Operating Cost Ratio", "unit": "%", "benchmark": 75.0},
            ],
            "common_leakage_vectors": ["SaaS tool sprawl", "Process bottlenecks", "Billing delay"],
        }
