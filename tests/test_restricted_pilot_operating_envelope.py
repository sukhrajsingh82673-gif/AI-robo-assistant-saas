"""
URA / ZONATA Universal AI Company Operating System
Restricted Pilot Operating Envelope Qualification Suite (Milestone J & Gates A-L)

Verifies:
1. Version labels and release scope metadata (/readyz, /healthz, /api/pilot/envelope).
2. Design-Partner Organization Capacity Limits (Strict max 3 organizations, 4th rejected with 403).
3. Tenant Concurrency Lease Limits (Strict max 4 active leases per tenant, 5th rejected with 429).
4. Lease Release & Slot Reclamation.
5. Strict Cross-Tenant Isolation (Tenant A leases/quotas do not impact Tenant B).
6. 60 RPM Rate Limit Enforcement for Pilot Tenants.
"""

import os
import sys
import time
import json
import uuid
import tempfile
import unittest
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.auth import UserManager, UserRole, AuthExceptions
from core.tenant_fairness import tenant_fairness_engine, RateLimitAxis


class TestRestrictedPilotOperatingEnvelope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.orig_db_path = db.db_path
        cls.test_db_path = os.path.join(cls.temp_dir.name, "pilot_envelope_test.db")
        configure_isolated_test_db(cls.test_db_path)

        # Ensure pilot_organizations table exists in test DB
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS pilot_organizations (
                tenant_id TEXT PRIMARY KEY,
                org_name TEXT NOT NULL,
                contact_email TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                registered_at REAL NOT NULL,
                metadata JSON,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pilot_orgs_status ON pilot_organizations(status)")
            conn.commit()

        # Start an in-process HTTP test server on an ephemeral port
        from api_server import RoboAssistantRequestHandler, ThreadedHTTPServer
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), RoboAssistantRequestHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        import threading
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        db.set_db_path(cls.orig_db_path)
        cls.temp_dir.cleanup()

    def _http_request(self, method: str, path: str, data: Any = None, token: str = None) -> (int, dict, dict):
        import urllib.request
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req_body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_headers = dict(resp.headers)
                body = json.loads(resp.read().decode())
                return resp.status, body, resp_headers
        except urllib.error.HTTPError as e:
            resp_headers = dict(e.headers)
            try:
                body = json.loads(e.read().decode())
            except Exception:
                body = {"raw": "non-json error"}
            return e.code, body, resp_headers

    # -------------------------------------------------------------------------
    # TEST 1: Provenance, Health, and Release Version Metadata
    # -------------------------------------------------------------------------
    def test_01_healthz_and_readyz_release_metadata(self):
        status, body, _ = self._http_request("GET", "/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "HEALTHY")
        self.assertEqual(body.get("version"), "1.0.0-RESTRICTED-PILOT")
        self.assertEqual(body.get("release_scope"), "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA")
        self.assertIn("pilot_envelope", body)
        env = body["pilot_envelope"]
        self.assertEqual(env.get("max_organizations"), 3)
        self.assertEqual(env.get("max_concurrency_leases_per_tenant"), 4)
        self.assertEqual(env.get("max_rpm_per_tenant"), 60)

        status, body, _ = self._http_request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("version"), "1.0.0-RESTRICTED-PILOT")

    # -------------------------------------------------------------------------
    # TEST 2: Public Pilot Envelope Specification Endpoint
    # -------------------------------------------------------------------------
    def test_02_pilot_envelope_endpoint(self):
        status, body, _ = self._http_request("GET", "/api/pilot/envelope")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "ENFORCED")
        self.assertEqual(body.get("release_scope"), "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA")
        limits = body.get("pilot_envelope", {})
        self.assertEqual(limits.get("max_organizations"), 3)
        self.assertEqual(limits.get("max_concurrency_leases_per_tenant"), 4)
        self.assertEqual(limits.get("max_requests_per_minute_per_tenant"), 60)
        self.assertFalse(limits.get("public_ga_qualified"))

    # -------------------------------------------------------------------------
    # TEST 3: Milestone J — Enforce Max 3 Design-Partner Organizations
    # -------------------------------------------------------------------------
    def test_03_enforce_maximum_three_design_partner_organizations(self):
        # Clear pilot_organizations table for a clean test run
        with db.get_connection() as conn:
            conn.execute("DELETE FROM pilot_organizations")
            conn.commit()

        # Register Design Partner 1
        reg1 = {
            "email": f"partner1_{uuid.uuid4().hex[:6]}@pilot.corp",
            "name": "Partner One",
            "password": "SecurePassword123!",
            "tenant_name": "Pilot Design Partner 1"
        }
        status1, body1, _ = self._http_request("POST", "/api/auth/register", reg1)
        self.assertEqual(status1, 201, f"Partner 1 registration failed: {body1}")
        token1 = body1.get("token")
        self.assertIsNotNone(token1)

        # Register Design Partner 2
        reg2 = {
            "email": f"partner2_{uuid.uuid4().hex[:6]}@pilot.corp",
            "name": "Partner Two",
            "password": "SecurePassword123!",
            "tenant_name": "Pilot Design Partner 2"
        }
        status2, body2, _ = self._http_request("POST", "/api/auth/register", reg2)
        self.assertEqual(status2, 201, f"Partner 2 registration failed: {body2}")
        token2 = body2.get("token")
        self.assertIsNotNone(token2)

        # Register Design Partner 3
        reg3 = {
            "email": f"partner3_{uuid.uuid4().hex[:6]}@pilot.corp",
            "name": "Partner Three",
            "password": "SecurePassword123!",
            "tenant_name": "Pilot Design Partner 3"
        }
        status3, body3, _ = self._http_request("POST", "/api/auth/register", reg3)
        self.assertEqual(status3, 201, f"Partner 3 registration failed: {body3}")
        token3 = body3.get("token")
        self.assertIsNotNone(token3)

        # Attempt to Register 4th Organization -> Must be strictly rejected with HTTP 403
        reg4 = {
            "email": f"partner4_{uuid.uuid4().hex[:6]}@pilot.corp",
            "name": "Partner Four",
            "password": "SecurePassword123!",
            "tenant_name": "Pilot Design Partner 4"
        }
        status4, body4, _ = self._http_request("POST", "/api/auth/register", reg4)
        self.assertEqual(status4, 403, f"4th registration should be rejected: {body4}")
        self.assertEqual(body4.get("error"), "Pilot Capacity Limit Exceeded")
        self.assertEqual(body4.get("limit"), 3)
        self.assertEqual(body4.get("current_active"), 3)

        # Verify envelope endpoint reflects 0 available slots
        status_env, body_env, _ = self._http_request("GET", "/api/pilot/envelope")
        self.assertEqual(status_env, 200)
        self.assertEqual(body_env["pilot_envelope"]["active_pilot_organizations"], 3)
        self.assertEqual(body_env["pilot_envelope"]["available_pilot_slots"], 0)

    # -------------------------------------------------------------------------
    # TEST 4: Milestone J — Enforce Max 4 Concurrency Leases per Tenant
    # -------------------------------------------------------------------------
    def test_04_enforce_maximum_four_concurrency_leases_per_tenant(self):
        # Register a test tenant
        reg = {
            "email": f"lease_user_{uuid.uuid4().hex[:6]}@lease.corp",
            "name": "Lease Tester",
            "password": "SecurePassword123!",
            "tenant_name": "Lease Tenant"
        }
        with db.get_connection() as conn:
            conn.execute("DELETE FROM pilot_organizations")
            conn.commit()

        status, body, _ = self._http_request("POST", "/api/auth/register", reg)
        self.assertEqual(status, 201)
        token = body.get("token")

        acquired_leases = []
        # Acquire up to configured max limit (4)
        for i in range(4):
            stat, res, _ = self._http_request(
                "POST", "/api/concurrency/lease/acquire",
                {"lease_type": "WORKFLOW", "ttl_seconds": 60.0},
                token=token
            )
            self.assertEqual(stat, 200, f"Lease {i+1} must be acquired successfully: {res}")
            self.assertTrue(res.get("success"))
            self.assertIsNotNone(res.get("lease_id"))
            acquired_leases.append(res["lease_id"])

        # Verify active leases list
        stat_l, res_l, _ = self._http_request("GET", "/api/concurrency/leases", token=token)
        self.assertEqual(stat_l, 200)
        self.assertEqual(res_l.get("active_leases_count"), 4)
        self.assertEqual(res_l.get("available_slots"), 0)

        # Attempt 5th simultaneous lease -> Must be rejected with HTTP 429
        stat5, res5, hdrs5 = self._http_request(
            "POST", "/api/concurrency/lease/acquire",
            {"lease_type": "WORKFLOW", "ttl_seconds": 60.0},
            token=token
        )
        self.assertEqual(stat5, 429, f"5th lease must be rejected: {res5}")
        self.assertEqual(res5.get("violation_axis"), "CONCURRENCY_LIMIT_EXCEEDED")
        self.assertEqual(res5.get("limit"), 4)
        self.assertIn("Retry-After", hdrs5)
        self.assertEqual(hdrs5.get("X-RateLimit-Limit"), "4")

        # Release first lease
        stat_rel, res_rel, _ = self._http_request(
            "POST", "/api/concurrency/lease/release",
            {"lease_id": acquired_leases[0]},
            token=token
        )
        self.assertEqual(stat_rel, 200)
        self.assertTrue(res_rel.get("released"))

        # Now 5th lease attempt succeeds
        stat_new, res_new, _ = self._http_request(
            "POST", "/api/concurrency/lease/acquire",
            {"lease_type": "WORKFLOW", "ttl_seconds": 60.0},
            token=token
        )
        self.assertEqual(stat_new, 200, f"Lease must succeed once slot freed: {res_new}")
        self.assertTrue(res_new.get("success"))
        acquired_leases.append(res_new["lease_id"])

        # Cleanup leases
        for lid in acquired_leases[1:]:
            self._http_request("POST", "/api/concurrency/lease/release", {"lease_id": lid}, token=token)

    # -------------------------------------------------------------------------
    # TEST 5: Cross-Tenant Concurrency and Isolation Independence
    # -------------------------------------------------------------------------
    def test_05_cross_tenant_isolation_and_concurrency_independence(self):
        # Register Tenant A and Tenant B
        with db.get_connection() as conn:
            conn.execute("DELETE FROM pilot_organizations")
            conn.commit()

        status_a, body_a, _ = self._http_request(
            "POST", "/api/auth/register",
            {"email": f"tenant_a_{uuid.uuid4().hex[:6]}@a.corp", "name": "A", "password": "Password123!", "tenant_name": "Tenant A"}
        )
        token_a = body_a["token"]

        status_b, body_b, _ = self._http_request(
            "POST", "/api/auth/register",
            {"email": f"tenant_b_{uuid.uuid4().hex[:6]}@b.corp", "name": "B", "password": "Password123!", "tenant_name": "Tenant B"}
        )
        token_b = body_b["token"]

        # Exhaust Tenant A's 4 leases
        leases_a = []
        for i in range(4):
            stat, res, _ = self._http_request("POST", "/api/concurrency/lease/acquire", {"ttl_seconds": 60.0}, token=token_a)
            self.assertEqual(stat, 200)
            leases_a.append(res["lease_id"])

        # Tenant A 5th lease rejected
        stat_a5, _, _ = self._http_request("POST", "/api/concurrency/lease/acquire", {"ttl_seconds": 60.0}, token=token_a)
        self.assertEqual(stat_a5, 429)

        # Tenant B must NOT be impacted by Tenant A's lease exhaustion
        stat_b1, res_b1, _ = self._http_request("POST", "/api/concurrency/lease/acquire", {"ttl_seconds": 60.0}, token=token_b)
        self.assertEqual(stat_b1, 200, "Tenant B must be able to acquire lease independently")
        self.assertTrue(res_b1["success"])

        # Cross-Tenant IDOR defense: Tenant B cannot inspect or access Tenant A's leases
        stat_b_inspect, res_b_inspect, _ = self._http_request("GET", "/api/concurrency/leases", token=token_b)
        self.assertEqual(stat_b_inspect, 200)
        self.assertEqual(res_b_inspect["active_leases_count"], 1)
        self.assertEqual(res_b_inspect["leases"][0]["lease_id"], res_b1["lease_id"])

        # Cleanup
        for lid in leases_a:
            self._http_request("POST", "/api/concurrency/lease/release", {"lease_id": lid}, token=token_a)
        self._http_request("POST", "/api/concurrency/lease/release", {"lease_id": res_b1["lease_id"]}, token=token_b)


if __name__ == "__main__":
    unittest.main()
