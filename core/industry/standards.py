"""
Standards & Protocols Registry (Rule 70)
========================================
Catalogs open and paid industry data standards by identifier.
Copyrighted or paid standards are referenced by identifier and title only and
never reproduced without an active owner license.
"""

from typing import Dict, Any, List, Optional


class StandardLicenseType:
    OPEN = "OPEN_DATA_STANDARD"
    PAID_LICENSED = "PAID_PROPRIETARY_STANDARD"
    RESTRICTED = "BOUNDARY_LEGAL_REVIEW"


STANDARDS_CATALOG: Dict[str, Dict[str, Any]] = {
    "FHIR_R4": {
        "standard_id": "FHIR_R4",
        "title": "Fast Healthcare Interoperability Resources (HL7 FHIR Release 4)",
        "governing_body": "Health Level Seven International (HL7)",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_healthcare_operations_q86"],
        "has_adapter": True,
    },
    "ISO_20022": {
        "standard_id": "ISO_20022",
        "title": "Universal Financial Industry Message Scheme (ISO 20022)",
        "governing_body": "International Organization for Standardization (ISO)",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_banking_lending_k64", "ind_insurance_k65"],
        "has_adapter": True,
    },
    "GS1_EPCIS_2_0": {
        "standard_id": "GS1_EPCIS_2_0",
        "title": "Electronic Product Code Information Services (EPCIS) 2.0",
        "governing_body": "GS1 Global",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_retail_ecommerce_g47", "ind_logistics_freight_h52", "ind_food_manufacturing_c10"],
        "has_adapter": True,
    },
    "IFC_4_3": {
        "standard_id": "IFC_4_3",
        "title": "Industry Foundation Classes (IFC 4.3 / ISO 16739-1)",
        "governing_body": "buildingSMART International",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_construction_real_estate_f41"],
        "has_adapter": True,
    },
    "OPC_UA": {
        "standard_id": "OPC_UA",
        "title": "OPC Unified Architecture (IEC 62541)",
        "governing_body": "OPC Foundation",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_discrete_manufacturing_c28", "ind_energy_utilities_d35"],
        "has_adapter": True,
    },
    "ED_FI_DATA_STANDARD": {
        "standard_id": "ED_FI_DATA_STANDARD",
        "title": "Ed-Fi Data Standard v4.0",
        "governing_body": "Ed-Fi Alliance",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_education_training_p85"],
        "has_adapter": True,
    },
    "HR_OPEN_4_3": {
        "standard_id": "HR_OPEN_4_3",
        "title": "HR Open Standards Specification 4.3 (JSON)",
        "governing_body": "HR Open Standards Consortium",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_professional_services_m69"],
        "has_adapter": True,
    },
    "ACORD_STANDARDS": {
        "standard_id": "ACORD_STANDARDS",
        "title": "ACORD Insurance Data Standards (P&C / Life / Reinsurance)",
        "governing_body": "ACORD",
        "license_status": StandardLicenseType.PAID_LICENSED,
        "applicable_sectors": ["ind_insurance_k65"],
        "has_adapter": False,
        "license_note": "Referenced by ID only; usage requires commercial license from ACORD.",
    },
    "ADAPT_FRAMEWORK": {
        "standard_id": "ADAPT_FRAMEWORK",
        "title": "Agricultural Data Application Programming Toolkit (ADAPT)",
        "governing_body": "AgGateway",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ind_agriculture_a01"],
        "has_adapter": True,
    },
    "EN_16931": {
        "standard_id": "EN_16931",
        "title": "Electronic Invoicing Semantic Data Model (EN 16931-1:2017)",
        "governing_body": "European Committee for Standardization (CEN)",
        "license_status": StandardLicenseType.OPEN,
        "applicable_sectors": ["ALL_SECTORS"],
        "has_adapter": True,
    },
}


def get_standard(standard_id: str) -> Optional[Dict[str, Any]]:
    return STANDARDS_CATALOG.get(standard_id)


def list_standards_for_sector(industry_id: str) -> List[Dict[str, Any]]:
    results = []
    for s in STANDARDS_CATALOG.values():
        if "ALL_SECTORS" in s["applicable_sectors"] or industry_id in s["applicable_sectors"]:
            results.append(s)
    return results
