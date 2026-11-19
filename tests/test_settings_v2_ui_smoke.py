"""Live smoke test for the Settings V2 console.

This is the bridge between the pure UI contract tests
(``tests/settings_v2_ui_test.js``) and a running deployment.  It starts an
in-process API server on an isolated database and exercises the exact HTTP
data contract the browser console consumes:

  * the console assets are shipped and wired into ``index.html``
  * the registry exposes caller capabilities
  * resolved values carry provenance, version, and override state
  * a write and a reset round-trip with optimistic concurrency

It deliberately does not need a browser: the rendering rules are covered by
the JS contract tests, while this test proves the console is talking to a
real, permission-checked backend rather than fixtures.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from core.auth import UserManager
from core.db import configure_isolated_test_db
from core.settings.service import settings_v2_service

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(REPO_ROOT, "web")
MASTER_KEY = "ab" * 32


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestSettingsV2ConsoleSmoke(unittest.TestCase):
    """End-to-end smoke of the console's HTTP contract."""

    _server = None
    _tempdir = None
    _old_master_key = None
    _old_settings_path = None

    @classmethod
    def setUpClass(cls):
        cls._tempdir = tempfile.mkdtemp(prefix="zonata_settings_v2_ui_")
        isolated_db = os.path.join(cls._tempdir, "settings_ui.db")
        configure_isolated_test_db(isolated_db)
        cls._old_settings_path = os.environ.get("ZONATA_SETTINGS_PATH")
        os.environ["ZONATA_SETTINGS_PATH"] = os.path.join(
            cls._tempdir, "isolated_settings.json"
        )
        cls._old_master_key = os.environ.get("ZONATA_SETTINGS_MASTER_KEY")
        os.environ["ZONATA_SETTINGS_MASTER_KEY"] = MASTER_KEY

        from core.db import db

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) "
                "VALUES ('tnt_ui', 'Console Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (time.time(),),
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, "
                "company_type, status, revenue, cost, contribution, understanding_pct, created_at) "
                "VALUES ('comp_ui', 'tnt_ui', 'Console Corp', 'Technology', 'NEW', "
                "'OPERATIONAL', 0.0, 0.0, 0.0, 100.0, ?)",
                (time.time(),),
            )
            conn.commit()

        settings_v2_service.ensure_schema()

        from api_server import RoboAssistantRequestHandler, ThreadedHTTPServer

        cls.port = _get_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls._server = ThreadedHTTPServer(
            ("127.0.0.1", cls.port), RoboAssistantRequestHandler
        )
        threading.Thread(target=cls._server.serve_forever, daemon=True).start()
        time.sleep(1.0)

    @classmethod
    def tearDownClass(cls):
        if cls._server is not None:
            try:
                cls._server.shutdown()
                cls._server.server_close()
            except Exception:
                pass
        if cls._old_master_key is None:
            os.environ.pop("ZONATA_SETTINGS_MASTER_KEY", None)
        else:
            os.environ["ZONATA_SETTINGS_MASTER_KEY"] = cls._old_master_key
        if cls._old_settings_path is None:
            os.environ.pop("ZONATA_SETTINGS_PATH", None)
        else:
            os.environ["ZONATA_SETTINGS_PATH"] = cls._old_settings_path
        if cls._tempdir:
            shutil.rmtree(cls._tempdir, ignore_errors=True)

    # ------------------------------------------------------------------ HTTP
    def _headers(self, role="OWNER", permission_list=None):
        token = UserManager.generate_token(
            {
                "user_id": f"usr_ui_{role.lower()}",
                "tenant_id": "tnt_ui",
                "company_id": "comp_ui",
                "role": role,
                "permissions": permission_list or ["*"],
            }
        )
        return {"Authorization": f"Bearer {token}"}

    def _request(self, method, path, payload=None, headers=None):
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method
        )
        if data is not None:
            req.add_header("Content-Type", "application/json")
        for key, value in (headers or self._headers()).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8")), resp.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                return json.loads(body), exc.code
            except Exception:
                return {"error": body}, exc.code

    def _get(self, path, headers=None):
        return self._request("GET", path, None, headers)

    def _post(self, path, payload, headers=None):
        return self._request("POST", path, payload, headers)

    # ------------------------------------------------------------------ tests
    def test_console_assets_are_shipped_and_wired(self):
        index_path = os.path.join(WEB_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as handle:
            index = handle.read()

        for asset in ("settings_v2.css", "settings_v2.js"):
            self.assertTrue(
                os.path.isfile(os.path.join(WEB_DIR, asset)),
                f"{asset} is missing from web/",
            )
            self.assertIn(asset, index, f"{asset} is not wired into index.html")

        # The console module must load after the legacy module it coexists with.
        self.assertLess(
            index.index("settings_enterprise.js"),
            index.index("settings_v2.js"),
            "settings_v2.js must load after settings_enterprise.js",
        )

    def test_default_settings_route_opens_the_v2_console(self):
        with open(os.path.join(WEB_DIR, "app.js"), "r", encoding="utf-8") as handle:
            app_js = handle.read()
        with open(os.path.join(WEB_DIR, "settings_v2.js"), "r", encoding="utf-8") as handle:
            console_js = handle.read()

        # The router sends the default settings route to the console and keeps
        # a real legacy escape hatch.
        self.assertIn("window.SettingsV2.render(cleanPath)", app_js)
        self.assertIn("/settings-legacy", app_js)
        self.assertIn("legacyDomain", app_js)

        # Every console link to the old UI targets the legacy alias, never the
        # default route (which would loop back into the console).
        self.assertIn("#/settings-legacy", console_js)
        self.assertNotIn('href="#/settings"', console_js)

    def test_registry_exposes_capabilities_and_hides_hidden_definitions(self):
        payload, status = self._get(
            "/api/settings/v2/registry?section=ai_agents_employees"
        )
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["success"])
        registry = payload["registry"]
        capabilities = registry["capabilities"]
        self.assertTrue(capabilities["can_write"])
        self.assertTrue(capabilities["can_lock"])
        self.assertTrue(capabilities["can_manage_secrets"])
        self.assertEqual(capabilities["role"], "OWNER")

        keys = {item["key"] for item in registry["settings"]}
        self.assertIn("wf_max_concurrent_agents", keys)
        # A hidden definition must never reach the public catalog.
        self.assertNotIn("bill_plan_tier", keys)
        self.assertIn("counts", registry)

        live = [item for item in registry["settings"] if item["status"] == "live"]
        self.assertTrue(live, "expected live definitions in section 4")
        for item in live:
            self.assertIn("allowed_scopes", item)
            self.assertIn("required_permission", item)

    def test_values_carry_provenance_version_and_override_state(self):
        payload, status = self._get(
            "/api/settings/v2/values"
            "?section=ai_agents_employees&scope=company&company_id=comp_ui"
        )
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["success"])
        settings = payload["settings"]
        self.assertEqual(payload["count"], len(settings))
        self.assertTrue(settings)

        by_key = {row["key"]: row for row in settings}
        self.assertIn("wf_max_concurrent_agents", by_key)
        for row in settings:
            self.assertIn("provenance", row, row["key"])
            self.assertIn("status", row, row["key"])
            self.assertIn("overridden_here", row, row["key"])
            self.assertIn("allowed_scopes", row, row["key"])

        row = by_key["wf_max_concurrent_agents"]
        self.assertFalse(row["overridden_here"])
        self.assertIn("default", row["provenance"].lower())
        self.assertIn("company", row["allowed_scopes"])

    def test_write_then_reset_round_trip(self):
        key = "wf_max_concurrent_agents"
        company_id = "comp_ui"

        written, status = self._post(
            "/api/settings/v2/values",
            {
                "key": key,
                "value": 12,
                "scope_type": "company",
                "scope_id": company_id,
                "company_id": company_id,
                "expected_version": 0,
                "reason": "Settings V2 console smoke test.",
            },
        )
        self.assertEqual(status, 200, written)
        self.assertTrue(written["success"])
        result = written["result"]
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["scope_type"], "company")
        self.assertEqual(result["scope_id"], company_id)

        effective, status = self._get(
            f"/api/settings/v2/effective?key={key}&scope=company"
            f"&company_id={company_id}"
        )
        self.assertEqual(status, 200, effective)
        setting = effective["setting"]
        self.assertEqual(setting["value"], 12)
        self.assertTrue(setting["overridden_here"])
        self.assertEqual(setting["version"], 1)
        self.assertEqual(setting["source_scope"], "company")
        self.assertEqual(setting["source_id"], company_id)

        reset, status = self._post(
            "/api/settings/v2/values/reset",
            {
                "key": key,
                "scope_type": "company",
                "scope_id": company_id,
                "company_id": company_id,
                "expected_version": 1,
                "reason": "Reset from the console smoke test.",
            },
        )
        self.assertEqual(status, 200, reset)
        self.assertTrue(reset["success"])
        self.assertTrue(reset["result"]["removed"])
        self.assertEqual(reset["result"]["version"], 2)

        effective, status = self._get(
            f"/api/settings/v2/effective?key={key}&scope=company"
            f"&company_id={company_id}"
        )
        self.assertEqual(status, 200, effective)
        self.assertFalse(effective["setting"]["overridden_here"])

    def test_stale_version_is_rejected_with_conflict(self):
        key = "llm_temperature"
        company_id = "comp_ui"

        first, status = self._post(
            "/api/settings/v2/values",
            {
                "key": key,
                "value": 0.5,
                "scope_type": "company",
                "scope_id": company_id,
                "company_id": company_id,
                "expected_version": 0,
            },
        )
        self.assertEqual(status, 200, first)

        stale, status = self._post(
            "/api/settings/v2/values",
            {
                "key": key,
                "value": 0.6,
                "scope_type": "company",
                "scope_id": company_id,
                "company_id": company_id,
                "expected_version": 0,
            },
        )
        self.assertEqual(status, 409, stale)
        self.assertEqual(stale["code"], "VERSION_CONFLICT")

        # Leave the database clean for later assertions in this class.
        self._post(
            "/api/settings/v2/values/reset",
            {
                "key": key,
                "scope_type": "company",
                "scope_id": company_id,
                "company_id": company_id,
                "expected_version": 1,
            },
        )

    def test_observer_cannot_write(self):
        payload, status = self._get(
            "/api/settings/v2/registry",
            self._headers(role="OBSERVER"),
        )
        self.assertEqual(status, 200, payload)
        self.assertFalse(payload["registry"]["capabilities"]["can_write"])

        rejected, status = self._post(
            "/api/settings/v2/values",
            {
                "key": "wf_max_concurrent_agents",
                "value": 3,
                "scope_type": "company",
                "scope_id": "comp_ui",
                "company_id": "comp_ui",
                "expected_version": 0,
            },
            self._headers(role="OBSERVER"),
        )
        self.assertEqual(status, 403, rejected)


if __name__ == "__main__":
    unittest.main()
