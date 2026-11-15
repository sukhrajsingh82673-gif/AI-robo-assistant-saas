"""Honest email delivery for company exports.

There is no transactional email provider in the dependency set. This adapter
uses the SMTP settings that already exist in the settings catalogue. If no host
is configured it returns ``NOT_CONFIGURED``; it never reports a send that did
not happen.

Credentials are read from environment variables (``ZONATA_SMTP_USERNAME`` and
``ZONATA_SMTP_PASSWORD``) so they never enter settings JSON, audit events,
logs, or the export itself. A relay that allows unauthenticated submission from
the deployment host works with both variables empty.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict, Optional


def _setting(tenant_id: str, company_id: str, key: str, default: Any) -> Any:
    try:
        from core.settings_service import settings_service

        return settings_service.get_effective_setting(tenant_id, company_id, key, default)
    except Exception:
        return default


class ExportEmailAdapter:
    """SMTP delivery for a single export, with an honest unavailable state."""

    def send(
        self,
        *,
        tenant_id: str,
        company_id: str,
        company_name: str,
        recipient: str,
        filename: str,
        content: bytes,
        content_type: str,
        purge_after: Optional[float] = None,
        recovery_days: int = 7,
    ) -> Dict[str, Any]:
        host = str(_setting(tenant_id, company_id, "comm_smtp_server", "") or "").strip()
        if not host:
            return {
                "status": "NOT_CONFIGURED",
                "detail": "No SMTP server is configured. Use the in-app download instead.",
            }
        try:
            port = int(_setting(tenant_id, company_id, "comm_smtp_port", 587) or 587)
        except (TypeError, ValueError):
            port = 587
        sender = str(
            _setting(tenant_id, company_id, "comm_sender_identity", "dispatch@zonata.internal")
            or "dispatch@zonata.internal"
        ).strip()
        tls = bool(_setting(tenant_id, company_id, "comm_tls_enforced", True))

        if len(content) > 20 * 1024 * 1024:
            return {
                "status": "TOO_LARGE",
                "detail": "The export is larger than 20 MB; use the in-app download instead.",
            }

        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = f"Your ZONATA export for {company_name}"
        body = [
            f"Hello,",
            "",
            f"Attached is the export of {company_name} before deletion.",
            f"Recovery window: {recovery_days} day(s).",
        ]
        if recovery_days == 0:
            body.append("The recovery window is set to zero, so deletion can complete immediately.")
        else:
            body.append("You can cancel the deletion from the company overview until the recovery window ends.")
        body.extend(
            [
                "",
                "If you did not request this deletion, cancel it in ZONATA immediately and treat this file as sensitive.",
                "",
                "ZONATA",
            ]
        )
        message.set_content("\n".join(body))
        maintype, subtype = (content_type.split("/", 1) + ["octet-stream"])[:2]
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

        username = os.environ.get("ZONATA_SMTP_USERNAME", "").strip()
        password = os.environ.get("ZONATA_SMTP_PASSWORD", "")
        try:
            if port == 465:
                context = ssl.create_default_context() if tls else None
                with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
                    if username:
                        server.login(username, password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(host, port, timeout=20) as server:
                    if tls:
                        server.starttls(context=ssl.create_default_context())
                    if username:
                        server.login(username, password)
                    server.send_message(message)
            return {"status": "SENT", "detail": "The export was emailed."}
        except Exception as exc:
            # Never put the SMTP response, host, or credentials into the audit
            # trail or the API response.
            return {
                "status": "FAILED",
                "detail": "The email could not be sent. Use the in-app download instead.",
                "error_type": type(exc).__name__,
            }


export_email_adapter = ExportEmailAdapter()
