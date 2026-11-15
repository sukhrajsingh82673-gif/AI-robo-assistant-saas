"""Stage 1 tests — company data model, API, permissions, drafts, deletion steps.

Run: python3 -m pytest tests/test_company_setup.py -q
"""

import os
import sys
import tempfile
import time
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.auth import TenantManager, UserManager, UserRole

_ORIG_DB = None
_TMP = None


def setUpModule():
    global _ORIG_DB, _TMP
    _ORIG_DB = db.db_path
    _TMP = tempfile.TemporaryDirectory()
    configure_isolated_test_db(os.path.join(_TMP.name, "company_setup_test.db"))


def tearDownModule():
    global _ORIG_DB, _TMP
    if _ORIG_DB:
        db.set_db_path(_ORIG_DB)
        os.environ["ZONATA_DB_PATH"] = _ORIG_DB
    if _TMP:
        _TMP.cleanup()


from core.company_setup import CompanySetupService, CompanySetupError, CompanyStatus
from core.company_setup.api import company_setup_api
from core.company_setup.permissions import PermissionDenied, Principal
from core.company_setup.status import InvalidTransition, validate_transition


BASE_PAYLOAD = {
    "type": "NEW",
    "name": "Northwind Labs",
    "title": "AI research studio",
    "description": "A studio that builds applied AI products for mid-market companies.",
    "owner": {"name": "Sukhraj", "email": "owner@northwind.test"},
    "country": "IN",
    "industry": "Software",
}


