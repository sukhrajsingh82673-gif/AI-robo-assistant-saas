"""Native company export.

Produces a real, multi-page PDF without any third-party dependency, splits it
into numbered parts when it grows past a safe page count, and wraps the result
in a ZIP together with a JSON data file and a short README.

Why a ZIP at all:

* the PDF uses the standard Helvetica fonts (the only fonts guaranteed in a
  dependency-free deployment), so characters outside WinAnsi cannot be drawn;
* when the source text contains such characters, or when the PDF is split,
  the archive carries ``company-export.json`` with the exact original values.

Nothing here pretends to be a full typesetting system. The output is honest:
it says which part it is, how many pages it has, that a ZIP preserves the
original text, and when it was generated.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import textwrap
import time
import zipfile
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 50
TOP_Y = 782
BOTTOM_Y = 64
MAX_PAGES_PER_PART = 40

#: Characters that are safe to draw with the built-in Helvetica font.
_WINANSI_MAP = {
    "\u20b9": "Rs. ",
    "\u2014": "-",
    "\u2013": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u00a0": " ",
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\ufeff": "",
}


def _safe_slug(value: str, fallback: str = "company") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    return slug[:60] or fallback


def _pdf_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_text(text: Any) -> Tuple[str, int]:
    """Return a WinAnsi-safe string and the number of replaced characters."""
    raw = str(text if text is not None else "")
    if not raw:
        return "", 0
    mapped = "".join(_WINANSI_MAP.get(ch, ch) for ch in raw)
    out: List[str] = []
    replaced = 0
    for ch in mapped:
        if ch in ("\n", "\r", "\t"):
            out.append(" ")
            continue
        if ord(ch) < 32 or ord(ch) == 127:
            out.append(" ")
            replaced += 1
            continue
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            out.append("?")
            replaced += 1
    return _pdf_escape("".join(out)), replaced


def _wrap(text: str, width: int) -> List[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return [""]
    return textwrap.wrap(clean, width=width, break_long_words=True, break_on_hyphens=False) or [""]


def _money(value: Any, currency: str) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    prefix = (currency or "").strip()
    formatted = f"{number:,.2f}".rstrip("0").rstrip(".")
    return f"{prefix} {formatted}".strip()


def _percent(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    if number <= 1:
        number *= 100
    return f"{number:.0f}%"


def _timestamp(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return ""
    if not seconds:
        return ""
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(seconds))


class NativePdfWriter:
    """Minimal A4 text layout with automatic pagination."""

    def __init__(self, title: str, subtitle: str = ""):
        self.title = str(title or "Company export")
        self.subtitle = str(subtitle or "")
        self.pages: List[List[Tuple[str, float, float, str, float]]] = [[]]
        self.y = TOP_Y
        self.replaced = 0

    # ------------------------------------------------------------- layout API
    def _add(self, text: str, font: str = "F2", size: float = 10.0, x: float = MARGIN_X,
             gap_before: float = 0.0, gap_after: float = 0.0) -> None:
        safe, replaced = _pdf_text(text)
        self.replaced += replaced
        line_height = size * 1.35
        if gap_before:
            self._space(gap_before)
        if self.y - line_height < BOTTOM_Y:
            self.pages.append([])
            self.y = TOP_Y
        self.y -= line_height
        self.pages[-1].append((font, size, x, safe, self.y))
        if gap_after:
            self._space(gap_after)

    def _space(self, amount: float) -> None:
        self.y -= max(0.0, float(amount))
        if self.y < BOTTOM_Y:
            self.pages.append([])
            self.y = TOP_Y

    def rule(self, gap_before: float = 6.0, gap_after: float = 6.0) -> None:
        self._space(gap_before)
        self.pages[-1].append(("RULE", 0.0, MARGIN_X, "", self.y))
        self._space(gap_after)

    def title_line(self, text: str) -> None:
        self._add(text, font="F1", size=18, gap_before=4, gap_after=2)

    def h1(self, text: str) -> None:
        if self.y < BOTTOM_Y + 40:
            self.pages.append([])
            self.y = TOP_Y
        self._add(text, font="F1", size=13, gap_before=12, gap_after=2)

    def h2(self, text: str) -> None:
        self._add(text, font="F1", size=10.5, gap_before=8, gap_after=1)

    def body(self, text: str, gap_before: float = 0.0) -> None:
        for line in _wrap(text, 92):
            self._add(line, font="F2", size=10, gap_before=gap_before)
            gap_before = 0

    def small(self, text: str) -> None:
        for line in _wrap(text, 108):
            self._add(line, font="F2", size=8.5)

    def bullet(self, text: str) -> None:
        lines = _wrap(text, 88)
        if not lines:
            return
        self._add("- " + lines[0], font="F2", size=10)
        for line in lines[1:]:
            self._add("  " + line, font="F2", size=10)

    def kv(self, label: str, value: Any) -> None:
        label_safe, label_replaced = _pdf_text(label)
        value_text = str(value if value is not None else "")
        value_lines = _wrap(value_text, 62) or [""]
        self.replaced += label_replaced
        line_height = 13.5
        if self.y - line_height < BOTTOM_Y:
            self.pages.append([])
            self.y = TOP_Y
        first_y = self.y - line_height
        safe_value, value_replaced = _pdf_text(value_lines[0])
        self.replaced += value_replaced
        self.pages[-1].append(("F1", 9.0, MARGIN_X, label_safe, first_y))
        self.pages[-1].append(("F2", 9.5, MARGIN_X + 125, safe_value, first_y))
        self.y = first_y
        for line in value_lines[1:]:
            safe, replaced = _pdf_text(line)
            self.replaced += replaced
            if self.y - line_height < BOTTOM_Y:
                self.pages.append([])
                self.y = TOP_Y
            self.y -= line_height
            self.pages[-1].append(("F2", 9.5, MARGIN_X + 125, safe, self.y))

    def table(self, headers: Sequence[str], rows: Iterable[Sequence[Any]], widths: Sequence[float]) -> None:
        headers = list(headers)
        widths = list(widths)
        self.h2("  |  ".join(str(h) for h in headers))
        for row in rows:
            cells = [str(cell if cell is not None else "") for cell in row]
            wrapped = [_wrap(cell, max(8, int(widths[i] / 4.8)) if i < len(widths) else 30) for i, cell in enumerate(cells)]
            height = max(len(lines) for lines in wrapped) if wrapped else 1
            for line_index in range(height):
                if self.y - 12 < BOTTOM_Y:
                    self.pages.append([])
                    self.y = TOP_Y
                x = MARGIN_X
                for index, lines in enumerate(wrapped):
                    text = lines[line_index] if line_index < len(lines) else ""
                    safe, replaced = _pdf_text(text)
                    self.replaced += replaced
                    self.pages[-1].append(("F2", 8.5, x, safe, self.y - 12))
                    x += widths[index] if index < len(widths) else 80
                self.y -= 12

    # ---------------------------------------------------------------- render
    def render(self, part_index: int = 1, part_total: int = 1) -> bytes:
        pages = self.pages or [[]]
        count = len(pages)
        part_label = f"Part {part_index} of {part_total}" if part_total > 1 else ""
        title_safe, _ = _pdf_text(self.title)
        subtitle_safe, _ = _pdf_text(self.subtitle)
        part_safe, _ = _pdf_text(part_label)
        generated_safe, _ = _pdf_text(time.strftime("Generated %Y-%m-%d %H:%M UTC", time.gmtime()))

        page_ids: List[int] = []
        content_ids: List[int] = []
        objects: List[bytes] = []
        # Reserve ids: 1 catalog, 2 pages tree, fonts at the end.
        first_page_id = 3
        for index in range(count):
            page_ids.append(first_page_id + index * 2)
            content_ids.append(first_page_id + index * 2 + 1)
        font_bold_id = first_page_id + count * 2
        font_regular_id = font_bold_id + 1

        def add(obj: bytes) -> int:
            objects.append(obj)
            return len(objects)

        add(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        add(f"<< /Type /Pages /Kids [{kids}] /Count {count} >>".encode("ascii"))

        for index, ops in enumerate(pages):
            commands: List[str] = []
            # Header
            commands.append("BT")
            commands.append(f"/F1 9 Tf 0.45 0.45 0.45 rg 1 0 0 1 {MARGIN_X} {PAGE_HEIGHT - 40} Tm ({title_safe}) Tj")
            commands.append("ET")
            if part_safe:
                commands.append("BT")
                commands.append(f"/F2 8 Tf 0.45 0.45 0.45 rg 1 0 0 1 {PAGE_WIDTH - 150} {PAGE_HEIGHT - 40} Tm ({part_safe}) Tj")
                commands.append("ET")
            commands.append(f"{MARGIN_X} {PAGE_HEIGHT - 48} m {PAGE_WIDTH - MARGIN_X} {PAGE_HEIGHT - 48} l S")
            # Body
            for font, size, x, text, y in ops:
                if font == "RULE":
                    commands.append(f"0.85 0.85 0.85 RG {MARGIN_X} {y:.1f} m {PAGE_WIDTH - MARGIN_X} {y:.1f} l S")
                    continue
                font_id = font_bold_id if font == "F1" else font_regular_id
                commands.append("BT")
                commands.append(f"/F{1 if font == 'F1' else 2} {size:.1f} Tf 0.08 0.08 0.08 rg 1 0 0 1 {x:.1f} {y:.1f} Tm ({text}) Tj")
                commands.append("ET")
            # Footer
            commands.append("BT")
            commands.append(
                f"/F2 8 Tf 0.45 0.45 0.45 rg 1 0 0 1 {MARGIN_X} {PAGE_HEIGHT - 826} Tm "
                f"({generated_safe}  |  Page {index + 1} of {count}) Tj"
            )
            commands.append("ET")
            if subtitle_safe:
                commands.append("BT")
                commands.append(
                    f"/F2 8 Tf 0.45 0.45 0.45 rg 1 0 0 1 {MARGIN_X} {PAGE_HEIGHT - 814} Tm ({subtitle_safe}) Tj"
                )
                commands.append("ET")

            stream = "\n".join(commands).encode("latin-1", errors="replace")
            add(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                    f"/Contents {content_ids[index]} 0 R /Resources << /Font << /F1 {font_bold_id} 0 R /F2 {font_regular_id} 0 R >> >> >>"
                ).encode("ascii")
            )
            add(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")

        add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

        buffer = io.BytesIO()
        buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: List[int] = []
        for index, obj in enumerate(objects, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{index} 0 obj\n".encode("ascii"))
            buffer.write(obj)
            buffer.write(b"\nendobj\n")
        xref = buffer.tell()
        buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets:
            buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        buffer.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
        return buffer.getvalue()


def _sections(data: Dict[str, Any], writer: NativePdfWriter) -> None:
    company = data.get("company") or {}
    build = data.get("build") or {}
    readiness = data.get("readiness") or {}
    counts = data.get("counts") or {}

    writer.title_line(company.get("name") or "Company export")
    writer.body(company.get("title") or "")
    writer.body(
        f"Status: {company.get('status_label') or company.get('status') or 'Unknown'}   |   "
        f"Type: {company.get('type') or 'Unknown'}   |   "
        f"Reference: {data.get('request_id') or company.get('id') or ''}"
    )
    writer.small(
        "Confidential. This export was produced for the company deletion workflow. "
        "If you did not request it, cancel the deletion in ZONATA and treat this file as sensitive."
    )
    writer.rule()

    # 1. Identity
    writer.h1("1. Company identity")
    writer.kv("Company id", company.get("id"))
    writer.kv("Legal name", company.get("name"))
    writer.kv("One-line title", company.get("title"))
    writer.kv("Status", company.get("status_label") or company.get("status"))
    writer.kv("Company type", company.get("type"))
    writer.kv("Industry", company.get("industry"))
    writer.kv("Country", company.get("country"))
    writer.kv("Website", company.get("website") or "Not provided")
    writer.kv("Business model", company.get("business_model") or "Not provided")
    writer.kv("Target customers", company.get("target_customers") or "Not provided")
    writer.kv("Created", _timestamp(company.get("created_at")))
    writer.kv("Last updated", _timestamp(company.get("updated_at")))
    if company.get("description"):
        writer.h2("Description")
        writer.body(company.get("description"))

    # 2. Owner and money
    writer.h1("2. Ownership and numbers")
    owner = company.get("owner") or {}
    writer.kv("Owner", owner.get("name") or "Not provided")
    writer.kv("Owner email", owner.get("email") or "Not provided")
    writer.kv("Owner role", owner.get("role") or "Not provided")
    revenue = company.get("revenue") or {}
    writer.kv("Revenue", _money(revenue.get("amount"), revenue.get("currency")))
    writer.kv("Revenue period", revenue.get("period") or "Not set")
    budget = company.get("budget") or {}
    writer.kv("Budget", _money(budget.get("amount"), budget.get("currency")))
    writer.kv("Timeline", company.get("timeline") or "Not provided")
    writer.kv("Readiness", f"{int(float(readiness.get('score') or 0))} / 100 ({readiness.get('band') or 'unknown'})")
    writer.kv("Departments", counts.get("departments", 0))
    writer.kv("People / agents", counts.get("employees", 0))
    writer.kv("Workflows", counts.get("workflows", 0))
    writer.kv("Connections", counts.get("connections", 0))
    writer.kv("Files", counts.get("files", 0))
    writer.kv("Approvals", counts.get("approvals", 0))
    if company.get("setup_notes"):
        writer.h2("Setup notes")
        writer.body(company.get("setup_notes"))

    # 3. Build / onboarding
    writer.h1("3. Build and onboarding progress")
    if build:
        writer.kv("Run type", build.get("run_type"))
        writer.kv("State", build.get("phase_state"))
        writer.kv("Progress", _percent(build.get("progress_percent") or build.get("progress")))
        writer.kv("Attempt", build.get("attempt") or 1)
        writer.kv("Started", _timestamp(build.get("started_at")))
        writer.kv("Finished", _timestamp(build.get("finished_at")))
        if build.get("failure_reason"):
            writer.kv("Failure", build.get("failure_reason"))
        for phase in build.get("phases") or []:
            note = phase.get("note") or phase.get("description") or ""
            writer.bullet(f"{phase.get('id')}: {phase.get('state')}" + (f" - {note}" if note else ""))
        gaps = build.get("waiting_on") or build.get("gaps") or []
        if gaps:
            writer.h2("Waiting on")
            for gap in gaps:
                writer.bullet(f"{gap.get('phase') or 'General'}: {gap.get('message') or ''}")
    else:
        writer.body("No build or onboarding run has been recorded for this company.")

    # 4. Sources and connections
    writer.h1("4. Sources and connections")
    sources = data.get("sources") or {}
    items = sources.get("sources") if isinstance(sources, dict) else None
    if items:
        for source in items:
            detail = (
                f"{source.get('name') or source.get('id')}: {source.get('status')}"
                + (f" - {source.get('skip_reason')}" if source.get("skip_reason") else "")
            )
            writer.bullet(detail)
    else:
        writer.body("No source catalogue state was recorded.")
    connections = data.get("connections") or []
    if connections:
        writer.h2("Connections")
        for connection in connections:
            scopes = ", ".join(str(s) for s in (connection.get("scope") or []))
            writer.bullet(
                f"{connection.get('name') or connection.get('provider_id') or 'Connection'} "
                f"[{connection.get('status') or 'UNKNOWN'}]"
                + (f" scopes: {scopes}" if scopes else "")
                + (f" verified: {_timestamp(connection.get('verified_at'))}" if connection.get("verified_at") else "")
            )
    if readiness.get("reasons"):
        writer.h2("Readiness gaps")
        for reason in readiness.get("reasons") or []:
            writer.bullet(f"{reason.get('label') or reason.get('id')}: {reason.get('detail') or ''}")

    # 5. Legal pack
    writer.h1("5. Legal pack")
    legal = data.get("legal_items") or []
    if legal:
        for item in legal:
            writer.bullet(
                f"{item.get('name')} - {item.get('status')} ({item.get('authority') or 'authority not set'})"
            )
            if item.get("draft_disclaimer"):
                writer.small(item.get("draft_disclaimer"))
    else:
        writer.body("No legal drafts have been prepared for this company.")

    # 6. Files
    writer.h1("6. Files and evidence")
    files = data.get("files") or []
    if files:
        writer.table(
            ["Filename", "Kind", "Size", "Scan", "SHA-256"],
            [
                [
                    row.get("filename"),
                    row.get("kind"),
                    row.get("size_bytes"),
                    row.get("scan_status"),
                    (row.get("sha256") or "")[:24],
                ]
                for row in files
            ],
            [150, 80, 60, 70, 130],
        )
    else:
        writer.body("No files are recorded for this company.")

    # 7. Audit trail
    writer.h1("7. Audit trail (most recent first)")
    events = data.get("audit") or []
    if events:
        for event in events:
            writer.bullet(
                f"{_timestamp(event.get('created_at'))}  {event.get('action')}  "
                f"by {event.get('actor_role') or 'unknown'} ({event.get('actor_id') or 'unknown'})"
            )
    else:
        writer.body("No audit events were recorded.")

    # 8. Data fidelity
    writer.h1("8. Data fidelity")
    writer.body(
        "This PDF is produced with the standard Helvetica font that ships with every PDF reader. "
        "Characters outside its Latin range are replaced with a question mark in the PDF. "
        "The original text is preserved in company-export.json inside the ZIP archive. "
        "The archive also contains a SHA-256 manifest for every file."
    )
    if writer.replaced:
        writer.body(f"Characters replaced in this PDF: {writer.replaced}.")


def _manifest(data: Dict[str, Any], files: List[Dict[str, Any]], parts: int) -> Dict[str, Any]:
    company = data.get("company") or {}
    return {
        "export_type": "ZONATA company export",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "company": {
            "id": company.get("id"),
            "name": company.get("name"),
            "status": company.get("status"),
            "type": company.get("type"),
        },
        "request_id": data.get("request_id"),
        "parts": parts,
        "files": files,
    }


def build_company_export(
    data: Dict[str, Any],
    output_dir: str,
    tenant_id: str,
    company_id: str,
    request_id: str,
) -> Dict[str, Any]:
    """Render the export and return file metadata.

    The caller owns the database transaction and the deletion state machine;
    this function only writes files inside ``output_dir``.
    """
    company = data.get("company") or {}
    title = f"{company.get('name') or 'Company'} - company export"
    writer = NativePdfWriter(title, "ZONATA company export")
    _sections(data, writer)

    pages = writer.pages or [[]]
    chunks = [pages[i:i + MAX_PAGES_PER_PART] for i in range(0, len(pages), MAX_PAGES_PER_PART)]
    if not chunks:
        chunks = [[[]]]
    part_total = len(chunks)

    safe_company = _safe_slug(company.get("name") or company_id)
    safe_request = _safe_slug(request_id, "export")
    base_name = f"zonata-company-{safe_company}-{safe_request}"
    folder = os.path.join(
        os.path.abspath(output_dir),
        _safe_slug(tenant_id, "tenant"),
        _safe_slug(company_id, "company"),
        safe_request,
    )
    os.makedirs(folder, exist_ok=True, mode=0o750)

    written: List[Dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        part_writer = NativePdfWriter(title, "ZONATA company export")
        part_writer.pages = chunk
        pdf_bytes = part_writer.render(part_index=index, part_total=part_total)
        filename = f"{base_name}-part-{index}-of-{part_total}.pdf" if part_total > 1 else f"{base_name}.pdf"
        path = os.path.join(folder, filename)
        _atomic_write(path, pdf_bytes)
        written.append(
            {
                "filename": filename,
                "path": path,
                "size_bytes": len(pdf_bytes),
                "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                "pages": len(chunk),
            }
        )

    needs_zip = part_total > 1 or writer.replaced > 0
    if needs_zip:
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        manifest = _manifest(data, written, part_total)
        manifest["encoding_replacements"] = writer.replaced
        readme = (
            "ZONATA company export\n"
            "=====================\n\n"
            "This archive contains:\n"
            "  - the PDF part(s) of the company export;\n"
            "  - company-export.json with the exact original values;\n"
            "  - manifest.json with SHA-256 hashes for every file.\n\n"
            "The PDF uses a standard Latin font. Characters outside that range are\n"
            "shown as '?' in the PDF; company-export.json preserves the original text.\n\n"
            f"Company: {company.get('name') or company_id}\n"
            f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n"
        ).encode("utf-8")
        zip_name = f"{base_name}.zip"
        zip_path = os.path.join(folder, zip_name)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in written:
                archive.write(item["path"], item["filename"])
            archive.writestr("company-export.json", json_bytes)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
            archive.writestr("README.txt", readme)
        for item in written:
            try:
                os.remove(item["path"])
            except OSError:
                pass
        zip_bytes = open(zip_path, "rb").read()
        final_name = zip_name
        final_path = zip_path
        content_type = "application/zip"
        size_bytes = len(zip_bytes)
        sha256 = hashlib.sha256(zip_bytes).hexdigest()
    else:
        single = written[0]
        final_name = single["filename"]
        final_path = single["path"]
        content_type = "application/pdf"
        size_bytes = single["size_bytes"]
        sha256 = single["sha256"]

    relative = os.path.relpath(final_path, os.path.abspath(output_dir))
    return {
        "filename": final_name,
        "path": final_path,
        "relative_ref": relative,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "parts": part_total,
        "pages": len(pages),
        "replaced_characters": writer.replaced,
        "archive": needs_zip,
        "files": [
            {
                "filename": item["filename"],
                "size_bytes": item["size_bytes"],
                "sha256": item["sha256"],
                "pages": item["pages"],
            }
            for item in written
        ],
    }


def _atomic_write(path: str, content: bytes) -> None:
    temporary = f"{path}.tmp"
    with open(temporary, "wb") as handle:
        handle.write(content)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    os.replace(temporary, path)
