"""ZONATA Sovereign Core — Email Out Port & SMTP / Mailpit Adapter.

Implements OpenCode Step 1D.5:
- Port interface: EmailOutPort
- RealProvider: SMTPEmailProvider (SMTP send + Mailpit HTTP verification).
- Reality Ladder:
  - Accepted by SMTP server -> ACCEPTED_BY_PROVIDER (never DELIVERED).
  - Provider ref -> Message-ID from SMTP conversation.
  - In CI: Polls Mailpit HTTP API to confirm arrival by Message-ID -> DELIVERED.
    (Byte-for-byte body comparison is not yet asserted.)
- NotConfiguredProvider: When SMTP_HOST / SMTP_PORT missing.
- SandboxProvider: Test-only simulation when ZONATA_TEST_MODE=1.
"""

from __future__ import annotations
import email.utils
import hashlib
import json
import os
import smtplib
import time
import urllib.error
import urllib.request
import uuid
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
)


class EmailOutPort(Port):
    name = "email_out"
    capability = "email_out"

    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_addr: Optional[str] = None,
        **kwargs
    ) -> ProviderResult:
        raise NotImplementedError

    def verify_delivery_in_ci(
        self,
        message_id: str,
        mailpit_http_url: Optional[str] = None,
        timeout_seconds: float = 10.0
    ) -> ProviderResult:
        raise NotImplementedError


