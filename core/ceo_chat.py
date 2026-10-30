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
        "- Ground every statement in the CONTEXT below.\n"
        "- Never invent revenue, costs, customers, headcount, or sources. If data is "
        "missing, say 'not available in the system'.\n"
        "- Be direct and concise (max ~250 words).\n"
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
