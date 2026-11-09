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
from unittest.mock import patch
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

from core.models import EvidencePackage, EvidenceStatus, ExecutionClassification, ActionContract, AuthorityLevel, HostType, PhysicalVerification
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
BASELINE_DB_SHA256 = "f71d9d79b95f2dc924385f90e97c7c565afd3b070b5d4628c3e2ad86aa52deda"

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

    def test_09_production_mode_locks_out_bootstrap_token_minting(self):
        """In production mode, administrative bootstrap is rejected with HTTP 403 Forbidden."""
        os.environ["APP_ENV"] = "production"
        try:
            payload = {
                "tenant_id": self.tenant_alpha,
                "secret": self.bootstrap_secret,
                "role": "OWNER"
            }
            status, body, _ = self._http_request("POST", "/api/auth/token", data=payload)
            self.assertEqual(status, 403)
            self.assertIn("strictly locked out in production mode", body.get("detail", ""))
        finally:
            os.environ.pop("APP_ENV", None)

    def test_10_production_mode_bootstrap_without_secret_fails(self):
        """In production mode with bootstrap provisioning enabled but secret missing, returns HTTP 403."""
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_BOOTSTRAP_PROVISIONING"] = "1"
        old_secret = os.environ.pop("ZONATA_BOOTSTRAP_SECRET", None)
        try:
            payload = {
                "tenant_id": self.tenant_alpha,
                "secret": "some_secret",
                "role": "OWNER"
            }
            status, body, _ = self._http_request("POST", "/api/auth/token", data=payload)
            self.assertEqual(status, 403)
            self.assertIn("at least 32 high-entropy characters", body.get("detail", ""))
        finally:
            os.environ.pop("APP_ENV", None)
            os.environ.pop("ZONATA_ALLOW_BOOTSTRAP_PROVISIONING", None)
            if old_secret is not None:
                os.environ["ZONATA_BOOTSTRAP_SECRET"] = old_secret

    def test_11_production_mode_bootstrap_invalid_credentials_fails(self):
        """In production mode with bootstrap provisioning enabled, invalid secret returns HTTP 401."""
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_BOOTSTRAP_PROVISIONING"] = "1"
        valid_sec = "a" * 32
        os.environ["ZONATA_BOOTSTRAP_SECRET"] = valid_sec
        try:
            payload = {
                "tenant_id": self.tenant_alpha,
                "secret": "wrong_secret_12345678901234567890",
                "role": "OWNER"
            }
            status, body, _ = self._http_request("POST", "/api/auth/token", data=payload)
            self.assertEqual(status, 401)
            self.assertIn("Invalid bootstrap credentials", body.get("detail", ""))
        finally:
            os.environ.pop("APP_ENV", None)
            os.environ.pop("ZONATA_ALLOW_BOOTSTRAP_PROVISIONING", None)
            os.environ["ZONATA_BOOTSTRAP_SECRET"] = self.bootstrap_secret

    def test_12_production_mode_authorized_bootstrap_succeeds_and_locks_repeated_requests(self):
        """Authorized production bootstrap succeeds once, and repeated bootstrap for the tenant is locked."""
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_BOOTSTRAP_PROVISIONING"] = "1"
        valid_sec = "a" * 32
        os.environ["ZONATA_BOOTSTRAP_SECRET"] = valid_sec
        os.environ["ZONATA_AUTH_SECRET"] = "valid_auth_secret_32_chars_long_entropy_12345"
        target_tnt = f"tnt_boot_{uuid.uuid4().hex[:6]}"
        try:
            payload = {
                "tenant_id": target_tnt,
                "secret": valid_sec,
                "role": "OWNER"
            }
            # First request: authorized
            status, body, _ = self._http_request("POST", "/api/auth/token", data=payload)
            self.assertEqual(status, 200)
            self.assertIn("token", body)
            self.assertEqual(body.get("user", {}).get("tenant_id"), target_tnt)

            # Second request: locked out
            status2, body2, _ = self._http_request("POST", "/api/auth/token", data=payload)
            self.assertEqual(status2, 403)
            self.assertIn("Repeated bootstrap is locked", body2.get("detail", ""))
        finally:
            os.environ.pop("APP_ENV", None)
            os.environ.pop("ZONATA_ALLOW_BOOTSTRAP_PROVISIONING", None)
            os.environ.pop("ZONATA_AUTH_SECRET", None)
            os.environ["ZONATA_BOOTSTRAP_SECRET"] = self.bootstrap_secret


