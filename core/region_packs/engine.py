"""ZONATA Sovereign Core — Regional Compliance & Tax Engine.

Implements Stage 6 & Global Readiness Regional Packs:
- India Pack: INR currency, GST calculations (intra vs inter-state), DPDP 2023 consent validation.
- US Pack: USD currency, State Sales Tax nexus calculations, SOC 2 audit checks, HIPAA PHI sanitization.
- EU Pack: EUR currency, EU VAT (B2B cross-border reverse charge vs B2C destination rate), GDPR Article 30 ROPA verification.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import yaml

logger = logging.getLogger("zonata.core.region_packs")

_DEFAULT_PACKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "packs",
    "regions",
)

# Structural check only: two-letter country prefix plus 8-12 alphanumerics.
# A live VIES lookup is a separate integration and is not performed offline.
_EU_VAT_ID_RE = re.compile(r"^[A-Z]{2}[0-9A-Z]{8,12}$")

_GDPR_LEGAL_BASES = {
    "consent",
    "contract",
    "legal_obligation",
    "vital_interests",
    "public_task",
    "legitimate_interests",
}
_GDPR_LEGAL_BASIS_ALIASES = {"contractual_necessity": "contract"}


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

    def __init__(self, packs_dir: Optional[str] = None):
        self.packs_dir = packs_dir or _DEFAULT_PACKS_DIR
        self.packs: Dict[str, Dict[str, Any]] = {}
        self._load_available_packs()

    def _load_available_packs(self):
        for reg in ["india", "us", "eu"]:
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

        # 3. European Union VAT Calculation
        if reg == "eu":
            member_rates = {
                str(k).upper(): float(v)
                for k, v in pack.get("taxation", {}).get("member_states", {}).items()
            }
            member_state = str(context.get("member_state") or "").upper()
            if not member_state:
                raise ValueError("EU tax calculation requires an explicit 'member_state'.")
            if member_state not in member_rates:
                raise ValueError(
                    f"Unsupported EU member state '{member_state}': no verified VAT rate configured."
                )

            is_b2b = bool(context.get("is_b2b", False))
            supplier_state = str(context.get("supplier_member_state") or "").upper()
            vat_id = str(context.get("vies_vat_id") or "").strip().upper()
            vat_id_valid = bool(_EU_VAT_ID_RE.match(vat_id)) and vat_id[:2] == member_state
            cross_border = supplier_state in member_rates and supplier_state != member_state

            # Reverse charge applies only to a cross-border B2B supply whose
            # customer VAT ID is structurally valid and issued by the customer state.
            if is_b2b and vat_id_valid and cross_border:
                tax_amt = 0.0
                breakdown = {"EU_VAT_REVERSE_CHARGE": 0.0}
            else:
                rate = member_rates[member_state]
                tax_amt = round(amount * rate, 2)
                breakdown = {f"EU_VAT_{member_state}": tax_amt}

            return TaxCalculationResult(
                base_amount=amount,
                tax_amount=tax_amt,
                total_amount=round(amount + tax_amt, 2),
                currency=currency,
                tax_breakdown=breakdown,
                region="eu"
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

    def validate_gdpr_ropa(self, processing_activity: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the mandatory Article 30 ROPA fields for a processing activity.

        DPO contact is required only when the activity explicitly sets
        ``requires_dpo`` (GDPR Art. 37), not for every ROPA entry.
        """
        errors: List[str] = []

        legal_basis = processing_activity.get("legal_basis")
        if isinstance(legal_basis, str):
            legal_basis = legal_basis.strip().lower()
            legal_basis = _GDPR_LEGAL_BASIS_ALIASES.get(legal_basis, legal_basis)
        if legal_basis not in _GDPR_LEGAL_BASES:
            errors.append(
                f"GDPR Violation: Invalid legal basis '{legal_basis}'. "
                f"Must be one of {sorted(_GDPR_LEGAL_BASES)}."
            )

        controller = processing_activity.get("controller_identity") or processing_activity.get("controller")
        if not str(controller or "").strip():
            errors.append("GDPR Violation: Controller identity and contact details must be recorded.")

        purposes = processing_activity.get("purposes")
        if not purposes:
            errors.append("GDPR Violation: Processing purposes must be explicitly recorded.")

        categories_of_data = processing_activity.get("data_categories")
        if not categories_of_data:
            errors.append("GDPR Violation: Article 30 requires explicit categorization of personal data processed.")

        retention_period = processing_activity.get("retention_days")
        if isinstance(retention_period, bool) or not isinstance(retention_period, (int, float)):
            errors.append("GDPR Violation: Data retention period must be a numeric number of days.")
        elif retention_period <= 0:
            errors.append("GDPR Violation: Data retention period must be greater than 0.")

        requires_dpo = bool(processing_activity.get("requires_dpo", False))
        has_dpo = bool(str(processing_activity.get("dpo_contact") or "").strip())
        if requires_dpo and not has_dpo:
            errors.append("GDPR Violation: DPO contact is required for this activity under Article 37.")

        if processing_activity.get("third_country_transfers") and not processing_activity.get("transfer_safeguards"):
            errors.append("GDPR Violation: Third-country transfers require a recorded transfer safeguard.")

        return {
            "compliant": len(errors) == 0,
            "law": "GDPR_ARTICLE_30",
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
