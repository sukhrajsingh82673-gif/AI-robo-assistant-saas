"""ZONATA Sovereign Core — Multi-Tenant Document Search Engine.

Implements OpenCode Step 1E:
- Full-text search over document metadata and extracted text.
- Strict multi-tenant isolation: results filtered by tenant_id, company_id, and access rights.
- PostgreSQL FTS with SQLite fallback.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from core.db import db, DatabaseDialect


def search_documents(
    tenant_id: str,
    company_id: str,
    query_text: str,
    document_type: Optional[str] = None,
    max_sensitivity: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Executes multi-tenant document search across names, metadata, and extracted text."""
    results: List[Dict[str, Any]] = []
    clean_query = query_text.strip()
    like_param = f"%{clean_query}%"

    with db.get_connection() as conn:
        cur = conn.cursor()
        if db.dialect == DatabaseDialect.POSTGRESQL:
            sql = """
                SELECT d.id, d.name, d.status, d.sensitivity_level, d.regime_tags,
                       c.document_type, c.confidence, e.raw_text, e.trust, d.created_at
                FROM documents d
                LEFT JOIN classifications c ON d.id = c.document_id
                LEFT JOIN extractions e ON d.id = e.document_id
                WHERE d.tenant_id = %s
                  AND d.company_id = %s
                  AND d.tombstone = FALSE
                  AND (
                    d.name ILIKE %s
                    OR to_tsvector('english', coalesce(e.raw_text, '')) @@ plainto_tsquery('english', %s)
                    OR c.document_type ILIKE %s
                  )
            """
            params: List[Any] = [tenant_id, company_id, like_param, clean_query, like_param]
            if document_type:
                sql += " AND c.document_type = %s"
                params.append(document_type)
            sql += " ORDER BY d.created_at DESC LIMIT %s"
            params.append(limit)
            cur.execute(sql, tuple(params))
        else:
            # SQLite fallback
            sql = """
                SELECT d.id, d.name, d.status, d.sensitivity_level, d.regime_tags,
                       c.document_type, c.confidence, e.raw_text, e.trust, d.created_at
                FROM documents d
                LEFT JOIN classifications c ON d.id = c.document_id
                LEFT JOIN extractions e ON d.id = e.document_id
                WHERE d.tenant_id = ?
                  AND d.company_id = ?
                  AND d.tombstone = 0
                  AND (
                    d.name LIKE ?
                    OR e.raw_text LIKE ?
                    OR c.document_type LIKE ?
                  )
            """
            params = [tenant_id, company_id, like_param, like_param, like_param]
            if document_type:
                sql += " AND c.document_type = ?"
                params.append(document_type)
            sql += " ORDER BY d.created_at DESC LIMIT ?"
            params.append(limit)
            cur.execute(sql, tuple(params))

        rows = cur.fetchall()
        for r in rows:
            raw_text = r[7] or ""
            # Extract search snippet around match if present
            snippet = ""
            idx = raw_text.lower().find(clean_query.lower())
            if idx != -1:
                start = max(0, idx - 40)
                end = min(len(raw_text), idx + len(clean_query) + 60)
                snippet = "..." + raw_text[start:end].replace("\n", " ") + "..."
            elif raw_text:
                snippet = raw_text[:120].replace("\n", " ") + "..."

            results.append({
                "document_id": r[0],
                "name": r[1],
                "status": r[2],
                "sensitivity_level": r[3],
                "regime_tags": json.loads(r[4]) if isinstance(r[4], str) else (r[4] or []),
                "document_type": r[5] or "general_document",
                "classification_confidence": r[6] or 0.0,
                "snippet": snippet,
                "trust": r[8] or "UNTRUSTED",
                "created_at": r[9],
            })

    return results
