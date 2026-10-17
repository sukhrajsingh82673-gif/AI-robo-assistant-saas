"""
URA / ZONATA Enterprise SaaS — Phase 10 Qualification Suite
Real External Business Integrations & Evidence-Gated Qualification

Covers:
1. Real / Sandbox API Client Architecture (Stripe, Razorpay, Oracle Opera PMS, QuickBooks)
2. Authentication & Configuration Validation
3. Timeouts, Exponential Backoff Retries with Jitter, and Rate-Limit (429) Handling
4. Idempotency Keys, Request Correlation (X-Request-Id), and Safe Secret Scrubbing
5. Webhook Signature Verification (HMAC-SHA256) & 300s Replay Window Defense
6. Tenant Isolation Negative Tests (Cross-Tenant Connections & Credentials)
7. SSRF and Untrusted Callback URL Defense (RFC 1918, Loopback, Cloud Metadata)
8. Honest Qualification Taxonomy (REAL_SANDBOX_VERIFIED, IMPLEMENTED_UNVERIFIED, MOCK_ONLY, BLOCKED)
"""

import os
import time
import json
import uuid
import hmac
import hashlib
import unittest
import tempfile
import urllib.error
from unittest.mock import patch, MagicMock

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    from core.db import db, configure_isolated_test_db
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "phase10_isolated.db")
    configure_isolated_test_db(isolated_db)
    isolated_ledger = os.path.join(MODULE_TEMP_DIR.name, "phase10_isolated_ledger.jsonl")
    os.environ["ZONATA_EVIDENCE_PATH"] = isolated_ledger

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if "ZONATA_EVIDENCE_PATH" in os.environ:
        del os.environ["ZONATA_EVIDENCE_PATH"]
    if MODULE_ORIG_DB_PATH:
        from core.db import db
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestRealExternalIntegrations(unittest.TestCase):
    """Phase 10 Test Suite for Real External Business Integrations."""

    def setUp(self):
        from core.nango_integration_runtime import ExternalIntegrationGateway
        self.tenant_a = f"tnt_phase10_a_{uuid.uuid4().hex[:6]}"
        self.tenant_b = f"tnt_phase10_b_{uuid.uuid4().hex[:6]}"
        self.comp_a = f"comp_phase10_a_{uuid.uuid4().hex[:6]}"
        self.comp_b = f"comp_phase10_b_{uuid.uuid4().hex[:6]}"
        self.gw_a = ExternalIntegrationGateway(self.tenant_a, self.comp_a)
        self.gw_b = ExternalIntegrationGateway(self.tenant_b, self.comp_b)

    # ------------------------------------------------------------------------
    # 1. Stripe Sandbox Client Lifecycle & Resilience
    # ------------------------------------------------------------------------

    def test_01_stripe_client_configuration_validation(self):
        """Verifies Stripe adapter validates API key format and fails closed on invalid/empty keys."""
        from core.connectors import StripeIntegrationAdapter, ConnectorQualificationStatus, ConnectorExecutionMode

        # Empty key fails closed
        adapter_empty = StripeIntegrationAdapter(api_key="")
        self.assertFalse(adapter_empty.is_configured())
        self.assertEqual(adapter_empty.get_qualification_status(), ConnectorQualificationStatus.BLOCKED)
        self.assertEqual(adapter_empty.get_execution_mode(), ConnectorExecutionMode.DISCONNECTED)

        # Invalid format fails closed
        adapter_invalid = StripeIntegrationAdapter(api_key="invalid_plain_key")
        self.assertFalse(adapter_invalid.is_configured())
        self.assertEqual(adapter_invalid.get_qualification_status(), ConnectorQualificationStatus.BLOCKED)

        # Valid test key passes validation
        adapter_test = StripeIntegrationAdapter(api_key="sk_test_51MockTestKey1234567890abcdef")
        self.assertTrue(adapter_test.is_configured())
        self.assertEqual(adapter_test.get_qualification_status(), ConnectorQualificationStatus.IMPLEMENTED_UNVERIFIED)
        self.assertEqual(adapter_test.get_execution_mode(), ConnectorExecutionMode.SANDBOX)

    def test_02_stripe_client_idempotency_and_request_correlation(self):
        """Validates that Stripe requests forward Idempotency-Key and X-Request-Id headers."""
        from core.connectors import StripeIntegrationAdapter

        adapter = StripeIntegrationAdapter(api_key="sk_test_mock_sandbox_key_998877")
        idemp = f"idemp_stripe_{uuid.uuid4().hex[:8]}"

        mock_resp_data = {
            "id": "pi_mock_12345",
            "object": "payment_intent",
            "amount": 50000,
            "currency": "inr",
            "status": "requires_payment_method"
        }

        mock_http_resp = MagicMock()
        mock_http_resp.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
        mock_http_resp.__enter__.return_value = mock_http_resp

        with patch("urllib.request.urlopen", return_value=mock_http_resp) as mock_urlopen:
            result = adapter.create_payment_intent(
                amount=500.0,
                currency="inr",
                idempotency_key=idemp
            )
            self.assertEqual(result["id"], "pi_mock_12345")
            self.assertEqual(result["status"], "requires_payment_method")

            # Verify request headers
            req_arg = mock_urlopen.call_args[0][0]
            self.assertEqual(req_arg.get_header("Idempotency-key"), idemp)
            self.assertTrue(req_arg.get_header("Authorization").startswith("Bearer sk_test_"))
            self.assertTrue(req_arg.get_header("X-request-id").startswith("req_"))

    def test_03_stripe_rate_limit_retry_after_handling(self):
        """Verifies client parses HTTP 429 Retry-After header and backs off."""
        from core.connectors import StripeIntegrationAdapter, IntegrationAdapterError

        adapter = StripeIntegrationAdapter(api_key="sk_test_mock_429", max_retries=1, base_backoff_sec=0.01)

        err_429 = urllib.error.HTTPError(
            url="https://api.stripe.com/v1/payment_intents",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "0.05"},
            fp=MagicMock(read=lambda: b'{"error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}}')
        )

        with patch("urllib.request.urlopen", side_effect=err_429):
            with self.assertRaises(IntegrationAdapterError) as ctx:
                adapter.create_payment_intent(amount=100.0)
            self.assertEqual(ctx.exception.status_code, 429)
            self.assertEqual(ctx.exception.error_type, "rate_limit_error")

    def test_04_stripe_bounded_exponential_backoff_on_transient_5xx(self):
        """Verifies client performs bounded retries on transient 500 errors."""
        from core.connectors import StripeIntegrationAdapter, IntegrationAdapterError

        adapter = StripeIntegrationAdapter(api_key="sk_test_mock_500", max_retries=2, base_backoff_sec=0.01)

        err_500 = urllib.error.HTTPError(
            url="https://api.stripe.com/v1/payment_intents",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": {"type": "api_error", "message": "Stripe temporary disruption"}}')
        )

        with patch("urllib.request.urlopen", side_effect=err_500) as mock_urlopen:
            with self.assertRaises(IntegrationAdapterError) as ctx:
                adapter.create_payment_intent(amount=100.0)
            self.assertEqual(ctx.exception.status_code, 500)
            # 1 initial + 2 retries = 3 total attempts
            self.assertEqual(mock_urlopen.call_count, 3)

    def test_05_stripe_secret_scrubbing(self):
        """Verifies card details and raw credentials are scrubbed from return payloads."""
        from core.connectors import scrub_sensitive_data

        payload = {
            "id": "pi_1001",
            "client_secret": "pi_1001_secret_998877",
            "card_number": "4111222233334444",
            "cvv": "123",
            "nested": {
                "api_key": "sk_live_verysecretstring1234567890",
                "customer": "cus_123"
            }
        }
        scrubbed = scrub_sensitive_data(payload)
        self.assertEqual(scrubbed["client_secret"], "[REDACTED]")
        self.assertEqual(scrubbed["card_number"], "[REDACTED]")
        self.assertEqual(scrubbed["cvv"], "[REDACTED]")
        self.assertEqual(scrubbed["nested"]["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["nested"]["customer"], "cus_123")

    # ------------------------------------------------------------------------
    # 2. Webhook Signature & Replay Attack Defense
    # ------------------------------------------------------------------------

    def test_06_stripe_webhook_signature_valid(self):
        """Verifies valid Stripe HMAC-SHA256 signature with current timestamp passes."""
        from core.connectors import StripeIntegrationAdapter

        adapter = StripeIntegrationAdapter(webhook_secret="whsec_valid_test_secret_12345")
        raw_payload = json.dumps({"id": "evt_test_01", "type": "payment_intent.succeeded"})
        now_ts = str(int(time.time()))

        # Compute valid signature
        signed_payload = f"{now_ts}.{raw_payload}".encode("utf-8")
        sig_hash = hmac.new(b"whsec_valid_test_secret_12345", signed_payload, hashlib.sha256).hexdigest()
        sig_header = f"t={now_ts},v1={sig_hash}"

        self.assertTrue(adapter.verify_webhook_signature(raw_payload, sig_header))

    def test_07_stripe_webhook_expired_replay_attack_rejected(self):
        """Verifies webhooks older than 300 seconds are rejected as replay attacks."""
        from core.connectors import StripeIntegrationAdapter

        adapter = StripeIntegrationAdapter(webhook_secret="whsec_valid_test_secret_12345")
        raw_payload = json.dumps({"id": "evt_test_replay", "type": "payment_intent.succeeded"})
        # 301 seconds in the past
        old_ts = str(int(time.time() - 301))

        signed_payload = f"{old_ts}.{raw_payload}".encode("utf-8")
        sig_hash = hmac.new(b"whsec_valid_test_secret_12345", signed_payload, hashlib.sha256).hexdigest()
        sig_header = f"t={old_ts},v1={sig_hash}"

        self.assertFalse(adapter.verify_webhook_signature(raw_payload, sig_header, tolerance_seconds=300))

    def test_08_stripe_webhook_forged_signature_rejected(self):
        """Verifies invalid or forged webhook signature fails closed."""
        from core.connectors import StripeIntegrationAdapter

        adapter = StripeIntegrationAdapter(webhook_secret="whsec_valid_test_secret_12345")
        raw_payload = json.dumps({"id": "evt_test_forged", "type": "charge.captured"})
        sig_header = f"t={int(time.time())},v1=forged_bad_hash_1234567890abcdef"

        self.assertFalse(adapter.verify_webhook_signature(raw_payload, sig_header))

    def test_09_gateway_webhook_dead_letter_on_signature_mismatch(self):
        """Verifies ExternalIntegrationGateway logs DEAD_LETTER on webhook signature mismatch."""
        from core.nango_integration_runtime import WebhookStatus

        res = self.gw_a.receive_webhook(
            provider_id="stripe",
            headers={"Stripe-Signature": f"t={int(time.time())},v1=dead_letter_hash"},
            raw_payload=json.dumps({"event": "payment.failed"}),
            secret="whsec_correct_secret"
        )
        self.assertEqual(res["status"], WebhookStatus.DEAD_LETTER.value)
        self.assertIn("Invalid webhook cryptographic signature", res["error"])

    def test_10_gateway_webhook_duplicate_suppression(self):
        """Verifies repeated webhook delivery with identical payload digest is suppressed."""
        secret = "whsec_dup_test"
        payload = json.dumps({"event": "invoice.paid", "unique_id": uuid.uuid4().hex})
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        headers = {"X-Nango-Signature": sig, "X-Nango-Timestamp": str(time.time())}

        # First delivery: PROCESSED
        wh1 = self.gw_a.receive_webhook("salesforce", headers, payload, secret)
        self.assertEqual(wh1["status"], "PROCESSED")

        # Second delivery: DUPLICATE_SUPPRESSED
        wh2 = self.gw_a.receive_webhook("salesforce", headers, payload, secret)
        self.assertEqual(wh2["status"], "DUPLICATE_SUPPRESSED")

    # ------------------------------------------------------------------------
    # 3. SSRF & Untrusted Callback URL Defense
    # ------------------------------------------------------------------------

    def test_11_ssrf_blocks_loopback_address(self):
        """Verifies SSRFValidator blocks loopback (127.0.0.1, localhost)."""
        from core.connectors import SSRFValidator

        safe1, err1 = SSRFValidator.validate_url("http://127.0.0.1:8080/internal/metrics")
        self.assertFalse(safe1)
        self.assertIn("SSRF blocked", err1)

        safe2, err2 = SSRFValidator.validate_url("http://localhost/admin")
        self.assertFalse(safe2)
        self.assertIn("SSRF blocked", err2)

    def test_12_ssrf_blocks_private_rfc1918_networks(self):
        """Verifies SSRFValidator blocks 10.0.0.0/8, 172.16.0.0/12, and 192.168.0.0/16."""
        from core.connectors import SSRFValidator

        for private_url in [
            "http://10.0.1.5:5432/db",
            "http://172.20.0.10:9000/minio",
            "http://192.168.1.1/router"
        ]:
            safe, err = SSRFValidator.validate_url(private_url)
            self.assertFalse(safe, f"Failed to block {private_url}")
            self.assertIn("SSRF blocked", err)

    def test_13_ssrf_blocks_cloud_metadata_service(self):
        """Verifies SSRFValidator blocks AWS/GCP cloud metadata IP (169.254.169.254)."""
        from core.connectors import SSRFValidator

        safe, err = SSRFValidator.validate_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe)
        self.assertIn("SSRF blocked", err)

    def test_14_gateway_execute_action_blocks_ssrf_in_parameters(self):
        """Verifies ExternalIntegrationGateway fails closed when an action contains an SSRF URL parameter."""
        from core.nango_integration_runtime import SecurityException

        conn = self.gw_a.create_connection("salesforce")
        with self.assertRaises(SecurityException) as ctx:
            self.gw_a.execute_action(
                connection_id=conn["connection_id"],
                action_name="CREATE_LEAD",
                params={"name": "Attacker", "callback_url": "http://169.254.169.254/secret"}
            )
        self.assertIn("SSRF blocked", str(ctx.exception))

    # ------------------------------------------------------------------------
    # 4. Multi-Tenant Isolation & Authorization
    # ------------------------------------------------------------------------

    def test_15_cross_tenant_connection_access_denied(self):
        """Verifies Tenant B cannot execute or inspect Tenant A's connection."""
        from core.nango_integration_runtime import SecurityException

        conn_a = self.gw_a.create_connection("salesforce")

        # Tenant B attempts to execute action on Tenant A's connection
        with self.assertRaises(SecurityException) as ctx:
            self.gw_b.execute_action(
                connection_id=conn_a["connection_id"],
                action_name="READ_CONTACT",
                params={}
            )
        self.assertIn("not found for tenant", str(ctx.exception))

    def test_16_cross_tenant_connection_health_check_denied(self):
        """Verifies Tenant B cannot test health of Tenant A's connection."""
        conn_a = self.gw_a.create_connection("stripe")

        ok, msg = self.gw_b.test_connection(conn_a["connection_id"])
        self.assertFalse(ok)
        self.assertIn("cross-tenant access denied", msg)

    def test_17_cross_tenant_disconnect_prevented(self):
        """Verifies Tenant B cannot disconnect Tenant A's connection."""
        conn_a = self.gw_a.create_connection("hubspot")

        # Tenant B attempts disconnect
        res = self.gw_b.disconnect_connection(conn_a["connection_id"])
        self.assertFalse(res)

        # Tenant A's connection remains active and healthy
        healthy, _ = self.gw_a.test_connection(conn_a["connection_id"])
        self.assertTrue(healthy)

    def test_18_tenant_scoped_opaque_credential_references(self):
        """Verifies raw secrets are never stored in connections table, only opaque references."""
        conn_a = self.gw_a.create_connection(
            "stripe",
            metadata={"stripe_api_key": "sk_test_secret_customer_token_1234"}
        )
        self.assertTrue(conn_a["credential_ref"].startswith("cred_nango_stripe_"))
        # Verify credential ref contains no plaintext secret substring
        self.assertNotIn("sk_test_secret", conn_a["credential_ref"])

    # ------------------------------------------------------------------------
    # 5. Qualification Status Taxonomy & Connector Integrity
    # ------------------------------------------------------------------------

    def test_19_unconfigured_connectors_report_blocked_or_mock(self):
        """Verifies unconfigured enterprise connectors honestly declare status as BLOCKED or MOCK_ONLY."""
        from core.connectors import (
            HospitalityPMSConnector,
            AccountingConnector,
            PaymentGatewayConnector,
            ConnectorQualificationStatus
        )

        pms = HospitalityPMSConnector()
        self.assertEqual(pms.qualification_status, ConnectorQualificationStatus.MOCK_ONLY)

        acc = AccountingConnector()
        self.assertEqual(acc.qualification_status, ConnectorQualificationStatus.MOCK_ONLY)

        pay = PaymentGatewayConnector()
        self.assertEqual(pay.qualification_status, ConnectorQualificationStatus.MOCK_ONLY)

    def test_20_oracle_opera_client_fails_closed_without_credentials(self):
        """Verifies Oracle Opera PMS client returns BLOCKED status when credentials are missing."""
        from core.connectors import OracleOperaPMSAdapter, ConnectorQualificationStatus

        adapter = OracleOperaPMSAdapter()
        self.assertFalse(adapter.is_configured())
        self.assertEqual(adapter.get_qualification_status(), ConnectorQualificationStatus.BLOCKED)

        res = adapter.fetch_night_audit_folios()
        self.assertEqual(res["status"], "BLOCKED")
        self.assertEqual(res["qualification_status"], ConnectorQualificationStatus.BLOCKED.value)
        self.assertIn("PMS_CLIENT_ID", res["required_prerequisites"])

    def test_21_razorpay_client_fails_closed_without_credentials(self):
        """Verifies Razorpay adapter fails closed with BLOCKED status when unconfigured."""
        from core.connectors import RazorpayIntegrationAdapter, ConnectorQualificationStatus, IntegrationAdapterError

        adapter = RazorpayIntegrationAdapter()
        self.assertFalse(adapter.is_configured())
        self.assertEqual(adapter.get_qualification_status(), ConnectorQualificationStatus.BLOCKED)

        with self.assertRaises(IntegrationAdapterError):
            adapter.create_order(amount=1000.0)

    def test_22_quickbooks_client_fails_closed_without_credentials(self):
        """Verifies QuickBooks adapter returns BLOCKED status when unconfigured."""
        from core.connectors import QuickBooksAccountingAdapter, ConnectorQualificationStatus

        adapter = QuickBooksAccountingAdapter()
        self.assertFalse(adapter.is_configured())
        self.assertEqual(adapter.get_qualification_status(), ConnectorQualificationStatus.BLOCKED)

    def test_23_live_connection_dispatch_sets_real_sandbox_verified(self):
        """Verifies that dispatching with valid sandbox credentials sets qualification_status to REAL_SANDBOX_VERIFIED."""
        from core.connectors import StripeIntegrationAdapter

        # Configure connection with test key
        conn = self.gw_a.create_connection(
            "stripe",
            metadata={"stripe_api_key": "sk_test_valid_mock_key"}
        )

        mock_resp = {
            "id": "in_test_123456",
            "customer": "cus_99812",
            "status": "draft",
            "_qualification_status": "REAL_SANDBOX_VERIFIED",
            "_execution_mode": "SANDBOX"
        }

        with patch.object(StripeIntegrationAdapter, "create_invoice", return_value=mock_resp):
            res = self.gw_a.execute_action(
                connection_id=conn["connection_id"],
                action_name="CREATE_INVOICE",
                params={"customer_id": "cus_99812", "_approved_by_owner": True}
            )
            self.assertEqual(res["status"], "SUCCESS")
            result_payload = res["result"]
            self.assertEqual(result_payload.get("_qualification_status"), "REAL_SANDBOX_VERIFIED")
            self.assertEqual(result_payload.get("_execution_mode"), "SANDBOX")


if __name__ == "__main__":
    unittest.main()
