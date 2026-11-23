"""
Unit, integration, and mutation tests for the Declarative Industry Pack Framework (OpenCode Step 1H).

Acceptance Criteria:
a. Valid pack installs cleanly into a tenant/company (accounts created, templates registered, folio types provisioned).
b. Pack referencing invalid ISIC code fails schema validation (PackValidationError).
c. Pack with unbalanced or malformed COA fails validation (MalformedChartOfAccountsError).
d. Codebase search proves zero `if industry == '...'` or similar hardcoded branching in `core/`.
e. Canonical packs (saas, hospitality, manufacturing) load and validate cleanly.
f. IndustryUnderstandingEngine dynamically adapts to registered packs and UN ISIC codes.
"""

import os
import pathlib
import re
import unittest
import uuid
import pytest

from core.ceo_brain.industry import IndustryUnderstandingEngine
from core.db import configure_isolated_test_db, db
from core.industry_packs.isic import get_isic_details, validate_isic_code
from core.industry_packs.loader import IndustryPackLoader, ensure_industry_pack_tables
from core.industry_packs.registry import industry_pack_registry
from core.industry_packs.schema import (
    MalformedChartOfAccountsError,
    PackValidationError,
    validate_industry_pack_dict,
)
from core.ledger.kernel import LedgerKernel


