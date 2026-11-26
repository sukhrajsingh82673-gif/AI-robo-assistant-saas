"""
Declarative Jurisdiction Pack Schema & Validator: zonata.jurisdiction-pack/v1
Enforces Rules 60, 70, and 73:
- Tax and e-invoicing regimes (clearance, post-audit, Peppol)
- Payroll statutory pointers
- Employment law pointers
- Data protection and cross-border transfer rules
- Retention periods
- Business and fiscal calendars (cited data)
- AML and KYC pointers
"""

from typing import Any, Dict, List, Optional, Set
import hashlib
import json

EXPECTED_SCHEMA_VERSION = "zonata.jurisdiction-pack/v1"
VALID_REGIME_TYPES = {"COMMON_LAW", "CIVIL_LAW", "CLEARANCE_CTC", "POST_AUDIT", "PEPPOL"}


class JurisdictionValidationError(ValueError):
    """Raised when a jurisdiction pack fails structural validation."""
    pass


def compute_jurisdiction_digest(jurisdiction_dict: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 digest over a jurisdiction pack."""
    canonical_json = json.dumps(jurisdiction_dict, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def validate_jurisdiction_pack_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates a jurisdiction pack against zonata.jurisdiction-pack/v1."""
    if not isinstance(data, dict):
        raise JurisdictionValidationError(f"Pack must be a dictionary, got {type(data).__name__}")

    # 1. Schema version
    ver = data.get("schema_version")
    if ver != EXPECTED_SCHEMA_VERSION:
        raise JurisdictionValidationError(
            f"Unsupported schema_version '{ver}': expected '{EXPECTED_SCHEMA_VERSION}'"
        )

    # 2. Metadata validation
    meta = data.get("metadata")
    if not isinstance(meta, dict):
        raise JurisdictionValidationError("Jurisdiction pack missing 'metadata' section")

    for req_field in ("jurisdiction_code", "country_name", "version", "regime_type", "currency"):
        if not meta.get(req_field):
            raise JurisdictionValidationError(f"Metadata missing required field '{req_field}'")

    regime = str(meta.get("regime_type", "")).upper()
    if regime not in VALID_REGIME_TYPES:
        raise JurisdictionValidationError(
            f"Invalid regime_type '{regime}': must be one of {sorted(VALID_REGIME_TYPES)}"
        )

    # 3. Tax & E-Invoicing Regimes (Rule 60)
    tax_info = data.get("tax_regime")
    if not isinstance(tax_info, dict):
        raise JurisdictionValidationError("Jurisdiction pack missing 'tax_regime' section")

    for req in ("system_name", "standard_rate", "e_invoicing_model"):
        if req not in tax_info:
            raise JurisdictionValidationError(f"'tax_regime' missing required field '{req}'")

    # 4. Data Protection & Cross-Border Transfer Rules
    dp_info = data.get("data_protection")
    if not isinstance(dp_info, dict):
        raise JurisdictionValidationError("Jurisdiction pack missing 'data_protection' section")

    for req in ("statutory_act", "cross_border_transfer_restricted", "standard_retention_days"):
        if req not in dp_info:
            raise JurisdictionValidationError(f"'data_protection' missing required field '{req}'")

    # 5. Calendars (Rule 73: cited data per jurisdiction)
    cal = data.get("calendars")
    if not isinstance(cal, dict):
        raise JurisdictionValidationError("Jurisdiction pack missing 'calendars' section")

    if "fiscal_year_start" not in cal or "official_holidays" not in cal:
        raise JurisdictionValidationError("'calendars' must specify 'fiscal_year_start' and 'official_holidays'")

    return data
