"""
ZONATA Agent Factory — Phase 2 API Contract & Foundation Route Tests
Tests /health, /ready, /requests, /jobs, /kill, /quotas under /api/v8/agent-factory/
"""

import unittest
import sqlite3
import json
import uuid
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from agent_factory.api.routes import AgentFactoryRouter
from migrations.migration_manager import split_sql_statements


class TestAgentFactoryRoutes(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        sql_path = os.path.join(os.path.dirname(__file__), "../../migrations/sqlite/0013_agent_factory_core.sql")
        with open(sql_path, "r") as f:
            sql = f.read()
        stmts = split_sql_statements(sql, dialect="sqlite")
        for stmt in stmts:
            self.conn.execute(stmt)
        self.conn.commit()

        self.router = AgentFactoryRouter(db_conn_factory=lambda: self.conn)

        self.tenant_id = "tnt_api_test"
        self.company_id = "cmp_api_test"
        self.user_id = "emp.cmo"
        self.default_headers = {
            "X-Tenant-ID": self.tenant_id,
            "X-User-ID": self.user_id,
            "X-Company-ID": self.company_id
        }

    def test_01_health_and_ready_endpoints(self):
        status, body, headers = self.router.dispatch("GET", "/api/v8/agent-factory/health", {}, b"")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "HEALTHY")

        status, body, headers = self.router.dispatch("GET", "/api/v8/agent-factory/ready", {}, b"")
        self.assertEqual(status, 200)
        self.assertEqual(body["ready"], True)
        self.assertEqual(body["orchestrator"], "DbQueueOrchestrator")
        self.assertEqual(body["sandbox_tiers_available"], ["T0"])

    def test_02_post_request_with_idempotency_and_evidence(self):
        idem_key = f"idem_{uuid.uuid4().hex[:12]}"
        payload = {
            "mode": "single",
            "natural_language": "Build an autonomous customer support triage agent with verified SOPs",
            "budget_cap_usd": 15.0
        }
        headers = {**self.default_headers, "Idempotency-Key": idem_key}

        status, body, res_headers = self.router.dispatch(
            "POST", "/api/v8/agent-factory/requests", headers, json.dumps(payload).encode()
        )
        self.assertEqual(status, 202)
        self.assertIn("request_id", body)
        self.assertEqual(body["status"], "ANALYSING")
        self.assertIn("X-Evidence-Id", res_headers)
        self.assertIn("Location", res_headers)
        request_id = body["request_id"]

        # Replay identical payload -> 200 OK with Idempotent-Replay header
        status_rep, body_rep, res_headers_rep = self.router.dispatch(
            "POST", "/api/v8/agent-factory/requests", headers, json.dumps(payload).encode()
        )
        self.assertEqual(status_rep, 200)
        self.assertEqual(body_rep["request_id"], request_id)
        self.assertEqual(res_headers_rep.get("Idempotent-Replay"), "true")

        # Different payload with same key -> 409 Conflict
        diff_payload = {**payload, "natural_language": "Completely different instruction text"}
        status_mismatch, body_mismatch, _ = self.router.dispatch(
            "POST", "/api/v8/agent-factory/requests", headers, json.dumps(diff_payload).encode()
        )
        self.assertEqual(status_mismatch, 409)
        self.assertEqual(body_mismatch["code"], "AF-IDEMPOTENCY-MISMATCH")

    def test_03_get_requests_and_detail(self):
        # Create request first
        headers = {**self.default_headers, "Idempotency-Key": "idem_get_test"}
        payload = {"natural_language": "Test specification for list and detail"}
        status, body, _ = self.router.dispatch("POST", "/api/v8/agent-factory/requests", headers, json.dumps(payload).encode())
        req_id = body["request_id"]

        # List requests
        status_list, body_list, _ = self.router.dispatch("GET", "/api/v8/agent-factory/requests", self.default_headers, b"")
        self.assertEqual(status_list, 200)
        self.assertGreaterEqual(len(body_list["items"]), 1)

        # Inspect detail
        status_det, body_det, _ = self.router.dispatch("GET", f"/api/v8/agent-factory/requests/{req_id}", self.default_headers, b"")
        self.assertEqual(status_det, 200)
        self.assertEqual(body_det["request_id"], req_id)
        self.assertGreaterEqual(len(body_det["lifecycle_events"]), 1)

    def test_04_kill_switch_endpoint(self):
        payload = {
            "scope": "AGENT",
            "target_id": "agt_kill_test_99",
            "reason": "Security quarantine test"
        }
        status, body, headers = self.router.dispatch(
            "POST", "/api/v8/agent-factory/kill", self.default_headers, json.dumps(payload).encode()
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["killed"], True)
        self.assertIn("evidence_id", body)
        self.assertIn("X-Evidence-Id", headers)

    def test_05_quotas_endpoint(self):
        status, body, _ = self.router.dispatch("GET", "/api/v8/agent-factory/quotas", self.default_headers, b"")
        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], self.tenant_id)
        self.assertIn("quotas", body)
        self.assertIn("builds", body["quotas"])

    def test_06_unauthorized_missing_headers_returns_rfc9457(self):
        status, body, _ = self.router.dispatch("GET", "/api/v8/agent-factory/requests", {}, b"")
        self.assertEqual(status, 401)
        self.assertEqual(body["code"], "AF-UNAUTHORIZED")
        self.assertIn("correlation_id", body)


if __name__ == "__main__":
    unittest.main()
