"""ZONATA Sovereign Core — Document Safety, Content Sniffing, and Prompt Injection Defense.

Implements OpenCode Step 1E & Standing Rule 9:
- Content sniffing by magic bytes, not just file extension.
- Executables, scripts, and macro-enabled Office files rejected unless through quarantined Import lane.
- Active PDF content detection (/JavaScript, /JS, /Launch, /EmbeddedFiles).
- Zip bomb & archive ratio/depth limits.
- Untrusted content isolation: All extracted document text carries trust: UNTRUSTED.
- Model fence delimiters: <<<UNTRUSTED_DOCUMENT_CONTENT:id:sha>>> ... <<<//UNTRUSTED_DOCUMENT_CONTENT:id:sha>>>.
- Neutralization of nested closing tags to prevent delimiter breakout.
- Adversarial prompt injection pattern detection.
"""

from __future__ import annotations
import io
import re
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# Sniffing signatures
PE_MAGIC = b"MZ"
ELF_MAGIC = b"\x7fELF"
MACHO_MAGICS = {b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"}
SHEBANG_MAGIC = b"#!"

# Prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*:\s*", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?unrestricted", re.IGNORECASE),
    re.compile(r"jailbreak\s+mode", re.IGNORECASE),
    re.compile(r"developer\s+mode\s+enabled", re.IGNORECASE),
    re.compile(r"bypass\s+(content\s+)?filters?", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"as\s+an\s+ai\s+without\s+rules", re.IGNORECASE),
]

PDF_ACTIVE_CONTENT_PATTERNS = [
    re.compile(rb"/JavaScript\b", re.IGNORECASE),
    re.compile(rb"/JS\b", re.IGNORECASE),
    re.compile(rb"/Launch\b", re.IGNORECASE),
    re.compile(rb"/EmbeddedFiles\b", re.IGNORECASE),
]


@dataclass
class SniffResult:
    allowed: bool
    mime_type: str
    is_executable: bool = False
    is_macro_enabled: bool = False
    has_active_pdf_content: bool = False
    is_decompression_bomb: bool = False
    rejection_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


