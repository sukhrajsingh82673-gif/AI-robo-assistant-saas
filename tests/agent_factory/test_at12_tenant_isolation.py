"""
ZONATA Agent Factory — Acceptance Test AT-12: Multi-Tenant Isolation
Specification:
  Given: Agents in Tenant A and Tenant B with canary records
  When: Tenant B probes Tenant A entities through Factory routes and queries
  Then: Every probe returns 404/deny; zero canary strings in response; cross-tenant query returns 0 rows.
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


class TestAT12TenantIsolation(unittest.TestCase):
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

        self.tenant_a = "tnt_alpha_canary"
        self.tenant_b = "tnt_beta_attacker"
        self.canary_secret = "CANARY_SECRET_ALPHA_TOKEN_9988"

        # Seed canary request and artifact in Tenant A
        self.req_a_id = f"req_a_{uuid.uuid4().hex[:8]}"
        now = time.time()
        self.conn.execute("""
            INSERT INTO af_request (
                id, tenant_id, company_id, requester_principal_id, requester_kind,
                mode, natural_language, status, budget_cap_usd, spent_usd,
                idempotency_key, correlation_id, created_at, updated_at
            ) VALUES (?, ?, 'cmp_a', 'emp.cmo', 'ai_employee', 'single', ?, 'REQUESTED', 10.0, 0.0, 'idem_a', 'corr_a', ?, ?)
        """, (self.req_a_id, self.tenant_a, f"Need agent with {self.canary_secret}", now, now))
        self.conn.commit()

    def test_at12_cross_tenant_read_via_api_returns_404_no_canary_leak(self):
        # Tenant B queries Tenant A request ID
        headers_b = {
            "X-Tenant-ID": self.tenant_b,
            "X-User-ID": "emp.attacker",
            "X-Company-ID": "cmp_b"
        }
        status, body, _ = self.router.dispatch("GET", f"/api/v8/agent-factory/requests/{self.req_a_id}", headers_b, b"")
        self.assertEqual(status, 404)
        self.assertEqual(body["code"], "AF-NOT-FOUND")

        # Assert no canary secret leaked in error response
        body_str = json.dumps(body)
        self.assertNotIn(self.canary_secret, body_str)

    def test_at12_cross_tenant_list_returns_zero_rows_of_foreign_tenant(self):
        headers_b = {
            "X-Tenant-ID": self.tenant_b,
            "X-User-ID": "emp.attacker",
            "X-Company-ID": "cmp_b"
        }
        status, body, _ = self.router.dispatch("GET", "/api/v8/agent-factory/requests", headers_b, b"")
        self.assertEqual(status, 200)
        # Must return empty list for Tenant B
        self.assertEqual(len(body["items"]), 0)

    def test_at12_direct_sql_scoping_isolation(self):
        cur = self.conn.execute(
            "SELECT id, natural_language FROM af_request WHERE tenant_id = ?",
            (self.tenant_b,)
        )
        rows = cur.fetchall()
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
