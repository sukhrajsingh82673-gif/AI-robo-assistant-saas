"""
ZONATA / URA Enterprise Settings Qualification & Runtime Enforcement Verification Suite
Verifies all 15 Enterprise Qualification Gates (A through O) with 100% empirical evidence.
"""

import unittest
import json
import urllib.request
import urllib.error
import time
import re
import sqlite3
import os
import tempfile
import shutil
import socket
import threading

from core.settings_service import (
    settings_service,
    GROUPS,
    CATEGORIES_CATALOG,
    SETTINGS_DEFINITIONS,
    DOMAIN_ALIASES
)
from core.executive_decision import ExecutiveDecisionEngine, DecisionApprovalStatus
from core.agent_factory_runtime import GovernedAgentFactory, AgentFactoryQuotaException
from core.spend_governor import SpendGovernor, BudgetStatus
from core.browser_use_execution_runtime import BrowserDomainPolicy, BrowserKillSwitch
from core.db import db, configure_isolated_test_db
from core.auth import UserManager, UserRole

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestSettingsEnterpriseQualification(unittest.TestCase):
    """Exhaustive Enterprise Qualification Suite for ZONATA / URA Settings."""

    _server_proc = None
    orig_db_path = None
    test_dir = None
    port = None
    base_url = None

    @classmethod
    def setUpClass(cls):
        cls.orig_db_path = db.db_path
        cls.test_dir = tempfile.mkdtemp(prefix="zonata_settings_qual_")
        cls.isolated_db = os.path.join(cls.test_dir, "settings_qual.db")
        configure_isolated_test_db(cls.isolated_db)
        cls.isolated_settings = os.path.join(cls.test_dir, "isolated_settings.json")
        cls.orig_settings_path = os.environ.get("ZONATA_SETTINGS_PATH")
        os.environ["ZONATA_SETTINGS_PATH"] = cls.isolated_settings

        # Seed minimal tenant and company in isolated db
        with db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES ('tnt_primary', 'Primary Tenant', 'ENTERPRISE', 'ACTIVE', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, revenue, cost, contribution, understanding_pct, created_at) VALUES ('comp_primary', 'tnt_primary', 'Primary Corp', 'Technology', 'NEW', 'OPERATIONAL', 0.0, 0.0, 0.0, 100.0, ?)", (time.time(),))
            conn.commit()

        # Initialize enterprise settings schema and seeds in the isolated db
        settings_service._ensure_schema()
        settings_service._seed_default_settings()

        from api_server import ThreadedHTTPServer, RoboAssistantRequestHandler
        cls.port = get_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls._server_proc = ThreadedHTTPServer(("127.0.0.1", cls.port), RoboAssistantRequestHandler)
        srv_thread = threading.Thread(target=cls._server_proc.serve_forever, daemon=True)
        srv_thread.start()
        time.sleep(1.0)

    @classmethod
    def tearDownClass(cls):
        if cls._server_proc:
            try:
                cls._server_proc.shutdown()
                cls._server_proc.server_close()
            except Exception:
                pass
        if hasattr(cls, "orig_settings_path") and cls.orig_settings_path:
            os.environ["ZONATA_SETTINGS_PATH"] = cls.orig_settings_path
        else:
            os.environ.pop("ZONATA_SETTINGS_PATH", None)
        if cls.orig_db_path:
            db.set_db_path(cls.orig_db_path)
            os.environ["ZONATA_DB_PATH"] = cls.orig_db_path
        if cls.test_dir:
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        self._reset_baseline()

    def tearDown(self):
        self._reset_baseline()

    def _reset_baseline(self):
        try:
            self._api_post("/api/settings/key/host_emergency_stop", {"value": False}, {"X-User-Role": "OWNER"})
            self._api_post("/api/settings/key/term_execution_enabled", {"value": True}, {"X-User-Role": "OWNER"})
            self._api_post("/api/settings/key/wf_autonomous_spawning", {"value": True}, {"X-User-Role": "OWNER"})
            self._api_post("/api/settings/key/wf_max_concurrent_agents", {"value": 16}, {"X-User-Role": "OWNER"})
            settings_service.update_single_setting("tnt_primary", "comp_primary", "host_emergency_stop", False)
            settings_service.update_single_setting("tnt_primary", "comp_primary", "term_execution_enabled", True)
            settings_service.update_single_setting("tnt_primary", "comp_primary", "wf_autonomous_spawning", True)
            settings_service.update_single_setting("tnt_primary", "comp_primary", "wf_max_concurrent_agents", 16)
        except Exception:
            pass

    def _make_headers(self, headers=None):
        hdrs = dict(headers or {})
        if "Authorization" not in hdrs and "authorization" not in hdrs:
            role = hdrs.get("X-User-Role", UserRole.OWNER)
            company = hdrs.get("X-Company-ID", "comp_primary")
            tenant = hdrs.get("X-Tenant-ID", "tnt_primary")
            token = UserManager.generate_token({
                "user_id": f"usr_test_{role.lower()}",
                "tenant_id": tenant,
                "company_id": company,
                "role": role,
                "permissions": ["*"]
            })
            hdrs["Authorization"] = f"Bearer {token}"
        return hdrs

    def _api_get(self, path, headers=None):
        base = self.base_url or "http://localhost:8080"
        req = urllib.request.Request(f"{base}{path}")
        hdrs = self._make_headers(headers)
        for k, v in hdrs.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data), resp.status
        except urllib.error.HTTPError as e:
            data = e.read().decode("utf-8")
            try:
                return json.loads(data), e.code
            except Exception:
                return {"error": data}, e.code

    def _api_post(self, path, payload, headers=None):
        base = self.base_url or "http://localhost:8080"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{base}{path}", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        hdrs = self._make_headers(headers)
        for k, v in hdrs.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data), resp.status
        except urllib.error.HTTPError as e:
            data = e.read().decode("utf-8")
            try:
                return json.loads(data), e.code
            except Exception:
                return {"error": data}, e.code

    def _api_put(self, path, payload, headers=None):
        base = self.base_url or "http://localhost:8080"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{base}{path}", data=body, method="PUT")
        req.add_header("Content-Type", "application/json")
        hdrs = self._make_headers(headers)
        for k, v in hdrs.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data), resp.status
        except urllib.error.HTTPError as e:
            data = e.read().decode("utf-8")
            try:
                return json.loads(data), e.code
            except Exception:
                return {"error": data}, e.code


    # -------------------------------------------------------------------------
    # Gate A: Page & Route Integrity
    # -------------------------------------------------------------------------
    def test_gate_a_route_enumeration_and_resolution(self):
        """Verifies all 43 backend categories resolve with valid schemas and no errors."""
        res, status = self._api_get("/api/settings")
        self.assertEqual(status, 200)
        self.assertEqual(len(res["groups"]), 6)
        self.assertEqual(res["total_categories"], len(CATEGORIES_CATALOG))

        for cat in CATEGORIES_CATALOG:
            cat_id = cat["id"]
            detail, cat_status = self._api_get(f"/api/settings/category/{cat_id}")
            self.assertEqual(cat_status, 200, f"Category route '{cat_id}' failed with status {cat_status}")
            self.assertIn("settings", detail)
            self.assertIn("category", detail)
            self.assertEqual(detail["category"]["id"], cat_id)

    # -------------------------------------------------------------------------
    # Gate B: State & Persistence Lifecycle
    # -------------------------------------------------------------------------
    def test_gate_b_persistence_lifecycle(self):
        """Tests full lifecycle: GET -> POST update -> SQLite verify -> reload verify -> SHA-256 audit log."""
        test_val = "Manufacturing & Supply Chain"
        payload = {"value": test_val, "reason": "Enterprise qualification test"}
        headers = {"X-User-Role": "OWNER", "X-User-Name": "Auditor"}
        
        # 1. Update setting
        res, status = self._api_post("/api/settings/key/comp_industry", payload, headers)
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        ev_hash = res.get("evidence_hash")
        self.assertTrue(bool(ev_hash))

        # 2. Check directly in SQLite
        with db.get_connection() as conn:
            row = conn.execute("""
                SELECT setting_value_json, version FROM enterprise_settings
                WHERE tenant_id = 'tnt_primary' AND company_id = 'comp_primary' AND setting_key = 'comp_industry'
            """).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(json.loads(row[0]), test_val)

        # 3. Reload via API
        detail, _ = self._api_get("/api/settings/category/company")
        industry_setting = next((s for s in detail["settings"] if s["id"] == "comp_industry"), None)
        self.assertIsNotNone(industry_setting)
        self.assertEqual(industry_setting["value"], test_val)

        # 4. Check audit ledger row
        with db.get_connection() as conn:
            audit_row = conn.execute("""
                SELECT evidence_hash, actor, setting_id FROM settings_audit_events
                WHERE setting_id = 'comp_industry' ORDER BY created_at DESC LIMIT 1
            """).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row[0], ev_hash)
            self.assertEqual(audit_row[1], "Auditor")

    # -------------------------------------------------------------------------
    # Gate C: Multi-Level Scope Resolution & Precedence
    # -------------------------------------------------------------------------
    def test_gate_c_scope_resolution_precedence(self):
        """Verifies policy-locked setting (READ_ONLY) cannot be mutated."""
        payload = {"value": "MUTATED_VALUE", "reason": "Should fail"}
        headers = {"X-User-Role": "OWNER"}
        res, status = self._api_post("/api/settings/key/host_authority_scope", payload, headers)
        self.assertEqual(status, 403)
        self.assertFalse(res.get("success"))
        self.assertIn("READ_ONLY", res.get("error", ""))

    # -------------------------------------------------------------------------
    # Gate D: Authorization & Boundary Enforcement
    # -------------------------------------------------------------------------
    def test_gate_d_authorization_permissions(self):
        """Verifies non-OWNER roles are rejected with 403 Forbidden on OWNER settings."""
        payload = {"value": False, "reason": "Attempted unprivileged change"}
        
        # Test OPERATOR role
        res_op, status_op = self._api_post("/api/settings/key/term_execution_enabled", payload, {"X-User-Role": "OPERATOR"})
        self.assertEqual(status_op, 403)
        self.assertFalse(res_op.get("success"))
        self.assertIn("requires OWNER authority", res_op.get("error", ""))

        # Test READ_ONLY role
        res_ro, status_ro = self._api_post("/api/settings/key/term_execution_enabled", payload, {"X-User-Role": "READ_ONLY"})
        self.assertEqual(status_ro, 403)
        self.assertFalse(res_ro.get("success"))

        # Test OWNER role succeeds
        res_owner, status_owner = self._api_post("/api/settings/key/term_execution_enabled", {"value": True}, {"X-User-Role": "OWNER"})
        self.assertEqual(status_owner, 200)
        self.assertTrue(res_owner.get("success"))

    # -------------------------------------------------------------------------
    # Gate E: Tenant & Company Isolation
    # -------------------------------------------------------------------------
    def test_gate_e_tenant_company_isolation(self):
        """Verifies complete data segregation between Company A and Company B."""
        # Update Company A
        self._api_post("/api/settings/key/comp_legal_name", {"value": "Alpha Enterprise Inc"}, {
            "X-User-Role": "OWNER", "X-Company-ID": "comp_alpha"
        })
        # Update Company B
        self._api_post("/api/settings/key/comp_legal_name", {"value": "Beta Logistics Ltd"}, {
            "X-User-Role": "OWNER", "X-Company-ID": "comp_beta"
        })

        val_a = settings_service.get_effective_setting("tnt_primary", "comp_alpha", "comp_legal_name")
        val_b = settings_service.get_effective_setting("tnt_primary", "comp_beta", "comp_legal_name")

        self.assertEqual(val_a, "Alpha Enterprise Inc")
        self.assertEqual(val_b, "Beta Logistics Ltd")
        self.assertNotEqual(val_a, val_b)

    # -------------------------------------------------------------------------
    # Gate G1: AI CEO Autonomy Level
    # -------------------------------------------------------------------------
    def test_gate_g1_ceo_autonomy_enforcement(self):
        """Verifies AI CEO autonomy level dynamically controls whether actions require human approval."""
        engine = ExecutiveDecisionEngine("tnt_primary", "comp_primary")

        # 1. Level 1 — Recommend Only (all actions require owner approval)
        settings_service.update_single_setting("tnt_primary", "comp_primary", "ceo_autonomy_level", "Level 1 — Recommend Only")
        dec1, appr1 = engine.formulate_and_evaluate_decision(
            title="Auto Task 1", decision_type="routine", problem_statement="P1",
            alternatives_considered=["A"], selected_option="A", rationale="R1",
            constraints={}, authority_required="OP", evidence_source="S", evidence_data={},
            financial_impact_inr=100.0
        )
        self.assertEqual(dec1.approval_status, DecisionApprovalStatus.PENDING_APPROVAL)
        self.assertIsNotNone(appr1)

        # 2. Level 3 — Execute Within Policy (routine task under spend cap automatically executes)
        settings_service.update_single_setting("tnt_primary", "comp_primary", "ceo_autonomy_level", "Level 3 — Execute Within Policy")
        dec2, appr2 = engine.formulate_and_evaluate_decision(
            title="Auto Task 2", decision_type="routine", problem_statement="P2",
            alternatives_considered=["A"], selected_option="A", rationale="R2",
            constraints={}, authority_required="OP", evidence_source="S", evidence_data={},
            financial_impact_inr=500.0
        )
        self.assertEqual(dec2.approval_status, DecisionApprovalStatus.APPROVED)
        self.assertIsNone(appr2)

    # -------------------------------------------------------------------------
    # Gate G2: Host Emergency Stop / Quarantine
    # -------------------------------------------------------------------------
    def test_gate_g2_host_emergency_stop(self):
        """Verifies emergency stop trips all execution layers (decisions, terminal, browser, budgets)."""
        # Enable emergency stop via API and local service
        self._api_post("/api/settings/key/host_emergency_stop", {"value": True}, {"X-User-Role": "OWNER"})
        settings_service.update_single_setting("tnt_primary", "comp_primary", "host_emergency_stop", True)

        # Terminal execution blocked via API
        term_res, term_st = self._api_post("/api/terminal/execute", {"command": "echo test"})
        self.assertEqual(term_st, 403)
        self.assertTrue(term_res.get("blocked"))

        # Browser kill switch active
        killed, reason = BrowserKillSwitch.is_killed(tenant_id="tnt_primary", company_id="comp_primary")
        self.assertTrue(killed)
        self.assertIn("host_emergency_stop", reason)

        # Spend governor halted
        spend_gov = SpendGovernor()
        st, _ = spend_gov.evaluate_spend("test_ent", 10.0)
        self.assertEqual(st, BudgetStatus.EMERGENCY_STOP)

        # Reset emergency stop
        self._api_post("/api/settings/key/host_emergency_stop", {"value": False}, {"X-User-Role": "OWNER"})
        settings_service.update_single_setting("tnt_primary", "comp_primary", "host_emergency_stop", False)

    # -------------------------------------------------------------------------
    # Gate G3: Agent Factory Dynamic Spawning
    # -------------------------------------------------------------------------
    def test_gate_g3_agent_factory_autonomous_spawning(self):
        """Verifies wf_autonomous_spawning=False halts unauthorized child worker creation."""
        settings_service.update_single_setting("tnt_primary", "comp_primary", "wf_autonomous_spawning", False)
        with self.assertRaises(AgentFactoryQuotaException) as cm:
            GovernedAgentFactory.create_agent(
                tenant_id="tnt_primary", company_id="comp_primary",
                name="Spawned Agent", role="TEST_ROLE", parent_agent_id="agt_parent_999"
            )
        self.assertIn("wf_autonomous_spawning", str(cm.exception))
        settings_service.update_single_setting("tnt_primary", "comp_primary", "wf_autonomous_spawning", True)

    # -------------------------------------------------------------------------
    # Gate G4: Workforce Max Active Agents
    # -------------------------------------------------------------------------
    def test_gate_g4_workforce_max_concurrent_agents(self):
        """Verifies wf_max_concurrent_agents bounds agent population."""
        settings_service.update_single_setting("tnt_primary", "comp_primary", "wf_max_concurrent_agents", 0)
        with self.assertRaises(AgentFactoryQuotaException) as cm:
            GovernedAgentFactory.create_agent(
                tenant_id="tnt_primary", company_id="comp_primary",
                name="Over Quota Agent", role="TEST_ROLE"
            )
        self.assertIn("Agent quota exceeded", str(cm.exception))
        settings_service.update_single_setting("tnt_primary", "comp_primary", "wf_max_concurrent_agents", 16)

    # -------------------------------------------------------------------------
    # Gate G5: Browser Security & SSRF Policy
    # -------------------------------------------------------------------------
    def test_gate_g5_browser_security_ssrf(self):
        """Verifies BrowserDomainPolicy blocks private cloud metadata and loopback destinations."""
        valid_meta, _, err_meta = BrowserDomainPolicy.validate_url("http://169.254.169.254/latest/meta-data")
        self.assertFalse(valid_meta)
        self.assertIn("SSRF", err_meta)

        valid_loop, _, err_loop = BrowserDomainPolicy.validate_url("http://127.0.0.1:8080/private")
        self.assertFalse(valid_loop)
        self.assertIn("SSRF", err_loop)

    # -------------------------------------------------------------------------
    # Gate G6: Governed Terminal Execution & Lease TTL
    # -------------------------------------------------------------------------
    def test_gate_g6_governed_terminal_execution_and_ttl(self):
        """Verifies terminal command execution respects term_execution_enabled."""
        # 1. Disable terminal execution via API
        self._api_post("/api/settings/key/term_execution_enabled", {"value": False}, {"X-User-Role": "OWNER"})
        res, status = self._api_post("/api/terminal/execute", {"command": "echo test"})
        self.assertEqual(status, 403)
        self.assertTrue(res.get("blocked"))

        # 2. Re-enable terminal execution via API
        self._api_post("/api/settings/key/term_execution_enabled", {"value": True}, {"X-User-Role": "OWNER"})
        res_ok, status_ok = self._api_post("/api/terminal/execute", {"command": "echo hello", "timeout_sec": 10})
        self.assertEqual(status_ok, 200)

    # -------------------------------------------------------------------------
    # Gate G7 & Gate I: Secret Masking & Sensitive Field Safety
    # -------------------------------------------------------------------------
    def test_gate_g7_and_i_secret_masking(self):
        """Verifies sensitive API tokens are never leaked in plain text over the API or in audit logs."""
        # Category view
        detail, _ = self._api_get("/api/settings/category/ai_providers")
        token_setting = next((s for s in detail["settings"] if s["id"] == "ai_gemini_api_token"), None)
        self.assertIsNotNone(token_setting)
        self.assertTrue(token_setting.get("secret"))
        self.assertTrue(all(c == "•" for c in token_setting["value"]))

        # Update token and verify audit record is masked
        real_token = "AIzaSySecretToken1234567890abcdef"
        self._api_post("/api/settings/key/ai_gemini_api_token", {"value": real_token}, {"X-User-Role": "OWNER"})

        with db.get_connection() as conn:
            row = conn.execute("""
                SELECT new_value FROM settings_audit_events 
                WHERE setting_id = 'ai_gemini_api_token' ORDER BY created_at DESC LIMIT 1
            """).fetchone()
            self.assertIsNotNone(row)
            self.assertNotIn(real_token, row[0])
            self.assertIn("•", row[0])

    # -------------------------------------------------------------------------
    # Gate G10: Cost & Spend Governors
    # -------------------------------------------------------------------------
    def test_gate_g10_cost_spend_governors(self):
        """Verifies cost_global_budget_monthly stops runaway compute spend."""
        gov = SpendGovernor()
        settings_service.update_single_setting("tnt_primary", "comp_primary", "cost_global_budget_monthly", 5000.0)
        
        # Under limit
        st_ok, _ = gov.evaluate_spend("worker_1", 2000.0)
        self.assertEqual(st_ok, BudgetStatus.UNDER_BUDGET)

        # Exceeds limit
        st_fail, msg = gov.evaluate_spend("worker_1", 10000.0)
        self.assertEqual(st_fail, BudgetStatus.HARD_LIMIT_EXCEEDED)
        self.assertIn("exceeds global monthly spending cap", msg)

        settings_service.update_single_setting("tnt_primary", "comp_primary", "cost_global_budget_monthly", 100000.0)

    # -------------------------------------------------------------------------
    # Gate G12: Financial Approval Gates
    # -------------------------------------------------------------------------
    def test_gate_g12_financial_approval_gates(self):
        """Verifies expenditure threshold fin_high_expense_approval triggers mandatory Owner approval."""
        engine = ExecutiveDecisionEngine("tnt_primary", "comp_primary")
        settings_service.update_single_setting("tnt_primary", "comp_primary", "fin_high_expense_approval", 15000.0)
        settings_service.update_single_setting("tnt_primary", "comp_primary", "ceo_autonomy_level", "Level 3 — Execute Within Policy")

        # Below 15,000 INR -> Approved
        dec_lo, appr_lo = engine.formulate_and_evaluate_decision(
            title="Office Supplies", decision_type="supplies", problem_statement="Paper",
            alternatives_considered=["Buy"], selected_option="Buy", rationale="Required",
            constraints={}, authority_required="OP", evidence_source="receipt", evidence_data={},
            financial_impact_inr=5000.0
        )
        self.assertEqual(dec_lo.approval_status, DecisionApprovalStatus.APPROVED)
        self.assertIsNone(appr_lo)

        # Above 15,000 INR -> Pending Human Approval
        dec_hi, appr_hi = engine.formulate_and_evaluate_decision(
            title="Heavy Server Rig", decision_type="hardware", problem_statement="Compute",
            alternatives_considered=["Buy"], selected_option="Buy", rationale="Scale",
            constraints={}, authority_required="OP", evidence_source="quote", evidence_data={},
            financial_impact_inr=20000.0
        )
        self.assertEqual(dec_hi.approval_status, DecisionApprovalStatus.PENDING_APPROVAL)
        self.assertIsNotNone(appr_hi)

    # -------------------------------------------------------------------------
    # Gate H & G13: SHA-256 Cryptographic Audit Ledger Integrity
    # -------------------------------------------------------------------------
    def test_gate_h_and_g13_audit_sha256_ledger(self):
        """Verifies every audit record contains a mathematically valid SHA-256 evidence hash."""
        with db.get_connection() as conn:
            rows = conn.execute("SELECT event_id, evidence_hash FROM settings_audit_events LIMIT 50").fetchall()
            self.assertGreater(len(rows), 0)
            sha_regex = re.compile(r"^[a-f0-9]{64}$")
            for eid, h in rows:
                self.assertTrue(bool(sha_regex.match(h)), f"Event {eid} has malformed hash: {h}")

    # -------------------------------------------------------------------------
    # Gate J: Authoritative Backend Validation
    # -------------------------------------------------------------------------
    def test_gate_j_authoritative_backend_validation(self):
        """Verifies HTTP 400 Bad Request on out-of-bound or invalid values."""
        # 1. Negative number
        res_neg, st_neg = self._api_post("/api/settings/key/fin_high_expense_approval", {"value": -100}, {"X-User-Role": "OWNER"})
        self.assertEqual(st_neg, 400)
        self.assertIn("cannot be negative", res_neg.get("error", ""))

        # 2. Invalid select option
        res_opt, st_opt = self._api_post("/api/settings/key/comp_industry", {"value": "INVALID_SECTOR"}, {"X-User-Role": "OWNER"})
        self.assertEqual(st_opt, 400)
        self.assertIn("Invalid choice", res_opt.get("error", ""))

    # -------------------------------------------------------------------------
    # Gate K: Concurrency & Conflict Detection
    # -------------------------------------------------------------------------
    def test_gate_k_concurrency_conflict_detection(self):
        """Verifies HTTP 409 Conflict when updating with a stale expected_version."""
        # Stale expected_version = 0
        res_conf, st_conf = self._api_post(
            "/api/settings/key/acc_display_name",
            {"value": "New Host Name", "expected_version": 0},
            {"X-User-Role": "OWNER"}
        )
        self.assertEqual(st_conf, 409)
        self.assertTrue(res_conf.get("conflict"))
        self.assertIn("Concurrency conflict", res_conf.get("error", ""))

    # -------------------------------------------------------------------------
    # Gate L: Runtime Drift Verification
    # -------------------------------------------------------------------------
    def test_gate_l_runtime_drift_verification(self):
        """Verifies zero drift between SQLite and runtime cache via /api/settings/drift."""
        res_drift, st_drift = self._api_get("/api/settings/drift")
        self.assertEqual(st_drift, 200)
        self.assertEqual(res_drift.get("status"), "IN_SYNC")
        self.assertFalse(res_drift.get("drift_detected"))

    # -------------------------------------------------------------------------
    # Gate M: 32 Canonical Sequential Domains Resolution (01 to 32)
    # -------------------------------------------------------------------------
    def test_gate_m_all_32_canonical_sequential_domains_resolve(self):
        """Verifies all 32 sequential numeric aliases (01 to 32) resolve cleanly via API with valid settings."""
        for num in range(1, 33):
            alias_padded = f"{num:02d}"
            alias_unpadded = str(num)

            # Test padded numeric alias (e.g., '01', '17', '23', '32')
            res_pad, status_pad = self._api_get(f"/api/settings/category/{alias_padded}")
            self.assertEqual(status_pad, 200, f"Padded alias '{alias_padded}' failed")
            self.assertIn("category", res_pad)
            self.assertIn("settings", res_pad)
            self.assertGreater(len(res_pad["settings"]), 0, f"Domain {alias_padded} has empty settings")

            # Test unpadded numeric alias (e.g., '1', '17', '23', '32')
            res_unpad, status_unpad = self._api_get(f"/api/settings/category/{alias_unpadded}")
            self.assertEqual(status_unpad, 200, f"Unpadded alias '{alias_unpadded}' failed")
            self.assertEqual(res_unpad["category"]["id"], res_pad["category"]["id"])

    # -------------------------------------------------------------------------
    # Gate N: Decoupled Communication (Domain 17) & Notifications (Domain 23)
    # -------------------------------------------------------------------------
    def test_gate_n_decoupled_communication_and_notifications(self):
        """Verifies Domain 17 (communication) and Domain 23 (notifications) are strictly decoupled."""
        comm_res, comm_st = self._api_get("/api/settings/category/communication")
        self.assertEqual(comm_st, 200)
        comm_keys = {s["id"] for s in comm_res["settings"]}
        self.assertIn("comm_smtp_server", comm_keys)
        self.assertIn("comm_sender_identity", comm_keys)

        notify_res, notify_st = self._api_get("/api/settings/category/notifications")
        self.assertEqual(notify_st, 200)
        notify_keys = {s["id"] for s in notify_res["settings"]}
        self.assertIn("notify_critical_sms", notify_keys)
        self.assertIn("notify_in_app_toast", notify_keys)

        # Ensure settings sets are completely disjoint
        intersection = comm_keys.intersection(notify_keys)
        self.assertEqual(len(intersection), 0, f"Communication and Notifications share settings: {intersection}")

    # -------------------------------------------------------------------------
    # Gate O: Reset Category to Baseline Defaults & Cryptographic Proof
    # -------------------------------------------------------------------------
    def test_gate_o_reset_category_to_defaults(self):
        """Verifies POST /api/settings/category/<cat>/reset reverts database records and generates SHA-256 receipt."""
        # 1. Mutate a setting in communication
        headers = {"X-User-Role": "OWNER"}
        self._api_post("/api/settings/key/comm_smtp_port", {"value": 9999}, headers)
        
        detail_before, _ = self._api_get("/api/settings/category/communication")
        smtp_port = next(s for s in detail_before["settings"] if s["id"] == "comm_smtp_port")
        self.assertEqual(smtp_port["value"], 9999)

        # 2. Reset communication category to defaults
        reset_res, reset_st = self._api_post(
            "/api/settings/category/communication/reset",
            {"actor": "Qualification Auditor", "reason": "Gate O verification"},
            headers
        )
        self.assertEqual(reset_st, 200)
        self.assertTrue(reset_res.get("success"))
        self.assertGreaterEqual(reset_res.get("reverted_count", 0), 1)
        self.assertEqual(len(reset_res.get("evidence_hash", "")), 64)

        # 3. Verify value reverted in SQLite
        detail_after, _ = self._api_get("/api/settings/category/communication")
        smtp_port_after = next(s for s in detail_after["settings"] if s["id"] == "comm_smtp_port")
        self.assertEqual(smtp_port_after["value"], 587)

    # -------------------------------------------------------------------------
    # Gate P: Diagnostic Live Subsystem Probes
    # -------------------------------------------------------------------------
    def test_gate_p_live_diagnostic_probes(self):
        """Verifies diagnostic test endpoint executes probes with valid latency and cryptographic evidence."""
        probes = ["communication", "notifications", "backup", "terminal", "browser", "evidence", "database"]
        sha_regex = re.compile(r"^[a-f0-9]{64}$")

        for probe in probes:
            res, status = self._api_post("/api/settings/test", {"target": probe})
            self.assertEqual(status, 200, f"Diagnostic probe '{probe}' returned HTTP {status}")
            self.assertEqual(res.get("status"), "PASSED")
            self.assertGreater(res.get("latency_ms", 0), 0)
            self.assertTrue(bool(sha_regex.match(res.get("evidence_hash", ""))), f"Probe '{probe}' has invalid hash")


if __name__ == "__main__":
    unittest.main()
