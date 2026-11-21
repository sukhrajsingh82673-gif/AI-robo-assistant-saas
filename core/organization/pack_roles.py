"""
ZONATA Industry Pack Role and Organization Mapping (OpenCode Step 2D)

Maps declarative industry blueprints into initial corporate hierarchies.
Allows two companies with different industry packs to instantiate structurally
distinct, domain-tailored organizations using identical execution code.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from core.organization.types import OrgLevel


INDUSTRY_ORG_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # SaaS Enterprise Blueprint (ISIC J62: Software & Cloud Platforms)
    # -------------------------------------------------------------------------
    "saas_enterprise": {
        "industry_code": "J62",
        "industry_name": "B2B SaaS & Cloud Platforms",
        "departments": [
            {"code": "EXEC", "name": "Executive Leadership", "budget_minor_units": 200_000_000},
            {"code": "ENG", "name": "Cloud Engineering & Platform", "budget_minor_units": 150_000_000},
            {"code": "REV", "name": "Revenue Operations & Sales", "budget_minor_units": 100_000_000},
            {"code": "FIN", "name": "Finance, Accounting & Legal", "budget_minor_units": 50_000_000},
        ],
        "positions": [
            {
                "pos_key": "ceo",
                "title": "Chief Executive Officer",
                "level": OrgLevel.CEO,
                "dept_code": "EXEC",
                "reports_to_key": None,
                "authority_grade": "G9",
                "spend_limit_minor_units": 100_000_000,
                "kra_kpi_set": ["ARR_GROWTH", "NET_REVENUE_RETENTION", "RUNWAY_MONTHS"],
                "allowed_tools": ["all"],
            },
            {
                "pos_key": "cto",
                "title": "Chief Technology Officer",
                "level": OrgLevel.C_SUITE,
                "dept_code": "ENG",
                "reports_to_key": "ceo",
                "authority_grade": "G8",
                "spend_limit_minor_units": 25_000_000,
                "kra_kpi_set": ["SYSTEM_UPTIME", "SECURITY_VULNERABILITY_SLO", "DEPLOY_FREQUENCY"],
                "allowed_tools": ["cloud.infra", "code.deploy", "db.admin"],
            },
            {
                "pos_key": "vp_eng",
                "title": "VP of Engineering",
                "level": OrgLevel.DIRECTOR,
                "dept_code": "ENG",
                "reports_to_key": "cto",
                "authority_grade": "G7",
                "spend_limit_minor_units": 10_000_000,
                "kra_kpi_set": ["SPRINT_VELOCITY", "BUG_RESOLUTION_TIME"],
                "allowed_tools": ["cloud.infra", "code.review"],
            },
            {
                "pos_key": "lead_eng",
                "title": "Lead Platform Engineer",
                "level": OrgLevel.TEAM_LEAD,
                "dept_code": "ENG",
                "reports_to_key": "vp_eng",
                "authority_grade": "G5",
                "spend_limit_minor_units": 1_000_000,
                "kra_kpi_set": ["CODE_QUALITY_SCORE", "LATENCY_P99"],
                "allowed_tools": ["code.write", "test.run"],
            },
            {
                "pos_key": "vp_sales",
                "title": "VP of Global Sales",
                "level": OrgLevel.DIRECTOR,
                "dept_code": "REV",
                "reports_to_key": "ceo",
                "authority_grade": "G7",
                "spend_limit_minor_units": 10_000_000,
                "kra_kpi_set": ["QUOTA_ATTAINMENT", "PIPELINE_COVERAGE"],
                "allowed_tools": ["crm.read", "crm.write", "email.send"],
            },
            {
                "pos_key": "ae",
                "title": "Enterprise Account Executive",
                "level": OrgLevel.EMPLOYEE,
                "dept_code": "REV",
                "reports_to_key": "vp_sales",
                "authority_grade": "G4",
                "spend_limit_minor_units": 500_000,
                "kra_kpi_set": ["CLOSED_WON_ACV", "DISCOVERY_CALLS_HELD"],
                "allowed_tools": ["crm.write", "email.send"],
            },
            {
                "pos_key": "head_fin",
                "title": "Head of Finance & Accounting",
                "level": OrgLevel.DIRECTOR,
                "dept_code": "FIN",
                "reports_to_key": "ceo",
                "authority_grade": "G7",
                "spend_limit_minor_units": 15_000_000,
                "kra_kpi_set": ["DAYS_SALES_OUTSTANDING", "CLOSE_CYCLE_DAYS"],
                "allowed_tools": ["ledger.read", "ledger.post", "banking.view"],
            },
        ],
    },

    # -------------------------------------------------------------------------
    # Outpatient Clinic Blueprint (ISIC Q86: Human Healthcare Activities)
    # -------------------------------------------------------------------------
    "clinic_health": {
        "industry_code": "Q86",
        "industry_name": "Outpatient Healthcare Clinic & Practice",
        "departments": [
            {"code": "EXEC", "name": "Practice Leadership", "budget_minor_units": 100_000_000},
            {"code": "CLIN", "name": "Clinical & Patient Care", "budget_minor_units": 80_000_000},
            {"code": "OPS", "name": "Clinic Administration & Facilities", "budget_minor_units": 40_000_000},
            {"code": "BILL", "name": "Medical Billing & Statutory Compliance", "budget_minor_units": 30_000_000},
        ],
        "positions": [
            {
                "pos_key": "ceo",
                "title": "Medical Director & Practice Principal",
                "level": OrgLevel.CEO,
                "dept_code": "EXEC",
                "reports_to_key": None,
                "authority_grade": "G9",
                "spend_limit_minor_units": 50_000_000,
                "kra_kpi_set": ["PATIENT_OUTCOMES_INDEX", "CLINICAL_PROTOCOL_ADHERENCE", "HIPAA_AUDIT_PASS_RATE"],
                "allowed_tools": ["all"],
            },
            {
                "pos_key": "practice_mgr",
                "title": "Clinical Practice Operations Manager",
                "level": OrgLevel.MANAGER,
                "dept_code": "OPS",
                "reports_to_key": "ceo",
                "authority_grade": "G7",
                "spend_limit_minor_units": 10_000_000,
                "kra_kpi_set": ["APPOINTMENT_UTILIZATION_RATE", "AVERAGE_WAIT_TIME_MINUTES"],
                "allowed_tools": ["calendar.manage", "supplies.order", "staff.roster"],
            },
            {
                "pos_key": "head_nurse",
                "title": "Clinical Nurse Supervisor",
                "level": OrgLevel.SUPERVISOR,
                "dept_code": "CLIN",
                "reports_to_key": "practice_mgr",
                "authority_grade": "G6",
                "spend_limit_minor_units": 3_000_000,
                "kra_kpi_set": ["TRIAGE_ACCURACY_RATE", "MEDICATION_ADMINISTRATION_ACCURACY"],
                "allowed_tools": ["emr.triage", "medical_devices.read"],
            },
            {
                "pos_key": "staff_nurse",
                "title": "Registered Triage Nurse",
                "level": OrgLevel.EMPLOYEE,
                "dept_code": "CLIN",
                "reports_to_key": "head_nurse",
                "authority_grade": "G4",
                "spend_limit_minor_units": 500_000,
                "kra_kpi_set": ["PATIENT_INTAKE_COMPLETION", "VITAL_SIGNS_ACCURACY"],
                "allowed_tools": ["emr.intake", "patient.comm"],
            },
            {
                "pos_key": "compliance_off",
                "title": "HIPAA & Statutory Privacy Officer",
                "level": OrgLevel.MANAGER,
                "dept_code": "BILL",
                "reports_to_key": "ceo",
                "authority_grade": "G7",
                "spend_limit_minor_units": 5_000_000,
                "kra_kpi_set": ["PHI_ACCESS_AUDIT_SCORE", "STATUTORY_FILING_TIMELINESS"],
                "allowed_tools": ["audit.logs", "compliance.certify"],
            },
            {
                "pos_key": "billing_spec",
                "title": "Medical Billing & Claims Specialist",
                "level": OrgLevel.EMPLOYEE,
                "dept_code": "BILL",
                "reports_to_key": "practice_mgr",
                "authority_grade": "G4",
                "spend_limit_minor_units": 1_000_000,
                "kra_kpi_set": ["CLEAN_CLAIMS_RATE", "DENIAL_RESOLUTION_RATE"],
                "allowed_tools": ["claims.submit", "ledger.post"],
            },
        ],
    },
}


def resolve_org_template_for_pack(pack_id: str, industry_code: Optional[str] = None) -> Dict[str, Any]:
    """Resolves matching organization blueprint template by pack_id or ISIC code."""
    if pack_id in INDUSTRY_ORG_TEMPLATES:
        return INDUSTRY_ORG_TEMPLATES[pack_id]

    # Search by ISIC code
    if industry_code:
        for tpl in INDUSTRY_ORG_TEMPLATES.values():
            if tpl.get("industry_code") == industry_code:
                return tpl

    # Check substring matches (e.g. saas, clinic)
    lower_pack = pack_id.lower()
    if "saas" in lower_pack or "tech" in lower_pack:
        return INDUSTRY_ORG_TEMPLATES["saas_enterprise"]
    if "clinic" in lower_pack or "health" in lower_pack or "medical" in lower_pack:
        return INDUSTRY_ORG_TEMPLATES["clinic_health"]

    # Fallback default general operating structure
    return {
        "industry_code": "GENERIC",
        "industry_name": "General Commercial Enterprise",
        "departments": [
            {"code": "EXEC", "name": "Executive Office", "budget_minor_units": 50_000_000},
            {"code": "OPS", "name": "Operations & Fulfillment", "budget_minor_units": 30_000_000},
        ],
        "positions": [
            {
                "pos_key": "ceo",
                "title": "Chief Executive Officer",
                "level": OrgLevel.CEO,
                "dept_code": "EXEC",
                "reports_to_key": None,
                "authority_grade": "G9",
                "spend_limit_minor_units": 50_000_000,
                "kra_kpi_set": ["OVERALL_PROFITABILITY"],
                "allowed_tools": ["all"],
            },
            {
                "pos_key": "ops_mgr",
                "title": "General Operations Manager",
                "level": OrgLevel.MANAGER,
                "dept_code": "OPS",
                "reports_to_key": "ceo",
                "authority_grade": "G7",
                "spend_limit_minor_units": 10_000_000,
                "kra_kpi_set": ["OPERATIONAL_EFFICIENCY"],
                "allowed_tools": ["ops.manage"],
            },
        ],
    }
