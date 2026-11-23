"""ZONATA Sovereign Core — Builtin Ledger Tools.

Implements OpenCode Step 2E (Requirement 2):
- Ledger read: inspects account balances and journal entries.
- Ledger post: dispatches journal entry posting through ActionGateway (ActionClass.POST_LEDGER);
  strictly enforces approval and spend limits before committing.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.authority.types import ActionClass, PrincipalType
from core.action_envelope import ActionEnvelope
from core.action_gateway import action_gateway, ActionGatewayRejection
from core.tools.contract import ToolContract, SideEffectClass
from core.ledger.kernel import LedgerKernel


class LedgerReadInput(BaseModel):
    account_code: Optional[str] = Field(None, description="Account code to read balance for")
    journal_entry_id: Optional[str] = Field(None, description="Journal entry ID to read")


class LedgerReadOutput(BaseModel):
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    balance_minor_units: Optional[int] = None
    currency: Optional[str] = None
    journal_entry: Optional[Dict[str, Any]] = None


class LedgerReadTool(ToolContract):
    name = "ledger_read"
    description = "Reads account balances and immutable double-entry journal records."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "database"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 15.0

    input_schema = LedgerReadInput
    output_schema = LedgerReadOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: LedgerReadInput,
        idempotency_key: Optional[str] = None,
    ) -> LedgerReadOutput:
        kernel = LedgerKernel(tenant_id=tenant_id, company_id=company_id)
        acct_name = None
        bal = None
        curr = None
        j_entry = None

        if args.account_code:
            acct = kernel.get_account_by_code(args.account_code)
            if acct:
                acct_name = acct.get("name")
                bal = acct.get("balance_minor_units", 0)
                curr = acct.get("currency", "USD")

        if args.journal_entry_id:
            j_entry = kernel.get_journal_entry(args.journal_entry_id)

        return LedgerReadOutput(
            account_code=args.account_code,
            account_name=acct_name,
            balance_minor_units=bal,
            currency=curr,
            journal_entry=j_entry,
        )


class JournalLineInput(BaseModel):
    account_id: str
    direction: str = Field(..., description="'DEBIT' or 'CREDIT'")
    amount_minor_units: int
    description: Optional[str] = None


class LedgerPostInput(BaseModel):
    journal_entry_id: str = Field(..., description="ID of the journal entry to post")
    description: str = Field(..., description="Business description of the ledger posting")
    total_amount_minor_units: int = Field(..., description="Total posting amount in integer minor units")
    currency: str = Field("USD", description="Currency code (e.g. USD, EUR)")


class LedgerPostOutput(BaseModel):
    journal_entry_id: str
    status: str
    posted_at: float
    total_minor_units: int
    currency: str


class LedgerPostTool(ToolContract):
    name = "ledger_post"
    description = "Posts double-entry journal entry to ledger through ActionGateway governance."
    version = "1.0.0"
    side_effect_class = SideEffectClass.MONEY
    required_capability = "database"
    required_action_class = ActionClass.POST_LEDGER
    cost_cents = 0
    timeout_seconds = 20.0

    input_schema = LedgerPostInput
    output_schema = LedgerPostOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: LedgerPostInput,
        idempotency_key: Optional[str] = None,
    ) -> LedgerPostOutput:
        # Route through ActionGateway for authority and approval checks
        envelope = ActionEnvelope.create(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=principal_id,
            principal_id=principal_id,
            principal_type=PrincipalType.AGENT.value,
            action_class=ActionClass.POST_LEDGER.value,
            capability_id="database",
            target=f"ledger:{args.journal_entry_id}",
            intent=f"Post ledger entry: {args.description}",
            parameters={
                "journal_entry_id": args.journal_entry_id,
                "amount_minor_units": args.total_amount_minor_units,
                "currency": args.currency,
            },
            spend_amount_minor_units=args.total_amount_minor_units,
            idempotency_key=idempotency_key,
        )
        decision = action_gateway.evaluate_decision_gate(envelope)
        if decision.status != "APPROVED":
            raise ActionGatewayRejection(
                f"Ledger post rejected by ActionGateway: {decision.reason or decision.rule_id}"
            )

        kernel = LedgerKernel(tenant_id=tenant_id, company_id=company_id)
        res = kernel.post_journal_entry(args.journal_entry_id)

        return LedgerPostOutput(
            journal_entry_id=args.journal_entry_id,
            status=res.get("status", "POSTED"),
            posted_at=res.get("posted_at", 0.0),
            total_minor_units=args.total_amount_minor_units,
            currency=args.currency,
        )