class TestRuntimeSandboxFailClosed(unittest.TestCase):
    """Verifies that terminal and agent execution fail closed when sandbox runtimes are unavailable."""

    def setUp(self):
        self.orig_env = {
            k: os.environ.get(k)
            for k in ["ZONATA_ALLOW_HOST_SHELL", "STRICT_ISOLATION_REQUIRED", "APP_ENV", "ZONATA_ENV", "ZONATA_STRICT_AUTH", "ZONATA_PRODUCTION"]
        }
        for k in self.orig_env:
            if k in os.environ:
                del os.environ[k]

    def tearDown(self):
        for k, v in self.orig_env.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

    def test_01_container_runtime_fails_closed_without_sandbox(self):
        """Container adapter must fail closed with code 126 and sandbox_failure flag."""
        adapter = ContainerRuntimeAdapter()
        # Force the "no container engine" condition deterministically. CI runners
        # ship Docker, so relying on host detection would make this test pass or
        # fail based on the machine rather than on the fail-closed contract.
        with patch.object(ContainerRuntimeAdapter, "_detect_engine", return_value=None):
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
        """When ZONATA_ALLOW_HOST_SHELL=1 is explicitly set in non-production, controlled host execution is permitted."""
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        adapter = ContainerRuntimeAdapter()
        res = adapter.execute_command(
            session_id="test_sess_optin",
            command="echo 'host_authorized'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res.get("exit_code"), 0)
        self.assertIn("host_authorized", res.get("stdout", ""))

    def test_05_production_mode_refuses_host_shell_override(self):
        """In production mode (APP_ENV=production), host-shell override is unconditionally rejected."""
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"

        container_adapter = ContainerRuntimeAdapter()
        res_container = container_adapter.execute_command(
            session_id="test_sess_prod_reject",
            command="echo 'should_fail'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res_container.get("exit_code"), 126)
        self.assertIn("strictly prohibited in production mode", res_container.get("stderr", ""))

        vm_adapter = VMRuntimeAdapter()
        res_vm = vm_adapter.execute_command(
            session_id="test_sess_prod_vm_reject",
            command="echo 'should_fail'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res_vm.get("exit_code"), 126)
        self.assertIn("strictly prohibited in production mode", res_vm.get("stderr", ""))

        res_oh = OpenHandsExecutionProvider(None).execute_command(
            workspace_path=tempfile.gettempdir(),
            command="echo 'should_fail'"
        )
        self.assertEqual(res_oh.get("exit_code"), 126)
        self.assertIn("strictly prohibited in production mode", res_oh.get("stderr", ""))

    def test_06_server_startup_refuses_host_shell_in_production(self):
        """api_server.run_server raises RuntimeError if ZONATA_ALLOW_HOST_SHELL=1 is set in production."""
        from api_server import run_server
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        with self.assertRaises(RuntimeError) as cm:
            run_server(port=9999)
        self.assertIn("strictly prohibited in production mode", str(cm.exception))

    def test_07_strict_isolation_required_blocks_host_shell_override(self):
        """When STRICT_ISOLATION_REQUIRED=1, host shell fallback is forbidden even if ZONATA_ALLOW_HOST_SHELL=1."""
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        os.environ["STRICT_ISOLATION_REQUIRED"] = "1"

        container_adapter = ContainerRuntimeAdapter()
        res_container = container_adapter.execute_command(
            session_id="test_sess_strict_container",
            command="echo 'should_fail'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res_container.get("exit_code"), 126)
        self.assertTrue(res_container.get("sandbox_failure"))

        vm_adapter = VMRuntimeAdapter()
        res_vm = vm_adapter.execute_command(
            session_id="test_sess_strict_vm",
            command="echo 'should_fail'",
            cwd=tempfile.gettempdir()
        )
        self.assertEqual(res_vm.get("exit_code"), 126)
        self.assertTrue(res_vm.get("sandbox_failure"))

        res_oh = OpenHandsExecutionProvider(None).execute_command(
            workspace_path=tempfile.gettempdir(),
            command="echo 'should_fail'"
        )
        self.assertEqual(res_oh.get("exit_code"), 126)

    def test_08_strict_isolation_rejects_caller_env_host_shell_override(self):
        """Caller-supplied env dictionary cannot bypass STRICT_ISOLATION_REQUIRED restriction."""
        os.environ["STRICT_ISOLATION_REQUIRED"] = "1"

        container_adapter = ContainerRuntimeAdapter()
        res = container_adapter.execute_command(
            session_id="test_sess_injected_env",
            command="echo 'should_fail'",
            cwd=tempfile.gettempdir(),
            env={"ZONATA_ALLOW_HOST_SHELL": "1"}
        )
        self.assertEqual(res.get("exit_code"), 126)
        self.assertTrue(res.get("sandbox_failure"))

    def test_09_simulation_fixtures_enforce_strict_isolation(self):
        """init_simulation_environment configures STRICT_ISOLATION_REQUIRED=1 and ZONATA_ALLOW_HOST_SHELL=0."""
        from core.simulation_fixtures import init_simulation_environment
        old_strict = os.environ.get("STRICT_ISOLATION_REQUIRED")
        old_shell = os.environ.get("ZONATA_ALLOW_HOST_SHELL")
        old_db_path = db.db_path
        old_env_db = os.environ.get("ZONATA_DB_PATH")
        old_env_ev = os.environ.get("ZONATA_EVIDENCE_PATH")
        try:
            with tempfile.TemporaryDirectory() as td:
                fixture_db = os.path.join(td, "sim_test.db")
                cfg = init_simulation_environment(fixture_db)
                self.assertEqual(os.environ.get("STRICT_ISOLATION_REQUIRED"), "1")
                self.assertEqual(os.environ.get("ZONATA_ALLOW_HOST_SHELL"), "0")
                self.assertTrue(cfg.get("strict_isolation"))
                self.assertFalse(cfg.get("allow_host_shell"))
        finally:
            db.set_db_path(old_db_path)
            for k, v in [
                ("STRICT_ISOLATION_REQUIRED", old_strict),
                ("ZONATA_ALLOW_HOST_SHELL", old_shell),
                ("ZONATA_DB_PATH", old_env_db),
                ("ZONATA_EVIDENCE_PATH", old_env_ev),
            ]:
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    @patch.object(ContainerRuntimeAdapter, "_detect_engine", return_value="docker")
    def test_10_docker_present_production_mode_refuses_host_shell_override(self, mock_detect):
        """Even when Docker engine is present on host, APP_ENV=production strictly refuses host shell override."""
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        try:
            adapter = ContainerRuntimeAdapter()
            res = adapter.execute_command(
                session_id="test_sess_docker_prod",
                command="echo 'bypass_attempt'",
                cwd=tempfile.gettempdir()
            )
            self.assertEqual(res.get("exit_code"), 126)
            self.assertTrue(res.get("sandbox_failure"))
            self.assertIn("strictly prohibited in production mode", res.get("stderr", ""))
        finally:
            os.environ.pop("APP_ENV", None)
            os.environ.pop("ZONATA_ALLOW_HOST_SHELL", None)

    @patch.object(ContainerRuntimeAdapter, "_detect_engine", return_value="docker")
    def test_11_docker_present_strict_isolation_blocks_host_shell_override(self, mock_detect):
        """Even when Docker engine is present, STRICT_ISOLATION_REQUIRED=1 strictly blocks host shell override."""
        os.environ["STRICT_ISOLATION_REQUIRED"] = "1"
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        try:
            adapter = ContainerRuntimeAdapter()
            res = adapter.execute_command(
                session_id="test_sess_docker_strict",
                command="echo 'bypass_attempt'",
                cwd=tempfile.gettempdir()
            )
            self.assertEqual(res.get("exit_code"), 126)
            self.assertTrue(res.get("sandbox_failure"))
            self.assertIn("strictly prohibited when strict isolation is required", res.get("stderr", ""))
        finally:
            os.environ.pop("STRICT_ISOLATION_REQUIRED", None)
            os.environ.pop("ZONATA_ALLOW_HOST_SHELL", None)

    @patch.object(VMRuntimeAdapter, "_has_virtualization", return_value=True)
    def test_12_vm_virtualization_present_production_mode_refuses_host_shell_override(self, mock_virt):
        """Even when KVM/hardware virtualization is present, APP_ENV=production strictly refuses host shell override."""
        os.environ["APP_ENV"] = "production"
        os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
        try:
            adapter = VMRuntimeAdapter()
            res = adapter.execute_command(
                session_id="test_sess_vm_prod",
                command="echo 'bypass_attempt'",
                cwd=tempfile.gettempdir()
            )
            self.assertEqual(res.get("exit_code"), 126)
            self.assertTrue(res.get("sandbox_failure"))
            self.assertIn("strictly prohibited in production mode", res.get("stderr", ""))
        finally:
            os.environ.pop("APP_ENV", None)
            os.environ.pop("ZONATA_ALLOW_HOST_SHELL", None)


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
        """Unconfigured PMS connector reports NOT_CONFIGURED and never fabricates folios."""
        connector = HospitalityPMSConnector()
        connector.connect({"token_hash": "hash_sample"})
        res = connector.fetch_night_audit_records()
        self.assertFalse(res.get("is_mock"))
        self.assertEqual(res.get("code"), "NOT_CONFIGURED")
        self.assertEqual(res.get("execution_mode"), "DISCONNECTED")
        self.assertFalse(res.get("verified"))
        self.assertFalse(res.get("ledger_verified"))
        self.assertEqual(res.get("folios"), [])
        self.assertEqual(res.get("records_count"), 0)

    def test_03_accounting_connector_provenance(self):
        """Unconfigured accounting connector reports NOT_CONFIGURED with no ledger fixture."""
        connector = AccountingConnector()
        connector.connect({"token_hash": "hash_sample"})
        res = connector.fetch_general_ledger()
        self.assertFalse(res.get("is_mock"))
        self.assertEqual(res.get("code"), "NOT_CONFIGURED")
        self.assertEqual(res.get("execution_mode"), "DISCONNECTED")
        self.assertFalse(res.get("verified"))
        self.assertEqual(res.get("entries"), [])
        self.assertEqual(res.get("accounts_reconciled"), 0)

    def test_04_payment_connector_provenance(self):
        """Unconfigured payment connector reports NOT_CONFIGURED with no settlement fixture."""
        connector = PaymentGatewayConnector()
        connector.connect({"token_hash": "hash_sample"})
        res = connector.fetch_settlement_batch()
        self.assertFalse(res.get("is_mock"))
        self.assertEqual(res.get("code"), "NOT_CONFIGURED")
        self.assertEqual(res.get("execution_mode"), "DISCONNECTED")
        self.assertFalse(res.get("verified"))
        self.assertFalse(res.get("payout_verified"))
        self.assertEqual(res.get("settlements"), [])

    def test_05_desktop_robot_simulated_provenance(self):
        """Screen capture without a display must fail closed — never fake pixels."""
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
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("code"), "DISPLAY_NOT_AVAILABLE")
        self.assertFalse(res.get("verified"))
        self.assertIsNone(res.get("evidence_id"))

    def test_06_browser_robot_simulated_provenance(self):
        """Browser robot never stamps synthetic provenance; it reports live outcomes."""
        browser = BrowserExecutionFabric(session_id="test_browser_sess")
        res = browser.navigate("https://example.com/checkout")
        self.assertFalse(res.get("simulated"))
        self.assertEqual(res.get("execution_mode"), "LIVE_HTTP")
        self.assertEqual(res.get("provenance"), "REAL_HTTP_GET")

    def test_07_simulated_evidence_with_successful_verifications_cannot_promote_to_verified(self):
        """Even with passing physical verifications, simulated metadata strictly forces SIMULATED status."""
        verification = PhysicalVerification(
            check_type="file_exists",
            target_path="/tmp/fake_verified_file",
            expected_val=True,
            actual_val=True,
            verified=True,
            details={"note": "mock physical check"}
        )
        sealed = self.ledger.seal_evidence(
            action_id="act_sim_spoof",
            mission_id="msn_sim_spoof",
            agent_id="agt_sim_spoof",
            verifications=[verification],
            metadata={"simulated": True, "execution_mode": "SIMULATED"}
        )
        self.assertEqual(sealed.status, EvidenceStatus.SIMULATED)
        self.assertEqual(sealed.execution_classification, "SIMULATED")
        self.assertNotEqual(sealed.status, EvidenceStatus.VERIFIED)

        # Confirm persisted record in ledger preserves SIMULATED status
        record = self.ledger.get_evidence(sealed.evidence_id)
        self.assertEqual(record["status"], "SIMULATED")
        self.assertEqual(record["execution_classification"], "SIMULATED")

    def test_08_downstream_consumer_cannot_treat_simulated_as_verified(self):
        """Downstream audit/reporting consumers must distinguish SIMULATED from VERIFIED records."""
        # Record 1: Simulated record
        pkg1 = self.ledger.seal_evidence(
            action_id="act_sim_downstream",
            mission_id="msn_downstream",
            agent_id="agt_downstream",
            verifications=[],
            metadata={"simulated": True}
        )
        # Record 2: Real verification
        real_verif = PhysicalVerification(
            check_type="file_exists",
            target_path="/bin/sh",
            expected_val=True,
            actual_val=True,
            verified=True,
            details={"note": "true physical check"}
        )
        pkg2 = self.ledger.seal_evidence(
            action_id="act_real_downstream",
            mission_id="msn_downstream",
            agent_id="agt_downstream",
            verifications=[real_verif],
            metadata={"simulated": False}
        )

        rec1 = self.ledger.get_evidence(pkg1.evidence_id)
        rec2 = self.ledger.get_evidence(pkg2.evidence_id)

        # Verify downstream invariant: simulated cannot be counted as VERIFIED
        self.assertEqual(rec1["status"], "SIMULATED")
        self.assertEqual(rec1["execution_classification"], "SIMULATED")
        self.assertEqual(rec2["status"], "VERIFIED")
        self.assertEqual(rec2["execution_classification"], "LIVE")

        verified_records = [r for r in self.ledger.chain if r.get("status") == "VERIFIED" and r.get("execution_classification") == "LIVE"]
        simulated_records = [r for r in self.ledger.chain if r.get("status") == "SIMULATED" or r.get("execution_classification") == "SIMULATED"]
        self.assertIn(rec2, verified_records)
        self.assertNotIn(rec1, verified_records)
        self.assertIn(rec1, simulated_records)


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

            orig_ev = os.environ.get("ZONATA_EVIDENCE_PATH")
            orig_db = os.environ.get("ZONATA_DB_PATH")
            os.environ["ZONATA_EVIDENCE_PATH"] = custom_ledger
            os.environ["ZONATA_DB_PATH"] = custom_db
            try:
                self.assertEqual(get_default_ledger_path(), custom_ledger)
                self.assertEqual(get_default_db_path(), custom_db)
            finally:
                if orig_ev is not None:
                    os.environ["ZONATA_EVIDENCE_PATH"] = orig_ev
                elif "ZONATA_EVIDENCE_PATH" in os.environ:
                    del os.environ["ZONATA_EVIDENCE_PATH"]

                if orig_db is not None:
                    os.environ["ZONATA_DB_PATH"] = orig_db
                elif "ZONATA_DB_PATH" in os.environ:
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
