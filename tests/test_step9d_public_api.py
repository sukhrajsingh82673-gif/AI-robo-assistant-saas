"""
Tests for Sub-Step 9D: Public API, Standard Webhooks, SSRF Protection, and SDKs (Rule 80).
"""

import os
import json
import time
import pytest
from core.webhooks.standard_webhooks import (
    StandardWebhooksSigner,
    SSRFValidator,
    WebhookSignatureError,
)
from core.api.public_v1 import PublicApiRouter
from core.api.portal import DeveloperPortal
from sdk.python.zonata_sdk.client import ZonataClient
from sdk.python.zonata_sdk.webhooks import WebhookVerifier as PythonWebhookVerifier

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep9dPublicApi:

    def test_openapi_v9_public_spec_is_valid_310(self):
        """Verify openapi_v9_public.json exists and adheres to OpenAPI 3.1.0."""
        spec_path = os.path.join(REPO_ROOT, "openapi_v9_public.json")
        assert os.path.isfile(spec_path), "openapi_v9_public.json must exist in root"

        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        assert spec.get("openapi") == "3.1.0"
        assert "paths" in spec
        paths = spec["paths"]
        assert "/plans" in paths
        assert "/usage" in paths
        assert "/webhooks" in paths
        assert "/tasks" in paths

        # Verify RFC 9457 Problem Details schema component
        schemas = spec.get("components", {}).get("schemas", {})
        assert "RFC9457Problem" in schemas
        assert "application/problem+json" in str(spec.get("components", {}).get("responses", {}))

    def test_standard_webhooks_signing_and_replay_protection(self):
        """Verify HMAC-SHA256 signature, 300s replay window, and rotation (ADR 0050, Rule 80)."""
        active_secret = "whsec_primary_secret_123456"
        prev_secret = "whsec_old_rotated_secret_789012"
        signer = StandardWebhooksSigner(active_secret=active_secret, previous_secret=prev_secret)

        msg_id = "msg_001"
        payload = '{"event": "task.completed", "task_id": "task_abc"}'
        t0 = 1700000000.0

        # 1. Sign and verify with active secret
        header = signer.generate_header(msg_id, payload, timestamp=int(t0))
        assert header.startswith("t=1700000000,v1=")
        assert signer.verify_header(msg_id, payload, header, current_time=t0)

        # 2. Tampered payload fails
        tampered_payload = '{"event": "task.completed", "task_id": "task_ATTACK"}'
        with pytest.raises(WebhookSignatureError, match="Signature mismatch"):
            signer.verify_header(msg_id, tampered_payload, header, current_time=t0)

        # 3. Replay protection: 350 seconds later fails
        with pytest.raises(WebhookSignatureError, match="Timestamp outside tolerance window"):
            signer.verify_header(msg_id, payload, header, current_time=t0 + 350)

        # 4. Rotation: Signed with previous secret still passes
        old_signer = StandardWebhooksSigner(active_secret=prev_secret)
        old_header = old_signer.generate_header(msg_id, payload, timestamp=int(t0))
        assert signer.verify_header(msg_id, payload, old_header, current_time=t0)

    def test_ssrf_validator_prohibits_private_and_metadata_addresses(self):
        """Verify SSRF mitigation blocks loopback, private ranges, and cloud metadata."""
        # Loopback URL
        safe1, reason1 = SSRFValidator.is_url_safe("http://127.0.0.1:8080/hook")
        assert not safe1
        assert "Prohibited scheme" in reason1

        safe1_https, reason1_https = SSRFValidator.is_url_safe("https://localhost/hook")
        assert not safe1_https
        assert "Prohibited hostname" in reason1_https

        # Cloud metadata
        safe2, reason2 = SSRFValidator.is_url_safe("https://metadata.google.internal/computeMetadata/v1")
        assert not safe2
        assert "Prohibited hostname" in reason2

    def test_public_api_router_dispatch_and_idempotency(self):
        """Verify PublicApiRouter operations, cursor pagination, and idempotency key deduplication."""
        router = PublicApiRouter()
        headers = {"X-Tenant-ID": "tenant_test", "X-Test-Mode": "1"}

        # 1. GET /plans
        st, hd, body = router.dispatch("GET", "/api/public/v1/plans", headers)
        assert st == 200
        data = json.loads(body)
        assert len(data["plans"]) >= 4

        # 2. POST /webhooks with Idempotency-Key
        post_headers = dict(headers)
        post_headers["Idempotency-Key"] = "idem_webhook_test_01"
        wh_body = json.dumps({"url": "https://example.com/webhook", "event_types": ["task.completed"]})

        st_post, hd_post, body_post = router.dispatch("POST", "/api/public/v1/webhooks", post_headers, wh_body)
        assert st_post == 201
        wh_data = json.loads(body_post)
        assert wh_data["url"] == "https://example.com/webhook"
        assert "secret" in wh_data

        # 3. Duplicate POST with same Idempotency-Key returns cached response
        st_dup, hd_dup, body_dup = router.dispatch("POST", "/api/public/v1/webhooks", post_headers, wh_body)
        assert st_dup == 201
        assert hd_dup.get("X-Cache-Lookup") == "HIT-IDEMPOTENT"
        assert body_dup == body_post

        # 4. GET /webhooks paginated
        st_list, _, body_list = router.dispatch("GET", "/api/public/v1/webhooks", headers)
        assert st_list == 200
        list_data = json.loads(body_list)
        assert len(list_data["items"]) >= 1

        # 5. Route 404 returns RFC 9457 Problem Details
        st_404, hd_404, body_404 = router.dispatch("GET", "/api/public/v1/nonexistent", headers)
        assert st_404 == 404
        assert hd_404["Content-Type"] == "application/problem+json"
        p404 = json.loads(body_404)
        assert p404["type"] == "https://zonata.ai/errors/not-found"
        assert p404["status"] == 404

    def test_sdk_helpers_and_portal(self):
        """Verify Python SDK client helpers and developer portal snippets."""
        # Developer Portal snippets
        snippets = DeveloperPortal.get_code_snippets("/tasks", "POST")
        assert "curl" in snippets
        assert "python" in snippets
        assert "typescript" in snippets
        assert "Idempotency-Key" in snippets["curl"]

        # Python SDK Client
        client = ZonataClient(api_key="sk_test_mock_key_123")
        res = client.create_task("Draft annual 10-K report")
        assert res["status"] == "ACCEPTED"
        assert "task_id" in res

        # Python SDK Webhook Verifier
        verifier = PythonWebhookVerifier(secret="whsec_test_secret_abc")
        ts = int(time.time())
        msg_id = "msg_test"
        payload = '{"event": "task.progress"}'
        signer = StandardWebhooksSigner(active_secret="whsec_test_secret_abc")
        header = signer.generate_header(msg_id, payload, timestamp=ts)
        assert verifier.verify(msg_id, payload, header)
