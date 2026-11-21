"""
Declarative Industry Pack Schema & Validator: zonata.industry-pack/v1
Enforces strict statutory requirements: data-driven blueprints, UN ISIC taxonomy,
balanced Chart of Accounts, and zero hardcoded branching (OpenCode Step 1H).
"""

from typing import Any, Dict, List, Optional, Set

from core.industry_packs.isic import get_isic_details, validate_isic_code
from core.ledger.currency import SUPPORTED_CURRENCIES, validate_currency
from core.ledger.schema import AccountType

EXPECTED_SCHEMA_VERSION = "zonata.industry-pack/v1"
VALID_ACCOUNT_TYPES = {t.value for t in AccountType}


class PackValidationError(ValueError):
    """Raised when an industry pack fails structural schema validation."""
    pass


class MalformedChartOfAccountsError(PackValidationError):
    """Raised when an industry pack's Chart of Accounts is malformed or structurally incomplete."""
    pass


def validate_industry_pack_dict(pack_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates an industry pack dictionary against the zonata.industry-pack/v1 schema.
    
    Returns the validated pack data or raises PackValidationError / MalformedChartOfAccountsError.
    """
    if not isinstance(pack_data, dict):
        raise PackValidationError(f"Industry pack must be a mapping, got {type(pack_data).__name__}")

    # 1. Schema version
    schema_ver = pack_data.get("schema_version")
    if schema_ver != EXPECTED_SCHEMA_VERSION:
        raise PackValidationError(
            f"Unsupported schema_version '{schema_ver}': expected '{EXPECTED_SCHEMA_VERSION}'"
        )

    # 2. Metadata validation
    meta = pack_data.get("metadata")
    if not isinstance(meta, dict):
        raise PackValidationError("Industry pack missing 'metadata' section")

    for req_field in ("pack_id", "name", "version", "industry_code"):
        if not meta.get(req_field):
            raise PackValidationError(f"Metadata missing required field '{req_field}'")

    isic_code = str(meta.get("industry_code", "")).strip()
    if not validate_isic_code(isic_code):
        raise PackValidationError(
            f"Invalid UN ISIC Rev. 4 taxonomy code '{isic_code}' in metadata: code not found in authoritative registry"
        )

    # 3. Chart of Accounts validation
    coa = pack_data.get("chart_of_accounts")
    if not isinstance(coa, list) or len(coa) == 0:
        raise MalformedChartOfAccountsError("Industry pack must define a non-empty 'chart_of_accounts' list")

    seen_codes: Set[str] = set()
    present_types: Set[str] = set()

    for i, acct in enumerate(coa):
        if not isinstance(acct, dict):
            raise MalformedChartOfAccountsError(f"Account at index {i} must be a dictionary")

        code = str(acct.get("code", "")).strip()
        name = str(acct.get("name", "")).strip()
        acct_type = str(acct.get("type", "")).strip().upper()
        curr = str(acct.get("currency", "")).strip().upper()

        if not code or not name:
            raise MalformedChartOfAccountsError(f"Account at index {i} missing 'code' or 'name'")
        if code in seen_codes:
            raise MalformedChartOfAccountsError(f"Duplicate account code '{code}' in chart_of_accounts")
        seen_codes.add(code)

        if acct_type not in VALID_ACCOUNT_TYPES:
            raise MalformedChartOfAccountsError(
                f"Account '{code}' has invalid type '{acct_type}': must be one of {sorted(VALID_ACCOUNT_TYPES)}"
            )
        present_types.add(acct_type)

        try:
            validate_currency(curr)
        except Exception as exc:
            raise MalformedChartOfAccountsError(
                f"Account '{code}' has invalid ISO 4217 currency '{curr}': {exc}"
            )

    # Completeness check: functional double-entry accounting requires Assets, Liabilities/Equity, Revenue, and Expenses
    if "ASSET" not in present_types:
        raise MalformedChartOfAccountsError("Chart of accounts is structurally incomplete: missing required 'ASSET' account")
    if not (present_types & {"LIABILITY", "EQUITY"}):
        raise MalformedChartOfAccountsError("Chart of accounts is structurally incomplete: missing 'LIABILITY' or 'EQUITY' account")
    if "REVENUE" not in present_types:
        raise MalformedChartOfAccountsError("Chart of accounts is structurally incomplete: missing required 'REVENUE' account")
    if "EXPENSE" not in present_types:
        raise MalformedChartOfAccountsError("Chart of accounts is structurally incomplete: missing required 'EXPENSE' account")

    # 4. Document Templates validation
    templates = pack_data.get("document_templates", [])
    if not isinstance(templates, list):
        raise PackValidationError("'document_templates' must be a list")

    template_ids: Set[str] = set()
    for i, tpl in enumerate(templates):
        if not isinstance(tpl, dict):
            raise PackValidationError(f"Template at index {i} must be a dictionary")
        tpl_id = str(tpl.get("template_id", "")).strip()
        tpl_name = str(tpl.get("name", "")).strip()
        retention = tpl.get("default_retention_days", 365)

        if not tpl_id or not tpl_name:
            raise PackValidationError(f"Template at index {i} missing 'template_id' or 'name'")
        if not isinstance(retention, int) or retention <= 0:
            raise PackValidationError(f"Template '{tpl_id}' must specify positive integer 'default_retention_days'")
        template_ids.add(tpl_id)

    # 5. Folio Types validation
    folio_types = pack_data.get("folio_types", [])
    if not isinstance(folio_types, list):
        raise PackValidationError("'folio_types' must be a list")

    for i, ft in enumerate(folio_types):
        if not isinstance(ft, dict):
            raise PackValidationError(f"Folio type at index {i} must be a dictionary")
        ft_name = str(ft.get("folio_type", "")).strip()
        if not ft_name:
            raise PackValidationError(f"Folio type at index {i} missing 'folio_type'")

        # Verify referenced document templates exist
        for doc_ref in ft.get("required_documents", []):
            if doc_ref not in template_ids:
                raise PackValidationError(
                    f"Folio type '{ft_name}' references non-existent document template '{doc_ref}'"
                )
        for doc_ref in ft.get("optional_documents", []):
            if doc_ref not in template_ids:
                raise PackValidationError(
                    f"Folio type '{ft_name}' references non-existent optional template '{doc_ref}'"
                )

    # 6. Workflows validation
    workflows = pack_data.get("workflows", [])
    if not isinstance(workflows, list):
        raise PackValidationError("'workflows' must be a list")

    for i, wf in enumerate(workflows):
        if not isinstance(wf, dict):
            raise PackValidationError(f"Workflow at index {i} must be a dictionary")
        wf_id = str(wf.get("workflow_id", "")).strip()
        triggers = wf.get("triggers", [])
        if not wf_id:
            raise PackValidationError(f"Workflow at index {i} missing 'workflow_id'")
        if not isinstance(triggers, list) or len(triggers) == 0:
            raise PackValidationError(f"Workflow '{wf_id}' must define at least one trigger")

        steps = wf.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue
            # If step specifies accounting legs, accounts must exist in chart_of_accounts
            for leg_key in ("debit_account", "credit_account"):
                acct_ref = step.get(leg_key)
                if acct_ref and str(acct_ref).strip() not in seen_codes:
                    raise PackValidationError(
                        f"Workflow '{wf_id}' step references non-existent account '{acct_ref}' in '{leg_key}'"
                    )

    return pack_data
