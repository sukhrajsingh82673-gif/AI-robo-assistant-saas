"""
Enterprise Procurement and Buyer Evaluation Pack Generator (Rule 70 & Rule 73)
"""

from typing import Dict, Any, List, Optional
import datetime
import hashlib
import json


class ProcurementEvidenceMissingError(ValueError):
    """Raised when an enterprise procurement pack is generated without required audited evidence citations."""
    pass


REQUIRED_EVIDENCE_KEYS = {
    "soc2_type2_attestation": "SOC 2 Type II Examination Report",
    "iso27001_certification": "ISO/IEC 27001:2022 Certification",
    "gdpr_dpa_standard_clauses": "GDPR Data Processing Addendum with EU Standard Contractual Clauses",
    "last_pentest_attestation": "Independent Third-Party Penetration Test Executive Summary",
    "dr_rpo_rto_sla": "Disaster Recovery SLA (RPO <= 1h, RTO <= 4h)",
}


class BuyerPackGenerator:
    """Generates verifiable enterprise procurement evaluation dossiers."""

    @classmethod
    def generate_dossier(
        cls,
        company_name: str,
        target_industry_code: str,
        target_jurisdiction: str,
        evidence_citations: Dict[str, str],
        author_id: str,
    ) -> Dict[str, Any]:
        """
        Compiles enterprise procurement pack.
        Strictly requires all 5 mandatory security and compliance evidence citations.
        """
        missing = [
            f"{k} ({desc})"
            for k, desc in REQUIRED_EVIDENCE_KEYS.items()
            if not evidence_citations.get(k)
        ]
        if missing:
            raise ProcurementEvidenceMissingError(
                f"PROCUREMENT_EVIDENCE_MISSING: Cannot generate enterprise buyer pack. "
                f"Missing required audit citations: {', '.join(missing)}"
            )

        dossier = {
            "title": f"Enterprise Buyer Security & Compliance Pack — {company_name}",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "target_industry_code": target_industry_code,
            "target_jurisdiction": target_jurisdiction,
            "author_id": author_id,
            "security_certifications": {
                "soc2": evidence_citations["soc2_type2_attestation"],
                "iso27001": evidence_citations["iso27001_certification"],
                "pentest": evidence_citations["last_pentest_attestation"],
            },
            "privacy_and_legal": {
                "dpa_clauses": evidence_citations["gdpr_dpa_standard_clauses"],
                "data_sovereignty_model": "Cellular Regional Residency (ADR 0044)",
            },
            "sla_and_resilience": {
                "dr_sla": evidence_citations["dr_rpo_rto_sla"],
                "availability_sla": "99.95% multi-region cellular failover",
            },
            "zero_trust_architecture": {
                "identity": "OIDC / SAML 2.0 with Hardware Token MFA",
                "database_isolation": "PostgreSQL Row-Level Security with isolated tenant encryption keys",
                "supply_chain": "SLSA Level 3 signed provenance",
            }
        }

        # Deterministic cryptographic seal
        serialized = json.dumps(dossier, sort_keys=True)
        dossier["dossier_seal_sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return dossier
