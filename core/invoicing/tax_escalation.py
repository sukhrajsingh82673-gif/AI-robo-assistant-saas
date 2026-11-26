"""
Statutory Tax Determination & Escalation Gate (Rule 70 & Rule 73)
=================================================================
Tax determination is strictly data-driven and never guessed.
If no verified rule exists for a jurisdiction + commodity code + transaction type,
the system blocks processing and escalates to a human tax accountant.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("zonata.invoicing.tax")


class TaxDeterminationEscalationRequired(PermissionError):
    """Raised when tax rate cannot be determined from verified statutory rule tables (Rule 70)."""
    def __init__(self, jurisdiction: str, commodity_code: str, reason: str):
        super().__init__(
            f"Tax determination escalated for [{jurisdiction}] code '{commodity_code}': {reason}. "
            f"Rule 70 prohibits automated guessing of statutory taxes without verified rule."
        )
        self.jurisdiction = jurisdiction
        self.commodity_code = commodity_code
        self.reason = reason


class TaxDeterminationEngine:
    """Evaluates statutory tax rules and manages escalation for unverified categories."""

    def __init__(self, verified_tax_rules: Optional[Dict[str, Dict[str, float]]] = None):
        # jurisdiction -> {commodity_or_tax_category: verified_rate_percentage}
        self.verified_rules = verified_tax_rules or {
            "DE": {"S": 19.0, "AA": 7.0, "Z": 0.0},
            "IN": {"STANDARD_GOODS": 18.0, "ESSENTIAL_GOODS": 5.0, "EXEMPT": 0.0},
            "BE": {"S": 21.0, "REDUCED": 6.0, "Z": 0.0},
            "PL": {"S": 23.0, "REDUCED_8": 8.0, "REDUCED_5": 5.0, "Z": 0.0},
            "US": {"STATE_SALES_TAX_DEFAULT": 7.5, "WHOLESALE_RESALE": 0.0},
        }

    def determine_tax_rate(
        self,
        jurisdiction_code: str,
        tax_category: str,
        is_rule_verified: bool = True,
    ) -> float:
        """Determines applicable tax rate or raises TaxDeterminationEscalationRequired."""
        jur = jurisdiction_code.upper()

        # Rule 70 Invariant: Unverified rules must escalate
        if not is_rule_verified:
            logger.warning("Tax rule unverified for jurisdiction %s: escalation triggered", jur)
            raise TaxDeterminationEscalationRequired(
                jurisdiction=jur,
                commodity_code=tax_category,
                reason="Tax rule in jurisdiction pack is marked UNVERIFIED by human professional"
            )

        jur_rules = self.verified_rules.get(jur)
        if not jur_rules:
            logger.warning("No tax rules configured for jurisdiction %s: escalation triggered", jur)
            raise TaxDeterminationEscalationRequired(
                jurisdiction=jur,
                commodity_code=tax_category,
                reason=f"Jurisdiction '{jur}' has no active tax rule configuration"
            )

        if tax_category not in jur_rules:
            logger.warning("Tax category '%s' unknown in %s: escalation triggered", tax_category, jur)
            raise TaxDeterminationEscalationRequired(
                jurisdiction=jur,
                commodity_code=tax_category,
                reason=f"Tax category '{tax_category}' not found in verified statutory schedule for {jur}"
            )

        return jur_rules[tax_category]


TaxEscalationEngine = TaxDeterminationEngine
