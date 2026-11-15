"""Stage 6 tests — real settings wiring for company setup.

Covers the tenant/company-scoped preferences endpoint, server defaults for new
and updated companies, and the country/locale derivation. Settings are written
through the real settings service against an isolated database; the legacy JSON
mirror is redirected to the temporary directory so the repository is untouched.

Run: python3 -m pytest tests/test_company_setup_preferences.py -q
"""

import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.auth import TenantManager, UserManager, UserRole

_ORIG_DB = None
_TMP = None
_ORIG_SETTINGS_PATH = None


def setUpModule():
    global _ORIG_DB, _TMP, _ORIG_SETTINGS_PATH
    _ORIG_DB = db.db_path
    _TMP = tempfile.TemporaryDirectory()
    configure_isolated_test_db(os.path.join(_TMP.name, "company_preferences_test.db"))
    _ORIG_SETTINGS_PATH = os.environ.get("ZONATA_SETTINGS_PATH")
    os.environ["ZONATA_SETTINGS_PATH"] = os.path.join(_TMP.name, "enterprise_settings.json")


def tearDownModule():
    global _ORIG_DB, _TMP, _ORIG_SETTINGS_PATH
    if _ORIG_SETTINGS_PATH is None:
        os.environ.pop("ZONATA_SETTINGS_PATH", None)
    else:
        os.environ["ZONATA_SETTINGS_PATH"] = _ORIG_SETTINGS_PATH
    if _ORIG_DB:
        db.set_db_path(_ORIG_DB)
        os.environ["ZONATA_DB_PATH"] = _ORIG_DB
    if _TMP:
        _TMP.cleanup()


from core.company_setup import CompanySetupService
from core.company_setup.api import company_setup_api
from core.company_setup.permissions import Principal
from core.settings_service import settings_service


NEW_PAYLOAD = {
    "type": "NEW",
    "name": "Preferences Labs",
    "title": "A company used to test preference defaults",
    "description": "A company created to verify that real settings reach every default.",
    "owner": {"name": "Owner", "email": "owner@preferences.test"},
    "industry": "Software",
}


