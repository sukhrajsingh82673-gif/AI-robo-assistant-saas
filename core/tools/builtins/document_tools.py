"""ZONATA Sovereign Core — Builtin Document Tools.

Implements OpenCode Step 2E (Requirement 2):
- Document search: queries document records.
- Document read: retrieves payload and labels output with defensive untrusted delimiters.
- Document create: creates document version and returns version ID.
"""

from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.authority.types import ActionClass
from core.tools.contract import ToolContract, SideEffectClass, wrap_untrusted_tool_output
from core.documents.search import search_documents
from core.documents.versioning import create_document_version, get_document_version_payload


# 1. Document Search
class DocumentSearchInput(BaseModel):
    query: str = Field(..., description="Query terms to search document text and titles")
    document_type: Optional[str] = Field(None, description="Optional filter by document type")
    limit: int = Field(10, description="Maximum number of matches")


class DocumentMatch(BaseModel):
    document_id: str
    title: str
    document_type: str
    created_at: float


class DocumentSearchOutput(BaseModel):
    query: str
    matches: List[Dict[str, Any]]
    total_found: int


class DocumentSearchTool(ToolContract):
    name = "document_search"
    description = "Searches sovereign document backbone for matching text and metadata."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "database"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 15.0

    input_schema = DocumentSearchInput
    output_schema = DocumentSearchOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: DocumentSearchInput,
        idempotency_key: Optional[str] = None,
    ) -> DocumentSearchOutput:
        results = search_documents(
            tenant_id=tenant_id,
            company_id=company_id,
            query_text=args.query,
            document_type=args.document_type,
            limit=args.limit,
        )
        return DocumentSearchOutput(
            query=args.query,
            matches=results,
            total_found=len(results),
        )


# 2. Document Read
class DocumentReadInput(BaseModel):
    document_id: str = Field(..., description="Unique document ID to read")
    version_number: Optional[int] = Field(None, description="Specific version number, or latest if omitted")


class DocumentReadOutput(BaseModel):
    document_id: str
    version_number: int
    sha256: str
    content: str
    untrusted_delimited_content: str = Field(
        ...,
        description="Tamper-proof fence delimited content for safe model consumption"
    )


class DocumentReadTool(ToolContract):
    name = "document_read"
    description = "Reads payload of a sovereign document version, safely delimited for model consumption."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "storage"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 20.0

    input_schema = DocumentReadInput
    output_schema = DocumentReadOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: DocumentReadInput,
        idempotency_key: Optional[str] = None,
    ) -> DocumentReadOutput:
        meta, payload_bytes = get_document_version_payload(
            document_id=args.document_id,
            version_number=args.version_number,
            tenant_id=tenant_id,
            company_id=company_id,
        )
        raw_text = payload_bytes.decode("utf-8", errors="replace")
        sha256_hash = meta.get("sha256") or hashlib.sha256(payload_bytes).hexdigest()
        version_num = meta.get("version_number", 1)

        delimited = wrap_untrusted_tool_output(
            source=f"document:{args.document_id}:v{version_num}",
            id=args.document_id,
            content=raw_text,
            sha256=sha256_hash,
        )

        return DocumentReadOutput(
            document_id=args.document_id,
            version_number=version_num,
            sha256=sha256_hash,
            content=raw_text,
            untrusted_delimited_content=delimited,
        )


# 3. Document Create
class DocumentCreateInput(BaseModel):
    document_id: str = Field(..., description="Document ID to create or version")
    title: str = Field(..., description="Title of the document")
    content: str = Field(..., description="Raw text or markdown content of the document")
    document_type: str = Field("MEMO", description="Document type (e.g. MEMO, REPORT, POLICY)")
    change_reason: str = Field("Created by agent runtime", description="Reason for document version")


class DocumentCreateOutput(BaseModel):
    document_id: str
    version_id: str
    sha256: str
    size_bytes: int


class DocumentCreateTool(ToolContract):
    name = "document_create"
    description = "Creates a new document version in the sovereign document backbone."
    version = "1.0.0"
    side_effect_class = SideEffectClass.WRITE_REVERSIBLE
    required_capability = "storage"
    required_action_class = ActionClass.CREATE_DOCUMENT
    cost_cents = 0
    timeout_seconds = 30.0

    input_schema = DocumentCreateInput
    output_schema = DocumentCreateOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: DocumentCreateInput,
        idempotency_key: Optional[str] = None,
    ) -> DocumentCreateOutput:
        from core.db import db
        import time

        # Ensure base document row exists
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM documents WHERE id = ?", (args.document_id,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO documents (
                        id, tenant_id, company_id, name, status, created_by, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                    """,
                    (args.document_id, tenant_id, company_id, args.title, principal_id, now, now)
                )
                conn.commit()

        payload = args.content.encode("utf-8")
        version_id, sha256_hash = create_document_version(
            document_id=args.document_id,
            new_payload=payload,
            author_id=principal_id,
            change_reason=args.change_reason,
            tenant_id=tenant_id,
            company_id=company_id,
        )
        return DocumentCreateOutput(
            document_id=args.document_id,
            version_id=version_id,
            sha256=sha256_hash,
            size_bytes=len(payload),
        )
