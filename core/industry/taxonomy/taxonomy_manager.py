"""
Taxonomy Manager & Crosswalk Service (Rule 69)
==============================================
Manages versioned multi-scheme industrial classifications:
- UN ISIC Rev. 5 & ISIC Rev. 4
- Eurostat NACE Rev. 2.1
- US NAICS 2022
- Official correspondence crosswalks & round-trip verification
"""

import os
import json
from typing import Dict, Any, List, Optional

TAXONOMY_DIR = os.path.dirname(os.path.abspath(__file__))


class TaxonomyManager:
    """Provides high-performance lookups and bidirectional crosswalks across industrial taxonomies."""

    def __init__(self):
        self._isic_rev5: Optional[Dict[str, Any]] = None
        self._xwalk_rev4_rev5: Optional[Dict[str, Any]] = None
        self._xwalk_rev5_nace: Optional[Dict[str, Any]] = None
        self._naics_2022: Optional[Dict[str, Any]] = None

    def get_isic_rev5(self) -> Dict[str, Any]:
        if self._isic_rev5 is None:
            path = os.path.join(TAXONOMY_DIR, "isic_rev5.json")
            with open(path, "r", encoding="utf-8") as f:
                self._isic_rev5 = json.load(f)
        return self._isic_rev5

    def get_crosswalk_rev4_rev5(self) -> Dict[str, Any]:
        if self._xwalk_rev4_rev5 is None:
            path = os.path.join(TAXONOMY_DIR, "isic_rev4_to_rev5_crosswalk.json")
            with open(path, "r", encoding="utf-8") as f:
                self._xwalk_rev4_rev5 = json.load(f)
        return self._xwalk_rev4_rev5

    def get_crosswalk_rev5_nace(self) -> Dict[str, Any]:
        if self._xwalk_rev5_nace is None:
            path = os.path.join(TAXONOMY_DIR, "isic_rev5_to_nace_rev21.json")
            with open(path, "r", encoding="utf-8") as f:
                self._xwalk_rev5_nace = json.load(f)
        return self._xwalk_rev5_nace

    def get_naics_2022(self) -> Dict[str, Any]:
        if self._naics_2022 is None:
            path = os.path.join(TAXONOMY_DIR, "naics_2022.json")
            with open(path, "r", encoding="utf-8") as f:
                self._naics_2022 = json.load(f)
        return self._naics_2022

    def resolve_rev4_to_rev5(self, isic_rev4_code: str) -> Optional[str]:
        """Maps an ISIC Rev. 4 code to its corresponding ISIC Rev. 5 code."""
        xwalk = self.get_crosswalk_rev4_rev5()
        for m in xwalk.get("mappings", []):
            if m.get("isic_rev4_code") == str(isic_rev4_code).strip():
                return m.get("isic_rev5_code")
        return None

    def resolve_rev5_to_rev4(self, isic_rev5_code: str) -> Optional[str]:
        """Maps an ISIC Rev. 5 code back to ISIC Rev. 4 (round-trip verification)."""
        xwalk = self.get_crosswalk_rev4_rev5()
        for m in xwalk.get("mappings", []):
            if m.get("isic_rev5_code") == str(isic_rev5_code).strip():
                return m.get("isic_rev4_code")
        return None

    def resolve_rev5_to_nace(self, isic_rev5_code: str) -> Optional[str]:
        """Maps an ISIC Rev. 5 code to Eurostat NACE Rev. 2.1."""
        nace = self.get_crosswalk_rev5_nace()
        for m in nace.get("mappings", []):
            if m.get("isic_rev5_code") == str(isic_rev5_code).strip():
                return m.get("nace_rev21_code")
        return None

    def get_division(self, division_code: str) -> Optional[Dict[str, Any]]:
        """Returns details for an ISIC Rev. 5 division code."""
        isic5 = self.get_isic_rev5()
        for div in isic5.get("divisions", []):
            if div.get("division_code") == str(division_code).strip():
                return div
        return None

    def migrate_step1h_pack_id(self, pack_id: str) -> Dict[str, Any]:
        """Maps Step 1H legacy pack identifiers to stable multi-scheme industry metadata."""
        lookup = {
            "saas": {
                "industry_id": "ind_telecom_software_j62",
                "title": "Computer programming, consultancy and related activities",
                "classification_codes": [
                    {"scheme": "ISIC", "version": "Rev.5", "code": "62", "is_primary": True},
                    {"scheme": "ISIC", "version": "Rev.4", "code": "62"},
                    {"scheme": "NACE", "version": "Rev.2.1", "code": "J.62"},
                    {"scheme": "NAICS", "version": "2022", "code": "5415"},
                ]
            },
            "hospitality": {
                "industry_id": "ind_hospitality_travel_i55",
                "title": "Accommodation & Lodging Activities",
                "classification_codes": [
                    {"scheme": "ISIC", "version": "Rev.5", "code": "55", "is_primary": True},
                    {"scheme": "ISIC", "version": "Rev.4", "code": "55"},
                    {"scheme": "NACE", "version": "Rev.2.1", "code": "I.55"},
                    {"scheme": "NAICS", "version": "2022", "code": "7211"},
                ]
            },
            "manufacturing": {
                "industry_id": "ind_discrete_manufacturing_c28",
                "title": "Manufacture of machinery and equipment",
                "classification_codes": [
                    {"scheme": "ISIC", "version": "Rev.5", "code": "28", "is_primary": True},
                    {"scheme": "ISIC", "version": "Rev.4", "code": "28"},
                    {"scheme": "NACE", "version": "Rev.2.1", "code": "C.28"},
                    {"scheme": "NAICS", "version": "2022", "code": "3332"},
                ]
            },
            "clinic": {
                "industry_id": "ind_healthcare_operations_q86",
                "title": "Human health activities & Clinic operations",
                "classification_codes": [
                    {"scheme": "ISIC", "version": "Rev.5", "code": "86", "is_primary": True},
                    {"scheme": "ISIC", "version": "Rev.4", "code": "86"},
                    {"scheme": "NACE", "version": "Rev.2.1", "code": "Q.86"},
                    {"scheme": "NAICS", "version": "2022", "code": "6211"},
                ]
            }
        }
        return lookup.get(pack_id.lower(), {
            "industry_id": f"ind_{pack_id.lower()}",
            "title": pack_id.title(),
            "classification_codes": [
                {"scheme": "ISIC", "version": "Rev.5", "code": "99", "is_primary": True}
            ]
        })
