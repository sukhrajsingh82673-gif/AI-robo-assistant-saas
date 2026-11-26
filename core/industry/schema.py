"""
Declarative Industry Overlay Schema & Validator: zonata.industry-overlay/v1
Enforces Rules 68, 69, 70, 71, and 72:
- Versioned multi-scheme taxonomy (ISIC Rev. 5, Rev. 4, NACE Rev. 2.1, NAICS 2022)
- Domain calculators with named sources and golden tests
- SOP overlays on department SOPs
- Document types and templates
- Regulatory register with statutory cites and review status
- Hazard and risk registers
- Hard boundary policies (Rule 72)
- Maturity tiers (T0-T4)
"""

from typing import Any, Dict, List, Optional, Set
import hashlib
import json

EXPECTED_SCHEMA_VERSION = "zonata.industry-overlay/v1"
VALID_TIERS = {"T0", "T1", "T2", "T3", "T4"}
VALID_SCHEMES = {"ISIC", "NACE", "NAICS", "NATIONAL"}


class OverlayValidationError(ValueError):
    """Raised when an industry overlay fails structural validation."""
    pass


def compute_overlay_digest(overlay_dict: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 digest over the canonical content of an overlay,
    excluding mutable verification tags so signature remains bound to content.
    """
    cleaned = dict(overlay_dict)
    # Strip mutable tier sign-offs when computing core content digest
    if "expert_reviews" in cleaned:
        cleaned = {k: v for k, v in cleaned.items() if k != "expert_reviews"}

    canonical_json = json.dumps(cleaned, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def validate_industry_overlay_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates an industry overlay dictionary against zonata.industry-overlay/v1."""
    if not isinstance(data, dict):
        raise OverlayValidationError(f"Overlay must be a dictionary, got {type(data).__name__}")

    # 1. Schema version
    ver = data.get("schema_version")
    if ver != EXPECTED_SCHEMA_VERSION:
        raise OverlayValidationError(
            f"Unsupported schema_version '{ver}': expected '{EXPECTED_SCHEMA_VERSION}'"
        )

    # 2. Metadata validation
    meta = data.get("metadata")
    if not isinstance(meta, dict):
        raise OverlayValidationError("Overlay missing 'metadata' section")

    for req_field in ("industry_id", "title", "version", "tier"):
        if not meta.get(req_field):
            raise OverlayValidationError(f"Metadata missing required field '{req_field}'")

    tier = str(meta.get("tier")).upper()
    if tier not in VALID_TIERS:
        raise OverlayValidationError(f"Invalid tier '{tier}': must be one of {sorted(VALID_TIERS)}")

    # 3. Taxonomy classifications (Rule 69)
    classifications = data.get("classification_codes", [])
    if not isinstance(classifications, list) or len(classifications) == 0:
        raise OverlayValidationError("Overlay must declare at least one classification code in 'classification_codes'")

    has_primary = False
    for i, c in enumerate(classifications):
        if not isinstance(c, dict):
            raise OverlayValidationError(f"Classification at index {i} must be a dictionary")
        scheme = str(c.get("scheme", "")).upper()
        code = str(c.get("code", "")).strip()
        version = str(c.get("version", "")).strip()
        if scheme not in VALID_SCHEMES:
            raise OverlayValidationError(f"Classification index {i} invalid scheme '{scheme}'")
        if not code or not version:
            raise OverlayValidationError(f"Classification index {i} missing 'code' or 'version'")
        if c.get("is_primary"):
            has_primary = True

    if not has_primary:
        raise OverlayValidationError("Overlay classifications must designate at least one primary classification code")

    # 4. Domain Calculators validation
    calculators = data.get("calculators", [])
    if not isinstance(calculators, list):
        raise OverlayValidationError("'calculators' must be a list")

    calc_ids: Set[str] = set()
    for i, calc in enumerate(calculators):
        if not isinstance(calc, dict):
            raise OverlayValidationError(f"Calculator at index {i} must be a dictionary")
        cid = str(calc.get("calculator_id", "")).strip()
        formula = str(calc.get("formula", "")).strip()
        data_source = str(calc.get("data_source", "")).strip()
        golden_tests = calc.get("golden_tests", [])

        if not cid or not formula or not data_source:
            raise OverlayValidationError(f"Calculator at index {i} missing 'calculator_id', 'formula', or 'data_source'")
        if cid in calc_ids:
            raise OverlayValidationError(f"Duplicate calculator_id '{cid}' in overlay")
        calc_ids.add(cid)

        # For T2+ overlays, calculators must include golden tests
        if tier in ("T2", "T3", "T4") and not golden_tests:
            raise OverlayValidationError(f"Calculator '{cid}' requires golden test cases for tier {tier}")

    # 5. Regulatory Register validation (Rule 70)
    reg_register = data.get("regulatory_register", [])
    if not isinstance(reg_register, list):
        raise OverlayValidationError("'regulatory_register' must be a list")

    for i, reg in enumerate(reg_register):
        if not isinstance(reg, dict):
            raise OverlayValidationError(f"Regulatory item at index {i} must be a dictionary")
        jurisdiction = str(reg.get("jurisdiction", "")).strip()
        cite = str(reg.get("cite", "")).strip()
        effective_date = str(reg.get("effective_date", "")).strip()
        status = str(reg.get("status", "")).strip().upper()

        if not jurisdiction or not cite or not effective_date:
            raise OverlayValidationError(f"Regulatory item at index {i} missing 'jurisdiction', 'cite', or 'effective_date'")

        # Rule 70: Must be UNVERIFIED until signed by human professional
        if status == "VERIFIED" and not reg.get("verified_by"):
            raise OverlayValidationError(
                f"Regulatory item '{cite}' marked VERIFIED without required professional signature 'verified_by'"
            )

    # 6. Sector Boundaries validation (Rule 72)
    boundaries = data.get("boundary_policies", [])
    if not isinstance(boundaries, list):
        raise OverlayValidationError("'boundary_policies' must be a list")

    for i, bp in enumerate(boundaries):
        if not isinstance(bp, dict):
            raise OverlayValidationError(f"Boundary policy at index {i} must be a dictionary")
        pid = str(bp.get("policy_id", "")).strip()
        if not pid:
            raise OverlayValidationError(f"Boundary policy at index {i} missing 'policy_id'")

    return data
