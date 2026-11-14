"""
URA Assistant — persistent background jobs.

A job is a small, honest unit of work that survives a page reload.  At most
three jobs may be active (queued, running or paused) per user; the limit is
enforced on the server, not only in the browser.

A job records every step it takes.  Pause, resume, cancel and retry act on the
stored row, and the worker checks the row between steps so a pause from another
request really stops progress.  Nothing is marked complete without a result: a
job with no executor, no provider or no data ends as `FAILED` with a plain
reason instead of a fabricated success.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .db import db

logger = logging.getLogger(__name__)

MAX_ACTIVE_JOBS = 3
ACTIVE_STATUSES = ("QUEUED", "RUNNING", "PAUSED")
TERMINAL_STATUSES = ("SUCCEEDED", "FAILED", "CANCELLED")

JOB_KINDS = ("research", "query")


def _now() -> float:
    return time.time()


class AssistantJobStore:
    """Persistence for assistant jobs.  One row per job."""

    def __init__(self, tenant_id: str = "tnt_primary") -> None:
        self.tenant_id = tenant_id
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assistant_jobs (
                        job_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        company_id TEXT,
                        user_id TEXT NOT NULL,
                        session_id TEXT,
                        kind TEXT NOT NULL DEFAULT 'research',
                        title TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        workspace_mode TEXT NOT NULL DEFAULT 'PERSONAL',
                        status TEXT NOT NULL DEFAULT 'QUEUED',
                        progress REAL NOT NULL DEFAULT 0,
                        step TEXT NOT NULL DEFAULT 'Queued',
                        steps JSON,
                        result JSON,
                        citations JSON,
                        error TEXT,
                        notification_seen INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        finished_at REAL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assistant_jobs_user "
                    "ON assistant_jobs(tenant_id, user_id, created_at)"
                )
                conn.commit()
        except Exception:
            logger.exception("Could not ensure assistant_jobs table")

    # ------------------------------------------------------------------ read
    def _row_to_job(self, row: Any) -> Dict[str, Any]:
        job = dict(row)
        for key in ("steps", "result", "citations"):
            value = job.get(key)
            if isinstance(value, str):
                try:
                    job[key] = json.loads(value) if value else None
                except Exception:
                    job[key] = None
        if not job.get("steps"):
            job["steps"] = []
        return job

    def get(self, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM assistant_jobs WHERE job_id = ? AND tenant_id = ?"
        params: List[Any] = [job_id, self.tenant_id]
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        with db.get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return self._row_to_job(row) if row else None

    def list(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM assistant_jobs WHERE tenant_id = ? AND user_id = ?"
        params: List[Any] = [self.tenant_id, user_id]
        if status == "active":
            sql += " AND status IN ('QUEUED','RUNNING','PAUSED')"
        elif status and status != "all":
            sql += " AND status = ?"
            params.append(status.upper())
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 100)))
        with db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    def active_count(self, user_id: str) -> int:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM assistant_jobs "
                "WHERE tenant_id = ? AND user_id = ? AND status IN ('QUEUED','RUNNING','PAUSED')",
                (self.tenant_id, user_id),
            ).fetchone()
        return int(row["c"]) if row else 0

    def unseen_count(self, user_id: str) -> int:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM assistant_jobs "
                "WHERE tenant_id = ? AND user_id = ? AND notification_seen = 0 "
                "AND status IN ('SUCCEEDED','FAILED')",
                (self.tenant_id, user_id),
            ).fetchone()
        return int(row["c"]) if row else 0

    # ----------------------------------------------------------------- write
    def create(
        self,
        user_id: str,
        title: str,
        prompt: str,
        kind: str = "research",
        company_id: Optional[str] = None,
        workspace_mode: str = "PERSONAL",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        now = _now()
        steps = [{"at": now, "label": "Queued", "progress": 0}]
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO assistant_jobs (
                    job_id, tenant_id, company_id, user_id, session_id, kind, title,
                    prompt, workspace_mode, status, progress, step, steps, result,
                    citations, error, notification_seen, created_at, updated_at,
                    finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, 'Queued', ?, NULL,
                          NULL, NULL, 0, ?, ?, NULL)
                """,
                (
                    job_id, self.tenant_id, company_id, user_id, session_id,
                    kind if kind in JOB_KINDS else "research", title[:160], prompt,
                    workspace_mode, json.dumps(steps), now, now,
                ),
            )
            conn.commit()
        return self.get(job_id, user_id) or {}

    def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        step: Optional[str] = None,
        append_step: bool = False,
        result: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        seen: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        job = self.get(job_id)
        if not job:
            return None
        now = _now()
        steps = list(job.get("steps") or [])
        if step is not None:
            steps.append({"at": now, "label": step, "progress": progress if progress is not None else job.get("progress", 0)})
        fields = ["updated_at = ?"]
        params: List[Any] = [now]
        if status is not None:
            fields.append("status = ?")
            params.append(status.upper())
            if status.upper() in TERMINAL_STATUSES:
                fields.append("finished_at = ?")
                params.append(now)
        if progress is not None:
            fields.append("progress = ?")
            params.append(max(0.0, min(100.0, float(progress))))
        if step is not None:
            fields.append("step = ?")
            params.append(step)
            fields.append("steps = ?")
            params.append(json.dumps(steps))
        if result is not None:
            fields.append("result = ?")
            params.append(json.dumps(result, default=str))
        if citations is not None:
            fields.append("citations = ?")
            params.append(json.dumps(citations, default=str))
        if error is not None:
            fields.append("error = ?")
            params.append(error)
        if seen is not None:
            fields.append("notification_seen = ?")
            params.append(1 if seen else 0)
        sql = f"UPDATE assistant_jobs SET {', '.join(fields)} WHERE job_id = ? AND tenant_id = ?"
        params.extend([job_id, self.tenant_id])
        with db.get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()
        return self.get(job_id)

    def mark_all_seen(self, user_id: str) -> Dict[str, Any]:
        with db.get_connection() as conn:
            cur = conn.execute(
                "UPDATE assistant_jobs SET notification_seen = 1 "
                "WHERE tenant_id = ? AND user_id = ? AND notification_seen = 0",
                (self.tenant_id, user_id),
            )
            conn.commit()
            changed = cur.rowcount or 0
        return {"success": True, "marked": changed}

    def reset_for_retry(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        job = self.get(job_id, user_id)
        if not job:
            return None
        steps = [{"at": _now(), "label": "Retry queued", "progress": 0}]
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE assistant_jobs
                SET status = 'QUEUED', progress = 0, step = 'Retry queued', steps = ?,
                    result = NULL, citations = NULL, error = NULL,
                    notification_seen = 0, updated_at = ?, finished_at = NULL
                WHERE job_id = ? AND tenant_id = ? AND user_id = ?
                """,
                (json.dumps(steps), _now(), job_id, self.tenant_id, user_id),
            )
            conn.commit()
        return self.get(job_id, user_id)


class AssistantJobRunner:
    """
    Runs jobs on a small thread pool and records progress as it goes.

    A singleton is used because the worker threads must outlive a single HTTP
    request.  Jobs are also resumable: a job left `RUNNING` by a process restart
    is marked `FAILED` (honestly) the next time the server starts.
    """

    _instance: Optional["AssistantJobRunner"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=MAX_ACTIVE_JOBS, thread_name_prefix="ura-job")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._guard = threading.Lock()

    @classmethod
    def instance(cls) -> "AssistantJobRunner":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # --------------------------------------------------------------- control
    def start(self, store: AssistantJobStore, job: Dict[str, Any]) -> None:
        job_id = job["job_id"]
        with self._guard:
            self._jobs[job_id] = {"store": store, "paused": False, "cancelled": False}
        self._pool.submit(self._run, store, job_id)

    def request_pause(self, job_id: str, paused: bool) -> None:
        with self._guard:
            state = self._jobs.get(job_id)
            if state:
                state["paused"] = paused

    def request_cancel(self, job_id: str) -> None:
        with self._guard:
            state = self._jobs.get(job_id)
            if state:
                state["cancelled"] = True
                state["paused"] = False

    def is_live(self, job_id: str) -> bool:
        with self._guard:
            return job_id in self._jobs

    # ---------------------------------------------------------------- worker
    def _run(self, store: AssistantJobStore, job_id: str) -> None:
        job = store.get(job_id)
        if not job:
            return
        try:
            store.update(job_id, status="RUNNING", progress=5, step="Planning", append_step=True)
            if not self._wait_if_paused(store, job_id):
                return
            kind = job.get("kind") or "research"
            if kind == "research":
                self._run_research(store, job)
            else:
                self._run_query(store, job)
        except Exception as exc:  # defensive: a job must never crash the process
            logger.exception("Assistant job failed: %s", job_id)
            store.update(
                job_id,
                status="FAILED",
                progress=100,
                step="Failed",
                error=f"{type(exc).__name__}: {exc}",
                append_step=True,
            )
        finally:
            with self._guard:
                self._jobs.pop(job_id, None)

    def _wait_if_paused(self, store: AssistantJobStore, job_id: str) -> bool:
        """Return False when the job was cancelled while paused."""
        while True:
            with self._guard:
                state = self._jobs.get(job_id)
                if not state:
                    return False
                if state["cancelled"]:
                    current = store.get(job_id)
                    if current and current["status"] not in TERMINAL_STATUSES:
                        store.update(job_id, status="CANCELLED", progress=current.get("progress", 0),
                                     step="Cancelled", append_step=True)
                    return False
                if not state["paused"]:
                    return True
            time.sleep(0.25)

    def _step(self, store: AssistantJobStore, job_id: str, progress: float, label: str) -> bool:
        if not self._wait_if_paused(store, job_id):
            return False
        store.update(job_id, progress=progress, step=label, append_step=True)
        return True

    def _run_research(self, store: AssistantJobStore, job: Dict[str, Any]) -> None:
        from .ura_assistant_web import (
            filter_results, get_web_search_provider, load_web_access,
        )

        job_id = job["job_id"]
        prompt = job.get("prompt") or ""
        tenant_id = job.get("tenant_id") or store.tenant_id
        company_id = job.get("company_id")
        policy = load_web_access(tenant_id, company_id)
        provider = get_web_search_provider()

        if not self._step(store, job_id, 15, f"Checking web access ({policy.mode})"):
            return
        if policy.mode == "off":
            store.update(
                job_id, status="FAILED", progress=100, step="Web access is off",
                error="Web access is off for this workspace, so research did not run. Turn it on in Assistant → Web access.",
                append_step=True,
            )
            return
        if not provider.configured():
            store.update(
                job_id, status="FAILED", progress=100, step="Web search is not configured",
                error="No web search provider is configured on the server, so no pages were searched.",
                append_step=True,
            )
            return

        if not self._step(store, job_id, 35, f"Searching the web with {provider.label}"):
            return
        try:
            results = provider.search(prompt, limit=6)
        except Exception as exc:
            store.update(
                job_id, status="FAILED", progress=100, step="Search failed",
                error=str(exc), append_step=True,
            )
            return

        if not self._step(store, job_id, 55, "Checking sources against the allow and block lists"):
            return
        allowed, blocked = filter_results(results, policy)
        if not allowed:
            reason = (
                blocked[0]["reason"] if blocked
                else "The provider returned no results, so there is nothing to cite."
            )
            store.update(
                job_id, status="FAILED", progress=100, step="No allowed sources",
                error=reason, append_step=True,
            )
            return

        if not self._step(store, job_id, 70, "Reading the allowed sources"):
            return

        citations: List[Dict[str, Any]] = []
        lines: List[str] = []
        for index, result in enumerate(allowed, start=1):
            citations.append({
                "source_type": "WEB",
                "label": result.title,
                "url": result.url,
                "provider": result.provider,
                "sample": bool(result.sample),
                "verified": not result.sample,
            })
            snippet = (result.snippet or "").strip()
            lines.append(f"{index}. {result.title} — {result.domain}")
            if snippet:
                lines.append(f"   {snippet}")
            if result.sample:
                lines.append("   Sample data. Not a real source.")

        summary_lines = [
            f"Research on “{prompt[:120]}” used {len(allowed)} allowed source(s).",
            "",
            *lines,
        ]
        if blocked:
            summary_lines.append("")
            summary_lines.append("Excluded by the access policy:")
            for item in blocked:
                summary_lines.append(f"- {item['url']} — {item['reason']}")
        if provider.is_sample:
            summary_lines.append("")
            summary_lines.append(
                "Sample provider: these are demonstration results, not pages fetched from the internet."
            )

        if not self._step(store, job_id, 90, "Writing the sourced summary"):
            return

        store.update(
            job_id,
            status="SUCCEEDED",
            progress=100,
            step="Completed",
            result={
                "summary": "\n".join(summary_lines),
                "sources": citations,
                "blocked": blocked,
                "sample": bool(provider.is_sample),
            },
            citations=citations,
            append_step=True,
        )

    def _run_query(self, store: AssistantJobStore, job: Dict[str, Any]) -> None:
        from .ura_assistant_service import URAAssistantService

        job_id = job["job_id"]
        tenant_id = job.get("tenant_id") or store.tenant_id
        scope = str(job.get("workspace_mode") or "PERSONAL").upper()
        if scope != "COMPANY" or not job.get("company_id"):
            store.update(
                job_id, status="FAILED", progress=100, step="Company scope is required",
                error=(
                    "This background job reads company data, and you are in Personal scope. "
                    "Switch to Company scope (after the AI CEO approval) and start it again."
                ),
                append_step=True,
            )
            return
        if not self._step(store, job_id, 40, "Reading live app data"):
            return
        service = URAAssistantService(tenant_id=tenant_id)
        result = service.execute_tool(
            "query_data",
            {"query": job.get("prompt") or ""},
            user_id=job.get("user_id") or "usr_owner",
            scope="COMPANY",
            company_id=job.get("company_id"),
        )
        if not result.get("ok"):
            store.update(
                job_id, status="FAILED", progress=100, step="Could not read the data",
                error=str(result.get("summary") or "The query did not complete."),
                append_step=True,
            )
            return
        data = result.get("data") or {}
        summary = result.get("answer") or result.get("summary") or "The query completed."
        store.update(
            job_id, status="SUCCEEDED", progress=100, step="Completed",
            result={"summary": summary, "items": data.get("items") or []},
            append_step=True,
        )


__all__ = [
    "ACTIVE_STATUSES",
    "AssistantJobRunner",
    "AssistantJobStore",
    "JOB_KINDS",
    "MAX_ACTIVE_JOBS",
    "TERMINAL_STATUSES",
]
