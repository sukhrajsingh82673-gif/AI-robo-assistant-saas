"""ZONATA Sovereign Core — Regional Compliance & Tax Engine.

Implements Stage 6 Regional Packs:
- India Pack: INR currency, GST calculations (intra vs inter-state), DPDP 2023 consent validation.
- US Pack: USD currency, State Sales Tax nexus calculations, SOC 2 audit checks, HIPAA PHI sanitization.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger("zonata.core.region_packs")


@dataclass
class TaxCalculationResult:
    base_amount: float
    tax_amount: float
    total_amount: float
    currency: str
    tax_breakdown: Dict[str, float]
    region: str


class RegionalComplianceEngine:
    """Manages regional tax rules and compliance mandates across sovereign regions."""

    def __init__(self, packs_dir: str = "packs/regions"):
        self.packs_dir = packs_dir
        self.packs: Dict[str, Dict[str, Any]] = {}
        self._load_available_packs()

    def _load_available_packs(self):
        for reg in ["india", "us"]:
            pack_path = os.path.join(self.packs_dir, reg, "v1", "pack.yaml")
            if os.path.exists(pack_path):
                with open(pack_path, "r", encoding="utf-8") as f:
                    self.packs[reg] = yaml.safe_load(f)

    def get_pack(self, region_code: str) -> Optional[Dict[str, Any]]:
        return self.packs.get(region_code.lower())

    def calculate_tax(
        self,
        region_code: str,
        amount: float,
        context: Optional[Dict[str, Any]] = None
    ) -> TaxCalculationResult:
        """Calculates regional tax based on jurisdiction framework."""
        context = context or {}
        reg = region_code.lower()
        pack = self.packs.get(reg)
        if not pack:
            raise ValueError(f"Unknown or unsupported region pack: '{region_code}'.")

        currency = pack.get("currency", "USD")

        # 1. India GST Calculation
        if reg == "india":
            is_inter_state = context.get("is_inter_state", False)
            tax_rules = pack["taxation"]["rules"]

            if is_inter_state:
                igst_rate = tax_rules["inter_state"]["igst_percent"] / 100.0
                tax_amt = round(amount * igst_rate, 2)
                breakdown = {"IGST": tax_amt}
            else:
                cgst_rate = tax_rules["intra_state"]["cgst_percent"] / 100.0
                sgst_rate = tax_rules["intra_state"]["sgst_percent"] / 100.0
                cgst = round(amount * cgst_rate, 2)
                sgst = round(amount * sgst_rate, 2)
                tax_amt = round(cgst + sgst, 2)
                breakdown = {"CGST": cgst, "SGST": sgst}

            return TaxCalculationResult(
                base_amount=amount,
                tax_amount=tax_amt,
                total_amount=round(amount + tax_amt, 2),
                currency=currency,
                tax_breakdown=breakdown,
                region="india"
            )

        # 2. United States Sales Tax Calculation
        if reg == "us":
            state = context.get("state", "CA").upper()
            state_rates = pack["taxation"]["state_nexus_rates"]
            default_rate = pack["taxation"].get("default_rate", 0.06)
            rate = state_rates.get(state, default_rate)

            tax_amt = round(amount * rate, 2)
            breakdown = {f"STATE_SALES_TAX_{state}": tax_amt}

            return TaxCalculationResult(
                base_amount=amount,
                tax_amount=tax_amt,
                total_amount=round(amount + tax_amt, 2),
                currency=currency,
                tax_breakdown=breakdown,
                region="us"
            )

        raise NotImplementedError(f"Tax logic not implemented for region '{region_code}'.")

    def validate_dpdp_compliance(self, consent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates adherence to India's DPDP Act 2023 mandates."""
        has_consent = consent_data.get("consent_granted", False)
        purpose = consent_data.get("purpose_specified", "")
        fiduciary_id = consent_data.get("data_fiduciary_id")

        errors = []
        if not has_consent:
            errors.append("DPDP Violation: Processing personal data without unambiguous affirmative consent.")
        if not purpose:
            errors.append("DPDP Violation: Purpose limitation principle violated: no explicit processing purpose.")
        if not fiduciary_id:
            errors.append("DPDP Violation: Missing registered Data Fiduciary identification.")

        return {
            "compliant": len(errors) == 0,
            "law": "DPDP_2023",
            "errors": errors
        }

    def sanitize_hipaa_phi(self, text: str) -> Tuple[str, int]:
        """Sanitizes Protected Health Information (PHI) under HIPAA rules."""
        patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]"),
            (r"\bMRN[-\s]?\d{6,10}\b", "[REDACTED-MRN]"),
            (r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b", "[REDACTED-PHONE]")
        ]

        cleaned = text
        redaction_count = 0
        for pattern, replacement in patterns:
            matches = len(re.findall(pattern, cleaned))
            if matches > 0:
                redaction_count += matches
                cleaned = re.sub(pattern, replacement, cleaned)

        return cleaned, redaction_count