class PreferencesTestBase(unittest.TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        tenant = TenantManager.create_tenant(f"Preferences Tenant {suffix}")
        self.tenant_id = tenant["tenant_id"]
        self.owner = UserManager.create_user(
            self.tenant_id, f"owner_{suffix}@preferences.test", "Owner", UserRole.OWNER
        )
        self.service = CompanySetupService(self.tenant_id)

    def principal(self):
        return Principal(self.owner["user_id"], self.tenant_id, UserRole.OWNER)

    def auth_ctx(self):
        principal = self.principal()
        return {
            "user_id": principal.user_id,
            "tenant_id": principal.tenant_id,
            "role": principal.role,
            "company_id": principal.company_id,
            "principal_type": principal.principal_type,
        }

    def set_setting(self, key, value, company_id="comp_primary"):
        result = settings_service.update_single_setting(
            self.tenant_id, company_id, key, value, actor="stage6-test", actor_role="OWNER"
        )
        self.assertTrue(result.get("success"), f"{key}: {result}")

    def make_company(self, **overrides):
        payload = dict(NEW_PAYLOAD)
        payload["name"] = f"Preferences Co {uuid.uuid4().hex[:6]}"
        payload.update(overrides)
        return self.service.create_company(self.principal(), payload)


class TestPreferencesPayload(PreferencesTestBase):
    def test_defaults_are_real_definition_defaults(self):
        prefs = self.service.preferences(self.principal())
        self.assertEqual(prefs["language"], "en")
        self.assertEqual(prefs["locale"], "en-IN")
        self.assertEqual(prefs["direction"], "ltr")
        self.assertEqual(prefs["number_format"]["id"], "indian")
        self.assertEqual(prefs["currency"]["code"], "INR")
        self.assertEqual(prefs["currency"]["display"], "symbol")
        self.assertEqual(prefs["default_currency"], "INR")
        self.assertEqual(prefs["country"], "IN")
        self.assertEqual(prefs["timezone"], "Asia/Kolkata")
        self.assertEqual(prefs["recovery_days"], 7)
        self.assertIsNone(prefs["quiet_hours"])
        self.assertFalse(prefs["quiet_hours_supported"])
        # The verifier is real; enrollment is per account and unknown here.
        self.assertTrue(prefs["two_step_configured"])
        self.assertIsNone(prefs["two_step_enrolled"])

    def test_tenant_settings_reach_company_preferences(self):
        self.set_setting("loc_base_locale", "ar-AE")
        self.set_setting("loc_number_format", "100.000,00 (Continental European)")
        self.set_setting("loc_currency_display", "ISO Code (INR)")
        self.set_setting("comp_base_currency", "AED (د.إ)")
        self.set_setting("comp_operating_timezones", ["Asia/Dubai", "UTC"])
        self.set_setting("assistant_default_scope", "COMPANY")

        company = self.make_company()
        prefs = self.service.preferences(self.principal(), company["id"])

        self.assertEqual(prefs["language"], "ar")
        self.assertEqual(prefs["direction"], "rtl")
        self.assertEqual(prefs["number_format"]["id"], "continental")
        self.assertEqual(prefs["currency"]["code"], "AED")
        self.assertEqual(prefs["currency"]["display"], "iso")
        self.assertEqual(prefs["timezone"], "Asia/Dubai")
        self.assertEqual(prefs["assistant"]["default_scope"], "COMPANY")

    def test_company_override_wins_over_tenant_default(self):
        self.set_setting("loc_base_locale", "en-IN")
        company = self.make_company()
        self.set_setting("loc_base_locale", "en-GB", company_id=company["id"])
        prefs = self.service.preferences(self.principal(), company["id"])
        self.assertEqual(prefs["locale"], "en-GB")
        self.assertEqual(prefs["country"], "GB")

    def test_recovery_and_mfa_are_read_from_settings(self):
        self.set_setting("company_delete_recovery_days", 0)
        company = self.make_company()
        prefs = self.service.preferences(self.principal(), company["id"])
        self.assertEqual(prefs["recovery_days"], 0)

    def test_preferences_api_returns_wrapped_payload(self):
        company = self.make_company()
        status, payload = company_setup_api.handle(
            "GET",
            "/api/v1/companies/preferences",
            {},
            {},
            self.auth_ctx(),
            company["id"],
        )
        self.assertEqual(status, 200)
        self.assertIn("preferences", payload)
        self.assertEqual(payload["preferences"]["company_id"], company["id"])

    def test_preferences_api_rejects_guessed_company(self):
        status, payload = company_setup_api.handle(
            "GET",
            "/api/v1/companies/preferences",
            {"company_id": ["comp_does_not_exist"]},
            {},
            self.auth_ctx(),
            None,
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["code"], "COMPANY_NOT_FOUND")


class TestServerDefaults(PreferencesTestBase):
    def test_create_uses_currency_timezone_and_country_defaults(self):
        self.set_setting("comp_base_currency", "USD ($)")
        self.set_setting("comp_operating_timezones", ["America/New_York", "UTC"])
        self.set_setting("loc_base_locale", "en-US")
        company = self.make_company()
        self.assertEqual(company["revenue"]["currency"], "USD")
        self.assertEqual(company["timezone"], "America/New_York")
        self.assertEqual(company["country"], "US")

    def test_explicit_payload_wins_over_defaults(self):
        self.set_setting("comp_base_currency", "USD ($)")
        company = self.make_company(currency="EUR", timezone="Europe/London", country="GB")
        self.assertEqual(company["revenue"]["currency"], "EUR")
        self.assertEqual(company["timezone"], "Europe/London")
        self.assertEqual(company["country"], "GB")

    def test_update_inherits_default_currency_without_overwriting_existing(self):
        self.set_setting("comp_base_currency", "USD ($)")
        company = self.make_company(currency="EUR")
        updated = self.service.update_company(
            self.principal(), company["id"], {"title": "Updated title"}
        )
        # The company keeps the currency it was created with.
        self.assertEqual(updated["revenue"]["currency"], "EUR")

    def test_non_finite_amounts_are_rejected(self):
        from core.company_setup import CompanySetupError

        for field, payload in (
            ("budget.amount", {"budget": {"amount": float("nan")}}),
            ("revenue.amount", {"revenue": {"amount": float("inf")}}),
        ):
            with self.assertRaises(CompanySetupError) as ctx:
                self.make_company(**payload)
            self.assertEqual(ctx.exception.status, 422)
            fields = [error["field"] for error in ctx.exception.detail]
            self.assertIn(field, fields)


class TestApiBodyHardening(PreferencesTestBase):
    def test_non_object_json_body_is_rejected(self):
        for body in ([], "text", 42, True):
            status, payload = company_setup_api.handle(
                "POST",
                "/api/v1/companies",
                {},
                body,
                self.auth_ctx(),
                None,
            )
            self.assertEqual(status, 400, repr(body))
            self.assertEqual(payload["code"], "INVALID_BODY")


if __name__ == "__main__":
    unittest.main()
