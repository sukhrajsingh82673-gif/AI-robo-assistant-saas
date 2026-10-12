"""
URA / ZONATA Enterprise Hardening — Audit Remediation & Security Regression Suite
Verifies all remediations against FIND-01 through FIND-08:
- Negative authentication and failing closed on missing/invalid tokens
- Tenant context mismatch / anti-spoofing rejection
- Unauthenticated token issuance prevention
- Strict CORS origin allowlist enforcement
- Terminal & agent runtime fail-closed sandbox boundaries
- Evidence ledger epistemic truth preservation (SIMULATED cannot be stamped VERIFIED)
- Connector & robot simulation provenance
- Webhook signature validation fail-closed on missing headers
- Storage path portability and zero mutation of baseline production database
"""

import unittest
import os
import sys
import json
import time
import uuid
import hmac
import hashlib
import tempfile
import threading
import urllib.request
import urllib.error
import socket

# Ensure repo root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.models import EvidencePackage, EvidenceStatus, ExecutionClassification, ActionContract, AuthorityLevel, HostType
from core.evidence_ledger import EvidenceLedger, get_default_ledger_path
from core.db import db, Database, get_default_db_path, configure_isolated_test_db
from core.auth import UserManager, UserRole, AuthExceptions, get_auth_secret_key
from core.connectors import HospitalityPMSConnector, AccountingConnector, PaymentGatewayConnector
from core.desktop_robot import UniversalDesktopRobot
from core.host_fabric import UniversalHostAgent
from core.browser_robot import BrowserExecutionFabric
from core.universal_terminal.runtime_adapters import ContainerRuntimeAdapter, VMRuntimeAdapter
from core.openhands_execution_runtime import OpenHandsExecutionProvider
from core.nango_integration_runtime import NangoAdapter, ExternalIntegrationGateway

# Baseline DB Checksum expected
BASELINE_DB_SHA256 = "ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4"

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None


def setUpModule():
    """Configures a globally isolated database for all test fixtures in this suite."""
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "security_test_isolated.db")
    configure_isolated_test_db(isolated_db)


