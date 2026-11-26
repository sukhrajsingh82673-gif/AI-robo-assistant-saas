"""
Standard Webhooks Verification Helper for Python.
"""

import hmac
import hashlib
import time


class WebhookVerifier:
    """Verifies incoming Standard Webhooks signatures."""

    def __init__(self, secret: str, tolerance_seconds: int = 300):
        self.secret = secret
        self.tolerance = tolerance_seconds

    def verify(self, msg_id: str, payload: str, signature_header: str) -> bool:
        pairs = dict(item.split("=", 1) for item in signature_header.strip().split(",") if "=" in item)
        if "t" not in pairs or "v1" not in pairs:
            return False

        ts = int(pairs["t"])
        if abs(time.time() - ts) > self.tolerance:
            return False

        to_sign = f"{msg_id}.{ts}.{payload}"
        expected = hmac.new(self.secret.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(pairs["v1"], expected)