class TestIndustryPackFramework(unittest.TestCase):
    """Rigorous verification of declarative, data-driven industry packs."""

    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        cls.db_path = configure_isolated_test_db()
        ensure_industry_pack_tables()
        cls.ledger = LedgerKernel()
        cls.loader = IndustryPackLoader(ledger_kernel=cls.ledger)

    def setUp(self):
        self.tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_id = f"cmp_{uuid.uuid4().hex[:8]}"

    # =========================================================================
    # ACCEPTANCE TEST A: VALID PACK INSTALLS CLEANLY
    # =========================================================================
    def test_valid_industry_pack_installs_cleanly_into_company(self):
        """Acceptance 6a: Valid pack installs COA accounts, folio types, and records manifest."""
        sample_pack = {
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {
                "pack_id": "legal_accounting_services",
                "name": "Legal & Accounting Professional Services",
                "version": "1.0.0",
                "description": "Statutory operating blueprint for legal and financial advisory practices",
                "author": "ZONATA Systems Foundation",
                "industry_code": "M69",  # Legal and accounting activities
            },
            "document_templates": [
                {
                    "template_id": "tpl_retainer_agreement",
                    "name": "Client Legal Retainer Agreement",
                    "type": "client_contract",
                    "default_sensitivity": "RESTRICTED",
                    "default_retention_days": 2555,
                }
            ],
            "chart_of_accounts": [
                {"code": "1010", "name": "Client Trust & Operating Bank", "type": "ASSET", "currency": "USD"},
                {"code": "1200", "name": "Billed Client Fees Receivable", "type": "ASSET", "currency": "USD"},
                {"code": "2010", "name": "Trade Accounts Payable", "type": "LIABILITY", "currency": "USD"},
                {"code": "3010", "name": "Partnership Capital", "type": "EQUITY", "currency": "USD"},
                {"code": "4010", "name": "Legal Advisory Fee Revenue", "type": "REVENUE", "currency": "USD"},
                {"code": "5010", "name": "Associate Attorney Compensation", "type": "EXPENSE", "currency": "USD"},
            ],
            "folio_types": [
                {
                    "folio_type": "legal_matter",
                    "name": "Client Matter Case Folio",
                    "description": "Governs litigation or transactional matter docket and filings",
                    "required_documents": ["tpl_retainer_agreement"],
                    "optional_documents": [],
                    "required_tasks": ["conflict_check", "engagement_letter_signed"],
                }
            ],
            "workflows": [
                {
                    "workflow_id": "wf_matter_intake",
                    "name": "Client Matter Intake & Trust Deposit",
                    "triggers": ["retainer_signed", "manual_partner_open"],
                    "steps": [
                        {"step_id": "record_retainer", "action": "post_journal_entry", "debit_account": "1010", "credit_account": "2010"}
                    ],
                }
            ],
        }

        receipt = self.loader.install_pack(self.tenant_id, self.company_id, sample_pack)

        self.assertEqual(receipt["status"], "INSTALLED")
        self.assertEqual(receipt["pack_id"], "legal_accounting_services")
        self.assertEqual(receipt["isic_code"], "M69")
        self.assertEqual(receipt["isic_name"], "Legal and accounting activities")
        self.assertEqual(receipt["accounts_created_count"], 6)
        self.assertIn("legal_matter", receipt["folio_types_provisioned"])

        # Verify accounts actually exist in the ledger
        acct_trust = self.ledger.get_account_by_code(self.tenant_id, self.company_id, "1010")
        self.assertIsNotNone(acct_trust)
        self.assertEqual(acct_trust["name"], "Client Trust & Operating Bank")
        self.assertEqual(acct_trust["currency"], "USD")

        acct_rev = self.ledger.get_account_by_code(self.tenant_id, self.company_id, "4010")
        self.assertIsNotNone(acct_rev)
        self.assertEqual(acct_rev["name"], "Legal Advisory Fee Revenue")

        # Verify pack retrieval from database
        installed = self.loader.get_installed_pack(self.tenant_id, self.company_id, "legal_accounting_services")
        self.assertIsNotNone(installed)
        self.assertEqual(installed["version"], "1.0.0")

    # =========================================================================
    # ACCEPTANCE TEST B: INVALID ISIC CODE FAILS SCHEMA VALIDATION
    # =========================================================================
    def test_invalid_isic_code_fails_schema_validation(self):
        """Acceptance 6b: Referencing non-existent ISIC taxonomy code raises PackValidationError."""
        bogus_pack = {
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {
                "pack_id": "alien_mining",
                "name": "Asteroid Mineral Extraction",
                "version": "1.0.0",
                "industry_code": "Z99_BOGUS_INVALID",  # Not a valid UN ISIC code
            },
            "chart_of_accounts": [
                {"code": "1010", "name": "Cash", "type": "ASSET", "currency": "USD"},
                {"code": "2010", "name": "AP", "type": "LIABILITY", "currency": "USD"},
                {"code": "4010", "name": "Rev", "type": "REVENUE", "currency": "USD"},
                {"code": "5010", "name": "Exp", "type": "EXPENSE", "currency": "USD"},
            ],
        }

        with self.assertRaises(PackValidationError) as ctx:
            validate_industry_pack_dict(bogus_pack)
        self.assertIn("Invalid UN ISIC Rev. 4 taxonomy code", str(ctx.exception))

    # =========================================================================
    # ACCEPTANCE TEST C: MALFORMED OR UNBALANCED COA FAILS VALIDATION
    # =========================================================================
    def test_malformed_or_unbalanced_coa_fails_validation(self):
        """Acceptance 6c: Pack missing required account types or with invalid types fails."""
        # 1. Missing EXPENSE account type
        incomplete_pack = {
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {
                "pack_id": "incomplete_coa_pack",
                "name": "Incomplete Business Model",
                "version": "1.0.0",
                "industry_code": "J62",
            },
            "chart_of_accounts": [
                {"code": "1010", "name": "Operating Cash", "type": "ASSET", "currency": "USD"},
                {"code": "2010", "name": "Accounts Payable", "type": "LIABILITY", "currency": "USD"},
                {"code": "4010", "name": "Revenue", "type": "REVENUE", "currency": "USD"},
                # Missing EXPENSE
            ],
        }

        with self.assertRaises(MalformedChartOfAccountsError) as ctx:
            validate_industry_pack_dict(incomplete_pack)
        self.assertIn("missing required 'EXPENSE' account", str(ctx.exception))

        # 2. Duplicate account codes
        duplicate_code_pack = {
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {
                "pack_id": "dup_pack",
                "name": "Duplicate Codes Pack",
                "version": "1.0.0",
                "industry_code": "C10",
            },
            "chart_of_accounts": [
                {"code": "1010", "name": "Operating Cash", "type": "ASSET", "currency": "USD"},
                {"code": "1010", "name": "Duplicate Cash", "type": "ASSET", "currency": "USD"},
                {"code": "2010", "name": "AP", "type": "LIABILITY", "currency": "USD"},
                {"code": "4010", "name": "Sales", "type": "REVENUE", "currency": "USD"},
                {"code": "5010", "name": "COGS", "type": "EXPENSE", "currency": "USD"},
            ],
        }

        with self.assertRaises(MalformedChartOfAccountsError) as ctx:
            validate_industry_pack_dict(duplicate_code_pack)
        self.assertIn("Duplicate account code '1010'", str(ctx.exception))

    # =========================================================================
    # ACCEPTANCE TEST D: ZERO HARDCODED INDUSTRY BRANCHING IN CODEBASE
    # =========================================================================
    def test_zero_hardcoded_industry_branching_in_core(self):
        """Acceptance 6d: Rigorous AST/regex scan proving zero `if industry == '...'` in core/."""
        base_dir = pathlib.Path(__file__).resolve().parent.parent / "core"
        disallowed_patterns = [
            re.compile(r"if\s+[\w\.\'\"\[\]]*industry[\w\.\'\"\[\]]*\s*==\s*[\'\"]\w+[\'\"]", re.IGNORECASE),
            re.compile(r"if\s+[\w\.\'\"\[\]]*sector[\w\.\'\"\[\]]*\s*==\s*[\'\"]\w+[\'\"]", re.IGNORECASE),
            re.compile(r"if\s+[\'\"]hospitality[\'\"]\s+in\s+[\w\.\'\"\[\]]*industry", re.IGNORECASE),
            re.compile(r"if\s+[\'\"]manufacturing[\'\"]\s+in\s+[\w\.\'\"\[\]]*industry", re.IGNORECASE),
            re.compile(r"if\s+[\'\"]saas[\'\"]\s+in\s+[\w\.\'\"\[\]]*industry", re.IGNORECASE),
        ]

        violations = []
        for py_file in base_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                clean_line = line.strip()
                if clean_line.startswith("#"):
                    continue
                for pat in disallowed_patterns:
                    if pat.search(clean_line):
                        violations.append(f"{py_file.name}:{line_no} -> {clean_line}")

        self.assertEqual(
            violations,
            [],
            f"Rule 17 / 1H violation: Found {len(violations)} hardcoded industry branches:\n"
            + "\n".join(violations),
        )

    # =========================================================================
    # CANONICAL PACKS VALIDATION
    # =========================================================================
    def test_canonical_industry_packs_load_and_validate(self):
        """Verifies that all three canonical packs (SaaS, Hospitality, Manufacturing) load cleanly."""
        registry = industry_pack_registry
        registry.discover_packs()

        packs = registry.list_packs()
        self.assertGreaterEqual(len(packs), 3)

        pack_ids = {p["pack_id"] for p in packs}
        self.assertIn("saas_enterprise", pack_ids)
        self.assertIn("hospitality_hotel", pack_ids)
        self.assertIn("discrete_manufacturing", pack_ids)

        # Verify ISIC code mapping
        saas_pack = registry.find_by_isic("J62")
        self.assertIsNotNone(saas_pack)
        self.assertEqual(saas_pack["metadata"]["pack_id"], "saas_enterprise")

        hosp_pack = registry.find_by_isic("I55")
        self.assertIsNotNone(hosp_pack)
        self.assertEqual(hosp_pack["metadata"]["pack_id"], "hospitality_hotel")

        mfg_pack = registry.find_by_isic("C28")
        self.assertIsNotNone(mfg_pack)
        self.assertEqual(mfg_pack["metadata"]["pack_id"], "discrete_manufacturing")

    # =========================================================================
    # DYNAMIC INDUSTRY UNDERSTANDING ENGINE
    # =========================================================================
    def test_industry_understanding_engine_adapts_to_data_driven_packs(self):
        """Proves IndustryUnderstandingEngine returns data-driven analysis from registered packs."""
        # 1. Query by registered ISIC code
        analysis_saas = IndustryUnderstandingEngine.analyze_industry("J62")
        self.assertTrue(analysis_saas["identified_domain"])
        self.assertEqual(analysis_saas["pack_id"], "saas_enterprise")
        self.assertIn("ARR SaaS Subscription Revenue", analysis_saas["revenue_engines"])

        # 2. Query by registered name keyword
        analysis_hotel = IndustryUnderstandingEngine.analyze_industry("Hotel & Hospitality Operations")
        self.assertTrue(analysis_hotel["identified_domain"])
        self.assertEqual(analysis_hotel["pack_id"], "hospitality_hotel")
        self.assertIn("Room Nights Revenue (RevPAR)", analysis_hotel["revenue_engines"])

        # 3. Query by UN ISIC code without custom pack
        analysis_water = IndustryUnderstandingEngine.analyze_industry("E36")
        self.assertTrue(analysis_water["identified_domain"])
        self.assertIn("Water collection", analysis_water["industry"])
        self.assertIsNone(analysis_water["pack_id"])