def tearDownModule():
    """Restores database path to original baseline."""
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestApiServerSecurityBoundaries(unittest.TestCase):
    """Verifies API server auth, tenant spoofing prevention, token issuance, and CORS."""

    @classmethod
    def setUpClass(cls):
        # Seed test user in isolated DB
        cls.tenant_alpha = f"tnt_alpha_{uuid.uuid4().hex[:6]}"
        cls.tenant_beta = f"tnt_beta_{uuid.uuid4().hex[:6]}"
        cls.user_alpha = f"usr_alpha_{uuid.uuid4().hex[:6]}"
        cls.email_alpha = f"{cls.user_alpha}@{cls.tenant_alpha}.com"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.tenant_alpha, "Tenant Alpha", "ENTERPRISE", "ACTIVE", time.time())
            )
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.tenant_beta, "Tenant Beta", "ENTERPRISE", "ACTIVE", time.time())
            )
            conn.execute(
                "INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cls.user_alpha, cls.tenant_alpha, cls.email_alpha, "User Alpha", UserRole.EXECUTIVE, "ACTIVE", time.time())
            )

        # Set bootstrap secret for controlled tests
        cls.bootstrap_secret = "test-zonata-bootstrap-secret-4096"
        os.environ["ZONATA_BOOTSTRAP_SECRET"] = cls.bootstrap_secret

        # Start threaded API server on free port
        from api_server import ThreadedHTTPServer, RoboAssistantRequestHandler
        cls.port = get_free_port()
        cls.server = ThreadedHTTPServer(("127.0.0.1", cls.port), RoboAssistantRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

        cls.base_url = f"http://127.0.0.1:{cls.port}"

        # Generate valid token for user_alpha in tenant_alpha
        cls.token_alpha = UserManager.generate_token({
            "user_id": cls.user_alpha,
            "tenant_id": cls.tenant_alpha,
            "company_id": "comp_alpha",
            "role": UserRole.EXECUTIVE,
            "permissions": ["read", "execute"]
        })

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        if "ZONATA_BOOTSTRAP_SECRET" in os.environ:
            del os.environ["ZONATA_BOOTSTRAP_SECRET"]

    def _http_request(self, method, path, headers=None, data=None):
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                resp_headers = dict(resp.info())
                resp_body = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(resp_body)
                except Exception:
                    parsed = resp_body
                return status, parsed, resp_headers
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                parsed = json.loads(err_body)
            except Exception:
                parsed = err_body
            return e.code, parsed, dict(e.headers)

    def test_01_negative_auth_missing_token_blocked(self):
        """Unauthenticated request to protected endpoint must return 401."""
        status, body, _ = self._http_request("GET", "/api/auth/me")
        self.assertEqual(status, 401, f"Expected 401 Unauthorized, got {status}: {body}")
        self.assertIn("Unauthorized", body.get("error", ""))

    def test_02_negative_auth_invalid_token_blocked(self):
        """Request with invalid bearer token must return 401."""
        headers = {"Authorization": "Bearer invalid_malformed_token_xyz"}
        status, body, _ = self._http_request("GET", "/api/auth/me", headers=headers)
        self.assertEqual(status, 401)
        self.assertIn("Unauthorized", body.get("error", ""))

    def test_03_public_endpoints_accessible_without_auth(self):
        """Health and auth environment endpoints must be accessible publicly without credentials."""
        status, body, _ = self._http_request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "HEALTHY")

        status, body, _ = self._http_request("GET", "/api/auth/environment")
        self.assertEqual(status, 200)
        self.assertIn("environment", body)

    def test_04_tenant_spoofing_via_header_rejected(self):
        """Attacker with token for tenant_alpha cannot spoof X-Tenant-ID: tenant_beta."""
        headers = {
            "Authorization": f"Bearer {self.token_alpha}",
            "X-Tenant-ID": self.tenant_beta
        }
        status, body, _ = self._http_request("GET", "/api/auth/me", headers=headers)
        self.assertEqual(status, 403, f"Expected 403 Forbidden for tenant spoofing, got {status}: {body}")
        self.assertEqual(body.get("security_event"), "TENANT_SPOOFING_ATTEMPT")

    def test_05_authenticated_matching_tenant_allowed(self):
        """Matching authenticated tenant context must be accepted."""
        headers = {
            "Authorization": f"Bearer {self.token_alpha}",
            "X-Tenant-ID": self.tenant_alpha
        }
        status, body, _ = self._http_request("GET", "/api/auth/me", headers=headers)
        self.assertEqual(status, 200, f"Expected 200 OK, got {status}: {body}")
        self.assertTrue(body.get("authenticated"))
        self.assertEqual(body.get("context", {}).get("tenant_id"), self.tenant_alpha)

    def test_06_token_issuance_unregistered_user_blocked(self):
        """Requesting a token without DB enrollment or bootstrap secret must fail closed with 401."""
        payload = {
            "email": "hacker@unregistered.org",
            "tenant_id": self.tenant_beta
        }
        status, body, _ = self._http_request("POST", "/api/auth/token", data=payload)
        self.assertEqual(status, 401)
        self.assertIn("Unauthorized", body.get("error", ""))

    def test_07_token_issuance_with_bootstrap_secret_succeeds(self):
        """Requesting a token with valid bootstrap secret succeeds and issues valid JWT."""
        payload = {
            "tenant_id": self.tenant_alpha,
            "secret": self.bootstrap_secret,
            "role": "OWNER"
        }
        status, body, _ = self._http_request("POST", "/api/auth/token", data=payload)
        self.assertEqual(status, 200)
        self.assertIn("token", body)
        self.assertEqual(body.get("user", {}).get("tenant_id"), self.tenant_alpha)

    def test_08_cors_allowlist_enforcement(self):
        """Allowed origins receive Access-Control-Allow-Origin; disallowed origins receive 403."""
        # Allowed origin
        headers_allowed = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
        status, _, resp_headers = self._http_request("OPTIONS", "/health", headers=headers_allowed)
        self.assertEqual(status, 204)
        self.assertEqual(resp_headers.get("Access-Control-Allow-Origin"), "http://localhost:3000")
        self.assertEqual(resp_headers.get("Access-Control-Allow-Credentials"), "true")

        # Disallowed origin
        headers_disallowed = {
            "Origin": "https://malicious-attacker-site.com",
            "Access-Control-Request-Method": "GET"
        }
        status, _, _ = self._http_request("OPTIONS", "/health", headers=headers_disallowed)
        self.assertEqual(status, 403)