class CompanySetupTestBase(unittest.TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        tenant = TenantManager.create_tenant(f"Company Setup Tenant {suffix}")
        self.tenant_id = tenant["tenant_id"]
        self.owner = UserManager.create_user(
            self.tenant_id, f"owner_{suffix}@northwind.test", "Owner", UserRole.OWNER
        )
        self.executive = UserManager.create_user(
            self.tenant_id, f"exec_{suffix}@northwind.test", "Executive", UserRole.EXECUTIVE
        )
        self.manager = UserManager.create_user(
            self.tenant_id, f"mgr_{suffix}@northwind.test", "Manager", UserRole.MANAGER
        )
        self.service = CompanySetupService(self.tenant_id)

    # ------------------------------------------------------------- helpers
    def owner_principal(self):
        return Principal(self.owner["user_id"], self.tenant_id, UserRole.OWNER)

    def executive_principal(self):
        return Principal(self.executive["user_id"], self.tenant_id, UserRole.EXECUTIVE)

    def manager_principal(self):
        return Principal(self.manager["user_id"], self.tenant_id, UserRole.MANAGER)

    def agent_principal(self):
        return Principal("agent_research_1", self.tenant_id, UserRole.SYSTEM_AGENT)

    def auth_ctx(self, principal):
        return {
            "user_id": principal.user_id,
            "tenant_id": principal.tenant_id,
            "role": principal.role,
            "company_id": principal.company_id,
            "principal_type": principal.principal_type,
        }

    def make_company(self, **overrides):
        payload = dict(BASE_PAYLOAD)
        payload["name"] = f"Northwind {uuid.uuid4().hex[:6]}"
        payload.update(overrides)
        return self.service.create_company(self.owner_principal(), payload)

    def complete_existing_payload(self, **overrides):
        payload = {
            "type": "EXISTING",
            "name": f"Existing Co {uuid.uuid4().hex[:6]}",
            "title": "Neighbourhood bakery chain",
            "description": "A six-store bakery business serving walk-in and online customers.",
            "owner": {"name": "Owner", "email": "owner@bakery.test", "role": "Founder"},
            "country": "IN",
            "industry": "Food & Beverage",
            "business_model": "Retail bakery with online ordering and corporate catering.",
            "revenue": {"amount": 12000000, "currency": "INR", "period": "ANNUAL"},
        }
        payload.update(overrides)
        return payload


class TestCompanyRecord(CompanySetupTestBase):
    def test_create_returns_draft_with_fields(self):
        company = self.make_company()
        self.assertEqual(company["status"], CompanyStatus.DRAFT)
        self.assertEqual(company["type"], "NEW")
        self.assertEqual(company["owner"]["email"], "owner@northwind.test")
        self.assertEqual(company["revenue"]["currency"], "INR")
        self.assertIsNotNone(company["created_at"])
        self.assertTrue(company["permissions"]["edit"])
        self.assertTrue(company["permissions"]["delete"])

    def test_duplicate_name_conflicts_unless_allowed(self):
        first = self.make_company(name="Duplicate Holdings")
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.create_company(
                self.owner_principal(), dict(BASE_PAYLOAD, name="duplicate holdings")
            )
        self.assertEqual(ctx.exception.code, "DUPLICATE_COMPANY_NAME")
        self.assertEqual(ctx.exception.status, 409)

        second = self.service.create_company(
            self.owner_principal(),
            dict(BASE_PAYLOAD, name="Duplicate Holdings", allow_duplicate=True),
        )
        self.assertNotEqual(first["id"], second["id"])

    def test_list_is_paginated_and_searchable(self):
        for i in range(5):
            self.make_company(name=f"Paged Company {i} {uuid.uuid4().hex[:4]}")
        page = self.service.list_companies(page=1, page_size=2)
        self.assertEqual(len(page["companies"]), 2)
        self.assertEqual(page["page_size"], 2)
        self.assertTrue(page["has_more"])
        found = self.service.list_companies(query="Paged Company 3")
        self.assertEqual(found["total"], 1)

    def test_update_changes_fields_and_audit(self):
        company = self.make_company()
        updated = self.service.update_company(
            self.owner_principal(),
            company["id"],
            {"title": "Updated title", "revenue": {"amount": 500000, "currency": "INR", "period": "MONTHLY"}},
        )
        self.assertEqual(updated["title"], "Updated title")
        self.assertEqual(updated["revenue"]["amount"], 500000.0)
        self.assertEqual(updated["revenue"]["period"], "MONTHLY")
        events = self.service.audit_events(self.owner_principal(), company["id"])["events"]
        actions = [e["action"] for e in events]
        self.assertIn("company.created", actions)
        self.assertIn("company.updated", actions)

    def test_company_type_is_immutable(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.update_company(self.owner_principal(), company["id"], {"type": "EXISTING"})
        self.assertEqual(ctx.exception.code, "COMPANY_TYPE_IMMUTABLE")

    def test_legacy_attention_status_is_normalised(self):
        company = self.make_company()
        with db.get_connection() as conn:
            conn.execute("UPDATE companies SET status = 'ATTENTION' WHERE company_id = ?", (company["id"],))
            conn.commit()
        record = self.service.get_company(self.owner_principal(), company["id"])
        self.assertEqual(record["status"], CompanyStatus.NEEDS_ATTENTION)
        self.assertEqual(record["status_label"], "Needs attention")


class TestStatusMachine(CompanySetupTestBase):
    def test_forbidden_transition_raises(self):
        with self.assertRaises(InvalidTransition):
            validate_transition(CompanyStatus.DRAFT, CompanyStatus.OPERATIONAL)
        with self.assertRaises(InvalidTransition):
            validate_transition(CompanyStatus.DELETED, CompanyStatus.OPERATIONAL)

    def test_submit_requires_complete_record(self):
        company = self.make_company(name="Thin Draft", description="short")
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.submit_company(self.owner_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "VALIDATION_FAILED")
        fields = {e["field"] for e in ctx.exception.detail}
        self.assertIn("description", fields)

    def test_submit_new_moves_to_creating_with_build_run(self):
        company = self.make_company()
        result = self.service.submit_company(self.owner_principal(), company["id"])
        self.assertEqual(result["build"]["run_type"], "BUILD")
        self.assertTrue(result["workflow_started"])
        self.assertTrue(result["build"]["estimate"]["is_estimate"])
        # The build runs synchronously on the durable runtime. With no research
        # or builder provider connected it finishes with gaps, so the company is
        # moved to NEEDS_ATTENTION rather than pretending the build succeeded.
        self.assertEqual(result["build"]["phase_state"], "DONE_WITH_GAPS")
        self.assertEqual(result["company"]["status"], CompanyStatus.NEEDS_ATTENTION)
        self.assertTrue(result["build"]["gaps"])
        states = {phase["id"]: phase["state"] for phase in result["build"]["phases"]}
        self.assertEqual(states["INTAKE"], "DONE")
        self.assertEqual(states["RESEARCH"], "SKIPPED")
        self.assertEqual(states["BUILD"], "SKIPPED")
        self.assertEqual(states["LEGAL_PACK"], "DONE")
        self.assertNotEqual(states["RESEARCH"], "DONE")

        with self.assertRaises(CompanySetupError) as ctx:
            self.service.submit_company(self.owner_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "ALREADY_SUBMITTED")

    def test_submit_existing_requires_revenue_and_starts_onboarding(self):
        payload = self.complete_existing_payload()
        del payload["revenue"]
        company = self.make_company(**payload)
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.submit_company(self.owner_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "VALIDATION_FAILED")

        fixed = self.make_company(**self.complete_existing_payload())
        result = self.service.submit_company(self.owner_principal(), fixed["id"])
        # Onboarding runs immediately. With no provider adapters configured it
        # honestly ends in NEEDS_ATTENTION instead of a fake OPERATIONAL state.
        self.assertTrue(result["workflow_started"])
        self.assertEqual(result["build"]["run_type"], "ONBOARDING")
        self.assertEqual(result["build"]["phase"], "ACT")
        self.assertIn(result["company"]["status"], (CompanyStatus.ONBOARDING, CompanyStatus.NEEDS_ATTENTION))

    def test_server_rejects_unknown_company_type(self):
        with self.assertRaises(CompanySetupError) as ctx:
            self.make_company(type="MERGED")
        self.assertEqual(ctx.exception.code, "INVALID_COMPANY_TYPE")


class TestTenantIsolation(CompanySetupTestBase):
    def setUp(self):
        super().setUp()
        other = TenantManager.create_tenant(f"Foreign {uuid.uuid4().hex[:6]}")
        self.other_tenant_id = other["tenant_id"]
        self.other_owner = UserManager.create_user(
            self.other_tenant_id, f"foreign_{uuid.uuid4().hex[:6]}@elsewhere.test", "Foreign", UserRole.OWNER
        )
        self.other_service = CompanySetupService(self.other_tenant_id)
        self.other_principal = Principal(self.other_owner["user_id"], self.other_tenant_id, UserRole.OWNER)

    def test_guessed_id_is_not_found(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.other_service.get_company(self.other_principal, company["id"])
        self.assertEqual(ctx.exception.status, 404)

    def test_cross_tenant_update_fails(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.other_service.update_company(self.other_principal, company["id"], {"title": "Hijacked"})
        self.assertEqual(ctx.exception.status, 404)
        original = self.service.get_company(self.owner_principal(), company["id"])
        self.assertNotEqual(original["title"], "Hijacked")

    def test_cross_tenant_delete_fails(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.other_service.request_deletion(self.other_principal, company["id"])
        self.assertEqual(ctx.exception.status, 404)
        self.assertIsNone(self.service.get_deletion(company["id"]))

    def test_cross_tenant_connection_access_fails(self):
        company = self.make_company()
        connection = self.service.connect(
            self.owner_principal(), company["id"], {"provider_id": "hubspot", "scope": ["crm.read"]}
        )
        with self.assertRaises(CompanySetupError) as ctx:
            self.other_service.disconnect(self.other_principal, company["id"], connection["connection_id"])
        self.assertEqual(ctx.exception.status, 404)
        with self.assertRaises(CompanySetupError):
            self.other_service.disconnect(self.other_principal, company["id"], "con_does_not_exist")
        with self.assertRaises(CompanySetupError):
            self.service.disconnect(self.owner_principal(), company["id"], "con_does_not_exist")

    def test_api_returns_404_for_foreign_company(self):
        company = self.make_company()
        status, payload = company_setup_api.handle(
            "GET", f"/api/v1/companies/{company['id']}", {}, {}, self.auth_ctx(self.other_principal)
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["code"], "COMPANY_NOT_FOUND")

    def test_list_only_returns_own_tenant(self):
        self.make_company()
        listing = self.other_service.list_companies()
        self.assertEqual(listing["total"], 0)


class TestPermissions(CompanySetupTestBase):
    def test_manager_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            self.service.create_company(self.manager_principal(), dict(BASE_PAYLOAD, name="Blocked Co"))
        status, payload = company_setup_api.handle(
            "POST", "/api/v1/companies", {}, dict(BASE_PAYLOAD, name="Blocked Co"), self.auth_ctx(self.manager_principal())
        )
        self.assertEqual(status, 403)

    def test_executive_needs_grant_to_edit(self):
        company = self.make_company()
        with self.assertRaises(PermissionDenied):
            self.service.update_company(self.executive_principal(), company["id"], {"title": "Nope"})

        self.service.grant_admin(self.owner_principal(), company["id"], self.executive["user_id"])
        updated = self.service.update_company(self.executive_principal(), company["id"], {"title": "Allowed"})
        self.assertEqual(updated["title"], "Allowed")
        self.assertTrue(updated["permissions"]["delete"])

    def test_only_owner_can_grant_admins(self):
        company = self.make_company()
        with self.assertRaises(PermissionDenied):
            self.service.grant_admin(self.executive_principal(), company["id"], self.manager["user_id"])

    def test_agent_can_draft_but_never_submit_or_delete(self):
        company = self.make_company()
        draft = self.service.save_draft(self.agent_principal(), {"name": "Agent draft"}, company_id=company["id"])
        self.assertTrue(draft["draft_id"])

        with self.assertRaises(PermissionDenied):
            self.service.submit_company(self.agent_principal(), company["id"])
        with self.assertRaises(PermissionDenied):
            self.service.request_deletion(self.agent_principal(), company["id"])
        with self.assertRaises(PermissionDenied):
            self.service.update_company(self.agent_principal(), company["id"], {"title": "Agent edit"})

    def test_agent_cannot_delete_even_when_granted(self):
        company = self.make_company()
        self.service.grant_admin(self.owner_principal(), company["id"], "agent_research_1")
        with self.assertRaises(PermissionDenied):
            self.service.request_deletion(self.agent_principal(), company["id"])

    def test_system_agent_role_on_wrong_tenant_cannot_view(self):
        company = self.make_company()
        foreign_agent = Principal("agent_x", "tnt_foreign", UserRole.SYSTEM_AGENT)
        with self.assertRaises(PermissionDenied):
            self.service.get_company(foreign_agent, company["id"])


class TestDrafts(CompanySetupTestBase):
    def test_draft_autosave_resume_and_delete(self):
        saved = self.service.save_draft(self.owner_principal(), {"name": "Half filled", "title": "Draft"})
        resumed = self.service.get_draft(self.owner_principal(), saved["draft_id"])
        self.assertEqual(resumed["payload"]["name"], "Half filled")

        updated = self.service.save_draft(
            self.owner_principal(), {"name": "Half filled v2"}, draft_id=saved["draft_id"]
        )
        self.assertEqual(updated["draft_id"], saved["draft_id"])
        self.assertEqual(self.service.get_draft(self.owner_principal(), saved["draft_id"])["payload"]["name"], "Half filled v2")

        listing = self.service.list_drafts(self.owner_principal())
        self.assertEqual(len(listing), 1)

        self.service.delete_draft(self.owner_principal(), saved["draft_id"])
        with self.assertRaises(CompanySetupError):
            self.service.get_draft(self.owner_principal(), saved["draft_id"])

    def test_draft_is_private_to_its_user(self):
        saved = self.service.save_draft(self.owner_principal(), {"name": "Owner draft"})
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.get_draft(self.executive_principal(), saved["draft_id"])
        self.assertEqual(ctx.exception.status, 404)

    def test_api_autosave(self):
        status, payload = company_setup_api.handle(
            "POST",
            "/api/v1/companies/drafts",
            {},
            {"payload": {"name": "API draft"}, "company_type": "NEW"},
            self.auth_ctx(self.owner_principal()),
        )
        self.assertEqual(status, 200)
        again = company_setup_api.handle(
            "GET", f"/api/v1/companies/drafts/{payload['draft_id']}", {}, {}, self.auth_ctx(self.owner_principal())
        )
        self.assertEqual(again[1]["payload"]["name"], "API draft")


class TestDeletionFlow(CompanySetupTestBase):
    def test_step_skipping_fails(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_name(self.owner_principal(), company["id"], company["name"])
        self.assertEqual(ctx.exception.code, "DELETION_NOT_REQUESTED")

        self.service.request_deletion(self.owner_principal(), company["id"])
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_identity(self.owner_principal(), company["id"], password="x")
        self.assertEqual(ctx.exception.code, "STEP_OUT_OF_ORDER")

    def test_wrong_name_fails(self):
        company = self.make_company()
        self.service.request_deletion(self.owner_principal(), company["id"])
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_name(self.owner_principal(), company["id"], "Wrong Name")
        self.assertEqual(ctx.exception.code, "NAME_MISMATCH")

    def test_request_returns_removal_summary_and_hides_nothing(self):
        company = self.make_company()
        request = self.service.request_deletion(self.owner_principal(), company["id"])
        self.assertEqual(request["status"], "AWAITING_NAME")
        self.assertIn("will_remove", request["removal_summary"])
        self.assertIn("will_keep", request["removal_summary"])
        still_there = self.service.get_company(self.owner_principal(), company["id"])
        self.assertEqual(still_there["status"], CompanyStatus.DRAFT)

    def test_name_confirmation_needs_password_before_export(self):
        suffix = uuid.uuid4().hex[:8]
        user = UserManager.create_user_with_credentials(
            self.tenant_id, f"pw_{suffix}@northwind.test", "Password Owner", "correct horse battery", UserRole.OWNER
        )
        principal = Principal(user["user_id"], self.tenant_id, UserRole.OWNER)
        company = self.make_company(name=f"Password Co {suffix}")

        # MFA is on by default in the canonical settings catalogue and no TOTP
        # verifier is wired yet, so exercise the password path explicitly.
        original = self.service._mfa_required
        self.service._mfa_required = lambda company_id: False
        try:
            self.service.request_deletion(principal, company["id"])
            request = self.service.confirm_delete_name(principal, company["id"], company["name"])
            self.assertEqual(request["status"], "AWAITING_IDENTITY")
            with self.assertRaises(CompanySetupError):
                self.service.confirm_delete_identity(principal, company["id"], password="wrong")
            ok = self.service.confirm_delete_identity(principal, company["id"], password="correct horse battery")
            self.assertEqual(ok["export"]["status"], "READY")
            self.assertTrue(ok["export"]["filename"].endswith((".pdf", ".zip")))
            self.assertEqual(ok["deletion"]["status"], "PENDING_DELETION")
        finally:
            self.service._mfa_required = original

    def test_mfa_enabled_without_enrollment_is_refused_honestly(self):
        company = self.make_company()
        original_mfa = self.service._mfa_required
        original_verify = self.service._verify_owner_password
        self.service._mfa_required = lambda company_id: True
        self.service._verify_owner_password = lambda principal, password: True
        try:
            self.service.request_deletion(self.owner_principal(), company["id"])
            self.service.confirm_delete_name(self.owner_principal(), company["id"], company["name"])

            # The TOTP verifier is real, but this account never enrolled. A
            # missing code and a dummy code must both be refused with the same
            # enrollment instruction; neither may imply a code would work.
            for extra in ({}, {"two_step_code": "123456"}):
                with self.assertRaises(CompanySetupError) as ctx:
                    self.service.confirm_delete_identity(
                        self.owner_principal(), company["id"], password="correct horse battery", **extra
                    )
                self.assertEqual(ctx.exception.code, "TWO_STEP_NOT_ENROLLED")
                self.assertEqual(ctx.exception.status, 409)
                self.assertTrue(ctx.exception.detail.get("enrollment_required"))
        finally:
            self.service._mfa_required = original_mfa
            self.service._verify_owner_password = original_verify

    def test_cancel_before_purge_keeps_company(self):
        company = self.make_company()
        self.service.request_deletion(self.owner_principal(), company["id"])
        result = self.service.cancel_deletion(self.owner_principal(), company["id"])
        self.assertTrue(result["cancelled"])
        self.assertIsNone(self.service.get_deletion(company["id"]))
        self.assertIsNotNone(self.service.get_company(self.owner_principal(), company["id"]))

    def test_cancel_reports_the_real_current_status(self):
        company = self.make_company()
        submitted = self.service.submit_company(self.owner_principal(), company["id"])
        expected_status = submitted["company"]["status"]
        self.service.request_deletion(self.owner_principal(), company["id"])
        result = self.service.cancel_deletion(self.owner_principal(), company["id"])
        self.assertEqual(result["company_status"], expected_status)
        current = self.service.get_company(self.owner_principal(), company["id"])
        self.assertEqual(current["status"], expected_status)

    def test_export_not_ready_is_honest(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.download_export(self.owner_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "EXPORT_NOT_READY")

    def test_delete_requires_owner_or_grant(self):
        company = self.make_company()
        with self.assertRaises(PermissionDenied):
            self.service.request_deletion(self.executive_principal(), company["id"])
        self.service.grant_admin(self.owner_principal(), company["id"], self.executive["user_id"])
        request = self.service.request_deletion(self.executive_principal(), company["id"])
        self.assertEqual(request["status"], "AWAITING_NAME")


class TestConnections(CompanySetupTestBase):
    def test_connect_stores_unverified_read_only_connection(self):
        company = self.make_company()
        result = self.service.connect(
            self.owner_principal(),
            company["id"],
            {"provider_id": "hubspot", "scope": ["crm.read", "contacts.read"]},
        )
        self.assertEqual(result["status"], "NEEDS_CHECK")
        self.assertFalse(result["verified"])
        connections = self.service.list_connections(self.owner_principal(), company["id"])
        self.assertEqual(len(connections), 1)
        self.assertFalse(connections[0]["has_secret"])
        self.assertEqual(connections[0]["scope"], ["crm.read", "contacts.read"])

    def test_write_scope_is_rejected(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.connect(
                self.owner_principal(), company["id"], {"provider_id": "crm", "scope": ["crm.write"]}
            )
        self.assertEqual(ctx.exception.code, "WRITE_SCOPE_NOT_ALLOWED")

    def test_test_connection_is_honest(self):
        company = self.make_company()
        connection = self.service.connect(
            self.owner_principal(), company["id"], {"provider_id": "crm", "scope": ["crm.read"]}
        )
        check = self.service.test_connection(
            self.owner_principal(), company["id"], connection["connection_id"]
        )
        self.assertFalse(check["simulated"])
        self.assertFalse(check["available"])
        self.assertFalse(check["verified"])
        self.assertIn("Nothing was read", check["error"])

    def test_disconnect_removes_connection(self):
        company = self.make_company()
        connection = self.service.connect(
            self.owner_principal(), company["id"], {"provider_id": "crm", "scope": ["crm.read"]}
        )
        result = self.service.disconnect(
            self.owner_principal(), company["id"], connection["connection_id"]
        )
        self.assertTrue(result["disconnected"])
        self.assertEqual(self.service.list_connections(self.owner_principal(), company["id"]), [])

    def test_manager_cannot_connect(self):
        company = self.make_company()
        with self.assertRaises(PermissionDenied):
            self.service.connect(self.manager_principal(), company["id"], {"provider_id": "crm"})


class TestApiRouter(CompanySetupTestBase):
    def _handle(self, method, path, body=None, principal=None):
        return company_setup_api.handle(
            method, path, {}, body or {}, self.auth_ctx(principal or self.owner_principal())
        )

    def test_full_journey_new_company(self):
        status, created = self._handle("POST", "/api/v1/companies", dict(BASE_PAYLOAD, name="Router Co"))
        self.assertEqual(status, 201)
        company_id = created["id"]

        status, listed = self._handle("GET", "/api/v1/companies")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(listed["total"], 1)

        status, fetched = self._handle("GET", f"/api/v1/companies/{company_id}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["status"], CompanyStatus.DRAFT)

        status, patched = self._handle(
            "PATCH", f"/api/v1/companies/{company_id}", {"title": "Router title"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(patched["title"], "Router title")

        status, submitted = self._handle("POST", f"/api/v1/companies/{company_id}/submit")
        self.assertEqual(status, 202)
        self.assertTrue(submitted["workflow_started"])
        self.assertEqual(submitted["company"]["status"], CompanyStatus.NEEDS_ATTENTION)

        status, build = self._handle("GET", f"/api/v1/companies/{company_id}/build")
        self.assertEqual(status, 200)
        self.assertEqual(build["phase"], "VERIFY")
        self.assertTrue(build["phases"])

        status, audit = self._handle("GET", f"/api/v1/companies/{company_id}/audit")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(audit["total"], 3)

    def test_build_retry_route_starts_a_new_attempt(self):
        status, created = self._handle("POST", "/api/v1/companies", dict(BASE_PAYLOAD, name="Router Retry Co"))
        self.assertEqual(status, 201)
        company_id = created["id"]
        status, _ = self._handle("POST", f"/api/v1/companies/{company_id}/submit")
        self.assertEqual(status, 202)

        status, retried = self._handle("POST", f"/api/v1/companies/{company_id}/build/retry")
        self.assertEqual(status, 202)
        self.assertTrue(retried["workflow_started"])
        self.assertEqual(retried["build"]["attempt"], 2)

        status, build = self._handle("GET", f"/api/v1/companies/{company_id}/build")
        self.assertEqual(status, 200)
        self.assertEqual(build["attempt"], 2)

    def test_unknown_route_returns_404(self):
        status, payload = self._handle("GET", "/api/v1/companies/comp_x/unknown")
        self.assertEqual(status, 404)

    def test_router_ignores_other_paths(self):
        self.assertIsNone(company_setup_api.handle("GET", "/api/companies", {}, {}, self.auth_ctx(self.owner_principal())))
        self.assertIsNone(company_setup_api.handle("GET", "/api/v1/companiesX", {}, {}, self.auth_ctx(self.owner_principal())))

    def test_unauthenticated_context_is_rejected(self):
        status, payload = company_setup_api.handle("GET", "/api/v1/companies", {}, {}, {})
        self.assertEqual(status, 401)

    def test_validation_error_shape(self):
        status, payload = self._handle(
            "POST", "/api/v1/companies", dict(BASE_PAYLOAD, name="X", owner={"email": "not-an-email"})
        )
        self.assertEqual(status, 422)
        self.assertEqual(payload["code"], "VALIDATION_FAILED")


if __name__ == "__main__":
    unittest.main()
