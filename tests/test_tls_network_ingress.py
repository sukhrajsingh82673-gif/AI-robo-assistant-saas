"""
URA / ZONATA Enterprise SaaS — TLS & Ingress Security Suite
Validates BLK-02 / CTL-C05:
- Enforcement of HTTPS transport security in production mode
- Rejection of cleartext HTTP (X-Forwarded-Proto: http -> HTTP 403 Forbidden)
- Acceptance of verified HTTPS requests (X-Forwarded-Proto: https)
- Presence of HSTS (Strict-Transport-Security) and standard security headers
- Validation of Nginx ingress configuration (port 80 redirect, TLS 1.2/1.3, modern ciphers)
- ProductionConfigValidator TLS and reverse proxy ingress gates
"""

import os
import sys
import unittest
import urllib.request
import urllib.error
import json
import time
import uuid
import socket
import threading
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import db, configure_isolated_test_db
from core.production_config import ProductionConfigValidator, ConfigurationError
from core.auth import UserManager, UserRole

NGINX_CONF_PATH = os.path.join(BASE_DIR, "docker", "nginx", "nginx.conf")

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None


def setUpModule():
    """Configures a globally isolated database for all test fixtures in this suite."""
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "tls_test_isolated.db")
    configure_isolated_test_db(isolated_db)


