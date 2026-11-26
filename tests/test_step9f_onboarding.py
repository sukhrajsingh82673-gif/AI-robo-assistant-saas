"""
Tests for Sub-Step 9F: Onboarding Wizard, Demo Company Sandbox, CSV Importer, and EU Data Act Export.
"""

import json
import pytest
from core.onboarding.wizard import OnboardingWizard, WizardStep
from core.onboarding.demo_company import DemoCompanySeeder
from core.onboarding.importer import CsvDataImporter
from core.compliance.data_act_export import DataActExportEngine


class TestStep9fOnboarding:

    def test_onboarding_wizard_step_by_step_progression(self):
        """Verify OnboardingWizard traverses all steps and completes setup."""
        wizard = OnboardingWizard(tenant_id="tenant_new_01")
        assert wizard.state.current_step == WizardStep.COMPANY_PROFILE

        # 1. Company Profile
        with pytest.raises(ValueError, match="Company name and jurisdiction are mandatory"):
            wizard.submit_profile(company_name="", jurisdiction="", industry="")

        wizard.submit_profile("OmniTech Labs", "DE", "Technology")
        assert wizard.state.current_step == WizardStep.DEPARTMENTS
        assert wizard.state.profile_data["company_name"] == "OmniTech Labs"

        # 2. Departments
        with pytest.raises(ValueError, match="Select at least one department"):
            wizard.select_departments([])

        wizard.select_departments(["finance", "sales", "hr"])
        assert wizard.state.current_step == WizardStep.PLAN_SELECTION
        assert "finance" in wizard.state.selected_departments

        # 3. Plan Selection
        with pytest.raises(ValueError, match="Invalid plan code"):
            wizard.select_plan("ultra_vip_invalid")

        wizard.select_plan("team")
        assert wizard.state.current_step == WizardStep.TEAM_INVITES
        assert wizard.state.selected_plan == "team"

        # 4. Team Invites
        wizard.invite_team(["lead@omnitech.de", "cfo@omnitech.de"])
        assert wizard.state.current_step == WizardStep.DEMO_PREVIEW
        assert len(wizard.state.invited_emails) == 2

        # 5. Complete Onboarding
        completed = wizard.complete_onboarding(seed_demo=True)
        assert completed.is_complete is True
        assert completed.demo_seeded is True
        assert completed.completed_at is not None

    def test_demo_company_sandbox_isolation_and_reset(self):
        """Verify DemoCompanySeeder generates isolated synthetic environment and resets cleanly."""
        demo = DemoCompanySeeder.seed_demo_tenant("tenant_demo_user")
        assert demo["is_demo"] is True
        assert demo["tenant_id"] == "tenant_demo_user"
        assert len(demo["chart_of_accounts"]) >= 3
        assert len(demo["invoices"]) >= 2
        assert len(demo["active_agents"]) >= 2
        assert demo["kpis"]["runway_months"] > 0

        # Reset demo data
        res = DemoCompanySeeder.reset_demo_data("tenant_demo_user")
        assert res["status"] == "RESET_COMPLETE"

    def test_csv_importer_dry_run_and_atomic_rollback(self):
        """Verify CSV importer validates rows, supports dry-run, and executes atomic rollback on error."""
        valid_csv = (
            "customer_name,email,country\n"
            "Globex Corp,billing@globex.com,US\n"
            "Initech,accounts@initech.com,CA\n"
            "Wayne Ent,bruce@wayne.com,US\n"
        )

        # 1. Dry run: valid rows checked without persistence
        dry_res = CsvDataImporter.import_customers_csv(valid_csv, dry_run=True)
        assert dry_res.success is True
        assert dry_res.valid_rows == 3
        assert dry_res.error_rows == 0
        assert len(dry_res.imported_records) == 0  # Dry run leaves records unpersisted

        # 2. Real import: records populated
        real_res = CsvDataImporter.import_customers_csv(valid_csv, dry_run=False)
        assert real_res.success is True
        assert len(real_res.imported_records) == 3

        # 3. Malformed CSV with errors on rows 2 and 3 -> Atomic rollback
        malformed_csv = (
            "customer_name,email,country\n"
            ",missing_name@example.com,US\n"  # Missing name (row 2)
            "Acme Corp,bad_email_no_at,US\n"    # Bad email (row 3)
            "Valid Corp,good@corp.com,DE\n"     # Valid (row 4)
        )
        bad_res = CsvDataImporter.import_customers_csv(malformed_csv, dry_run=False)
        assert bad_res.success is False
        assert bad_res.error_rows == 2
        assert len(bad_res.errors) == 2
        # Verify atomic rollback: valid row 4 was NOT imported
        assert len(bad_res.imported_records) == 0
        error_fields = [e.field for e in bad_res.errors]
        assert "customer_name" in error_fields
        assert "email" in error_fields

    def test_eu_data_act_export_engine_and_zero_exit_fees(self):
        """Verify EU Data Act export generates complete machine-readable bundle with zero exit fees."""
        tenant_id = "tenant_export_client"
        profile = {"company_name": "Berlin Logistics GmbH", "jurisdiction": "DE"}
        subs = [{"plan_id": "team", "status": "active"}]
        ledger = [{"metric": "ai_tokens", "quantity": 50000}]
        invoices = [{"invoice_id": "inv_01", "total_cents": 9900}]
        audit = [{"action": "LOGIN", "timestamp": 1700000000.0}]

        export = DataActExportEngine.generate_full_tenant_export(
            tenant_id=tenant_id,
            company_profile=profile,
            subscriptions=subs,
            usage_ledger=ledger,
            invoices=invoices,
            audit_trail=audit,
        )

        assert export.regulatory_framework == "Regulation (EU) 2023/2854"
        assert export.exit_fees_charged_cents == 0  # Zero exit fee strictly mandated
        assert export.manifest["entity_counts"]["invoices"] == 1
        assert export.manifest["entity_counts"]["usage_ledger_records"] == 1

        # Verify parsed archive
        parsed = json.loads(export.archive_json)
        assert parsed["metadata"]["governing_law"] == "EU Regulation 2023/2854 (EU Data Act)"
        assert parsed["company_profile"]["company_name"] == "Berlin Logistics GmbH"
        assert len(parsed["invoices"]) == 1
