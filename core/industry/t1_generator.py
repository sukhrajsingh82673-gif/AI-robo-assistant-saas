"""
Automated T1 Overlay Generator (Step 8C)
========================================
Generates compilable T1 industry overlays for every division of ISIC Rev. 5.
Contains only taxonomy-derived metadata, vocabulary, generic chart of accounts,
standard folios, and hard sector boundaries (Rule 68, Rule 69, Rule 72).
"""

from typing import Dict, Any, List
from core.industry.taxonomy.taxonomy_manager import TaxonomyManager
from core.industry.schema import validate_industry_overlay_dict, compute_overlay_digest


def generate_t1_overlay_for_division(division_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a compilable T1 overlay specification from an ISIC Rev. 5 division record."""
    div_code = division_dict["division_code"]
    sec = division_dict["section"]
    title = division_dict["title"]
    industry_id = division_dict["industry_id"]
    vocabulary = division_dict.get("vocabulary", [])

    overlay_spec = {
        "schema_version": "zonata.industry-overlay/v1",
        "metadata": {
            "industry_id": industry_id,
            "title": title,
            "version": "1.0.0",
            "tier": "T1",
            "section": sec,
            "division": div_code,
        },
        "classification_codes": [
            {
                "scheme": "ISIC",
                "version": "Rev.5",
                "code": div_code,
                "is_primary": True,
            },
            {
                "scheme": "ISIC",
                "version": "Rev.4",
                "code": div_code,
            },
            {
                "scheme": "NACE",
                "version": "Rev.2.1",
                "code": f"{sec}.{div_code}",
            },
        ],
        "sector_vocabulary": vocabulary,
        "chart_of_accounts": [
            {"code": "1000", "name": f"Operating Cash ({sec}{div_code})", "type": "ASSET", "currency": "USD"},
            {"code": "2000", "name": f"Operating Payables ({sec}{div_code})", "type": "LIABILITY", "currency": "USD"},
            {"code": "4000", "name": f"Operating Revenue - {title[:30]}", "type": "REVENUE", "currency": "USD"},
            {"code": "5000", "name": f"Cost of Operations ({sec}{div_code})", "type": "EXPENSE", "currency": "USD"},
        ],
        "folio_types": [
            {
                "folio_type": f"folio_{sec.lower()}{div_code}_operations",
                "description": f"Standard operational folio for {title}",
                "required_documents": [f"doc_{sec.lower()}{div_code}_statement"],
            }
        ],
        "document_types": [
            {
                "template_id": f"doc_{sec.lower()}{div_code}_statement",
                "name": f"{title[:40]} Operational Statement",
                "default_retention_days": 365,
            }
        ],
        "calculators": [
            {
                "calculator_id": f"turnover_calc_{sec.lower()}{div_code}",
                "name": "Standard Operational Margin Ratio",
                "formula": "operating_profit / gross_revenue",
                "data_source": "department_pnl_folio",
                "golden_tests": [
                    {"inputs": {"operating_profit": 20000, "gross_revenue": 100000}, "expected_output": 0.20},
                ],
            }
        ],
        "regulatory_register": [
            {
                "jurisdiction": "GLOBAL",
                "cite": f"UN ISIC Rev. 5 Explanatory Notes Division {div_code}",
                "effective_date": "2024-01-01",
                "status": "UNVERIFIED",
            }
        ],
        "boundary_policies": [
            {
                "policy_id": "standard_safe_operational_bounds",
                "prohibited_terms": ["unauthorized wire", "tamper ledger"],
                "rejection_message": "Standard operational safety boundary violation.",
            }
        ],
    }

    # Validate schema compliance
    validate_industry_overlay_dict(overlay_spec)
    overlay_spec["content_digest"] = compute_overlay_digest(overlay_spec)
    return overlay_spec


def generate_all_isic_rev5_t1_overlays() -> List[Dict[str, Any]]:
    """Generates T1 overlays for every single division defined in ISIC Rev. 5."""
    tm = TaxonomyManager()
    isic5 = tm.get_isic_rev5()
    overlays = []
    for div in isic5.get("divisions", []):
        ov = generate_t1_overlay_for_division(div)
        overlays.append(ov)
    return overlays
