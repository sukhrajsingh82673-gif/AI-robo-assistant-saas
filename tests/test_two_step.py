"""Real TOTP two-step verification — RFC 6238 vectors, replay, lockout, storage.

Run: python3 -m pytest tests/test_two_step.py -q
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
_ORIG_EXPORT_DIR = None
_ORIG_SECRET = None

# A deterministic deployment secret so the derived storage key is stable here.
_TEST_SECRET = "two-step-test-secret-0123456789abcdef"


def setUpModule():
    global _ORIG_DB, _TMP, _ORIG_EXPORT_DIR, _ORIG_SECRET
    _ORIG_DB = db.db_path
    _TMP = tempfile.TemporaryDirectory()
    configure_isolated_test_db(os.path.join(_TMP.name, "two_step_test.db"))
    _ORIG_EXPORT_DIR = os.environ.get("ZONATA_COMPANY_EXPORT_DIR")
    os.environ["ZONATA_COMPANY_EXPORT_DIR"] = os.path.join(_TMP.name, "exports")
    _ORIG_SECRET = os.environ.get("ZONATA_AUTH_SECRET")
    os.environ["ZONATA_AUTH_SECRET"] = _TEST_SECRET


def tearDownModule():
    global _ORIG_DB, _TMP, _ORIG_EXPORT_DIR, _ORIG_SECRET
    if _ORIG_SECRET is None:
        os.environ.pop("ZONATA_AUTH_SECRET", None)
    else:
        os.environ["ZONATA_AUTH_SECRET"] = _ORIG_SECRET
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
from core.company_setup.permissions import Principal
from core.two_step import (
    TwoStepError,
    TwoStepService,
    code_at,
    provisioning_uri,
)

# RFC 6238 appendix B seed: the ASCII string "12345678901234567890".
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


class Clock:
    def __init__(self, now=None):
        self.now = float(now if now is not None else 1_700_000_000.0)

    def __call__(self):
        return self.now


def fresh_user(suffix=None):
    suffix = suffix or uuid.uuid4().hex[:8]
    tenant = TenantManager.create_tenant(f"Two Step Tenant {suffix}")
    user = UserManager.create_user_with_credentials(
        tenant["tenant_id"],
        f"step_{suffix}@northwind.test",
        "Two Step Owner",
        "correct horse battery",
        UserRole.OWNER,
    )
    return tenant["tenant_id"], user


def enroll(user_id, tenant_id, email="owner@northwind.test", clock=None):
    service = TwoStepService(clock=clock or time.time)
    started = service.begin_enrollment(user_id, tenant_id, email)
    current = clock() if clock else time.time()
    service.confirm_enrollment(user_id, code_at(started["secret"], current))
    return started["secret"]


class TestTotpAlgorithm(unittest.TestCase):
    def test_rfc6238_sha1_vectors_truncated_to_six_digits(self):
        vectors = {
            59: "287082",
            1111111109: "081804",
            1111111111: "050471",
            1234567890: "005924",
            2000000000: "279037",
            20000000000: "353130",
        }
        for timestamp, expected in vectors.items():
            self.assertEqual(code_at(RFC_SECRET, timestamp), expected, f"T={timestamp}")

    def test_provisioning_uri_is_standard_otpauth(self):
        uri = provisioning_uri("owner@northwind.test", RFC_SECRET)
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn("secret=" + RFC_SECRET, uri)
        self.assertIn("issuer=ZONATA", uri)
        self.assertIn("digits=6", uri)
        self.assertIn("period=30", uri)


class TestEnrollmentAndVerification(unittest.TestCase):
    def setUp(self):
        self.tenant_id, self.user = fresh_user()
        self.user_id = self.user["user_id"]

    def test_secret_is_not_stored_in_plaintext(self):
        service = TwoStepService()
        started = service.begin_enrollment(self.user_id, self.tenant_id, self.user["email"])
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_two_step WHERE user_id = ?", (self.user_id,)
            ).fetchone()
        self.assertIsNotNone(row)
        stored = dict(row)
        self.assertTrue(stored["pending"] == 1)
        self.assertNotEqual(stored["secret_ciphertext"], started["secret"])
        self.assertNotIn(started["secret"], str(stored))

    def test_enrollment_needs_a_real_code_before_it_counts(self):
        service = TwoStepService()
        started = service.begin_enrollment(self.user_id, self.tenant_id, self.user["email"])
        self.assertFalse(service.enrolled(self.user_id))
        self.assertTrue(service.status(self.user_id)["pending"])

        with self.assertRaises(TwoStepError) as ctx:
            service.confirm_enrollment(self.user_id, "000000")
        self.assertEqual(ctx.exception.code, "INVALID_TWO_STEP_CODE")
        self.assertFalse(service.enrolled(self.user_id))

        service.confirm_enrollment(self.user_id, code_at(started["secret"]))
        self.assertTrue(service.enrolled(self.user_id))
        self.assertFalse(service.status(self.user_id)["pending"])

        with self.assertRaises(TwoStepError) as ctx:
            service.begin_enrollment(self.user_id, self.tenant_id, self.user["email"])
        self.assertEqual(ctx.exception.code, "TWO_STEP_ALREADY_ENABLED")
        self.assertEqual(ctx.exception.status, 409)

    def test_window_and_replay(self):
        clock = Clock()
        secret = enroll(self.user_id, self.tenant_id, clock=clock)
        service = TwoStepService(clock=clock)
        base = int(clock.now // 30)

        # The step used at enrollment cannot be replayed.
        replay = code_at(secret, base * 30)
        ok, reason = service.verify_code(self.user_id, replay)
        self.assertFalse(ok)
        self.assertEqual(reason, "invalid")

        # The next step is accepted exactly once.
        next_code = code_at(secret, (base + 1) * 30)
        self.assertEqual(service.verify_code(self.user_id, next_code), (True, "ok"))
        self.assertFalse(service.verify_code(self.user_id, next_code)[0])

        # A step three periods away is outside the +/-1 window.
        far = code_at(secret, (base + 3) * 30)
        self.assertEqual(service.verify_code(self.user_id, far), (False, "invalid"))

    def test_five_wrong_codes_lock_and_expire(self):
        clock = Clock()
        secret = enroll(self.user_id, self.tenant_id, clock=clock)
        service = TwoStepService(clock=clock)
        for _ in range(5):
            service.verify_code(self.user_id, "000000")
        ok, reason = service.verify_code(self.user_id, "000000")
        self.assertEqual((ok, reason), (False, "TWO_STEP_LOCKED"))
        clock.now += 301
        # After the lock expires a real next-step code works again.
        step = int(clock.now // 30)
        self.assertEqual(service.verify_code(self.user_id, code_at(secret, step * 30)), (True, "ok"))

    def test_rotating_the_auth_secret_fails_closed(self):
        service = TwoStepService()
        started = service.begin_enrollment(self.user_id, self.tenant_id, self.user["email"])
        os.environ["ZONATA_AUTH_SECRET"] = "a-different-deployment-secret-0123456789"
        try:
            with self.assertRaises(TwoStepError) as ctx:
                TwoStepService().confirm_enrollment(self.user_id, code_at(started["secret"]))
            self.assertEqual(ctx.exception.code, "TWO_STEP_KEY_UNAVAILABLE")
            self.assertEqual(ctx.exception.status, 503)
        finally:
            os.environ["ZONATA_AUTH_SECRET"] = _TEST_SECRET
        self.assertFalse(TwoStepService().enrolled(self.user_id))

    def test_disable_removes_the_row(self):
        enroll(self.user_id, self.tenant_id)
        TwoStepService().disable(self.user_id)
        self.assertFalse(TwoStepService().enrolled(self.user_id))
        self.assertEqual(
            TwoStepService().status(self.user_id),
            {"enabled": False, "pending": False, "method": None, "configured": True},
        )


class DeletionWithTotpTestBase(unittest.TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        tenant = TenantManager.create_tenant(f"Delete Two Step {suffix}")
        self.tenant_id = tenant["tenant_id"]
        self.owner = UserManager.create_user_with_credentials(
            self.tenant_id,
            f"owner_{suffix}@northwind.test",
            "Owner",
            "correct horse battery",
            UserRole.OWNER,
        )
        self.service = CompanySetupService(self.tenant_id)
        self._mfa_patch = self.service._mfa_required
        self.service._mfa_required = lambda company_id: True

    def tearDown(self):
        self.service._mfa_required = self._mfa_patch

    def principal(self):
        return Principal(self.owner["user_id"], self.tenant_id, UserRole.OWNER)

    def make_company(self):
        return self.service.create_company(
            self.principal(),
            {
                "type": "NEW",
                "name": f"Two Step Co {uuid.uuid4().hex[:6]}",
                "title": "Two-step deletion",
                "description": "A company created to prove two-step gating is real.",
                "owner": {"name": "Owner", "email": self.owner["email"], "role": "Founder"},
                "country": "IN",
                "industry": "Software",
            },
        )

    def next_code(self, secret):
        counter = int(time.time() // 30) + 1
        return code_at(secret, counter * 30)


class TestDeletionRequiresTotp(DeletionWithTotpTestBase):
    def test_plan_reports_real_enrollment_not_just_a_setting(self):
        company = self.make_company()
        plan = self.service.deletion_plan(self.principal(), company["id"])
        self.assertTrue(plan["two_step_configured"])
        self.assertFalse(plan["two_step_enrolled"])

        enroll(self.owner["user_id"], self.tenant_id, self.owner["email"])
        plan = self.service.deletion_plan(self.principal(), company["id"])
        self.assertTrue(plan["two_step_enrolled"])

    def test_deletion_needs_a_current_code_and_consumes_it(self):
        secret = enroll(self.owner["user_id"], self.tenant_id, self.owner["email"])
        company = self.make_company()
        self.service.request_deletion(self.principal(), company["id"])
        self.service.confirm_delete_name(self.principal(), company["id"], company["name"])

        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_identity(
                self.principal(), company["id"], password="correct horse battery"
            )
        self.assertEqual(ctx.exception.code, "TWO_STEP_REQUIRED")
        self.assertEqual(ctx.exception.status, 400)

        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_identity(
                self.principal(), company["id"], password="correct horse battery", two_step_code="000000"
            )
        self.assertEqual(ctx.exception.code, "INVALID_TWO_STEP_CODE")
        self.assertEqual(ctx.exception.status, 403)

        code = self.next_code(secret)
        result = self.service.confirm_delete_identity(
            self.principal(), company["id"], password="correct horse battery", two_step_code=code
        )
        self.assertEqual(result["deletion"]["status"], "PENDING_DELETION")
        self.assertIn(result["export"]["status"], ("READY", "EMAILED"))

        # The code cannot be reused for another sensitive action.
        ok, reason = TwoStepService().verify_code(self.owner["user_id"], code)
        self.assertFalse(ok)
        self.assertEqual(reason, "invalid")

    def test_wrong_password_is_checked_before_the_code(self):
        enroll(self.owner["user_id"], self.tenant_id, self.owner["email"])
        company = self.make_company()
        self.service.request_deletion(self.principal(), company["id"])
        self.service.confirm_delete_name(self.principal(), company["id"], company["name"])
        with self.assertRaises(CompanySetupError) as ctx:
            self.service.confirm_delete_identity(
                self.principal(), company["id"], password="wrong", two_step_code="000000"
            )
        self.assertEqual(ctx.exception.code, "INVALID_PASSWORD")
        self.assertFalse(self.service.get_deletion(company["id"])["export_available"])


if __name__ == "__main__":
    unittest.main()
