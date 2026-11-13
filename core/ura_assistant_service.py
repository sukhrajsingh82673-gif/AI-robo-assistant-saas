"""
URA Assistant — unified server-side orchestration service.

This is the single intelligent backend behind `web/ura_assistant.js`.  It is a
thin, auditable layer over the capabilities that already exist in the platform:

  tools            existing implementation
  ---------------  ---------------------------------------------------------
  navigate         client-side route table (returned as a card)
  query_data       core.search_engine.GlobalSearchEngine
  delegate_task    FloatingAssistantService.create_coworker_task
  decide_approval  core.approvals.ApprovalPipeline
  change_setting   core.settings_service.settings_service
  run_security_scan core.coworker.defense_monitor.DefensiveCybersecurityMonitor
  generate_report  core.enterprise_reports.EnterpriseReportsEngine
  install_agent    core.enterprise_agent_factory.EnterpriseAgentFactory
  connect_integration core.integrations registry (connection is a governance action)
  run_terminal     governed terminal (approval + role gated)

Nothing is fabricated.  Every tool reports what actually happened, and a tool
that is not authorised returns a blocked result rather than a fake success.

Company scope is gated on an approved `cowork` approval whose description
contains "URA Assistant" and "(kind: cowork)".  Until that approval exists, the
service refuses to read or act on company data.

The service is deliberately transport agnostic: `stream()` yields event dicts
that the HTTP layer serialises as NDJSON and the browser renders incrementally.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .db import db
from .approvals import ApprovalPipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent directory
# ---------------------------------------------------------------------------

AGENT_DIRECTORY: Dict[str, Dict[str, Any]] = {
    "CEO": {
        "label": "AI CEO",
        "title": "Chief Executive Officer",
        "remit": "company strategy, priorities, cross-department decisions and governed delegation",
    },
    "COO": {
        "label": "AI COO",
        "title": "Chief Operating Officer",
        "remit": "operations, delivery, missions, process execution and operational risk",
    },
    "CMO": {
        "label": "AI CMO",
        "title": "Chief Marketing Officer",
        "remit": "marketing, campaigns, pipeline, brand and customer growth",
    },
    "CTO": {
        "label": "AI CTO",
        "title": "Chief Technology Officer",
        "remit": "engineering, platform health, integrations and technical risk",
    },
    "CFO": {
        "label": "AI CFO",
        "title": "Chief Financial Officer",
        "remit": "finance, cash, margins, budgets and financial controls",
    },
    "CHRO": {
        "label": "AI CHRO",
        "title": "Chief Human Resources Officer",
        "remit": "people, hiring, workforce wellbeing and HR operations",
    },
}

_AGENT_ALIASES = {
    "ceo": "CEO",
    "coo": "COO",
    "cmo": "CMO",
    "cto": "CTO",
    "cfo": "CFO",
    "chro": "CHRO",
    "chief executive": "CEO",
    "chief operating": "COO",
    "chief marketing": "CMO",
    "chief technology": "CTO",
    "chief financial": "CFO",
    "chief human": "CHRO",
}

_AGENT_PREFIX = re.compile(r"^\s*@([A-Za-z]{3,5})\b[\s:,.-]*", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Typed tool catalogue
# ---------------------------------------------------------------------------

TOOL_SPECS: Dict[str, Dict[str, Any]] = {
    "navigate": {
        "description": "Open an app screen for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Screen key, label or path."},
            },
            "required": ["target"],
        },
        "mutating": False,
        "scope": "ANY",
    },
    "query_data": {
        "description": "Search live internal app data (companies, people, missions, approvals, records).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up."},
            },
            "required": ["query"],
        },
        "mutating": False,
        "scope": "COMPANY",
    },
    "delegate_task": {
        "description": "Hand a task to the Co-worker execution fabric.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The task to execute."},
                "agent_role": {"type": "string", "description": "Optional executive role to route to."},
            },
            "required": ["prompt"],
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "decide_approval": {
        "description": "Approve or decline a pending approval request.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "approved": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": ["request_id", "approved"],
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "change_setting": {
        "description": "Change an enterprise setting.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": ["string", "number", "boolean"]},
            },
            "required": ["key", "value"],
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "run_security_scan": {
        "description": "Run a defensive security patrol and report findings.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional path to scan."},
            },
        },
        "mutating": False,
        "scope": "COMPANY",
    },
    "generate_report": {
        "description": "Generate or list business intelligence reports.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "category": {"type": "string"},
                "query": {"type": "string"},
                "action": {"type": "string", "enum": ["list", "generate"]},
            },
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "install_agent": {
        "description": "Create/install a new AI workforce agent from a description.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "What the agent should do."},
                "department": {"type": "string"},
            },
            "required": ["prompt"],
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "connect_integration": {
        "description": "Start connecting an external integration.",
        "parameters": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
            },
            "required": ["provider"],
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "run_terminal": {
        "description": "Run a governed terminal command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
        },
        "mutating": True,
        "scope": "COMPANY",
    },
    "web_research": {
        "description": "Research a question on the public web and cite the sources that were read.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to research."},
                "limit": {"type": "number", "description": "Maximum sources to read."},
            },
            "required": ["query"],
        },
        "mutating": False,
        "scope": "ANY",
    },
}


# ---------------------------------------------------------------------------
# Screen catalogue
# ---------------------------------------------------------------------------

SCREENS: Dict[str, Dict[str, str]] = {
    "overview": {"label": "Overview", "path": "/overview"},
    "coworker": {"label": "Co-worker", "path": "/coworker"},
    "missions": {"label": "Work & Missions", "path": "/missions"},
    "approvals": {"label": "Approvals", "path": "/approvals"},
    "terminal": {"label": "Terminal", "path": "/terminal"},
    "activity": {"label": "Activity", "path": "/activity"},
    "artifacts": {"label": "Artifacts", "path": "/artifacts"},
    "schedule": {"label": "Schedule", "path": "/schedule"},
    "operations": {"label": "Operations", "path": "/operations"},
    "customers": {"label": "Customers", "path": "/customers"},
    "finance": {"label": "Finance", "path": "/finance"},
    "people": {"label": "People", "path": "/people"},
    "records": {"label": "Records", "path": "/records"},
    "files": {"label": "Files", "path": "/files"},
    "reports": {"label": "Reports", "path": "/reports"},
    "agent-factory": {"label": "Agent Factory", "path": "/agent-factory"},
    "integrations": {"label": "Integrations", "path": "/integrations"},
    "governance": {"label": "Governance", "path": "/governance"},
    "company": {"label": "Company", "path": "/company"},
    "organization": {"label": "Organization", "path": "/organization"},
    "ceo-records": {"label": "AI CEO Records", "path": "/company/ceo-records"},
    "workforce": {"label": "Workforce", "path": "/workforce"},
    "tasks": {"label": "TaskMaker", "path": "/tasks"},
    "workflows": {"label": "Workflows", "path": "/workflows"},
    "settings": {"label": "Settings", "path": "/settings"},
    "plugins": {"label": "Plugins", "path": "/plugins"},
    "design": {"label": "Design", "path": "/design"},
    "meetings": {"label": "Meeting library", "path": "/assistant"},
}

_SCREEN_ALIASES = {
    "home": "overview",
    "dashboard": "overview",
    "co-worker": "coworker",
    "co worker": "coworker",
    "autonomous coworker": "coworker",
    "work": "missions",
    "mission": "missions",
    "task": "missions",
    "tasks": "tasks",
    "approval": "approvals",
    "command terminal": "terminal",
    "console": "terminal",
    "audit": "activity",
    "audit activity": "activity",
    "evidence": "artifacts",
    "calendar": "schedule",
    "crm": "customers",
    "billing": "finance",
    "accounting": "finance",
    "hr": "people",
    "documents": "files",
    "bi": "reports",
    "business intelligence": "reports",
    "agent factory": "agent-factory",
    "agents": "agent-factory",
    "integrations hub": "integrations",
    "connectors": "integrations",
    "host authority": "governance",
    "ceo": "ceo-records",
    "ai ceo": "ceo-records",
    "ceo records": "ceo-records",
    "ai ceo records": "ceo-records",
    "organisation": "organization",
    "organisation matrix": "organization",
    "meeting": "meetings",
    "meeting room": "meetings",
    "meeting library": "meetings",
    "settings v2": "settings",
    "plugins & connections": "plugins",
}


# ---------------------------------------------------------------------------
# Intent helpers
# ---------------------------------------------------------------------------

_CONFIRM_WORDS = re.compile(r"\b(confirm|yes,? do it|go ahead|approved? to proceed)\b", re.IGNORECASE)


def _first(words: Iterable[str], text: str) -> bool:
    return any(word in text for word in words)


def _normalise_target(raw: str) -> Optional[str]:
    value = (raw or "").strip().lower()
    if not value:
        return None
    value = value.lstrip("#").strip()
    if value.startswith("/"):
        value = value.split("?", 1)[0].strip("/")
        if value in SCREENS:
            return value
        value = value.replace("/", " ").strip()
    if value in SCREENS:
        return value
    if value in _SCREEN_ALIASES:
        return _SCREEN_ALIASES[value]
    for key, meta in SCREENS.items():
        if value == meta["label"].lower():
            return key
    # Last resort: substring match on an exact screen label.
    for key, meta in SCREENS.items():
        label = meta["label"].lower()
        if label in value or value in label:
            return key
    return None


def _extract_target(prompt: str) -> Optional[str]:
    lower = prompt.lower()
    for key, meta in SCREENS.items():
        if key.replace("-", " ") in lower or meta["label"].lower() in lower:
            return key
    for alias, key in _SCREEN_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            return key
    return None


def _plan_tool(prompt: str, page: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Deterministic, auditable intent map.  The model is never allowed to pick
    an executing tool on its own."""
    text = (prompt or "").strip()
    lower = text.lower()

    # Navigation — must come before query so "open reports" is a screen change.
    if _first(("open ", "go to ", "take me to ", "show me the ", "navigate to ", "switch to "), lower):
        target = _extract_target(text)
        if target:
            return "navigate", {"target": target}

    if _first(("research ", "web research", "search the web", "look up online", "look online", "find sources", "latest news", "on the web", "from the internet", "internet search"), lower):
        return "web_research", {"query": text}

    if _first(("run command", "terminal", "shell command", "$ "), lower):
        command = re.sub(r"^(run|execute|please run|can you run)\s+(the\s+)?(command|in terminal|terminal)?\s*", "", text, flags=re.IGNORECASE).strip(" `")
        if command.lower().startswith("command "):
            command = command[8:].strip()
        return "run_terminal", {"command": command or text}

    approval_id = re.search(r"\b(apr_[A-Za-z0-9]+)\b", text)
    if approval_id and _first(("approve", "decline", "reject", "deny"), lower):
        approved = "approve" in lower and "reject" not in lower and "decline" not in lower and "deny" not in lower
        return "decide_approval", {"request_id": approval_id.group(1), "approved": approved}

    if _first(("security", "scan", "patrol", "vulnerab", "audit the system"), lower) and not _first(("report", "reports"), lower):
        return "run_security_scan", {}

    if _first(("install agent", "create an agent", "create a new agent", "hire an agent", "new agent"), lower):
        department = ""
        dept_match = re.search(r"\b(procurement|finance|sales|marketing|engineering|operations|hr|support)\b", lower)
        if dept_match:
            department = dept_match.group(1).title()
        return "install_agent", {"prompt": text, "department": department}

    if _first(("connect", "integration", "connector", "link my", "attach my"), lower):
        provider = ""
        prov_match = re.search(
            r"\b(gmail|google|slack|hubspot|salesforce|notion|jira|github|stripe|razorpay|zoho|outlook|teams|shopify)\b",
            lower,
        )
        if prov_match:
            provider = prov_match.group(1)
        if provider or _first(("connect", "integration", "connector"), lower):
            return "connect_integration", {"provider": provider or text}

    if _first(("generate a report", "generate report", "create a report", "weekly report", "monthly report", "report on"), lower):
        return "generate_report", {"action": "generate", "title": text[:120], "query": text}

    if _first(("delegate", "assign", "hand this to", "hand it to", "have the team", "ask the team", "run a mission"), lower):
        return "delegate_task", {"prompt": text}

    if _first(("turn on", "turn off", "enable ", "disable ", "change the setting", "set the setting"), lower):
        key_match = re.search(r"`?([a-z][a-z0-9_]{2,60})`?\s+(to|setting|option)", lower)
        value = True
        if _first(("turn off", "disable"), lower):
            value = False
        if key_match:
            return "change_setting", {"key": key_match.group(1), "value": value}
        return "change_setting", {"key": text, "value": value}

    if _first(("approve ", "decline ", "reject "), lower) and not approval_id:
        return "decide_approval", {"request_id": "", "approved": "approve" in lower}

    if _first(("what is", "what's", "who is", "how many", "how much", "summar", "find ", "search ", "list ", "show "), lower):
        return "query_data", {"query": text}

    return None, {}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class URAAssistantService:
    """Typed tools, scope gating, agent routing, memory and honest answers."""

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._ensure_memory_table()

    # ------------------------------------------------------------- persistence
    def _ensure_memory_table(self) -> None:
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assistant_memory (
                        memory_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        company_id TEXT,
                        user_id TEXT NOT NULL,
                        scope TEXT NOT NULL DEFAULT 'PERSONAL',
                        content TEXT NOT NULL,
                        source_session_id TEXT,
                        created_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assistant_memory_user "
                    "ON assistant_memory(tenant_id, user_id, created_at)"
                )
                conn.commit()
        except Exception:
            logger.exception("Could not ensure assistant_memory table")

    def remember(
        self,
        content: str,
        user_id: str,
        scope: str = "PERSONAL",
        company_id: Optional[str] = None,
        source_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        content = (content or "").strip()
        if not content:
            return {"success": False, "error": "Nothing to remember."}
        memory_id = f"mem_{uuid.uuid4().hex[:10]}"
        now = time.time()
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO assistant_memory (
                        memory_id, tenant_id, company_id, user_id, scope,
                        content, source_session_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory_id, self.tenant_id,
                        company_id if (scope or "").upper() == "COMPANY" else None,
                        user_id, (scope or "PERSONAL").upper(), content,
                        source_session_id, now,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Could not store assistant memory")
            return {"success": False, "error": "Memory could not be stored."}
        return {"success": True, "memory": {"memory_id": memory_id, "content": content, "created_at": now}}

    def list_memories(
        self,
        user_id: str,
        scope: Optional[str] = None,
        company_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM assistant_memory WHERE tenant_id = ? AND user_id = ?"
        params: List[Any] = [self.tenant_id, user_id]
        if scope:
            sql += " AND scope = ?"
            params.append(scope.upper())
        if scope and scope.upper() == "COMPANY":
            if company_id:
                sql += " AND company_id = ?"
                params.append(company_id)
            else:
                return []
        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query.strip()}%")
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 200)))
        try:
            with db.get_connection() as conn:
                rows = conn.execute(sql, params).fetchall()
        except Exception:
            logger.exception("Could not list assistant memory")
            return []
        return [dict(row) for row in rows]

    def forget(self, memory_id: str, user_id: str) -> Dict[str, Any]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT memory_id FROM assistant_memory WHERE memory_id = ? AND tenant_id = ? AND user_id = ?",
                (memory_id, self.tenant_id, user_id),
            ).fetchone()
            if not row:
                return {"success": False, "error": "Memory not found."}
            conn.execute(
                "DELETE FROM assistant_memory WHERE memory_id = ? AND tenant_id = ? AND user_id = ?",
                (memory_id, self.tenant_id, user_id),
            )
            conn.commit()
        return {"success": True, "memory_id": memory_id}

    def clear_memories(self, user_id: str, scope: Optional[str] = None) -> Dict[str, Any]:
        sql = "DELETE FROM assistant_memory WHERE tenant_id = ? AND user_id = ?"
        params: List[Any] = [self.tenant_id, user_id]
        if scope:
            sql += " AND scope = ?"
            params.append(scope.upper())
        with db.get_connection() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            removed = cur.rowcount or 0
        return {"success": True, "removed": removed}

    # ---------------------------------------------------------- scope gating
    def company_permission(self, company_id: Optional[str]) -> Dict[str, Any]:
        if not company_id:
            return {"granted": False, "reason": "NO_COMPANY", "request": None}
        try:
            rows = ApprovalPipeline.list_approvals(self.tenant_id, company_id)
        except Exception:
            logger.exception("Could not read approvals")
            return {"granted": False, "reason": "APPROVALS_UNAVAILABLE", "request": None}
        for row in rows:
            desc = str(row.get("action_desc") or "")
            status = str(row.get("status") or "").upper()
            if (
                re.search(r"ura assistant", desc, re.IGNORECASE)
                and re.search(r"\(kind:\s*cowork\)", desc, re.IGNORECASE)
                and status in ("APPROVED", "EXECUTED", "COMPLETE", "COMPLETED")
            ):
                return {"granted": True, "reason": "APPROVED", "request": row}
        pending = next(
            (
                row for row in rows
                if re.search(r"ura assistant", str(row.get("action_desc") or ""), re.IGNORECASE)
                and str(row.get("status") or "").upper() == "PENDING"
            ),
            None,
        )
        return {
            "granted": False,
            "reason": "PENDING" if pending else "NOT_REQUESTED",
            "request": pending,
        }

    def request_company_permission(
        self,
        company_id: str,
        user_id: str,
        reason: str = "The owner asked the assistant to read and act on company data in Company scope.",
    ) -> Dict[str, Any]:
        if not company_id:
            return {"success": False, "error": "No company context."}
        status = self.company_permission(company_id)
        if status.get("granted"):
            return {"success": True, "status": "APPROVED", "already_granted": True}
        if status.get("request"):
            return {
                "success": True,
                "status": "PENDING",
                "request": status["request"],
                "already_requested": True,
            }
        req = ApprovalPipeline.create_request(
            tenant_id=self.tenant_id,
            company_id=company_id,
            agent_id=user_id or "usr_owner",
            action_desc="URA Assistant access to company data (kind: cowork)",
            reason=reason,
            risk_level="LOW",
            consequence="Assistant can read company context and propose governed actions.",
        )
        return {"success": True, "status": "PENDING", "request": req}

    # ------------------------------------------------------------ background
    def plan_job_kind(self, prompt: str) -> str:
        tool, _ = _plan_tool(prompt, "overview")
        return "research" if tool == "web_research" else "query"

    def create_job(
        self,
        prompt: str,
        user_id: str,
        workspace_mode: str = "PERSONAL",
        company_id: Optional[str] = None,
        session_id: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a background job.  At most three may be active per user."""
        prompt = (prompt or "").strip()
        if not prompt:
            return {"success": False, "error": "Type what the job should do."}
        from .ura_assistant_jobs import (
            AssistantJobRunner, AssistantJobStore, MAX_ACTIVE_JOBS,
        )

        store = AssistantJobStore(self.tenant_id)
        active = store.active_count(user_id)
        if active >= MAX_ACTIVE_JOBS:
            return {
                "success": False,
                "error": (
                    f"You already have {MAX_ACTIVE_JOBS} active jobs. "
                    "Pause, cancel or wait for one to finish before starting another."
                ),
                "limit": MAX_ACTIVE_JOBS,
                "active": active,
            }
        scope = "COMPANY" if str(workspace_mode or "PERSONAL").upper() == "COMPANY" else "PERSONAL"
        if scope == "COMPANY" and not company_id:
            return {"success": False, "error": "Company scope needs a selected company."}
        job_kind = kind if kind in ("research", "query") else self.plan_job_kind(prompt)
        job = store.create(
            user_id=user_id,
            title=prompt[:80],
            prompt=prompt,
            kind=job_kind,
            company_id=company_id,
            workspace_mode=scope,
            session_id=session_id,
        )
        AssistantJobRunner.instance().start(store, job)
        return {
            "success": True,
            "job": store.get(job["job_id"], user_id) or job,
            "limit": MAX_ACTIVE_JOBS,
        }

    def job_action(self, job_id: str, user_id: str, action: str) -> Dict[str, Any]:
        from .ura_assistant_jobs import (
            AssistantJobRunner, AssistantJobStore, MAX_ACTIVE_JOBS,
        )

        store = AssistantJobStore(self.tenant_id)
        job = store.get(job_id, user_id)
        if not job:
            return {"success": False, "error": "Job not found."}
        runner = AssistantJobRunner.instance()
        action = str(action or "").lower()
        status = str(job.get("status") or "").upper()
        if action == "pause":
            if status not in ("QUEUED", "RUNNING"):
                return {"success": False, "error": f"A {status.lower()} job cannot be paused."}
            runner.request_pause(job_id, True)
            store.update(job_id, status="PAUSED", step="Paused", append_step=True)
        elif action == "resume":
            if status != "PAUSED":
                return {"success": False, "error": "Only a paused job can resume."}
            runner.request_pause(job_id, False)
            store.update(job_id, status="RUNNING", step="Resumed", append_step=True)
        elif action in ("cancel", "stop"):
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                return {"success": False, "error": "This job has already finished."}
            runner.request_cancel(job_id)
            store.update(
                job_id,
                status="CANCELLED",
                progress=job.get("progress", 0),
                step="Cancelled",
                append_step=True,
            )
        elif action == "retry":
            if status not in ("FAILED", "CANCELLED", "SUCCEEDED"):
                return {"success": False, "error": "Only a finished job can be retried."}
            if store.active_count(user_id) >= MAX_ACTIVE_JOBS:
                return {"success": False, "error": f"The {MAX_ACTIVE_JOBS}-job limit is reached."}
            reset = store.reset_for_retry(job_id, user_id)
            if not reset:
                return {"success": False, "error": "The job could not be reset."}
            runner.start(store, reset)
        elif action == "takeover":
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                return {"success": False, "error": "This job has already finished."}
            runner.request_pause(job_id, True)
            store.update(job_id, status="PAUSED", step="Paused for you to take over", append_step=True)
            return {
                "success": True,
                "job": store.get(job_id, user_id),
                "handoff": {
                    "path": "/coworker",
                    "label": "Take over in the Co-worker",
                    "message": (
                        "The job is paused. Continue it yourself in the Co-worker screen; "
                        "the assistant will not restart it unless you press Resume."
                    ),
                },
            }
        else:
            return {"success": False, "error": "Unknown job action."}
        return {"success": True, "job": store.get(job_id, user_id)}

    def recover_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """Honestly mark jobs interrupted by a server restart."""
        from .ura_assistant_jobs import AssistantJobRunner, AssistantJobStore

        store = AssistantJobStore(self.tenant_id)
        runner = AssistantJobRunner.instance()
        jobs = store.list(user_id, status="active", limit=50)
        for job in jobs:
            if job.get("status") in ("QUEUED", "RUNNING") and not runner.is_live(job["job_id"]):
                store.update(
                    job["job_id"],
                    status="FAILED",
                    progress=job.get("progress", 0),
                    step="Interrupted",
                    error=(
                        "The server restarted while this job was running, so it did not "
                        "finish. Retry it to continue."
                    ),
                    append_step=True,
                )
        return store.list(user_id, status="all", limit=25)

    # --------------------------------------------------------------- context
    def resolve_agent(self, prompt: str) -> Tuple[Optional[str], str]:
        """Return (role, prompt without the @role prefix)."""
        match = _AGENT_PREFIX.match(prompt or "")
        if not match:
            return None, prompt
        token = match.group(1).lower()
        role = _AGENT_ALIASES.get(token)
        if not role:
            return None, prompt
        return role, (prompt or "")[match.end():].strip()

    def _page_context_lines(self, page_context: Optional[Dict[str, Any]]) -> List[str]:
        if not page_context:
            return []
        lines = []
        page = page_context.get("page")
        if page:
            label = SCREENS.get(page, {}).get("label", str(page))
            lines.append(f"Current screen: {label} ({page}).")
        path = page_context.get("path")
        if path:
            lines.append(f"Current route: {path}.")
        entity = page_context.get("entity")
        if entity:
            lines.append(f"Selected entity on screen: {json.dumps(entity, default=str)[:400]}.")
        return lines

    def _memory_lines(
        self, user_id: str, scope: str, company_id: Optional[str]
    ) -> List[str]:
        memories = self.list_memories(user_id, scope=scope, company_id=company_id, limit=12)
        if not memories:
            return []
        return ["Owner memories:"] + [f"- {m['content']}" for m in memories]

    # ---------------------------------------------------------------- stream
    def stream(
        self,
        prompt: str,
        user_id: str,
        workspace_mode: str = "PERSONAL",
        company_id: Optional[str] = None,
        page_context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yield NDJSON-ready events: context, agent, tool, permission, confirm,
        answer, card, done, error."""
        prompt = (prompt or "").strip()
        if not prompt:
            yield {"type": "error", "message": "Type a question or instruction."}
            return

        sess_id = session_id or f"ura_{uuid.uuid4().hex[:10]}"
        scope = "COMPANY" if str(workspace_mode or "PERSONAL").upper() == "COMPANY" else "PERSONAL"
        company_name = self._company_name(company_id) if company_id else None

        role, cleaned = self.resolve_agent(prompt)
        if agent_role and not role:
            role = str(agent_role).upper()
            role = role if role in AGENT_DIRECTORY else None
        if role and role not in AGENT_DIRECTORY:
            yield {"type": "error", "message": f"Unknown agent role @{role}."}
            return
        prompt = cleaned or prompt

        agent_meta = AGENT_DIRECTORY.get(role or "", None)

        yield {
            "type": "context",
            "context": {
                "page": (page_context or {}).get("page") or "overview",
                "path": (page_context or {}).get("path") or "",
                "scope": scope,
                "company_id": company_id,
                "company_name": company_name,
                "agent": role,
                "agent_label": agent_meta["label"] if agent_meta else None,
            },
        }

        if role:
            yield {
                "type": "agent",
                "role": role,
                "label": agent_meta["label"],
                "title": agent_meta["title"],
                "remit": agent_meta["remit"],
            }

        # ---- Company scope permission gate --------------------------------
        if scope == "COMPANY":
            if not company_id:
                yield {
                    "type": "permission",
                    "state": "NO_COMPANY",
                    "message": "Company scope needs a selected company.",
                }
                yield {"type": "done", "session_id": sess_id, "routed_to": "OWNER_CLARIFICATION"}
                return
            permission = self.company_permission(company_id)
            if not permission.get("granted"):
                yield {
                    "type": "permission",
                    "state": permission.get("reason"),
                    "company_id": company_id,
                    "message": (
                        "Company scope is locked until the AI CEO approves assistant access "
                        "(kind: cowork). Nothing was read from company data."
                    ),
                }
                yield {"type": "done", "session_id": sess_id, "routed_to": "PERMISSION_REQUIRED"}
                return

        # ---- Record the user turn -----------------------------------------
        assistant = self._assistant_service()
        try:
            assistant._record_message(
                session_id=sess_id,
                user_id=user_id,
                company_id=company_id if scope == "COMPANY" else None,
                sender="user",
                workspace_mode=scope,
                content=(f"@{role} " if role else "") + prompt,
                intent_category="COMPANY_DELEGATION" if scope == "COMPANY" else "PERSONAL_TASK",
            )
        except Exception:
            logger.exception("Could not record the assistant user turn")

        # ---- Plan a typed tool --------------------------------------------
        tool_name, arguments = _plan_tool(prompt, (page_context or {}).get("page") or "overview")
        if role and tool_name in ("delegate_task", "query_data"):
            arguments["agent_role"] = role

        tool_result: Optional[Dict[str, Any]] = None
        card: Optional[Dict[str, Any]] = None

        if tool_name:
            spec = TOOL_SPECS[tool_name]
            if spec.get("scope") == "COMPANY" and scope != "COMPANY":
                yield {
                    "type": "tool",
                    "tool": tool_name,
                    "status": "blocked",
                    "label": "Needs Company scope",
                }
                yield {
                    "type": "answer",
                    "delta": (
                        f"“{prompt}” needs company data, and you are in Personal scope. "
                        "I did not read company data or execute anything. Switch to "
                        "Company scope (after the AI CEO approval) and ask again."
                    ),
                }
                yield {"type": "done", "session_id": sess_id, "routed_to": "PERSONAL_SANDBOX"}
                return

            preview = self._preview_tool(tool_name, arguments)
            if spec.get("mutating") and not self._is_confirmed(prompt, arguments):
                yield {
                    "type": "tool",
                    "tool": tool_name,
                    "status": "awaiting_confirmation",
                    "label": preview,
                }
                yield {
                    "type": "confirm",
                    "tool": tool_name,
                    "arguments": arguments,
                    "preview": preview,
                    "risk": "HIGH" if tool_name == "run_terminal" else "MEDIUM",
                }
                yield {
                    "type": "answer",
                    "delta": (
                        f"This would {preview.lower()}. I have not executed it. "
                        "Review and confirm the action card to continue."
                    ),
                }
                self._record_assistant_turn(
                    assistant, sess_id, user_id, scope, company_id,
                    f"Awaiting confirmation for {tool_name}.", intent="CONFIRMATION",
                )
                yield {"type": "done", "session_id": sess_id, "routed_to": "CONFIRMATION_REQUIRED"}
                return

            yield {
                "type": "tool",
                "tool": tool_name,
                "status": "running",
                "label": preview,
            }
            try:
                tool_result = self.execute_tool(
                    tool_name,
                    arguments,
                    user_id=user_id,
                    scope=scope,
                    company_id=company_id,
                    role=role,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Assistant tool failed: %s", tool_name)
                tool_result = {"ok": False, "summary": f"The tool failed: {type(exc).__name__}."}
            ok = bool(tool_result.get("ok"))
            yield {
                "type": "tool",
                "tool": tool_name,
                "status": "done" if ok else "blocked",
                "label": tool_result.get("summary") or preview,
                "ok": ok,
            }
            card = tool_result.get("card")

        # ---- Compose and stream the answer --------------------------------
        answer, citations, routed_to = self._compose_answer(
            prompt=prompt,
            role=role,
            scope=scope,
            company_id=company_id,
            page_context=page_context,
            user_id=user_id,
            tool_name=tool_name,
            tool_result=tool_result,
        )
        for chunk in self._chunks(answer):
            yield {"type": "answer", "delta": chunk}

        if card:
            yield {"type": "card", "card": card}

        self._record_assistant_turn(
            assistant, sess_id, user_id, scope, company_id, answer,
            citations=citations, intent="COMPANY_DELEGATION" if scope == "COMPANY" else "PERSONAL_TASK",
        )

        yield {
            "type": "done",
            "session_id": sess_id,
            "routed_to": routed_to,
            "agent": role,
            "citations": citations,
            "tool": tool_name,
            "ok": bool(tool_result.get("ok")) if tool_result else True,
        }

    # ------------------------------------------------------------- execution
    def execute_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]],
        user_id: str,
        scope: str = "PERSONAL",
        company_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        spec = TOOL_SPECS.get(name)
        if not spec:
            return {"ok": False, "summary": f"Unknown tool '{name}'."}
        if spec.get("scope") == "COMPANY" and scope != "COMPANY":
            return {"ok": False, "summary": "This tool needs Company scope."}
        if spec.get("scope") == "COMPANY" and not company_id:
            return {"ok": False, "summary": "This tool needs a selected company."}
        args = dict(arguments or {})
        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"ok": False, "summary": f"The '{name}' tool is not wired yet."}
        return handler(args, user_id=user_id, scope=scope, company_id=company_id, role=role)

    # --- individual tools ---------------------------------------------------
    def _tool_navigate(self, args: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        target = _normalise_target(str(args.get("target") or ""))
        if not target:
            return {"ok": False, "summary": "I could not match that to a screen."}
        meta = SCREENS[target]
        return {
            "ok": True,
            "summary": f"The {meta['label']} screen is ready to open.",
            "data": {"screen": target, "path": meta["path"], "label": meta["label"]},
            "card": {
                "type": "NAVIGATE",
                "title": f"Open {meta['label']}",
                "path": meta["path"],
                "label": meta["label"],
            },
        }

    def _tool_query_data(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        query = str(args.get("query") or "").strip()
        if not query:
            return {"ok": False, "summary": "Tell me what to look up."}
        try:
            from .search_engine import GlobalSearchEngine
            result = GlobalSearchEngine.search_all(self.tenant_id, query)
        except Exception:
            logger.exception("Internal search failed")
            return {"ok": False, "summary": "Internal search is unavailable right now. Nothing was invented."}
        items: List[Dict[str, Any]] = []
        for category, matches in (result or {}).items():
            for item in (matches or [])[:5]:
                if isinstance(item, dict):
                    items.append({
                        "category": category,
                        "title": item.get("title") or item.get("name") or item.get("id") or "Record",
                        "subtitle": item.get("subtitle") or item.get("status") or "",
                    })
        if not items:
            return {"ok": True, "summary": "No matching internal records were found.", "data": {"items": []}}
        lines = [f"{i+1}. {item['title']} — {item['category']}" for i, item in enumerate(items[:8])]
        return {
            "ok": True,
            "summary": f"Found {len(items)} internal match(es).",
            "data": {"items": items[:12]},
            "answer": "I found these records:\n" + "\n".join(lines),
            "card": {
                "type": "SEARCH_RESULTS",
                "title": f"{len(items)} matches for “{query[:60]}”",
                "items": items[:8],
            },
        }

    def _tool_web_research(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        query = str(args.get("query") or "").strip()
        if not query:
            return {"ok": False, "summary": "Tell me what to research."}
        from .ura_assistant_web import filter_results, get_web_search_provider, load_web_access

        company_id = kwargs.get("company_id")
        policy = load_web_access(self.tenant_id, company_id)
        if policy.mode == "off":
            return {
                "ok": False,
                "summary": (
                    "Web access is off, so I did not search the internet. "
                    "Turn it on in Assistant → Web access."
                ),
                "card": {"type": "WEB_ACCESS_OFF"},
            }
        provider = get_web_search_provider()
        if not provider.configured():
            return {
                "ok": False,
                "summary": (
                    "No web search provider is configured on the server, so I did not "
                    "search the internet. Nothing was invented."
                ),
                "card": {"type": "WEB_NOT_CONFIGURED"},
            }
        try:
            results = provider.search(query, limit=int(args.get("limit") or 5))
        except Exception as exc:
            logger.exception("Web research failed")
            return {
                "ok": False,
                "summary": f"The web search failed: {exc}. Nothing was invented.",
                "card": {"type": "WEB_SEARCH_FAILED"},
            }
        allowed, blocked = filter_results(results, policy)
        if not allowed:
            reason = blocked[0]["reason"] if blocked else "The provider returned no results."
            return {
                "ok": False,
                "summary": f"No allowed source could be read: {reason}",
                "data": {"blocked": blocked},
                "card": {"type": "WEB_NO_SOURCES", "blocked": blocked},
            }
        citations = [
            {
                "source_type": "WEB",
                "label": result.title,
                "url": result.url,
                "provider": result.provider,
                "sample": bool(result.sample),
                "verified": not result.sample,
            }
            for result in allowed
        ]
        lines = []
        for index, result in enumerate(allowed, start=1):
            lines.append(f"{index}. {result.title} — {result.domain}")
            if result.snippet:
                lines.append(f"   {result.snippet[:400]}")
            if result.sample:
                lines.append("   Sample data. Not a real source.")
        answer = f"I read {len(allowed)} allowed source(s):\n" + "\n".join(lines)
        if blocked:
            answer += "\n\nExcluded by the access policy: " + "; ".join(
                f"{item['url']} ({item['reason']})" for item in blocked
            )
        if provider.is_sample:
            answer += (
                "\n\nSample provider: these are demonstration results, not pages fetched "
                "from the internet."
            )
        return {
            "ok": True,
            "summary": f"Read {len(allowed)} allowed source(s).",
            "answer": answer,
            "citations": citations,
            "data": {"sources": citations, "blocked": blocked, "sample": bool(provider.is_sample)},
            "card": {
                "type": "WEB_SOURCES",
                "title": f"{len(allowed)} source(s) for “{query[:60]}”",
                "sources": citations,
                "blocked": blocked,
                "sample": bool(provider.is_sample),
            },
        }

    def _tool_delegate_task(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        prompt = str(args.get("prompt") or "").strip()
        if not prompt:
            return {"ok": False, "summary": "The task is empty."}
        role = kwargs.get("role")
        if role:
            prompt = f"@{role} {prompt}"
        try:
            res = self._assistant_service().create_coworker_task(
                prompt,
                "COMPANY",
                kwargs.get("company_id"),
                kwargs.get("user_id") or "usr_owner",
            )
        except Exception:
            logger.exception("Delegation failed")
            return {"ok": False, "summary": "The Co-worker task could not be created. Nothing was delegated."}
        task = (res or {}).get("task") or res or {}
        status = task.get("status") or res.get("status") or "UNKNOWN"
        task_id = task.get("task_id") or res.get("task_id")
        return {
            "ok": bool(task_id),
            "summary": f"Task {task_id or ''} handed to the Co-worker ({status}).".strip(),
            "data": {"task": task},
            "card": {
                "type": "COWORKER_TASK",
                "task_id": task_id,
                "title": "Delegated to the Co-worker",
                "status": status,
                "requires_approval": bool(task.get("requires_approval")),
                "path": "/coworker",
            },
        }

    def _tool_decide_approval(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        request_id = str(args.get("request_id") or "").strip()
        if not request_id:
            return {"ok": False, "summary": "Which approval should I decide? Include its ID."}
        approver = {
            "user_id": kwargs.get("user_id") or "usr_owner",
            "role": "OWNER",
        }
        try:
            res = ApprovalPipeline.decide_request(
                tenant_id=self.tenant_id,
                request_id=request_id,
                approver_user=approver,
                approved=bool(args.get("approved")),
                rejection_reason=args.get("reason") or None,
                company_id=kwargs.get("company_id"),
            )
        except Exception:
            logger.exception("Approval decision failed")
            return {"ok": False, "summary": "The approval decision could not be recorded."}
        if not res.get("success"):
            return {"ok": False, "summary": str(res.get("error") or "The decision was refused.")}
        return {
            "ok": True,
            "summary": f"Approval {request_id} is now {res.get('status')}.",
            "data": res,
            "card": {
                "type": "APPROVAL_DECISION",
                "request_id": request_id,
                "status": res.get("status"),
            },
        }

    def _tool_change_setting(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        key = str(args.get("key") or "").strip()
        if not key or " " in key:
            return {"ok": False, "summary": "Give me the exact setting key, for example `term_execution_enabled`."}
        from .settings_service import settings_service
        company_id = kwargs.get("company_id")
        try:
            settings_service.update_single_setting(
                self.tenant_id, company_id, key, args.get("value"),
                actor=kwargs.get("user_id") or "assistant",
            )
            value = settings_service.get_effective_setting(self.tenant_id, company_id, key)
        except Exception:
            logger.exception("Setting change failed")
            return {"ok": False, "summary": f"Setting '{key}' could not be changed."}
        return {
            "ok": True,
            "summary": f"Setting {key} is now {json.dumps(value, default=str)}.",
            "data": {"key": key, "value": value},
            "card": {"type": "SETTING_CHANGED", "key": key, "value": value},
        }

    def _tool_run_security_scan(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        try:
            from .coworker.defense_monitor import DefensiveCybersecurityMonitor
            monitor = DefensiveCybersecurityMonitor.get_instance()
            report = monitor.run_full_defensive_patrol()
        except Exception:
            logger.exception("Security patrol failed")
            return {"ok": False, "summary": "The security patrol could not run. Nothing is reported as clean."}
        findings = report.get("findings") if isinstance(report, dict) else None
        count = len(findings) if isinstance(findings, list) else report.get("finding_count") if isinstance(report, dict) else None
        return {
            "ok": True,
            "summary": (
                f"Security patrol completed with {count} finding(s)."
                if count is not None else "Security patrol completed."
            ),
            "data": {"report": report},
            "card": {"type": "SECURITY_SCAN", "finding_count": count, "path": "/governance"},
        }

    def _tool_generate_report(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        try:
            from .enterprise_reports import EnterpriseReportsEngine
            engine = EnterpriseReportsEngine(self.tenant_id)
        except Exception:
            logger.exception("Reports engine unavailable")
            return {"ok": False, "summary": "The reports engine is unavailable."}
        action = str(args.get("action") or "list").lower()
        if action != "generate":
            reports = engine.list_reports(company_id=kwargs.get("company_id"), search_query=args.get("query") or None)
            return {
                "ok": True,
                "summary": f"{len(reports)} report(s) available.",
                "data": {"reports": reports[:20]},
                "card": {"type": "REPORT_LIST", "count": len(reports), "path": "/reports"},
            }
        summary = "Report requested from the assistant."
        report = engine.generate_report({
            "company_id": kwargs.get("company_id") or "comp_primary",
            "title": args.get("title") or "Assistant requested report",
            "report_category": (args.get("category") or "CUSTOM").upper(),
            "ai_executive_summary": summary,
            "generated_by": kwargs.get("user_id") or "URA Assistant",
        })
        return {
            "ok": bool(report.get("report_id")),
            "summary": f"Report {report.get('report_id')} created.",
            "data": {"report": report},
            "card": {
                "type": "REPORT_CREATED",
                "report_id": report.get("report_id"),
                "title": report.get("title"),
                "path": "/reports",
            },
        }

    def _tool_install_agent(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        prompt = str(args.get("prompt") or "").strip()
        if not prompt:
            return {"ok": False, "summary": "Describe the agent to install."}
        try:
            from .enterprise_agent_factory import EnterpriseAgentFactory
            factory = EnterpriseAgentFactory(self.tenant_id)
            blueprint = factory.synthesize_blueprint_from_prompt(
                prompt, kwargs.get("company_id") or "comp_primary"
            )
        except Exception:
            logger.exception("Agent synthesis failed")
            return {"ok": False, "summary": "The agent blueprint could not be synthesised."}
        return {
            "ok": bool(blueprint),
            "summary": f"Blueprint {blueprint.get('blueprint_id') or blueprint.get('id') or ''} prepared (not yet activated).".strip(),
            "data": {"blueprint": blueprint},
            "card": {
                "type": "AGENT_BLUEPRINT",
                "blueprint_id": blueprint.get("blueprint_id") or blueprint.get("id"),
                "name": blueprint.get("name"),
                "path": "/agent-factory",
            },
        }

    def _tool_connect_integration(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        provider = str(args.get("provider") or "").strip()
        return {
            "ok": True,
            "summary": (
                f"Connection to {provider} needs a provider OAuth handshake, which the assistant "
                "cannot start on its own. Open the Integrations screen to complete it."
                if provider else
                "Open the Integrations screen to choose a provider and complete OAuth."
            ),
            "data": {"provider": provider, "status": "HANDOFF"},
            "card": {
                "type": "INTEGRATION_HANDOFF",
                "provider": provider,
                "path": "/integrations",
            },
            "answer": (
                f"Connecting {provider or 'an integration'} requires the provider's own OAuth "
                "handshake, so I cannot complete it from chat. I have opened the handoff "
                "card; nothing was connected yet."
            ),
        }

    def _tool_run_terminal(self, args: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        command = str(args.get("command") or "").strip()
        if not command:
            return {"ok": False, "summary": "No command was supplied."}
        role = str(kwargs.get("role") or "").upper()
        user = kwargs.get("user_id") or "usr_owner"
        # The terminal is a governed surface. The assistant hands the command to
        # the same governed endpoint contract and requires a human approval.
        try:
            from .settings_service import settings_service
            enabled = settings_service.get_effective_setting(
                self.tenant_id, kwargs.get("company_id"), "term_execution_enabled", True
            )
            emergency = settings_service.get_effective_setting(
                self.tenant_id, kwargs.get("company_id"), "host_emergency_stop", False
            )
        except Exception:
            enabled, emergency = True, False
        if emergency or not enabled:
            return {
                "ok": False,
                "summary": "Terminal execution is disabled by policy or emergency stop. Nothing ran.",
            }
        return {
            "ok": False,
            "summary": (
                "Terminal commands are not executed from the assistant chat. "
                "Open the governed Terminal so the command is attributed, leased and audited."
            ),
            "data": {"command": command, "status": "HANDOFF", "user": user, "role": role},
            "card": {"type": "TERMINAL_HANDOFF", "command": command, "path": "/terminal"},
        }

    # --------------------------------------------------------------- answer
    def _compose_answer(
        self,
        prompt: str,
        role: Optional[str],
        scope: str,
        company_id: Optional[str],
        page_context: Optional[Dict[str, Any]],
        user_id: str,
        tool_name: Optional[str],
        tool_result: Optional[Dict[str, Any]],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        citations: List[Dict[str, Any]] = list((tool_result or {}).get("citations") or [])
        routed_to = "PERSONAL_SANDBOX" if scope == "PERSONAL" else "AI_CEO"

        if tool_result:
            if tool_result.get("answer"):
                return str(tool_result["answer"]), citations, (
                    "WEB_RESEARCH" if tool_name == "web_research" else routed_to
                )
            if not tool_result.get("ok"):
                return (
                    str(tool_result.get("summary") or "The action did not complete."),
                    citations,
                    routed_to,
                )
            if tool_name == "navigate":
                data = tool_result.get("data") or {}
                return (
                    f"Opening {data.get('label') or 'that screen'}.",
                    citations,
                    routed_to,
                )
            if tool_name == "run_terminal":
                return str(tool_result.get("summary")), citations, "GOVERNED_TERMINAL"
            if tool_name == "connect_integration":
                return str(tool_result.get("summary")), citations, "INTEGRATIONS"
            if tool_name == "decide_approval":
                return str(tool_result.get("summary")), citations, "APPROVALS"
            base_summary = str(tool_result.get("summary") or "")
        else:
            base_summary = ""

        # Build honest grounding for the answer.
        context_lines = self._page_context_lines(page_context)
        context_lines += self._memory_lines(user_id, scope, company_id)
        if scope == "COMPANY" and company_id:
            name = self._company_name(company_id)
            if name:
                context_lines.append(f"Company: {name} ({company_id}).")
        if tool_result and tool_result.get("data"):
            context_lines.append(
                "Tool result: " + json.dumps(tool_result.get("data"), default=str)[:2500]
            )

        if scope == "COMPANY" and company_id:
            citations.append({
                "source_type": "INTERNAL",
                "label": f"ZONATA company registry: {self._company_name(company_id) or company_id}",
                "verified": True,
                "scope": f"Company: {company_id}",
            })

        agent_line = ""
        if role:
            meta = AGENT_DIRECTORY[role]
            agent_line = (
                f"You are answering as the {meta['label']} ({meta['title']}). "
                f"Your remit is {meta['remit']}. Do not claim authority outside that remit. "
            )

        answer = ""
        try:
            from .llm_runtime import llm_runtime
            system = (
                agent_line
                + "You are ZONATA URA Assistant, the single assistant for this application. "
                "Answer concisely, in the user's language. Use only the supplied context for "
                "facts and never invent numbers, sources or completed actions. If a tool "
                "result is present, it is the ground truth. If you do not know, say so and "
                "offer the screen or tool that would."
            )
            content = (
                (("Context:\n" + "\n".join(context_lines) + "\n\n") if context_lines else "")
                + f"Question: {prompt}"
            )
            res = llm_runtime.chat(
                tenant_id=self.tenant_id,
                company_id=company_id or "",
                system=system,
                messages=[{"role": "user", "content": content}],
                max_tokens=700,
                temperature=0.3,
                intent="assistant",
            )
            if res and res.content and not res.degraded:
                answer = res.content.strip()
                citations.append({
                    "source_type": "MODEL",
                    "label": f"{res.provider}/{res.model or 'default'}",
                    "verified": False,
                })
        except Exception as exc:
            logger.warning("Assistant model unavailable: %s", exc)

        if not answer:
            if base_summary:
                answer = base_summary
            elif role:
                meta = AGENT_DIRECTORY[role]
                answer = (
                    f"The {meta['label']} cannot answer that without a language model or live "
                    "records. Nothing was executed. Open the relevant screen or configure a "
                    "model key in Settings."
                )
            else:
                answer = (
                    "I could not reach a language model and found no matching live records, "
                    "so I will not invent an answer. Nothing was executed."
                )

        return answer, citations, routed_to

    # --------------------------------------------------------------- helpers
    def _preview_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "delegate_task":
            return f"Delegate “{str(args.get('prompt') or '')[:90]}” to the Co-worker"
        if name == "decide_approval":
            verdict = "Approve" if args.get("approved") else "Decline"
            return f"{verdict} approval {args.get('request_id')}"
        if name == "change_setting":
            return f"Change setting {args.get('key')} to {json.dumps(args.get('value'), default=str)}"
        if name == "generate_report":
            return "Generate a business intelligence report"
        if name == "install_agent":
            return "Prepare a new agent blueprint"
        if name == "connect_integration":
            return f"Start connecting {args.get('provider') or 'an integration'}"
        if name == "run_terminal":
            return f"Run the command “{str(args.get('command') or '')[:80]}”"
        return name.replace("_", " ")

    def _is_confirmed(self, prompt: str, args: Dict[str, Any]) -> bool:
        if args.get("confirmed") is True:
            return True
        return bool(_CONFIRM_WORDS.search(prompt or ""))

    def _chunks(self, text: str, size: int = 64) -> Iterator[str]:
        text = text or ""
        if not text:
            return
        for i in range(0, len(text), size):
            yield text[i:i + size]

    def _company_name(self, company_id: Optional[str]) -> Optional[str]:
        if not company_id:
            return None
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT name FROM companies WHERE company_id = ? AND tenant_id = ?",
                    (company_id, self.tenant_id),
                ).fetchone()
            return row["name"] if row else None
        except Exception:
            return None

    def _assistant_service(self):
        from .assistant_service import FloatingAssistantService
        return FloatingAssistantService(tenant_id=self.tenant_id)

    def _record_assistant_turn(
        self,
        assistant: Any,
        session_id: str,
        user_id: str,
        scope: str,
        company_id: Optional[str],
        answer: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        intent: str = "INFORMATION",
    ) -> None:
        try:
            assistant._record_message(
                session_id=session_id,
                user_id=user_id,
                company_id=company_id if scope == "COMPANY" else None,
                sender="assistant",
                workspace_mode=scope,
                content=answer,
                citations=citations or [],
                intent_category=intent,
            )
        except Exception:
            logger.exception("Could not record the assistant answer")


__all__ = [
    "AGENT_DIRECTORY",
    "SCREENS",
    "TOOL_SPECS",
    "URAAssistantService",
    "_normalise_target",
    "_plan_tool",
]
