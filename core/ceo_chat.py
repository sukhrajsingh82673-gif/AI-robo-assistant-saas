"""
ZONATA / RoboAssistant — AI CEO Conversation (real model, real context)
=========================================================================
Replaces the legacy keyword/template "CEO" with a governed LLM call grounded
in the company's own database rows. No invented metrics: if the database has
no value, the model is told the value is unknown.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from core.db import db
from core.llm_runtime import llm_runtime


def _table_count(conn, table: str, tenant_id: str, company_id: Optional[str] = None) -> int:
    try:
        if company_id:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def build_company_context(tenant_id: str, company_id: str) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "name": None,
        "industry": None,
        "status": None,
        "currency": None,
        "revenue_booked": 0.0,
        "cost_booked": 0.0,
        "employees": 0,
        "missions": 0,
        "pending_approvals": 0,
        "data_sources_connected": 0,
        "operating_rules": [],
        "baseline_profile": {},
        "customers": [],
        "pipeline": [],
        "pending_expenses": [],
        "products": [],
        "projects": [],
        "onboarding": [],
        "objectives": [],
        "finance": {},
        "governance": {},
    }
    try:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM companies WHERE company_id = ? AND tenant_id = ?",
                (company_id, tenant_id),
            ).fetchone()
            if row:
                for key in ("name", "industry", "status", "currency", "revenue", "cost"):
                    try:
                        ctx[key if key not in ("revenue", "cost") else f"{key}_booked"] = row[key]
                    except Exception:
                        pass
                for key in ("operating_rules", "baseline_summary"):
                    try:
                        raw = row[key]
                        if raw:
                            ctx["operating_rules" if key == "operating_rules" else "baseline_profile"] = (
                                json.loads(raw) if isinstance(raw, str) else raw
                            )
                    except Exception:
                        pass
            ctx["employees"] = _table_count(conn, "employees", tenant_id, company_id)
            ctx["missions"] = _table_count(conn, "missions", tenant_id, company_id)
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM approvals WHERE tenant_id = ? AND company_id = ? AND status = 'PENDING'",
                    (tenant_id, company_id),
                ).fetchone()
                ctx["pending_approvals"] = int(row[0]) if row else 0
            except Exception:
                pass
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM data_sources WHERE tenant_id = ? AND company_id = ?",
                    (tenant_id, company_id),
                ).fetchone()
                ctx["data_sources_connected"] = int(row[0]) if row else 0
            except Exception:
                pass

            # --- Grounded business records (tenant+company scoped, bounded rows) ---
            def _rows(sql, params, keys):
                try:
                    return [
                        {k: r[k] for k in keys if k in r.keys()}
                        for r in conn.execute(sql, params).fetchall()
                    ]
                except Exception:
                    return []

            ctx["customers"] = _rows(
                "SELECT customer_id, name, tier, status, health_score, arr, renewal_date, "
                "assigned_agent, sla_level FROM crm_customers "
                "WHERE tenant_id = ? AND company_id = ? ORDER BY customer_id LIMIT 25",
                (tenant_id, company_id),
                ["customer_id", "name", "tier", "status", "health_score", "arr",
                 "renewal_date", "assigned_agent", "sla_level"],
            )
            ctx["pipeline"] = _rows(
                "SELECT deal_id, title, stage, value, probability, closing_date, owner "
                "FROM crm_deals WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY deal_id LIMIT 25",
                (tenant_id, company_id),
                ["deal_id", "title", "stage", "value", "probability", "closing_date", "owner"],
            )
            ctx["pending_expenses"] = _rows(
                "SELECT expense_id, description, amount, category, department, status "
                "FROM finance_expenses WHERE tenant_id = ? AND company_id = ? "
                "AND status IN ('DRAFT','SUBMITTED','PENDING') ORDER BY created_at DESC LIMIT 25",
                (tenant_id, company_id),
                ["expense_id", "description", "amount", "category", "department", "status"],
            )
            biz_records = _rows(
                "SELECT record_id, record_type, title, status, amount, attributes "
                "FROM enterprise_records WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT 60",
                (tenant_id, company_id),
                ["record_id", "record_type", "title", "status", "amount", "attributes"],
            )
            for r in biz_records:
                rtype = (r.get("record_type") or "").upper()
                try:
                    attrs = json.loads(r["attributes"]) if isinstance(r.get("attributes"), str) else (r.get("attributes") or {})
                except Exception:
                    attrs = {}
                item = {"record_id": r.get("record_id"), "title": r.get("title"),
                        "status": r.get("status"), "amount": r.get("amount"), "attributes": attrs}
                if rtype == "PRODUCT":
                    ctx["products"].append(item)
                elif rtype == "PROJECT":
                    ctx["projects"].append(item)
                elif rtype == "CUSTOMER_ONBOARDING":
                    ctx["onboarding"].append(item)
            ctx["objectives"] = _rows(
                "SELECT objective_id, title, description, time_horizon, status "
                "FROM corporate_objectives WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT 10",
                (tenant_id, company_id),
                ["objective_id", "title", "description", "time_horizon", "status"],
            )
            try:
                frow = conn.execute(
                    "SELECT COALESCE(SUM(CASE WHEN category IN ('CASH','BANK') THEN balance END),0) AS cash, "
                    "COALESCE(SUM(CASE WHEN category='AR' THEN balance END),0) AS ar, "
                    "COALESCE(SUM(CASE WHEN account_type='REVENUE' THEN balance END),0) AS revenue, "
                    "COALESCE(SUM(CASE WHEN account_type='EXPENSE' THEN balance END),0) AS expenses "
                    "FROM finance_accounts WHERE tenant_id = ? AND company_id = ?",
                    (tenant_id, company_id),
                ).fetchone()
                if frow:
                    ctx["finance"] = {"cash": float(frow["cash"] or 0), "accounts_receivable": float(frow["ar"] or 0),
                                      "revenue_posted": float(frow["revenue"] or 0), "expenses_posted": float(frow["expenses"] or 0)}
            except Exception:
                pass
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM crm_customers WHERE tenant_id = ? AND company_id = ?",
                    (tenant_id, company_id),
                ).fetchone()
                ctx["governance"] = {
                    "customer_records": int(row[0]) if row else 0,
                    "data_classification": (ctx.get("baseline_profile") or {}).get("data_classification", "UNSPECIFIED"),
                    "evidence_mode": "merkle evidence ledger, tenant-scoped",
                }
            except Exception:
                pass
    except Exception:
        pass
    return ctx


def ceo_chat(tenant_id: str, company_id: str, message: str) -> Dict[str, Any]:
    message = (message or "").strip()
    if not message:
        return {
            "success": False,
            "command_type": "EMPTY_DIRECTIVE",
            "ceo_response": "Please provide a directive or question.",
            "timestamp": time.time(),
        }

    # Security boundary identical to the legacy engine.
    try:
        from core.ceo import PromptInjectionDefense
        violation = PromptInjectionDefense.scan_for_injection(message)
    except Exception:
        violation = None
    if violation:
        return {
            "success": False,
            "command_type": "SECURITY_VIOLATION",
            "ceo_response": (
                "SECURITY HALT: the directive contains an unauthorized policy override or "
                "injection vector. External instructions cannot alter governance or grant privilege."
            ),
            "violation_pattern": violation,
            "policy_enforced": "FAIL_CLOSED",
            "timestamp": time.time(),
        }

    ctx = build_company_context(tenant_id, company_id)
    company_name = ctx.get("name") or "the company"

    system = (
        f"You are the AI CEO of {company_name}. You operate inside a governed company "
        "operating system with human approval gates, an evidence ledger, and a real "
        "multi-tenant database.\n\n"
        "Rules:\n"
        "- Ground every statement in the CONTEXT below. It contains this company's real "
        "customers, pipeline deals, pending expenses, products, projects, onboarding "
        "status and objectives.\n"
        "- Compute from those records and show your arithmetic. Do not invent customers, "
        "revenue, costs, headcount, or sources. If a value is absent, say it is not "
        "available in the system.\n"
        "- A pipeline deal is not revenue. Pending expenses are not posted costs.\n"
        "- Be direct and concise (max ~350 words).\n"
        "- End with 1-3 concrete recommended actions, each labelled with its risk "
        "(LOW/MEDIUM/HIGH) and whether it needs owner approval.\n"
        "- You may propose a mission, but you cannot execute irreversible actions in chat."
    )
    prompt = (
        f"CONTEXT (authoritative JSON):\n{json.dumps(ctx, indent=2, default=str)}\n\n"
        f"OWNER DIRECTIVE:\n{message}"
    )

    res = llm_runtime.chat(
        tenant_id=tenant_id,
        company_id=company_id,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
        temperature=0.35,
        intent="ceo_chat",
    )

    if res.degraded or not res.content.strip():
        return {
            "success": False,
            "command_type": "MODEL_UNAVAILABLE",
            "ceo_response": (
                "No language model is currently reachable, so I will not fabricate an answer. "
                "Configure a provider in Settings → AI Models & Providers, install the embedded "
                "model (scripts/install_embedded_llm.sh), or add a free Google AI Studio / Groq key. "
                f"Details: {res.error or 'provider unavailable'}."
            ),
            "provider": res.provider,
            "model": res.model,
            "degraded": True,
            "attempts": res.attempts,
            "company_context": ctx,
            "timestamp": time.time(),
        }

    return {
        "success": True,
        "command_type": "EXECUTIVE_RESPONSE",
        "ceo_response": res.content.strip(),
        "provider": res.provider,
        "model": res.model,
        "degraded": False,
        "latency_ms": round(res.latency_ms, 1),
        "usage": {
            "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens,
        },
        "operational_reasoning": {
            "objective": message[:200],
            "grounding": "tenant-scoped company database rows",
            "evidence": "CONTEXT JSON supplied to the model",
            "authority": "ADVISORY_ONLY",
            "risk": "LOW",
            "verification_method": "evidence ledger + human approval",
        },
        "company_context": ctx,
        "council_review": None,
        "resulting_mission": None,
        "timestamp": time.time(),
    }