def tearDownModule():
    """Restores database path to original baseline."""
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestTlsNetworkIngress(unittest.TestCase):
    """Verifies transport layer security, HTTPS enforcement, and ingress headers."""

    @classmethod
    def setUpClass(cls):
        from api_server import ThreadedHTTPServer, RoboAssistantRequestHandler
        cls.port = get_free_port()
        cls.server = ThreadedHTTPServer(("127.0.0.1", cls.port), RoboAssistantRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass

    def test_01_http_forwarded_proto_rejected_in_production(self):
        """Verifies cleartext HTTP forwarded by reverse proxy is rejected with HTTP 403 in production."""
        old_env = os.environ.get("APP_ENV")
        try:
            os.environ["APP_ENV"] = "production"
            req = urllib.request.Request(f"{self.base_url}/api/auth/environment")
            req.add_header("X-Forwarded-Proto", "http")

            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)

            self.assertEqual(ctx.exception.code, 403)
            data = json.loads(ctx.exception.read().decode())
            self.assertEqual(data.get("code"), "TLS_TRANSPORT_SECURITY_VIOLATION")
            self.assertIn("Insecure HTTP connections are prohibited", data.get("detail", ""))
        finally:
            if old_env is not None:
                os.environ["APP_ENV"] = old_env
            else:
                os.environ.pop("APP_ENV", None)

    def test_02_https_forwarded_proto_accepted_in_production(self):
        """Verifies verified HTTPS forwarded by reverse proxy is accepted in production."""
        old_env = os.environ.get("APP_ENV")
        try:
            os.environ["APP_ENV"] = "production"
            req = urllib.request.Request(f"{self.base_url}/api/auth/environment")
            req.add_header("X-Forwarded-Proto", "https")

            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertEqual(data.get("environment"), "production")
        finally:
            if old_env is not None:
                os.environ["APP_ENV"] = old_env
            else:
                os.environ.pop("APP_ENV", None)

    def test_03_enforce_https_mode_rejects_unencrypted_direct_requests(self):
        """Verifies ZONATA_ENFORCE_HTTPS=1 rejects cleartext connections."""
        old_env = os.environ.get("APP_ENV")
        old_enforce = os.environ.get("ZONATA_ENFORCE_HTTPS")
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["ZONATA_ENFORCE_HTTPS"] = "1"

            # Request without X-Forwarded-Proto on cleartext socket
            req = urllib.request.Request(f"{self.base_url}/api/auth/environment")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)

            self.assertEqual(ctx.exception.code, 403)
            data = json.loads(ctx.exception.read().decode())
            self.assertEqual(data.get("code"), "TLS_ENCRYPTION_MANDATORY")
        finally:
            if old_env is not None:
                os.environ["APP_ENV"] = old_env
            else:
                os.environ.pop("APP_ENV", None)
            if old_enforce is not None:
                os.environ["ZONATA_ENFORCE_HTTPS"] = old_enforce
            else:
                os.environ.pop("ZONATA_ENFORCE_HTTPS", None)

    def test_04_hsts_and_security_headers_present(self):
        """Verifies Strict-Transport-Security (HSTS) and critical browser defense headers are returned."""
        req = urllib.request.Request(f"{self.base_url}/readyz")
        with urllib.request.urlopen(req) as resp:
            headers = resp.headers
            self.assertIn("Strict-Transport-Security", headers)
            self.assertIn("max-age=31536000", headers["Strict-Transport-Security"])
            self.assertIn("includeSubDomains", headers["Strict-Transport-Security"])
            self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
            self.assertEqual(headers.get("X-Frame-Options"), "DENY")
            self.assertIn("Content-Security-Policy", headers)

    def test_05_nginx_ingress_configuration_syntax_and_hardening(self):
        """Verifies Nginx ingress configuration enforces HTTPS redirect and modern TLS ciphers."""
        self.assertTrue(os.path.exists(NGINX_CONF_PATH), f"Nginx config missing at {NGINX_CONF_PATH}")
        with open(NGINX_CONF_PATH, "r") as f:
            conf = f.read()

        # Check port 80 redirect to HTTPS
        self.assertIn("listen 80;", conf)
        self.assertIn("return 301 https://$host$request_uri;", conf)

        # Check port 443 SSL configuration
        self.assertIn("listen 443 ssl http2;", conf)
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", conf)
        self.assertIn("ssl_ciphers", conf)
        self.assertIn("Strict-Transport-Security", conf)

        # Check reverse proxy forwarding
        self.assertIn("proxy_set_header X-Forwarded-Proto https;", conf)
        self.assertIn("proxy_pass http://zonata_api_backend;", conf)

    def test_06_production_config_validates_tls_and_ingress(self):
        """Verifies ProductionConfigValidator validates TLS cert paths and proxy declarations."""
        # 1. Missing cert files raises ConfigurationError
        bad_tls_env = {
            "ZONATA_ENV": "production",
            "DEBUG": "false",
            "SECRET_VAULT_KEY": "0123456789abcdef0123456789abcdef",
            "APPLICATION_SIGNING_KEY": "fedcba9876543210fedcba9876543210",
            "SOVEREIGN_ROOT_KEY_ID": "key_root_prod_01",
            "ALLOWED_ORIGINS": "https://admin.enterprise.internal",
            "TLS_CERT_PATH": "/nonexistent/path/to/cert.crt",
            "TLS_KEY_PATH": "/nonexistent/path/to/key.key"
        }
        with self.assertRaises(ConfigurationError) as ctx:
            ProductionConfigValidator.validate_environment(bad_tls_env)
        self.assertIn("does not exist on disk", str(ctx.exception))

        # 2. ZONATA_REQUIRE_TLS=1 without certs or proxy raises ConfigurationError
        bad_req_tls = {
            "ZONATA_ENV": "production",
            "DEBUG": "false",
            "SECRET_VAULT_KEY": "0123456789abcdef0123456789abcdef",
            "APPLICATION_SIGNING_KEY": "fedcba9876543210fedcba9876543210",
            "SOVEREIGN_ROOT_KEY_ID": "key_root_prod_01",
            "ALLOWED_ORIGINS": "https://admin.enterprise.internal",
            "ZONATA_REQUIRE_TLS": "1"
        }
        with self.assertRaises(ConfigurationError) as ctx:
            ProductionConfigValidator.validate_environment(bad_req_tls)
        self.assertIn("TLS enforcement active", str(ctx.exception))

        # 3. ZONATA_BEHIND_INGRESS_PROXY=1 satisfies ingress gate
        good_proxy_env = dict(bad_req_tls)
        good_proxy_env["ZONATA_BEHIND_INGRESS_PROXY"] = "1"
        res = ProductionConfigValidator.validate_environment(good_proxy_env)
        self.assertTrue(res["valid"])


if __name__ == "__main__":
    unittest.main()
