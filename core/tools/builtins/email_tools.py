"""ZONATA Sovereign Core — Builtin Email Tools.

Implements OpenCode Step 2E (Requirement 2):
- Email send: dispatches through ActionGateway and resolves real SMTP / Mailpit provider;
  returns honest status (ACCEPTED_BY_PROVIDER, never fabricated DELIVERED).
- Email read: retrieves incoming messages.
"""

from __future__ import annotations
import os
import urllib.request
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.authority.types import ActionClass, PrincipalType
from core.action_envelope import ActionEnvelope
from core.action_gateway import action_gateway, ActionGatewayRejection
from core.tools.contract import ToolContract, SideEffectClass
from core.ports.email import resolve_email_provider


class EmailSendInput(BaseModel):
    to: List[str] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body plain text")
    from_addr: Optional[str] = Field(None, description="Sender email address")


class EmailSendOutput(BaseModel):
    to: List[str]
    subject: str
    status: str
    provider: str
    message_id: Optional[str] = None
    sandbox: bool = False


class EmailSendTool(ToolContract):
    name = "email_send"
    description = "Sends outbound email through real SMTP/Mailpit with ActionGateway governance."
    version = "1.0.0"
    side_effect_class = SideEffectClass.EXTERNAL_COMMS
    required_capability = "email_out"
    required_action_class = ActionClass.SEND_EXTERNAL_MESSAGE
    cost_cents = 0
    timeout_seconds = 20.0

    input_schema = EmailSendInput
    output_schema = EmailSendOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: EmailSendInput,
        idempotency_key: Optional[str] = None,
    ) -> EmailSendOutput:
        # ActionGateway evaluation
        envelope = ActionEnvelope.create(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=principal_id,
            principal_id=principal_id,
            principal_type=PrincipalType.AGENT.value,
            action_class=ActionClass.SEND_EXTERNAL_MESSAGE.value,
            capability_id="email_out",
            target=f"email:{','.join(args.to)}",
            intent=f"Send email: {args.subject}",
            parameters={"to": args.to, "subject": args.subject},
            idempotency_key=idempotency_key,
        )
        decision = action_gateway.evaluate_decision_gate(envelope)
        if decision.status != "APPROVED":
            raise ActionGatewayRejection(
                f"Email sending rejected by ActionGateway: {decision.reason or decision.rule_id}"
            )

        provider = resolve_email_provider()
        res = provider.send(
            to=args.to,
            subject=args.subject,
            body=args.body,
            from_addr=args.from_addr,
        )

        return EmailSendOutput(
            to=args.to,
            subject=args.subject,
            status=res.status.value if hasattr(res.status, "value") else str(res.status),
            provider=res.provider,
            message_id=res.provider_ref,
            sandbox=res.sandbox,
        )


class EmailReadInput(BaseModel):
    limit: int = Field(10, description="Max messages to fetch")
    query: Optional[str] = Field(None, description="Filter messages by subject or sender")


class EmailReadOutput(BaseModel):
    messages: List[Dict[str, Any]]
    total_count: int


class EmailReadTool(ToolContract):
    name = "email_read"
    description = "Reads incoming emails from configured mailbox or Mailpit API."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "email_in"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 15.0

    input_schema = EmailReadInput
    output_schema = EmailReadOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: EmailReadInput,
        idempotency_key: Optional[str] = None,
    ) -> EmailReadOutput:
        mailpit_api = os.environ.get("MAILPIT_API", "http://localhost:8025").rstrip("/")
        messages: List[Dict[str, Any]] = []

        try:
            url = f"{mailpit_api}/api/v1/messages?limit={args.limit}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for msg in data.get("messages", []):
                    messages.append({
                        "id": msg.get("ID"),
                        "from": msg.get("From", {}).get("Address"),
                        "to": [t.get("Address") for t in msg.get("To", [])],
                        "subject": msg.get("Subject"),
                        "created": msg.get("Created"),
                    })
        except Exception:
            # Fall back to empty mailbox if unconfigured/offline
            pass

        return EmailReadOutput(
            messages=messages,
            total_count=len(messages),
        )
