"""Stage 5 tests — protected deletion, real export, recovery window and purge.

Run: python3 -m pytest tests/test_company_deletion_export.py -q
"""

import os
import sys
import tempfile
import time
import unittest
import uuid
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.auth import TenantManager, UserManager, UserRole

_ORIG_DB = None
_TMP = None
_ORIG_EXPORT_DIR = None


def setUpModule():
    global _ORIG_DB, _TMP, _ORIG_EXPORT_DIR
    _ORIG_DB = db.db_path
    _TMP = tempfile.TemporaryDirectory()
    configure_isolated_test_db(os.path.join(_TMP.name, "company_deletion_test.db"))
    _ORIG_EXPORT_DIR = os.environ.get("ZONATA_COMPANY_EXPORT_DIR")
    os.environ["ZONATA_COMPANY_EXPORT_DIR"] = os.path.join(_TMP.name, "exports")


def tearDownModule():
    global _ORIG_DB, _TMP, _ORIG_EXPORT_DIR
    if _ORIG_EXPORT_DIR is None:
        os.environ.pop("ZONATA_COMPANY_EXPORT_DIR", None)
    else:
        os.environ["ZONATA_COMPANY_EXPORT_DIR"] = _ORIG_EXPORT_DIR
    if _ORIG_DB:
        db.set_db_path(_ORIG_DB)
        os.environ["ZONATA_DB_PATH"] = _ORIG_DB
    if _TMP:
        _TMP.cleanup()


from core.company_setup import CompanySetupService, CompanySetupError, CompanyStatus
from core.company_setup import audit
from core.company_setup.api import company_setup_api
from core.company_setup.email_adapter import export_email_adapter
from core.company_setup.permissions import PermissionDenied, Principal