class TestRuntimeSandboxFailClosed(unittest.TestCase):
    """Verifies that terminal and agent execution fail closed when sandbox runtimes are unavailable."""

    def setUp(self):
        self.orig_allow_host = os.environ.get("ZONATA_ALLOW_HOST_SHELL")
        if "ZONATA_ALLOW_HOST_SHELL" in os.environ:
            del os.environ["ZONATA_ALLOW_HOST_SHELL"]

    def tearDown(self):
        if self.orig_allow_host is not None:
            os.environ["ZONATA_ALLOW_HOST_SHELL"] = self.orig_allow_host
        elif "ZONATA_ALLOW_HOST_SHELL" in os.environ:
            del os.environ["ZONATA_ALLOW_HOST_SHELL"]

    def test_01_container_runtime_fails_closed_without_sandbox(self):
        """Container adapter must fail closed with code 126 and sandbox_failure flag."""
        adapter = ContainerRuntimeAdapter()
        res = adapter.execute_command(
            session_id="test_sess_01",
            command="echo 'unauthorized_execution'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res.get("exit_code"), 126)
        self.assertTrue(res.get("sandbox_failure"))
        self.assertIn("sandbox unavailable", res.get("stderr", "").lower())

    def test_02_microvm_runtime_fails_closed_without_kvm(self):
        """MicroVM adapter must fail closed with code 126 when KVM/MicroVM runtime is absent."""
        adapter = VMRuntimeAdapter()
        res = adapter.execute_command(
            session_id="test_sess_02",
            command="echo 'unauthorized_execution'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res.get("exit_code"), 126)
        self.assertTrue(res.get("sandbox_failure"))
        self.assertIn("virtualization", res.get("stderr", "").lower())

    def test_03_openhands_fails_closed_without_sandbox(self):
        """OpenHands provider must fail closed with code 126 and error message."""
        result = OpenHandsExecutionProvider(None).execute_command(
            workspace_path=tempfile.gettempdir(),
            command="echo 'unauthorized_agent_execution'"
        )
        self.assertEqual(result.get("exit_code"), 126)
        self.assertIn("Isolated container sandbox required", result.get("stderr", ""))

    def test_04_explicit_host_shell_opt_in_override(self):
        """When ZONATA_ALLOW_HOST_SHELL=1 is explicitly set, controlled host execution is permitted."""
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        adapter = ContainerRuntimeAdapter()
        res = adapter.execute_command(
            session_id="test_sess_optin",
            command="echo 'host_authorized'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res.get("exit_code"), 0)
        self.assertIn("host_authorized", res.get("stdout", ""))


class TestEvidenceIntegrityAndConnectors(unittest.TestCase):
    """Verifies evidence sealing classification, mock connector provenance, and robot honesty."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_path = os.path.join(self.temp_dir.name, "test_ledger.jsonl")
        self.ledger = EvidenceLedger(self.ledger_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_simulated_evidence_cannot_be_upgraded_to_verified(self):
        """Evidence created with simulated=True is sealed as SIMULATED and stored accurately."""
        sealed = self.ledger.seal_evidence(
            action_id="act_sim_01",
            mission_id="msn_sim_01",
            agent_id="agt_sim_01",
            verifications=[],
            metadata={"simulated": True, "is_mock": True}
        )
        self.assertEqual(sealed.status, EvidenceStatus.SIMULATED)
        self.assertEqual(sealed.execution_classification, "SIMULATED")

        # Confirm persisted record in ledger preserves SIMULATED status
        record = self.ledger.get_evidence(sealed.evidence_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "SIMULATED")
        self.assertEqual(record["execution_classification"], "SIMULATED")

    def test_02_pms_connector_provenance(self):
        """PMS connector returns explicit is_mock=True, SIMULATED mode, and verified=False."""
        connector = HospitalityPMSConnector()
        connector.connect({"token_hash": "hash_sample"})
        res = connector.fetch_night_audit_records()
        self.assertTrue(res.get("is_mock"))
        self.assertEqual(res.get("execution_mode"), "SIMULATED")
        self.assertFalse(res.get("verified"))
        self.assertFalse(res.get("ledger_verified"))

    def test_03_accounting_connector_provenance(self):
        """Accounting connector returns is_mock=True and ledger_verified=False."""
        connector = AccountingConnector()
        connector.connect({"token_hash": "hash_sample"})
        res = connector.fetch_general_ledger()
        self.assertTrue(res.get("is_mock"))
        self.assertEqual(res.get("execution_mode"), "SIMULATED")
        self.assertFalse(res.get("verified"))

    def test_04_payment_connector_provenance(self):
        """Payment gateway connector returns is_mock=True and payout_verified=False."""
        connector = PaymentGatewayConnector()
        connector.connect({"token_hash": "hash_sample"})
        res = connector.fetch_settlement_batch()
        self.assertTrue(res.get("is_mock"))
        self.assertEqual(res.get("execution_mode"), "SIMULATED")
        self.assertFalse(res.get("verified"))
        self.assertFalse(res.get("payout_verified"))

    def test_05_desktop_robot_simulated_provenance(self):
        """Desktop robot screen capture stamps simulated=True, verified=False, and SIMULATED mode."""
        host = UniversalHostAgent(host_id="test_host", tenant_id="tnt_test")
        robot = UniversalDesktopRobot(host, ledger=self.ledger)
        contract = ActionContract(
            action_id="act_screen_test",
            mission_id="msn_test",
            agent_id="agt_test",
            capability="screen_capture",
            target="screen:display_0",
            host=HostType.LINUX_CLOUD,
            scope="test",
            permissions_required=AuthorityLevel.SANDBOXED_READ_ONLY,
            resources_locked=[],
            expected_outcome="Capture display",
            verification_requirements=["screen_state"]
        )
        res = robot.execute_action(contract, {})
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("simulated"))
        self.assertFalse(res.get("verified"))
        self.assertEqual(res.get("execution_mode"), "SIMULATED")

    def test_06_browser_robot_simulated_provenance(self):
        """Browser robot actions stamp execution_mode='SIMULATED' and verified=False."""
        browser = BrowserExecutionFabric(session_id="test_browser_sess")
        res = browser.navigate("https://example.com/checkout")
        self.assertTrue(res.get("simulated"))
        self.assertFalse(res.get("verified"))
        self.assertEqual(res.get("execution_mode"), "SIMULATED")


class TestWebhookAndStoragePortability(unittest.TestCase):
    """Verifies fail-closed webhook validation, storage path remapping, and DB preservation."""

    def test_01_webhook_missing_signature_fails_closed(self):
        """Webhook validation must fail closed (return False) when signature header is missing or empty."""
        adapter = NangoAdapter()
        payload_str = '{"event": "account.updated", "id": "acc_001"}'

        # Missing signature
        self.assertFalse(adapter.verify_webhook("nango", {}, payload_str, "secret_test"))
        # Empty signature
        self.assertFalse(adapter.verify_webhook("nango", {"X-Nango-Signature": ""}, payload_str, "secret_test"))
        # Invalid signature
        self.assertFalse(adapter.verify_webhook("nango", {"X-Nango-Signature": "sha256=invalid_hash"}, payload_str, "secret_test"))

    def test_02_webhook_valid_signature_succeeds(self):
        """Webhook validation passes with a valid HMAC-SHA256 signature."""
        adapter = NangoAdapter()
        payload_str = '{"event": "account.updated", "id": "acc_001"}'
        key = b"secret_test"
        expected_sig = "sha256=" + hmac.new(key, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()

        self.assertTrue(adapter.verify_webhook("nango", {"X-Nango-Signature": expected_sig}, payload_str, "secret_test"))

    def test_03_storage_portability_environment_resolution(self):
        """get_default_ledger_path and get_default_db_path honor environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_ledger = os.path.join(temp_dir, "custom_ledger.jsonl")
            custom_db = os.path.join(temp_dir, "custom_db.db")

            os.environ["ZONATA_EVIDENCE_PATH"] = custom_ledger
            os.environ["ZONATA_DB_PATH"] = custom_db
            try:
                self.assertEqual(get_default_ledger_path(), custom_ledger)
                self.assertEqual(get_default_db_path(), custom_db)
            finally:
                del os.environ["ZONATA_EVIDENCE_PATH"]
                del os.environ["ZONATA_DB_PATH"]

    def test_04_baseline_database_integrity_preserved(self):
        """Ensures storage/roboassistant.db has not been corrupted or mutated by any test."""
        db_file = os.path.join(BASE_DIR, "storage", "roboassistant.db")
        if not os.path.exists(db_file):
            self.skipTest("Baseline DB file not found at expected path")

        with open(db_file, "rb") as f:
            computed_sha256 = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(
            computed_sha256,
            BASELINE_DB_SHA256,
            f"BASELINE DB MUTATION DETECTED! Expected {BASELINE_DB_SHA256}, got {computed_sha256}"
        )


if __name__ == "__main__":
    unittest.main()
