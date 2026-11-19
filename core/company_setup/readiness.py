"""Readiness score for an existing company.

The score is calculated on the server from facts only: which profile fields are
present and which sources are connected, verified or skipped. It is a helpful
signal, not a judgement, and every missing point has a named reason so the UI
can show exactly what would raise it.
"""

from __future__ import annotations

from typing import Any, Dict, List

#: (id, label, weight, detail-when-missing)
PROFILE_CHECKS: List[tuple] = [
    ("name", "Company name", 5, "Add the company name."),
    ("title", "One-line title", 5, "Add a one-line title."),
    ("description", "Description", 8, "Describe the business in at least 20 characters."),
    ("owner_email", "Owner email", 6, "Add a verified email for export and notices."),
    ("country", "Country", 4, "Add the country of operation."),
    ("industry", "Industry", 4, "Add the closest industry."),
    ("business_model", "How the business works", 8, "Explain how the company makes money."),
    ("revenue", "Revenue", 10, "Add the revenue amount, currency and period."),
    ("owner_role", "Your role", 5, "Add your role in the company."),
]

SOURCE_CONNECT_POINTS = 15
SOURCE_BREADTH_POINTS = 10
SOURCE_VERIFIED_POINTS = 10
UPLOAD_POINTS = 5
SKIP_REASON_POINTS = 5


def _profile_ok(company: Dict[str, Any], check_id: str) -> bool:
    if check_id == "revenue":
        revenue = company.get("revenue") if isinstance(company.get("revenue"), dict) else {}
        amount = revenue.get("amount", company.get("revenue_amount"))
        currency = revenue.get("currency") or company.get("revenue_currency")
        period = revenue.get("period") or company.get("revenue_period")
        try:
            has_amount = amount is not None and float(amount) > 0
        except (TypeError, ValueError):
            has_amount = False
        return bool(has_amount and currency and period)
    if check_id == "owner_email":
        return bool(str(company.get("owner_email") or "").strip())
    if check_id == "owner_role":
        return bool(str(company.get("owner_role") or "").strip())
    if check_id == "description":
        return len(str(company.get("description") or "").strip()) >= 20
    value = company.get(check_id)
    return bool(str(value or "").strip())


def compute(company: Dict[str, Any], connections: List[Dict[str, Any]], file_count: int = 0) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    score = 0

    for check_id, label, weight, detail in PROFILE_CHECKS:
        ok = _profile_ok(company, check_id)
        if ok:
            score += weight
        checks.append(
            {
                "id": check_id,
                "label": label,
                "weight": weight,
                "ok": ok,
                "detail": "" if ok else detail,
            }
        )

    live = [row for row in connections if not row.get("skipped")]
    skipped = [row for row in connections if row.get("skipped")]
    verified = [row for row in live if row.get("verified_at")]

    if live:
        score += SOURCE_CONNECT_POINTS
    checks.append(
        {
            "id": "source_connected",
            "label": "At least one source connected",
            "weight": SOURCE_CONNECT_POINTS,
            "ok": bool(live),
            "detail": "" if live else "Connect one source, or upload a file directly.",
        }
    )

    if len(live) >= 3:
        score += SOURCE_BREADTH_POINTS
    checks.append(
        {
            "id": "source_breadth",
            "label": "Three or more sources connected",
            "weight": SOURCE_BREADTH_POINTS,
            "ok": len(live) >= 3,
            "detail": "" if len(live) >= 3 else f"{len(live)} of 3 sources connected.",
        }
    )

    if verified:
        score += SOURCE_VERIFIED_POINTS
    checks.append(
        {
            "id": "source_verified",
            "label": "Ownership verified",
            "weight": SOURCE_VERIFIED_POINTS,
            "ok": bool(verified),
            "detail": "" if verified else "Confirm ownership before any private data is read.",
        }
    )

    if file_count:
        score += UPLOAD_POINTS
    checks.append(
        {
            "id": "upload",
            "label": "A file uploaded or recorded",
            "weight": UPLOAD_POINTS,
            "ok": bool(file_count),
            "detail": "" if file_count else "Upload a CSV, spreadsheet or PDF to start without an integration.",
        }
    )

    skips_without_reason = [row for row in skipped if not str(row.get("skip_reason") or "").strip()]
    if skipped and not skips_without_reason:
        score += SKIP_REASON_POINTS
    checks.append(
        {
            "id": "skip_reasons",
            "label": "Every skipped source has a reason",
            "weight": SKIP_REASON_POINTS,
            "ok": not skips_without_reason,
            "detail": "" if not skips_without_reason else "Add a reason for each skipped source.",
        }
    )

    score = max(0, min(100, int(round(score))))
    if score >= 70:
        band = "HIGH"
    elif score >= 40:
        band = "MEDIUM"
    else:
        band = "LOW"

    reasons = [check for check in checks if not check["ok"]]
    return {
        "score": score,
        "band": band,
        "checks": checks,
        "reasons": reasons,
        "counts": {
            "sources_connected": len(live),
            "sources_verified": len(verified),
            "sources_skipped": len(skipped),
            "files": int(file_count or 0),
        },
        "is_estimate": False,
    }
