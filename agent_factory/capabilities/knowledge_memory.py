"""ZONATA Agent Factory - Knowledge and Memory Capability.

Provides scoped knowledge retrieval and short/long-term memory access with:
- Strict multi-tenant isolation
- Scopes: agent, team, company
- PII sanitization (redact policy)
"""

import re
from typing import Any, Dict, List, Optional


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_pii(text: str) -> str:
    """Redact standard PII fields (email, phone, SSN)."""
    if not isinstance(text, str):
        return text
    t = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)
    t = PHONE_PATTERN.sub("[PHONE REDACTED]", t)
    t = SSN_PATTERN.sub("[SSN REDACTED]", t)
    return t


class ScopedMemoryStore:
    def __init__(self):
        # (tenant_id, scope, scope_id) -> list of memory entries
        self._store: Dict[tuple, List[Dict[str, Any]]] = {}

    def store(
        self,
        tenant_id: str,
        scope: str,
        scope_id: str,
        content: str,
        pii_policy: str = "redact"
    ) -> None:
        key = (tenant_id, scope, scope_id)
        if key not in self._store:
            self._store[key] = []
        clean_content = redact_pii(content) if pii_policy == "redact" else content
        self._store[key].append({
            "content": clean_content,
            "policy_applied": pii_policy
        })

    def retrieve(
        self,
        tenant_id: str,
        scope: str,
        scope_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        key = (tenant_id, scope, scope_id)
        entries = self._store.get(key, [])
        # Simple relevance scoring
        q_lower = query.lower()
        scored = []
        for e in entries:
            score = 1.0 if q_lower in e["content"].lower() else 0.5
            scored.append({**e, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