def sniff_content_safety(
    payload: bytes,
    claimed_mime: Optional[str] = None,
    filename: Optional[str] = None,
    is_import_lane: bool = False,
    max_size_bytes: int = 50 * 1024 * 1024,
    max_decompression_ratio: float = 100.0,
    max_archive_depth: int = 3,
) -> SniffResult:
    """Sniffs raw bytes for executable headers, macro-enabled files, zip bombs, and active PDF content."""
    size = len(payload)
    if size > max_size_bytes:
        return SniffResult(
            allowed=False,
            mime_type=claimed_mime or "application/octet-stream",
            rejection_reason=f"FILE_SIZE_EXCEEDED: {size} bytes exceeds limit of {max_size_bytes} bytes",
        )

    # 1. Executable sniffing
    if payload.startswith(PE_MAGIC) or payload.startswith(ELF_MAGIC) or payload[:4] in MACHO_MAGICS:
        if not is_import_lane:
            return SniffResult(
                allowed=False,
                mime_type="application/x-executable",
                is_executable=True,
                rejection_reason="EXECUTABLE_CONTENT_DENIED: Binary executable header detected",
            )

    # Shell script sniffing
    if payload.startswith(SHEBANG_MAGIC) or payload.startswith(b"eval ") or payload.startswith(b"exec "):
        if not is_import_lane:
            return SniffResult(
                allowed=False,
                mime_type="text/x-shellscript",
                is_executable=True,
                rejection_reason="EXECUTABLE_CONTENT_DENIED: Script shebang / interpreter invocation detected",
            )

    # 2. Macro-enabled Office check & Zip bomb check
    is_zip = payload.startswith(b"PK\x03\x04")
    if is_zip:
        try:
            with zipfile.ZipFile(io.BytesIO(payload), "r") as zf:
                total_uncompressed = 0
                max_depth = 0
                has_macros = False
                for zinfo in zf.infolist():
                    total_uncompressed += zinfo.file_size
                    # Check archive depth
                    depth = zinfo.filename.count("/")
                    if depth > max_depth:
                        max_depth = depth
                    # Check for macro components
                    if "vbaProject.bin" in zinfo.filename or zinfo.filename.endswith(".vba"):
                        has_macros = True

                ratio = total_uncompressed / max(size, 1)
                if ratio > max_decompression_ratio:
                    return SniffResult(
                        allowed=False,
                        mime_type="application/zip",
                        is_decompression_bomb=True,
                        rejection_reason=f"DECOMPRESSION_BOMB_DENIED: Ratio {ratio:.1f}:1 exceeds safety limit {max_decompression_ratio}:1",
                    )
                if max_depth > max_archive_depth:
                    return SniffResult(
                        allowed=False,
                        mime_type="application/zip",
                        rejection_reason=f"ARCHIVE_DEPTH_DENIED: Depth {max_depth} exceeds limit {max_archive_depth}",
                    )
                if has_macros and not is_import_lane:
                    return SniffResult(
                        allowed=False,
                        mime_type="application/vnd.ms-office.activeX+xml",
                        is_macro_enabled=True,
                        rejection_reason="MACRO_ENABLED_DOCUMENT_DENIED: Embedded VBA macro project detected",
                    )
        except zipfile.BadZipFile:
            pass

    # Check macro extension if named explicitly
    if filename and not is_import_lane:
        lower_name = filename.lower()
        if lower_name.endswith((".docm", ".xlsm", ".pptm", ".dotm", ".xltm")):
            return SniffResult(
                allowed=False,
                mime_type="application/vnd.ms-office.activeX+xml",
                is_macro_enabled=True,
                rejection_reason="MACRO_ENABLED_DOCUMENT_DENIED: Macro-enabled file extension detected",
            )

    # 3. Active PDF content check
    has_active_pdf = False
    detected_active_features = []
    if payload.startswith(b"%PDF-"):
        for pattern in PDF_ACTIVE_CONTENT_PATTERNS:
            if pattern.search(payload):
                has_active_pdf = True
                detected_active_features.append(pattern.pattern.decode("ascii", errors="ignore"))

    # Determine resolved MIME
    detected_mime = claimed_mime or "application/octet-stream"
    if payload.startswith(b"%PDF-"):
        detected_mime = "application/pdf"
    elif is_zip:
        detected_mime = claimed_mime or "application/zip"
    elif payload.startswith(b"{\n") or payload.startswith(b"{\r") or payload.startswith(b'{"'):
        detected_mime = "application/json"
    elif payload.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif payload.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"

    return SniffResult(
        allowed=True,
        mime_type=detected_mime,
        has_active_pdf_content=has_active_pdf,
        details={
            "active_pdf_features": detected_active_features,
            "byte_size": size,
        },
    )


def wrap_untrusted_content_for_model(
    document_id: str,
    sha256: str,
    raw_text: str,
    page_number: Optional[int] = None
) -> str:
    """Wraps untrusted document content in tamper-proof fence delimiters.

    Neutralizes any rogue closing delimiter attempts embedded inside the document text.
    """
    prefix = f"<<<UNTRUSTED_DOCUMENT_CONTENT:{document_id}:{sha256[:16]}"
    if page_number is not None:
        prefix += f":page_{page_number}"
    prefix += ">>>"
    suffix = f"<<</UNTRUSTED_DOCUMENT_CONTENT:{document_id}:{sha256[:16]}>>>"

    # Neutralize closing delimiter attempts in text
    safe_text = raw_text.replace("<<</UNTRUSTED_DOCUMENT_CONTENT", "<<</NEUTRALIZED_UNTRUSTED_TAG")

    return f"{prefix}\n{safe_text}\n{suffix}"


def scan_for_prompt_injections(text: str) -> Tuple[bool, List[str]]:
    """Scans text for adversarial prompt injection patterns.

    Returns (is_injection_suspected, matched_patterns).
    """
    matches = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        m = pattern.search(text)
        if m:
            matches.append(m.group(0))
    return bool(matches), matches
