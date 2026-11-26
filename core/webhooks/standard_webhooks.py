"""
Standard Webhooks Delivery, HMAC-SHA256 Signing, Replay Prevention, and SSRF Mitigation.
"""

import hmac
import hashlib
import time
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional, List


class WebhookSignatureError(Exception):
    """Raised when webhook signature verification fails."""
    pass


class StandardWebhooksSigner:
    """
    Implements the Standard Webhooks cryptographic signing and verification specification.
    Header format: webhook-signature: t=1700000000,v1=sha256_hex
    Supports secret rotation with active and previous fallback secret.
    """

    TOLERANCE_SECONDS = 300  # 5 minutes

    def __init__(self, active_secret: str, previous_secret: Optional[str] = None):
        if not active_secret:
            raise ValueError("active_secret must be provided")
        self.active_secret = active_secret
        self.previous_secret = previous_secret

    def _sign_payload(self, msg_id: str, timestamp: int, payload: str, secret: str) -> str:
        # Standard Webhooks signature payload format: "{msg_id}.{timestamp}.{payload}"
        to_sign = f"{msg_id}.{timestamp}.{payload}"
        return hmac.new(secret.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    def generate_header(self, msg_id: str, payload: str, timestamp: Optional[int] = None) -> str:
        ts = int(timestamp if timestamp is not None else time.time())
        signature = self._sign_payload(msg_id, ts, payload, self.active_secret)
        return f"t={ts},v1={signature}"

    def verify_header(
        self,
        msg_id: str,
        payload: str,
        header_value: str,
        current_time: Optional[float] = None,
    ) -> bool:
        """
        Verifies signature header. Checks timestamp tolerance and compares against
        active_secret and previous_secret (for rotation).
        """
        now = current_time if current_time is not None else time.time()

        pairs = dict(item.split("=", 1) for item in header_value.strip().split(",") if "=" in item)
        if "t" not in pairs or "v1" not in pairs:
            raise WebhookSignatureError("Invalid signature header format; missing 't' or 'v1'")

        try:
            ts = int(pairs["t"])
        except ValueError:
            raise WebhookSignatureError("Invalid timestamp in signature header")

        # Replay prevention
        if abs(now - ts) > self.TOLERANCE_SECONDS:
            raise WebhookSignatureError(f"Timestamp outside tolerance window ({abs(now - ts):.1f}s > {self.TOLERANCE_SECONDS}s)")

        expected_active = self._sign_payload(msg_id, ts, payload, self.active_secret)
        if hmac.compare_digest(pairs["v1"], expected_active):
            return True

        if self.previous_secret:
            expected_prev = self._sign_payload(msg_id, ts, payload, self.previous_secret)
            if hmac.compare_digest(pairs["v1"], expected_prev):
                return True

        raise WebhookSignatureError("Signature mismatch")


class SSRFValidator:
    """
    Validates webhook destination URLs to prevent Server-Side Request Forgery.
    Blocks loopback, RFC 1918 private ranges, link-local, and cloud metadata endpoints.
    """

    PROHIBITED_HOSTS = {
        "metadata.google.internal",
        "instance-data",
        "localhost",
    }

    @classmethod
    def is_url_safe(cls, url: str, allow_private_for_tests: bool = False) -> Tuple[bool, str]:
        if allow_private_for_tests:
            return True, "Safe for testing."

        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False, f"Prohibited scheme: '{parsed.scheme}'. Only HTTPS endpoints are permitted."

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: missing hostname."

        if hostname.lower() in cls.PROHIBITED_HOSTS:
            return False, f"Prohibited hostname: '{hostname}'."

        # Resolve IP addresses
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False, f"Failed to resolve hostname: '{hostname}'."

        for entry in addr_info:
            ip_str = entry[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            # Block private, loopback, link-local, reserved
            if ip_obj.is_loopback:
                return False, f"Destination resolves to loopback IP: {ip_str}."
            if ip_obj.is_private:
                return False, f"Destination resolves to private RFC 1918 IP: {ip_str}."
            if ip_obj.is_link_local:
                return False, f"Destination resolves to link-local IP: {ip_str}."
            if ip_obj.is_multicast:
                return False, f"Destination resolves to multicast IP: {ip_str}."
            if ip_obj.is_reserved:
                return False, f"Destination resolves to reserved IP: {ip_str}."
            # Explicit AWS/GCP metadata IP check
            if ip_str == "169.254.169.254":
                return False, "Destination resolves to cloud metadata IP."

        return True, "Destination URL is safe."