class SMTPEmailProvider(EmailOutPort):
    """Real SMTP email delivery adapter with Mailpit CI verification."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        mailpit_http_url: Optional[str] = None
    ):
        self.host = host or os.environ.get("SMTP_HOST", "localhost")
        self.port = port or int(os.environ.get("SMTP_PORT", "1025"))
        self.mailpit_url = (mailpit_http_url or os.environ.get("MAILPIT_URL", "http://localhost:8025")).rstrip("/")
        super().__init__(provider_name="smtp_relay", sandbox=False)

    def probe(self) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            with smtplib.SMTP(self.host, self.port, timeout=3.0) as server:
                code, resp = server.noop()
                lat = (time.perf_counter() - t0) * 1000.0
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=f"smtp_noop_{code}",
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={"smtp_code": code, "host": self.host, "port": self.port}
                )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"SMTP server unreachable: {str(e)}"
            )

    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_addr: Optional[str] = None,
        **kwargs
    ) -> ProviderResult:
        """Sends email via SMTP. Reality Ladder: returns ACCEPTED_BY_PROVIDER (never DELIVERED)."""
        t0 = time.perf_counter()
        sender = from_addr or os.environ.get("SMTP_FROM", "system@zonata.internal")
        domain = sender.split("@")[-1] if "@" in sender else "zonata.internal"
        message_id = f"<{uuid.uuid4().hex}@{domain}>"

        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg["Message-ID"] = message_id
        msg["Date"] = email.utils.formatdate(localtime=False, usegmt=True)
        msg.set_content(body)

        if attachments:
            for att in attachments:
                fname = att.get("filename", "attachment.bin")
                mtype = att.get("maintype", "application")
                stype = att.get("subtype", "octet-stream")
                data = att.get("data", b"")
                msg.add_attachment(data, maintype=mtype, subtype=stype, filename=fname)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10.0) as server:
                smtp_resp = server.send_message(msg)
                lat = (time.perf_counter() - t0) * 1000.0

            # Reality ladder: Accepted by provider, not delivered!
            return ProviderResult(
                status=PortStatus.ACCEPTED_BY_PROVIDER,
                provider=self.provider_name,
                provider_ref=message_id,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={
                    "message_id": message_id,
                    "recipients": to,
                    "subject": subject,
                    "attachments_count": len(attachments) if attachments else 0,
                    "accepted": True
                }
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"SMTP transmission failed: {str(e)}"
            )

    def verify_delivery_in_ci(
        self,
        message_id: str,
        mailpit_http_url: Optional[str] = None,
        timeout_seconds: float = 10.0
    ) -> ProviderResult:
        """Polls Mailpit HTTP API in CI to confirm delivery by Message-ID."""
        t0 = time.perf_counter()
        base_url = (mailpit_http_url or self.mailpit_url).rstrip("/")
        list_url = f"{base_url}/api/v1/messages"
        clean_msg_id = message_id.strip("<>")

        deadline = time.time() + timeout_seconds
        last_error = None

        while time.time() < deadline:
            try:
                req = urllib.request.Request(list_url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))

                messages = payload.get("messages", [])
                for m in messages:
                    # Match by Message-ID header or ID
                    m_headers = m.get("Snippet", "")
                    m_id_hdr = m.get("ID", "")
                    if clean_msg_id in m_id_hdr or clean_msg_id in json.dumps(m):
                        # Message verified delivered in Mailpit sink!
                        lat = (time.perf_counter() - t0) * 1000.0
                        return ProviderResult(
                            status=PortStatus.OK,
                            provider="mailpit_verified",
                            provider_ref=m.get("ID", message_id),
                            sandbox=False,
                            latency_ms=lat,
                            cost=0.0,
                            metadata={
                                "message_id": message_id,
                                "mailpit_id": m.get("ID"),
                                "verified_in_sink": True,
                                "status": "DELIVERED"
                            }
                        )
            except Exception as e:
                last_error = str(e)

            time.sleep(0.3)

        lat = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="mailpit_verified",
            provider_ref=None,
            latency_ms=lat,
            error=f"Delivery confirmation timeout in Mailpit sink: {last_error or 'Message not found'}"
        )


class NotConfiguredEmailProvider(EmailOutPort):
    def __init__(self, reason: str = "SMTP_HOST / SMTP_PORT not configured"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return NotConfiguredProvider("email_out", self.reason).probe()

    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_addr: Optional[str] = None,
        **kwargs
    ) -> ProviderResult:
        return self.probe()

    def verify_delivery_in_ci(
        self,
        message_id: str,
        mailpit_http_url: Optional[str] = None,
        timeout_seconds: float = 10.0
    ) -> ProviderResult:
        return self.probe()


class SandboxEmailProvider(EmailOutPort):
    """Test-only simulation active when ZONATA_TEST_MODE=1."""
    def __init__(self):
        super().__init__(provider_name="sandbox_smtp", sandbox=True)
        self.outbox: List[Dict[str, Any]] = []

    def _is_test(self) -> bool:
        return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")

    def probe(self) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_smtp_sink",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"sandbox": True}
        )

    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_addr: Optional[str] = None,
        **kwargs
    ) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")

        msg_id = f"<sandbox_{uuid.uuid4().hex[:12]}@zonata.test>"
        item = {
            "message_id": msg_id,
            "to": to,
            "subject": subject,
            "body": body,
            "attachments": attachments or [],
            "from": from_addr or "sandbox@zonata.test",
            "time": time.time()
        }
        self.outbox.append(item)
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=msg_id,
            sandbox=True,
            latency_ms=0.2,
            cost=0.0,
            metadata={"message_id": msg_id, "recipients": to, "accepted": True}
        )

    def verify_delivery_in_ci(
        self,
        message_id: str,
        mailpit_http_url: Optional[str] = None,
        timeout_seconds: float = 10.0
    ) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")

        found = next((m for m in self.outbox if m["message_id"] == message_id), None)
        if found:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.provider_name,
                provider_ref=message_id,
                sandbox=True,
                latency_ms=0.1,
                cost=0.0,
                metadata={"delivered": True}
            )
        return ProviderResult(
            status=PortStatus.FAILED,
            provider=self.provider_name,
            provider_ref=None,
            error=f"Message {message_id} not found in sandbox outbox"
        )


def resolve_email_provider() -> EmailOutPort:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT")
    if smtp_host and smtp_port:
        return SMTPEmailProvider(smtp_host, int(smtp_port))
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    if is_test:
        return SandboxEmailProvider()
    return NotConfiguredEmailProvider()
