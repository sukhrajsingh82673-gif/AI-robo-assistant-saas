"""ZONATA Sovereign Core — Builtin Folio Tools.

Implements OpenCode Step 2E (Requirement 2):
- Folio read: inspects immutable folio log, status, and Merkle root.
- Folio append: records new append-only entry and recomputes Merkle root.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.authority.types import ActionClass
from core.tools.contract import ToolContract, SideEffectClass
from core.folios.manager import FolioManager


class FolioReadInput(BaseModel):
    folio_id: str = Field(..., description="Folio identifier to read")


class FolioReadOutput(BaseModel):
    folio_id: str
    status: str
    merkle_root: str
    entry_count: int
    entries: List[Dict[str, Any]]


class FolioReadTool(ToolContract):
    name = "folio_read"
    description = "Reads append-only folio log, status, and Merkle root."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "database"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 15.0

    input_schema = FolioReadInput
    output_schema = FolioReadOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: FolioReadInput,
        idempotency_key: Optional[str] = None,
    ) -> FolioReadOutput:
        mgr = FolioManager(tenant_id=tenant_id, company_id=company_id)
        folio = mgr.get_folio(args.folio_id)
        entries = mgr.list_entries(args.folio_id)
        return FolioReadOutput(
            folio_id=args.folio_id,
            status=folio.get("status", "ACTIVE"),
            merkle_root=folio.get("merkle_root", ""),
            entry_count=len(entries),
            entries=entries,
        )


class FolioAppendInput(BaseModel):
    folio_id: str = Field(..., description="Folio identifier to append to")
    entry_type: str = Field("NOTE", description="Type of entry (e.g. NOTE, AUDIT, METRIC)")
    payload: Dict[str, Any] = Field(..., description="Entry content dictionary")


class FolioAppendOutput(BaseModel):
    folio_id: str
    entry_id: str
    merkle_root: str
    sequence: int


class FolioAppendTool(ToolContract):
    name = "folio_append"
    description = "Appends an entry to an append-only sovereign folio."
    version = "1.0.0"
    side_effect_class = SideEffectClass.WRITE_REVERSIBLE
    required_capability = "database"
    required_action_class = ActionClass.WRITE_INTERNAL
    cost_cents = 0
    timeout_seconds = 15.0

    input_schema = FolioAppendInput
    output_schema = FolioAppendOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: FolioAppendInput,
        idempotency_key: Optional[str] = None,
    ) -> FolioAppendOutput:
        mgr = FolioManager(tenant_id=tenant_id, company_id=company_id)
        entry = mgr.add_entry(
            folio_id=args.folio_id,
            entry_type=args.entry_type,
            payload=args.payload,
            created_by=principal_id,
        )
        folio = mgr.get_folio(args.folio_id)
        return FolioAppendOutput(
            folio_id=args.folio_id,
            entry_id=entry.get("entry_id", ""),
            merkle_root=folio.get("merkle_root", ""),
            sequence=entry.get("sequence", 1),
        )