class DeletionExportTestBase(unittest.TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        tenant = TenantManager.create_tenant(f"Deletion Tenant {suffix}")
        self.tenant_id = tenant["tenant_id"]
        self.owner = UserManager.create_user_with_credentials(
            self.tenant_id,
            f"owner_{suffix}@northwind.test",
            "Owner",
            "correct horse battery",
            UserRole.OWNER,
        )
        self.other = UserManager.create_user(
            self.tenant_id, f"other_{suffix}@northwind.test", "Other", UserRole.EXECUTIVE
        )
        self.service = CompanySetupService(self.tenant_id)
        self._mfa_patch = self.service._mfa_required
        self.service._mfa_required = lambda company_id: False

    def tearDown(self):
        self.service._mfa_required = self._mfa_patch

    def owner_principal(self):
        return Principal(self.owner["user_id"], self.tenant_id, UserRole.OWNER)

    def agent_principal(self):
        return Principal("agent_deleter", self.tenant_id, UserRole.SYSTEM_AGENT)

    def auth_ctx(self, principal):
        return {
            "user_id": principal.user_id,
            "tenant_id": principal.tenant_id,
            "role": principal.role,
            "company_id": principal.company_id,
            "principal_type": principal.principal_type,
        }

    def make_company(self, name=None):
        return self.service.create_company(
            self.owner_principal(),
            {
                "type": "NEW",
                "name": name or f"Deletion Co {uuid.uuid4().hex[:6]}",
                "title": "Deletion test company",
                "description": "A company created to test the protected deletion workflow.",
                "owner": {"name": "Owner", "email": self.owner["email"], "role": "Founder"},
                "country": "IN",
                "industry": "Software",
            },
        )

    def advance(self, company, password="correct horse battery"):
        self.service.request_deletion(self.owner_principal(), company["id"])
        self.service.confirm_delete_name(self.owner_principal(), company["id"], company["name"])
        return self.service.confirm_delete_identity(
            self.owner_principal(), company["id"], password=password
        )


class TestDeletionGuards(DeletionExportTestBase):
    def test_step_skipping_and_wrong_name_fail(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_name(self.owner_principal(), company["id"], company["name"])
        self.assertEqual(ctx.exception.code, "DELETION_NOT_REQUESTED")
        self.service.request_deletion(self.owner_principal(), company["id"])
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_identity(self.owner_principal(), company["id"], password="x")
        self.assertEqual(ctx.exception.code, "STEP_OUT_OF_ORDER")
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_name(self.owner_principal(), company["id"], "Wrong name")
        self.assertEqual(ctx.exception.code, "NAME_MISMATCH")

    def test_wrong_password_never_exports_and_keeps_status(self):
        company = self.make_company()
        self.service.request_deletion(self.owner_principal(), company["id"])
        self.service.confirm_delete_name(self.owner_principal(), company["id"], company["name"])
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_identity(self.owner_principal(), company["id"], password="wrong")
        self.assertEqual(ctx.exception.code, "INVALID_PASSWORD")
        current = self.service.get_company(self.owner_principal(), company["id"])
        self.assertEqual(current["status"], CompanyStatus.DRAFT)
        self.assertFalse(self.service.get_deletion(company["id"])["export_available"])

    def test_agent_never_deletes_even_when_granted(self):
        company = self.make_company()
        with self.assertRaises(PermissionDenied):
            self.service.request_deletion(self.agent_principal(), company["id"])
        self.service.grant_admin(self.owner_principal(), company["id"], "agent_deleter")
        with self.assertRaises(PermissionDenied):
            self.service.request_deletion(self.agent_principal(), company["id"])

    def test_cross_tenant_and_guessed_ids_are_404(self):
        company = self.make_company()
        other_tenant = TenantManager.create_tenant(f"Other {uuid.uuid4().hex[:6]}")
        other_user = UserManager.create_user(other_tenant["tenant_id"], "other@x.test", "Other", UserRole.OWNER)
        other_service = CompanySetupService(other_tenant["tenant_id"])
        other_principal = Principal(other_user["user_id"], other_tenant["tenant_id"], UserRole.OWNER)
        with self.assertRaises(CompanySetupError) as ctx:
            other_service.request_deletion(other_principal, company["id"])
        self.assertEqual(ctx.exception.status, 404)
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.request_deletion(self.owner_principal(), "comp_does_not_exist")
        self.assertEqual(ctx.exception.status, 404)
        self.assertIsNone(self.service.get_deletion("comp_does_not_exist"))

    def test_cancel_before_identity_restores_nothing(self):
        company = self.make_company()
        self.service.request_deletion(self.owner_principal(), company["id"])
        result = self.service.cancel_deletion(self.owner_principal(), company["id"])
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["company_status"], CompanyStatus.DRAFT)
        self.assertIsNone(self.service.get_deletion(company["id"]))


class TestExportAndRecovery(DeletionExportTestBase):
    def test_identity_generates_a_real_downloadable_export(self):
        company = self.make_company()
        result = self.advance(company)
        self.assertIn(result["export"]["status"], ("READY", "EMAILED"))
        self.assertEqual(result["deletion"]["status"], "PENDING_DELETION")
        self.assertTrue(result["deletion"]["export_available"])
        self.assertGreater(result["export"]["size_bytes"], 500)
        self.assertGreater(result["export"]["pages"], 1)

        download = self.service.download_export_file(self.owner_principal(), company["id"])
        content = download["__file__"]
        self.assertTrue(content.startswith((b"%PDF-1.4", b"PK\x03\x04")))
        self.assertIn(download["filename"].rsplit(".", 1)[-1], ("pdf", "zip"))
        if content.startswith(b"%PDF"):
            self.assertGreaterEqual(content.count(b"/Type /Page"), 1)
            self.assertTrue(content.rstrip().endswith(b"%%EOF"))
        current = self.service.get_deletion(company["id"])
        self.assertIsNotNone(current["download_confirmed_at"])

    def test_export_zip_preserves_original_unicode_text(self):
        company = self.make_company(name=f"شركة النور {uuid.uuid4().hex[:4]}")
        result = self.advance(company)
        self.assertEqual(result["export"]["content_type"], "application/zip")
        self.assertTrue(result["export"]["filename"].endswith(".zip"))
        download = self.service.download_export_file(self.owner_principal(), company["id"])
        with zipfile.ZipFile(__import__("io").BytesIO(download["__file__"])) as archive:
            names = archive.namelist()
            self.assertIn("company-export.json", names)
            self.assertIn("manifest.json", names)
            self.assertTrue(any(name.endswith(".pdf") for name in names))
            data = archive.read("company-export.json").decode("utf-8")
            self.assertIn("شركة النور", data)

    def test_unconfigured_email_falls_back_to_in_app_download(self):
        company = self.make_company()
        original = export_email_adapter.send
        export_email_adapter.send = lambda **kwargs: {"status": "NOT_CONFIGURED", "detail": "No SMTP server"}
        try:
            result = self.advance(company)
        finally:
            export_email_adapter.send = original
        self.assertEqual(result["export"]["status"], "READY")
        self.assertEqual(result["email"]["status"], "NOT_CONFIGURED")
        self.assertEqual(result["deletion"]["email_status"], "NOT_CONFIGURED")
        self.assertEqual(result["deletion"]["purge_blocked_reason"], "WAITING_FOR_DOWNLOAD")
        self.assertGreater(result["deletion"]["purge_after"], time.time())
        self.assertFalse(result["purged"])

    def test_verified_account_email_sends_and_marks_emailed(self):
        company = self.make_company()
        sent = {}

        def fake_send(**kwargs):
            sent.update(kwargs)
            return {"status": "SENT", "detail": "sent"}

        original = export_email_adapter.send
        export_email_adapter.send = fake_send
        try:
            result = self.advance(company)
        finally:
            export_email_adapter.send = original
        self.assertEqual(result["export"]["status"], "EMAILED")
        self.assertEqual(result["email"]["status"], "SENT")
        self.assertEqual(sent["recipient"], self.owner["email"])
        self.assertIn("**", result["email"]["recipient"])
        self.assertEqual(result["deletion"]["email_status"], "SENT")
        self.assertIsNone(result["deletion"]["purge_blocked_reason"])

    def test_zero_day_window_with_email_purges_immediately(self):
        company = self.make_company()
        self.service._recovery_days = lambda company_id: 0
        original = export_email_adapter.send
        export_email_adapter.send = lambda **kwargs: {"status": "SENT", "detail": "sent"}
        try:
            result = self.advance(company)
        finally:
            export_email_adapter.send = original
        self.assertTrue(result["purged"])
        record = self.service._require_company(company["id"], include_deleted=True)
        self.assertEqual(record["status"], CompanyStatus.DELETED)
        latest = self.service._latest_deletion(company["id"])
        self.assertEqual(latest["status"], "COMPLETED")

    def test_zero_day_without_email_waits_for_download_then_purges(self):
        company = self.make_company()
        self.service._recovery_days = lambda company_id: 0
        result = self.advance(company)
        self.assertFalse(result["purged"])
        self.assertEqual(result["deletion"]["purge_blocked_reason"], "WAITING_FOR_DOWNLOAD")
        download = self.service.download_export_file(self.owner_principal(), company["id"])
        self.assertTrue(download["__file__"].startswith((b"%PDF", b"PK")))
        record = self.service._require_company(company["id"], include_deleted=True)
        self.assertEqual(record["status"], CompanyStatus.DELETED)

    def test_cancel_inside_window_restores_the_exact_status(self):
        company = self.make_company()
        submitted = self.service.submit_company(self.owner_principal(), company["id"])
        expected = submitted["company"]["status"]
        result = self.advance(company)
        self.assertEqual(result["deletion"]["previous_status"], expected)
        cancelled = self.service.cancel_deletion(self.owner_principal(), company["id"])
        self.assertTrue(cancelled["cancelled"])
        restored = self.service.get_company(self.owner_principal(), company["id"])
        self.assertEqual(restored["status"], expected)
        self.assertIsNone(self.service.get_deletion(company["id"]))

    def test_purge_due_after_window_keeps_minimal_audit_and_removes_data(self):
        company = self.make_company()
        self.advance(company)
        self.service.download_export_file(self.owner_principal(), company["id"])
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO departments (department_id, company_id, tenant_id, name, budget_limit, spending_limit, status, created_at) "
                "VALUES (?, ?, ?, ?, 0, 0, 'ACTIVE', ?)",
                (f"dep_{uuid.uuid4().hex[:8]}", company["id"], self.tenant_id, "Ops", time.time()),
            )
            conn.execute(
                "UPDATE company_deletion_requests SET purge_after = ? WHERE company_id = ? AND tenant_id = ?",
                (time.time() - 5, company["id"], self.tenant_id),
            )
            conn.commit()
        purged = self.service.purge_due(company_id=company["id"])
        self.assertEqual(len(purged), 1)
        self.assertTrue(purged[0]["purged"])
        record = self.service._require_company(company["id"], include_deleted=True)
        self.assertEqual(record["status"], CompanyStatus.DELETED)
        self.assertIsNone(record["description"])
        self.assertIsNone(record["website"])
        with db.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM departments WHERE company_id = ?", (company["id"],)
            ).fetchone()["n"]
            self.assertEqual(int(count), 0)
        events = audit.list_events(self.tenant_id, company["id"], limit=50)
        self.assertTrue(any(event["action"] == "company.delete.purged" for event in events))
        latest = self.service._latest_deletion(company["id"])
        self.assertEqual(latest["status"], "COMPLETED")
        self.assertIsNotNone(latest["completed_at"])

    def test_purge_is_blocked_until_export_is_delivered(self):
        company = self.make_company()
        self.advance(company)
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE company_deletion_requests SET purge_after = ? WHERE company_id = ? AND tenant_id = ?",
                (time.time() - 5, company["id"], self.tenant_id),
            )
            conn.commit()
        self.assertEqual(self.service.purge_due(company_id=company["id"]), [])
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.purge_now(self.owner_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "EXPORT_NOT_DELIVERED")
        self.service.download_export_file(self.owner_principal(), company["id"])
        record = self.service._require_company(company["id"], include_deleted=True)
        self.assertEqual(record["status"], CompanyStatus.DELETED)

    def test_api_export_returns_file_and_legal_items_route(self):
        company = self.make_company()
        self.advance(company)
        status, payload = company_setup_api.handle(
            "GET",
            f"/api/v1/companies/{company['id']}/export",
            {},
            {},
            self.auth_ctx(self.owner_principal()),
        )
        self.assertEqual(status, 200)
        self.assertIn("__file__", payload)
        self.assertIn(payload["content_type"], ("application/pdf", "application/zip"))
        status, legal = company_setup_api.handle(
            "GET",
            f"/api/v1/companies/{company['id']}/legal",
            {},
            {},
            self.auth_ctx(self.owner_principal()),
        )
        self.assertEqual(status, 200)
        self.assertIn("legal_items", legal)


if __name__ == "__main__":
    unittest.main()
