"""Stage 3 tests — the Company Build workflow and its projection.

Run: python3 -m pytest tests/test_company_build_workflow.py -q
"""

import json
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


def setUpModule():
    global _ORIG_DB, _TMP
    _ORIG_DB = db.db_path
    _TMP = tempfile.TemporaryDirectory()
    configure_isolated_test_db(os.path.join(_TMP.name, "company_build_test.db"))


def tearDownModule():
    global _ORIG_DB, _TMP
    if _ORIG_DB:
        db.set_db_path(_ORIG_DB)
        os.environ["ZONATA_DB_PATH"] = _ORIG_DB
    if _TMP:
        _TMP.cleanup()


from core.company_setup import CompanySetupError, CompanySetupService, CompanyStatus
from core.company_setup.build_workflow import CompanyBuildWorkflow, PHASE_SPECS
from core.company_setup.permissions import PermissionDenied, Principal


NEW_PAYLOAD = {
    "type": "NEW",
    "name": "Workflow Labs",
    "title": "Applied AI studio",
    "description": "A studio that builds applied AI products for mid-market companies.",
    "owner": {"name": "Owner", "email": "owner@workflow.test", "role": "Founder"},
    "country": "IN",
    "industry": "Software",
}

EXISTING_PAYLOAD = {
    "type": "EXISTING",
    "name": "Workflow Bakery",
    "title": "Neighbourhood bakery chain",
    "description": "A six-store bakery business serving walk-in and online customers.",
    "owner": {"name": "Owner", "email": "owner@bakery.test", "role": "Founder"},
    "country": "IN",
    "industry": "Food & Beverage",
    "business_model": "Retail bakery with online ordering and corporate catering.",
    "revenue": {"amount": 12000000, "currency": "INR", "period": "ANNUAL"},
}


class BuildWorkflowTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suffix = uuid.uuid4().hex[:8]
        cls.tenant = TenantManager.create_tenant(f"Build Tenant {suffix}")
        cls.tenant_id = cls.tenant["tenant_id"]
        cls.owner = UserManager.create_user(
            cls.tenant_id, f"owner_{suffix}@workflow.test", "Owner", UserRole.OWNER
        )
        cls.other_tenant = TenantManager.create_tenant(f"Build Other {suffix}")
        cls.other_owner = UserManager.create_user(
            cls.other_tenant["tenant_id"], f"other_{suffix}@workflow.test", "Other", UserRole.OWNER
        )

    def owner_principal(self):
        return Principal(self.owner["user_id"], self.tenant_id, UserRole.OWNER)

    def other_principal(self):
        return Principal(self.other_owner["user_id"], self.other_tenant["tenant_id"], UserRole.OWNER)

    def service(self):
        return CompanySetupService(self.tenant_id)

    def make_company(self, payload=None, **overrides):
        data = dict(payload or NEW_PAYLOAD)
        data["name"] = f"{data['name']} {uuid.uuid4().hex[:6]}"
        data.update(overrides)
        return self.service().create_company(self.owner_principal(), data)

    def submit_new(self, **overrides):
        company = self.make_company(**overrides)
        result = self.service().submit_company(self.owner_principal(), company["id"])
        return company, result


class TestBuildPhases(BuildWorkflowTestBase):
    def test_new_company_runs_real_phases_and_marks_provider_gaps(self):
        company, result = self.submit_new()

        self.assertTrue(result["workflow_started"])
        build = result["build"]
        self.assertEqual(build["attempt"], 1)
        self.assertEqual(build["run_type"], "BUILD")
        self.assertEqual(build["phase"], "VERIFY")
        self.assertEqual(build["phase_state"], "DONE_WITH_GAPS")
        self.assertEqual(result["company"]["status"], CompanyStatus.NEEDS_ATTENTION)

        phases = {phase["id"]: phase for phase in build["phases"]}
        self.assertEqual(list(phases), [spec["id"] for spec in PHASE_SPECS["NEW"]])
        for phase_id in ("INTAKE", "PLAN", "LEGAL_PACK", "VERIFY"):
            self.assertEqual(phases[phase_id]["state"], "DONE", phase_id)
        for phase_id in ("RESEARCH", "BUILD"):
            self.assertEqual(phases[phase_id]["state"], "SKIPPED", phase_id)
            self.assertTrue(phases[phase_id]["note"], "a skipped phase must say why")
        self.assertEqual(phases["OPERATIONAL"]["state"], "PENDING")

        gap_phases = {gap["phase"] for gap in build["gaps"]}
        self.assertEqual(gap_phases, {"RESEARCH", "BUILD"})
        self.assertEqual(gap_phases, {gap["phase"] for gap in build["waiting_on"]})

    def test_skipped_phases_never_invent_findings_or_assets(self):
        company, result = self.submit_new()
        build = result["build"]

        self.assertNotIn("research", build)
        self.assertEqual(build["brief"]["name"], company["name"])
        self.assertFalse(build["gaps"][0]["message"].startswith("Simulated"))

        log_messages = " ".join(entry["message"] for entry in build["log"]).lower()
        self.assertIn("nothing was researched", log_messages)
        self.assertIn("nothing was built", log_messages)

        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT name, status FROM company_legal_items WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, company["id"]),
            ).fetchall()
        names = {row["name"] for row in rows}
        self.assertIn("Privacy policy", names)
        self.assertIn("Terms of service", names)
        for row in rows:
            self.assertEqual(row["status"], "DRAFT")

    def test_progress_checks_and_estimate_are_projected(self):
        company, result = self.submit_new()
        build = result["build"]

        self.assertGreater(build["progress"], 0)
        self.assertLess(build["progress"], 1)
        self.assertEqual(build["progress_percent"], int(round(build["progress"] * 100)))
        self.assertTrue(build["estimate"]["is_estimate"])
        self.assertEqual(build["estimate"]["min_days"], 1)
        self.assertEqual(build["estimate"]["max_days"], 3)

        checks = {check["id"]: check["ok"] for check in build["checks"]}
        self.assertTrue(checks["brief"])
        self.assertTrue(checks["plan"])
        self.assertTrue(checks["legal"])
        self.assertFalse(checks["research"])
        self.assertFalse(checks["systems"])

        fetched = self.service().get_build(company["id"])
        self.assertEqual(fetched["phase"], "VERIFY")
        self.assertEqual(fetched["attempt"], 1)

    def test_build_actions_are_audited(self):
        company, result = self.submit_new()
        events = self.service().audit_events(self.owner_principal(), company["id"])["events"]
        actions = [event["action"] for event in events]
        self.assertIn("company.build_started", actions)
        self.assertIn("company.build_done_with_gaps", actions)

        started = next(event for event in events if event["action"] == "company.build_started")
        self.assertTrue(started["detail"]["workflow_id"].startswith("wfb_"))


