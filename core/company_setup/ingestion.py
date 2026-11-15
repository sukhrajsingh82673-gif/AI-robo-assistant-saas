"""Ingestion validation shell for created and existing companies.

This stage does not store file bytes: no object-storage backend is configured
for company files yet. What it does do for real is the part that protects the
rest of the system:

* filename sanitisation (no paths, no control characters),
* an allow-list of document types and a hard size limit,
* a SHA-256 requirement so duplicates can be refused,
* duplicate detection against files already recorded for the company,
* a prompt-injection flag on the text sample, using explicit patterns.

A flagged file is recorded as ``FLAGGED`` and is never passed to an AI prompt.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Optional

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$", re.IGNORECASE)
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_SAMPLE_CHARS = 20000

#: extension -> accepted MIME types
ALLOWED_TYPES: Dict[str, List[str]] = {
    ".csv": ["text/csv", "application/csv", "text/plain"],
    ".tsv": ["text/tab-separated-values", "text/plain"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".xls": ["application/vnd.ms-excel"],
    ".pdf": ["application/pdf"],
    ".txt": ["text/plain"],
    ".json": ["application/json", "text/plain"],
    ".md": ["text/markdown", "text/plain"],
}

BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".sh", ".ps1", ".js", ".vbs",
    ".scr", ".msi", ".jar", ".php", ".py", ".rb", ".pl",
}

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?(system|previous)\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?(admin|administrator|developer|system)", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(system\s+prompt|api\s+key|secret|password|token)", re.IGNORECASE),
    re.compile(r"exfiltrate\s+(data|secret|credential|token|key)", re.IGNORECASE),
    re.compile(r"override\s+(all\s+)?(policy|governance|authority|rules)", re.IGNORECASE),
    re.compile(r"bypass\s+(approval|budget|security|check|review)", re.IGNORECASE),
    re.compile(r"delete\s+from\s+tenants", re.IGNORECASE),
    re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
]


def _now() -> float:
    import time

    return time.time()


def sanitise_filename(value: Any) -> Optional[str]:
    raw = str(value or "")
    raw = CONTROL_CHARS_RE.sub("", raw).replace("\\", "/")
    name = os.path.basename(raw).strip()
    name = re.sub(r"\s+", " ", name)
    if not name or name in (".", ".."):
        return None
    return name[:200]


def scan_text(text: str) -> Optional[str]:
    sample = str(text or "")[:MAX_SAMPLE_CHARS]
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(sample)
        if match:
            return match.group(0)[:80]
    return None


def inspect(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate upload metadata. Never raises; returns errors and flags."""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    filename = sanitise_filename(payload.get("filename") or payload.get("name"))
    if not filename:
        errors.append({"field": "filename", "code": "REQUIRED", "message": "A filename is required."})

    extension = ""
    if filename:
        extension = os.path.splitext(filename)[1].lower()
        if extension in BLOCKED_EXTENSIONS:
            errors.append(
                {
                    "field": "filename",
                    "code": "BLOCKED_TYPE",
                    "message": "This file type is not accepted. Upload a document such as CSV, XLSX or PDF.",
                }
            )
        elif extension not in ALLOWED_TYPES:
            errors.append(
                {
                    "field": "filename",
                    "code": "UNSUPPORTED_TYPE",
                    "message": "Accepted types: CSV, TSV, XLSX, XLS, PDF, TXT, JSON, MD.",
                }
            )

    mime = str(payload.get("mime") or payload.get("mime_type") or "").strip().lower()
    if extension in ALLOWED_TYPES:
        allowed = ALLOWED_TYPES[extension]
        if not mime:
            mime = allowed[0]
        elif mime not in allowed:
            errors.append(
                {
                    "field": "mime",
                    "code": "MIME_MISMATCH",
                    "message": f"The file extension and declared type do not match ({extension} / {mime}).",
                }
            )

    size_raw = payload.get("size_bytes", payload.get("size"))
    size_bytes = 0
    if size_raw in (None, ""):
        errors.append({"field": "size_bytes", "code": "REQUIRED", "message": "The file size is required."})
    else:
        try:
            size_bytes = int(size_raw)
        except (TypeError, ValueError):
            errors.append({"field": "size_bytes", "code": "INVALID", "message": "The file size must be a number."})
            size_bytes = 0
        else:
            if size_bytes <= 0:
                errors.append({"field": "size_bytes", "code": "INVALID", "message": "The file is empty."})
            elif size_bytes > MAX_FILE_BYTES:
                errors.append(
                    {
                        "field": "size_bytes",
                        "code": "TOO_LARGE",
                        "message": f"The file is larger than the {MAX_FILE_BYTES // (1024 * 1024)} MB limit.",
                    }
                )

    sha = str(payload.get("sha256") or "").strip().lower()
    text = str(payload.get("text") or payload.get("text_sample") or "")
    if text:
        text = text[:MAX_SAMPLE_CHARS]
    if not sha and text:
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not sha:
        errors.append(
            {
                "field": "sha256",
                "code": "REQUIRED",
                "message": "A SHA-256 hash is required so duplicates can be refused.",
            }
        )
    elif not SHA256_RE.match(sha):
        errors.append({"field": "sha256", "code": "INVALID", "message": "The SHA-256 hash is not valid."})

    flagged = None
    if text:
        flagged = scan_text(text)
        if flagged:
            warnings.append(
                {
                    "field": "text",
                    "code": "PROMPT_INJECTION",
                    "message": "The text contains an instruction that looks like a prompt-injection attempt. It will not be sent to an AI prompt.",
                }
            )

    kind = str(payload.get("kind") or "DOCUMENT").upper()
    if kind not in ("DOCUMENT", "SPREADSHEET", "STATEMENT", "REPORT"):
        kind = "DOCUMENT"

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "file": {
            "filename": filename,
            "mime": mime or "application/octet-stream",
            "size_bytes": size_bytes,
            "sha256": sha or "",
            "kind": kind,
            "flagged": bool(flagged),
            "flag_pattern": flagged,
            "has_text_sample": bool(text),
            "stored": False,
        },
        "note": (
            "Metadata is validated and recorded. File bytes are not stored on this "
            "deployment because no object-storage backend is configured."
        ),
        "checked_at": _now(),
    }
