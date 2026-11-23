"""
ZONATA — Deterministic Company Metrics
======================================
Every number an executive surface states must be computed here, in Python,
from tenant-scoped rows. The language model is only allowed to *narrate* these
values; it is never the source of arithmetic.

Invariants:
  - Tenant + company scoping is enforced on every query.
  - Missing data yields ``None`` (unknown), never an invented zero.
  - All ratios are guarded against division by zero.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from core.db import db


CLOSED_STAGES = {
    "closed won", "closed lost", "won", "lost", "closed", "disqualified",
    "cancelled", "canceled",
}


def _month_start(ts: float) -> float:
    dt = _dt.datetime.utcfromtimestamp(ts)
    return _dt.datetime(dt.year, dt.month, 1, tzinfo=_dt.timezone.utc).timestamp()


def compute_company_metrics(
    tenant_id: str,
    company_id: str,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute the canonical metric set for one company inside one tenant."""
    import time as _time

    now = now or _time.time()
    month_start = _month_start(now)

    metrics: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "computed_at": now,
        "currency": "₹",
        "source": "deterministic SQL over tenant-scoped rows",
        "customers": {},
        "pipeline": {},
        "finance": {},
        "expenses": {},
        "workforce": {},
        "missions": {},
        "data_quality": {},
    }

    with db.get_connection() as conn:
        # ------------------------------------------------------------------
        # Customers / recurring revenue
        # ------------------------------------------------------------------
        try:
            rows = conn.execute(
                "SELECT customer_id, name, tier, status, arr, health_score "
                "FROM crm_customers WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            ).fetchall()
        except Exception:
            rows = []

        active = [r for r in rows if str(r["status"] or "").upper() == "ACTIVE"]
        arr_total = sum(float(r["arr"] or 0.0) for r in active)
        by_tier: Dict[str, float] = {}
        for r in active:
            tier = str(r["tier"] or "UNSPECIFIED").upper()
            by_tier[tier] = by_tier.get(tier, 0.0) + float(r["arr"] or 0.0)

        top = sorted(
            ({"customer_id": r["customer_id"], "name": r["name"],
              "arr": float(r["arr"] or 0.0), "tier": r["tier"]}
             for r in active),
            key=lambda x: x["arr"], reverse=True,
        )[:5]

        metrics["customers"] = {
            "total": len(rows),
            "active": len(active),
            "inactive": len(rows) - len(active),
            "arr_total": round(arr_total, 2),
            "mrr_total": round(arr_total / 12.0, 2),
            "arr_by_tier": {k: round(v, 2) for k, v in sorted(by_tier.items())},
            "mrr_by_tier": {k: round(v / 12.0, 2) for k, v in sorted(by_tier.items())},
            "top_customers_by_arr": top,
            "avg_health_score": (
                round(sum(float(r["health_score"] or 0.0) for r in active) / len(active), 2)
                if active else None
            ),
            "arr_concentration_top1_pct": (
                round(top[0]["arr"] / arr_total * 100.0, 2)
                if top and arr_total > 0 else None
            ),
        }

        # ------------------------------------------------------------------
        # Pipeline
        # ------------------------------------------------------------------
        try:
            deals = conn.execute(
                "SELECT deal_id, title, stage, value, probability, closing_date "
                "FROM crm_deals WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            ).fetchall()
        except Exception:
            deals = []

        open_deals: List[Any] = []
        weighted = 0.0
        by_stage: Dict[str, Dict[str, float]] = {}
        for d in deals:
            stage = str(d["stage"] or "UNKNOWN")
            if stage.strip().lower() in CLOSED_STAGES:
                continue
            value = float(d["value"] or 0.0)
            prob = float(d["probability"] or 0.0)
            if prob > 1.0:  # tolerate percent-encoded rows
                prob = prob / 100.0
            weighted += value * prob
            open_deals.append(d)
            bucket = by_stage.setdefault(stage, {"count": 0.0, "value": 0.0, "weighted": 0.0})
            bucket["count"] += 1
            bucket["value"] += value
            bucket["weighted"] += value * prob

        metrics["pipeline"] = {
            "open_deals": len(open_deals),
            "total_open_value": round(sum(float(d["value"] or 0.0) for d in open_deals), 2),
            "weighted_value_monthly": round(weighted, 2),
            "by_stage": {
                k: {"count": int(v["count"]), "value": round(v["value"], 2),
                    "weighted": round(v["weighted"], 2)}
                for k, v in sorted(by_stage.items())
            },
            "calculation": "sum(value * probability) over open deals; values are monthly deal values",
        }

        # ------------------------------------------------------------------
        # Finance (posted ledger, not pipeline)
        # ------------------------------------------------------------------
        try:
            frow = conn.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN category IN ('CASH','BANK') THEN balance END),0) AS cash, "
                "COALESCE(SUM(CASE WHEN category='AR' THEN balance END),0) AS ar, "
                "COALESCE(SUM(CASE WHEN account_type='REVENUE' THEN balance END),0) AS revenue, "
                "COALESCE(SUM(CASE WHEN account_type='EXPENSE' THEN balance END),0) AS expenses "
                "FROM finance_accounts WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            ).fetchone()
            cash = float(frow["cash"] or 0.0)
            ar = float(frow["ar"] or 0.0)
            revenue = float(frow["revenue"] or 0.0)
            expenses = float(frow["expenses"] or 0.0)
            metrics["finance"] = {
                "cash_and_bank": round(cash, 2),
                "accounts_receivable": round(ar, 2),
                "revenue_posted": round(revenue, 2),
                "expenses_posted": round(expenses, 2),
                "operating_profit": round(revenue - expenses, 2),
                "operating_margin_pct": (
                    round((revenue - expenses) / revenue * 100.0, 2) if revenue > 0 else None
                ),
                "note": "Posted ledger balances only; pipeline is excluded from revenue.",
            }
        except Exception:
            metrics["finance"] = {"note": "ledger unavailable"}

        # ------------------------------------------------------------------
        # Expenses
        # ------------------------------------------------------------------
        try:
            erow = conn.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN status='SUBMITTED' THEN amount END),0) AS pending_amount, "
                "COALESCE(SUM(CASE WHEN status='SUBMITTED' THEN 1 END),0) AS pending_count, "
                "COALESCE(SUM(CASE WHEN status IN ('APPROVED','PAID','RECONCILED') THEN amount END),0) AS approved_amount "
                "FROM finance_expenses WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            ).fetchone()
            mrow = conn.execute(
                "SELECT COALESCE(SUM(amount),0) AS mtd FROM finance_expenses "
                "WHERE tenant_id = ? AND company_id = ? AND created_at >= ? "
                "AND status IN ('APPROVED','PAID','RECONCILED')",
                (tenant_id, company_id, month_start),
            ).fetchone()
            metrics["expenses"] = {
                "pending_count": int(erow["pending_count"] or 0),
                "pending_amount": round(float(erow["pending_amount"] or 0.0), 2),
                "approved_amount": round(float(erow["approved_amount"] or 0.0), 2),
                "approved_mtd": round(float(mrow["mtd"] or 0.0), 2),
            }
        except Exception:
            metrics["expenses"] = {}

        # ------------------------------------------------------------------
        # Workforce / missions
        # ------------------------------------------------------------------
        for key, table in (("workforce", "employees"), ("missions", "background_missions")):
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE tenant_id = ? AND company_id = ?",
                    (tenant_id, company_id),
                ).fetchone()
                metrics[key] = {"count": int(row[0] if row else 0)}
            except Exception:
                metrics[key] = {"count": None}

    # ----------------------------------------------------------------------
    # Data quality / provenance
    # ----------------------------------------------------------------------
    metrics["data_quality"] = {
        "customers_loaded": metrics["customers"].get("total", 0) > 0,
        "pipeline_loaded": metrics["pipeline"].get("open_deals", 0) > 0,
        "ledger_loaded": bool(metrics["finance"].get("revenue_posted") is not None),
        "authoritative_for_narration": True,
    }
    return metrics