class TestBuildRetry(BuildWorkflowTestBase):
    def test_retry_creates_a_new_attempt_and_keeps_history(self):
        company, first = self.submit_new()
        self.assertEqual(first["build"]["attempt"], 1)
        first_build_id = first["build"]["build_id"]

        second = self.service().retry_build(self.owner_principal(), company["id"])
        self.assertTrue(second["workflow_started"])
        self.assertEqual(second["build"]["attempt"], 2)
        self.assertNotEqual(second["build"]["build_id"], first_build_id)

        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT build_id FROM company_build_runs WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, company["id"]),
            ).fetchall()
        build_ids = {row["build_id"] for row in rows}
        self.assertEqual(len(build_ids), 2)
        self.assertIn(first_build_id, build_ids)

        events = self.service().audit_events(self.owner_principal(), company["id"])["events"]
        self.assertIn("company.build_retried", [event["action"] for event in events])

    def test_retry_is_refused_before_submission(self):
        company = self.make_company()
        with self.assertRaises(CompanySetupError) as ctx:
            self.service().retry_build(self.owner_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "BUILD_NOT_RETRYABLE")
        self.assertEqual(ctx.exception.status, 409)


class TestBuildIsolation(BuildWorkflowTestBase):
    def test_another_tenant_cannot_read_or_retry_the_build(self):
        company, _ = self.submit_new()

        # A principal from another tenant is rejected before anything is read.
        with self.assertRaises(PermissionDenied):
            self.service().retry_build(self.other_principal(), company["id"])

        # A correctly-scoped service in the other tenant sees nothing, even with
        # the real company id.
        foreign_service = CompanySetupService(self.other_tenant["tenant_id"])
        with self.assertRaises(CompanySetupError) as ctx:
            foreign_service.get_company(self.other_principal(), company["id"])
        self.assertEqual(ctx.exception.code, "COMPANY_NOT_FOUND")
        with self.assertRaises(CompanySetupError):
            foreign_service.retry_build(self.other_principal(), company["id"])
        self.assertIsNone(foreign_service.get_build(company["id"]))

    def test_existing_company_submit_starts_the_onboarding_workflow(self):
        company = self.make_company(EXISTING_PAYLOAD)
        result = self.service().submit_company(self.owner_principal(), company["id"])

        self.assertTrue(result["workflow_started"])
        self.assertEqual(result["company"]["status"], CompanyStatus.NEEDS_ATTENTION)
        self.assertEqual(result["build"]["run_type"], "ONBOARDING")
        self.assertEqual(result["build"]["phase"], "ACT")
        self.assertEqual(result["build"]["phase_state"], "DONE_WITH_GAPS")
        self.assertEqual(result["build"]["phases"][0]["id"], "CONNECT_VERIFY")

    def test_failure_is_visible_and_never_marks_the_company_operational(self):
        company = self.make_company()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE companies SET title = '' WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, company["id"]),
            )
            conn.commit()

        workflow = CompanyBuildWorkflow(self.tenant_id, company["id"], self.owner_principal())
        result = workflow.start(attempt=1)

        self.assertTrue(result["started"])
        build = self.service().get_build(company["id"])
        self.assertEqual(build["phase_state"], "FAILED")
        self.assertIn("Brief is incomplete", build["failure_reason"] or "")
        self.assertNotEqual(
            self.service().get_company(self.owner_principal(), company["id"])["status"],
            CompanyStatus.OPERATIONAL,
        )


if __name__ == "__main__":
    unittest.main()