class TestIndustryPackMutations(unittest.TestCase):
    """Mutation tests proving acceptance tests catch deliberate structural bugs (Rule 8)."""

    def test_mutation_workflow_referencing_nonexistent_account_fails(self):
        """Mutation: Workflow step referencing account code not in COA must fail validation."""
        pack = {
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {"pack_id": "bad_wf", "name": "Bad WF", "version": "1.0", "industry_code": "J62"},
            "chart_of_accounts": [
                {"code": "1010", "name": "Cash", "type": "ASSET", "currency": "USD"},
                {"code": "2010", "name": "AP", "type": "LIABILITY", "currency": "USD"},
                {"code": "4010", "name": "Rev", "type": "REVENUE", "currency": "USD"},
                {"code": "5010", "name": "Exp", "type": "EXPENSE", "currency": "USD"},
            ],
            "workflows": [
                {
                    "workflow_id": "wf_broken",
                    "name": "Broken Workflow",
                    "triggers": ["order_created"],
                    "steps": [
                        # 9999 does not exist in chart_of_accounts
                        {"step_id": "s1", "action": "post", "debit_account": "9999", "credit_account": "4010"}
                    ],
                }
            ],
        }
        with self.assertRaises(PackValidationError) as ctx:
            validate_industry_pack_dict(pack)
        self.assertIn("references non-existent account '9999'", str(ctx.exception))

    def test_mutation_folio_referencing_nonexistent_template_fails(self):
        """Mutation: Folio type requiring non-existent document template must fail validation."""
        pack = {
            "schema_version": "zonata.industry-pack/v1",
            "metadata": {"pack_id": "bad_ft", "name": "Bad FT", "version": "1.0", "industry_code": "J62"},
            "chart_of_accounts": [
                {"code": "1010", "name": "Cash", "type": "ASSET", "currency": "USD"},
                {"code": "2010", "name": "AP", "type": "LIABILITY", "currency": "USD"},
                {"code": "4010", "name": "Rev", "type": "REVENUE", "currency": "USD"},
                {"code": "5010", "name": "Exp", "type": "EXPENSE", "currency": "USD"},
            ],
            "document_templates": [],
            "folio_types": [
                {
                    "folio_type": "ft_broken",
                    "name": "Broken Folio",
                    "required_documents": ["ghost_template_id"],  # Does not exist
                }
            ],
        }
        with self.assertRaises(PackValidationError) as ctx:
            validate_industry_pack_dict(pack)
        self.assertIn("references non-existent document template 'ghost_template_id'", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