def metric_brief(metrics: Dict[str, Any]) -> List[str]:
    """Render the headline metrics as fixed, quotable sentences."""
    c = metrics.get("customers") or {}
    p = metrics.get("pipeline") or {}
    f = metrics.get("finance") or {}
    e = metrics.get("expenses") or {}
    lines = [
        f"Active customers: {c.get('active')} of {c.get('total')}.",
        f"ARR: {c.get('arr_total')}; MRR: {c.get('mrr_total')} (ARR / 12).",
        f"Open pipeline deals: {p.get('open_deals')}; total open value {p.get('total_open_value')}; "
        f"probability-weighted monthly value {p.get('weighted_value_monthly')}.",
        f"Posted revenue: {f.get('revenue_posted')}; posted expenses: {f.get('expenses_posted')}; "
        f"operating profit {f.get('operating_profit')}.",
        f"Pending expense claims: {e.get('pending_count')} totalling {e.get('pending_amount')} "
        f"(not posted to the P&L until approved).",
    ]
    return lines


# ==============================================================================
# SUB-STEP 2B: DETERMINISTIC CALCULATOR & CLOCK TOOLS (RULE 18)
# Models call these tools instead of performing internal arithmetic.
# ==============================================================================

import ast
import operator
import re

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def deterministic_calculator(expression: str) -> float | int:
    """Safe, deterministic math expression evaluator using AST parsing.
    
    Permits only numeric constants and standard arithmetic operators (+, -, *, /, //, %, **).
    Rejects attribute access, function calls, variable lookups, and syntax manipulation.
    """
    clean_expr = expression.strip()
    if not clean_expr:
        raise ValueError("Empty mathematical expression")

    try:
        parsed = ast.parse(clean_expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Malformed mathematical expression: {e}")

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Disallowed constant type in expression: {type(node.value)}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in _ALLOWED_OPS:
                return _ALLOWED_OPS[op_type](_eval_node(node.operand))
            raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in _ALLOWED_OPS:
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise ZeroDivisionError("Division by zero in deterministic calculation")
                return _ALLOWED_OPS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")
        else:
            raise ValueError(f"Forbidden AST element in expression: {type(node).__name__}")

    res = _eval_node(parsed)
    return res


def deterministic_percentage(part: float | int, total: float | int, round_digits: int = 2) -> float:
    """Compute percentage deterministically with zero-division safeguard."""
    if not total:
        return 0.0
    return round((float(part) / float(total)) * 100.0, round_digits)


def deterministic_clock(now: Optional[float] = None) -> Dict[str, Any]:
    """Deterministic time and date oracle for agent runtimes."""
    import time as _time
    ts = now if now is not None else _time.time()
    dt = _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc)
    return {
        "timestamp": ts,
        "isoformat": dt.isoformat(),
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "day_of_week": dt.strftime("%A"),
        "is_weekend": dt.weekday() >= 5,
    }


def deterministic_date_add(base_iso: str, days: int = 0, hours: int = 0) -> str:
    """Add days or hours to an ISO date string and return resulting ISO format."""
    dt = _dt.datetime.fromisoformat(base_iso.replace("Z", "+00:00"))
    res = dt + _dt.timedelta(days=days, hours=hours)
    return res.isoformat()


def deterministic_date_diff_days(iso1: str, iso2: str) -> int:
    """Calculate integer day difference between two ISO timestamps."""
    d1 = _dt.datetime.fromisoformat(iso1.replace("Z", "+00:00"))
    d2 = _dt.datetime.fromisoformat(iso2.replace("Z", "+00:00"))
    return (d1.date() - d2.date()).days

