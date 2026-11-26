"""
Industry Overlay Maturity Tiers (T0 to T4) & Voiding Engine
Enforces Rule 71: Depth earned by review; changes after sign-off void tier.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
import hashlib
import json
from core.industry.schema import compute_overlay_digest


class OverlayTier(str, Enum):
    T0_SKELETON = "T0"      # Taxonomy skeleton & basic metadata
    T1_VOCABULARY = "T1"    # Generic core + sector vocabulary & accounts
    T2_DEEP_DRAFT = "T2"    # Calculators, SOP overlays, cited regulatory register, golden tasks
    T3_REVIEWED = "T3"      # Reviewed and signed by one named human domain professional
    T4_CERTIFIED = "T4"     # Independently certified by second expert + completed pilot evidence


class TierManager:
    """Manages progression, qualification gates, and post-modification voiding for industry overlays."""

    @staticmethod
    def verify_tier_integrity(overlay_data: Dict[str, Any]) -> Dict[str, Any]:
        """Checks if the overlay's stated tier is valid against its content and signatures.
        If content was modified after expert review, the tier is immediately voided.
        """
        meta = overlay_data.get("metadata", {})
        stated_tier = meta.get("tier", "T0").upper()
        current_digest = compute_overlay_digest(overlay_data)

        reviews = overlay_data.get("expert_reviews", [])

        # T0 / T1 / T2 require no external human sign-offs
        if stated_tier in ("T0", "T1", "T2"):
            return {
                "effective_tier": stated_tier,
                "is_voided": False,
                "current_digest": current_digest,
                "reason": "Draft tier within automated authoring boundary"
            }

        # T3 requires >= 1 human review matching the current content digest
        if stated_tier == "T3":
            if not reviews:
                return {
                    "effective_tier": "T2",
                    "is_voided": True,
                    "void_reason": "T3 requires expert review but no reviews present. Demoted to T2."
                }
            latest_review = reviews[0]
            signed_digest = latest_review.get("content_digest")
            if signed_digest != current_digest:
                return {
                    "effective_tier": "T2",
                    "is_voided": True,
                    "void_reason": f"Content modified after sign-off: signed={signed_digest[:10]}, current={current_digest[:10]}. Demoted to T2."
                }
            return {
                "effective_tier": "T3",
                "is_voided": False,
                "reviewer": latest_review.get("reviewer_name"),
                "current_digest": current_digest
            }

        # T4 requires >= 2 independent human reviews and pilot evidence
        if stated_tier == "T4":
            if len(reviews) < 2:
                return {
                    "effective_tier": "T2",
                    "is_voided": True,
                    "void_reason": "T4 requires 2 independent expert reviews. Demoted to T2."
                }
            pilot_evidence = overlay_data.get("pilot_evidence")
            if not pilot_evidence or not pilot_evidence.get("evidence_seal"):
                return {
                    "effective_tier": "T3",
                    "is_voided": True,
                    "void_reason": "T4 requires verified pilot evidence seal. Demoted to T3."
                }
            for rev in reviews[:2]:
                if rev.get("content_digest") != current_digest:
                    return {
                        "effective_tier": "T2",
                        "is_voided": True,
                        "void_reason": "Content modified after T4 certification. Demoted to T2."
                    }
            return {
                "effective_tier": "T4",
                "is_voided": False,
                "reviewers": [r.get("reviewer_name") for r in reviews[:2]],
                "current_digest": current_digest
            }

        return {"effective_tier": "T0", "is_voided": True, "void_reason": "Unknown tier"}

    @staticmethod
    def generate_coverage_report(overlays: List[Dict[str, Any]]) -> str:
        """Generates docs/reports/INDUSTRY_COVERAGE.md markdown table dynamically from overlay data."""
        lines = [
            "# Industry Coverage Register (`docs/reports/INDUSTRY_COVERAGE.md`)",
            "",
            "**Generated From Overlay Data (Rule 71)**",
            "",
            "| Industry ID | Title | Primary ISIC / Scheme | Calculators | SOP Overlays | Tier | Review Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for ov in overlays:
            meta = ov.get("metadata", {})
            iid = meta.get("industry_id", "UNKNOWN")
            title = meta.get("title", "Untitled")
            tier_info = TierManager.verify_tier_integrity(ov)
            eff_tier = tier_info["effective_tier"]

            primary_code = "N/A"
            for c in ov.get("classification_codes", []):
                if c.get("is_primary"):
                    primary_code = f"{c.get('scheme')} {c.get('code')}"
                    break

            calcs_count = len(ov.get("calculators", []))
            sops_count = len(ov.get("sop_overlays", []))
            status = "VOIDED / DEMOTED" if tier_info.get("is_voided") else "ACTIVE"

            lines.append(
                f"| `{iid}` | {title} | {primary_code} | {calcs_count} | {sops_count} | **{eff_tier}** | {status} |"
            )

        lines.append("")
        return "\n".join(lines)
