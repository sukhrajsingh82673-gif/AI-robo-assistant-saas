"""
URA Assistant — meetings, calendar and transcription adapters.

Meetings are company data and they stay honest:

* scheduling only claims success after the existing Google Calendar provider
  confirms the event (``core/calendar_provider.py``); otherwise the assistant
  says nothing was booked and shows no link;
* a pre-meeting brief is assembled from live tables (approvals, decisions,
  missions, meetings) and never invents a number;
* notes are transcript entries written by the Owner, and only the Owner writes
  them;
* a summary is compiled from the stored transcript, notes and decisions, and
  the existing minutes generator is used for the PDF;
* an action item becomes a governed Co-worker task, or an approval request when
  the Owner says it needs one;
* transcription is an adapter.  With no provider configured the assistant says
  transcription is not connected and records no audio.  The sample provider is
  explicitly enabled, returns clearly-labelled sample lines, and never pretends
  to have heard a real meeting.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .db import db

logger = logging.getLogger(__name__)

RECORDING_SETTING = "assistant_meeting_recording_notice"

ANNOUNCEMENT = (
    "Recording and transcription announcement: this session is recorded and its "
    "transcript is stored in the company meeting record. If you do not consent, "
    "say so now."
)
SAMPLE_ANNOUNCEMENT = (
    "Recording announcement (sample mode): this session would be recorded and "
    "transcribed into the company meeting record. No audio is captured in this build."
)


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def calendar_status(provider: Any = None) -> Dict[str, Any]:
    """Report the real calendar provider; never create a fake event."""
    try:
        from .calendar_provider import resolve_calendar_provider

        client = resolve_calendar_provider(provider)
        configured = bool(client is not None and getattr(client, "is_configured", lambda: False)())
        return {
            "configured": configured,
            "provider": "google_calendar" if configured else "none",
            "label": "Google Calendar" if configured else "Calendar not connected",
            "message": (
                "Scheduling uses Google Calendar, and every confirmed slot is recorded."
                if configured
                else "Calendar is not connected. No meeting can be booked and no link exists."
            ),
        }
    except Exception:
        logger.warning("Could not resolve the calendar provider", exc_info=True)
        return {
            "configured": False,
            "provider": "none",
            "label": "Calendar not connected",
            "message": "Calendar is not connected. No meeting can be booked and no link exists.",
        }


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

class TranscriptionAdapter(ABC):
    """Typed transcription adapter.  Implementations must be honest."""

    provider_id: str = "none"
    label: str = "Transcription not connected"
    is_sample: bool = False

    @abstractmethod
    def configured(self) -> bool:
        ...

    @abstractmethod
    def transcribe(self, meeting: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return transcript segments, or raise with a plain reason."""


class NoTranscriptionAdapter(TranscriptionAdapter):
    provider_id = "none"
    label = "Transcription not connected"

    def configured(self) -> bool:
        return False

    def transcribe(self, meeting: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise RuntimeError(
            "Transcription is not connected on this server, so no audio was "
            "recorded and no transcript exists."
        )


class SampleTranscriptionAdapter(TranscriptionAdapter):
    """Clearly labelled sample lines.  No audio is captured."""

    provider_id = "sample"
    label = "Sample transcript (not connected)"
    is_sample = True

    def configured(self) -> bool:
        return True

    def transcribe(self, meeting: Dict[str, Any]) -> List[Dict[str, Any]]:
        now = time.time()
        lines = [
            "Sample transcript line: no microphone was opened and no audio was captured.",
            "Sample transcript line: this text demonstrates how live notes would appear.",
            "Sample transcript line: it must not be treated as something anyone said.",
            "Sample transcript line: connect a real transcription provider to capture audio.",
        ]
        return [
            {
                "speaker": "Sample transcript",
                "mode": "SAMPLE",
                "text": line,
                "sample": True,
                "timestamp": now + index * 0.2,
            }
            for index, line in enumerate(lines)
        ]


def get_transcription_adapter() -> TranscriptionAdapter:
    choice = os.environ.get("URA_ASSISTANT_TRANSCRIPTION_PROVIDER", "none").strip().lower()
    if choice == "sample":
        return SampleTranscriptionAdapter()
    return NoTranscriptionAdapter()


def transcription_status() -> Dict[str, Any]:
    adapter = get_transcription_adapter()
    return {
        "configured": bool(adapter.configured()),
        "provider": adapter.provider_id,
        "label": adapter.label,
        "sample": bool(adapter.is_sample),
    }


def recording_notice(tenant_id: str, company_id: Optional[str]) -> Dict[str, Any]:
    """Read the announce-recording setting and prepare plain-language copy."""
    enabled = True
    try:
        from .settings_service import settings_service

        enabled = bool(
            settings_service.get_effective_setting(
                tenant_id, company_id, RECORDING_SETTING, True
            )
        )
    except Exception:
        logger.warning("Could not read the recording announcement setting", exc_info=True)

    adapter = get_transcription_adapter()
    if adapter.is_sample:
        text = (
            "Sample transcript only. No audio is being recorded. The announcement "
            "below is shown so the meeting flow can be reviewed."
        )
    elif adapter.configured():
        text = (
            "Recording and transcription are on. Everyone in the meeting must be "
            "told before the recording starts."
        )
    else:
        text = (
            "Transcription is not connected, so no audio is recorded. The "
            "announcement is ready for when a provider is configured."
        )
    return {
        "enabled": enabled,
        "text": text,
        "announcement": (SAMPLE_ANNOUNCEMENT if adapter.is_sample else ANNOUNCEMENT) if enabled else "",
        "transcription": {
            "configured": bool(adapter.configured()),
            "provider": adapter.provider_id,
            "label": adapter.label,
            "sample": bool(adapter.is_sample),
        },
    }


# ---------------------------------------------------------------------------
# Meeting service for the assistant
# ---------------------------------------------------------------------------

def _snippet(text: str, query: str, width: int = 90) -> str:
    text = (text or "").strip().replace("\n", " ")
    if not query:
        return text[: width * 2]
    low = text.lower()
    index = low.find(query.lower())
    if index < 0:
        return text[: width * 2]
    start = max(0, index - width)
    end = min(len(text), index + len(query) + width)
    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


class AssistantMeetingService:
    """Company-scoped meeting operations used by the assistant."""

    def __init__(self, tenant_id: str = "tnt_primary") -> None:
        self.tenant_id = tenant_id

    def _meeting_service(self):
        from .meeting_service import AiCeoMeetingService

        return AiCeoMeetingService(tenant_id=self.tenant_id)

    # ------------------------------------------------------------------ read
    def brief(self, company_id: str) -> Dict[str, Any]:
        """Assemble a pre-meeting brief from live app data only."""
        now = time.time()
        company = {"company_id": company_id, "name": "Selected company", "industry": ""}
        pending: List[Dict[str, Any]] = []
        decisions: List[Dict[str, Any]] = []
        missions: List[Dict[str, Any]] = []
        scheduled: List[Dict[str, Any]] = []
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT company_id, name, industry FROM companies WHERE company_id = ? AND tenant_id = ?",
                (company_id, self.tenant_id),
            ).fetchone()
            if row:
                company = {"company_id": row["company_id"], "name": row["name"], "industry": row["industry"] or ""}
            for item in conn.execute(
                "SELECT request_id, action_desc, risk_level, status FROM approvals "
                "WHERE tenant_id = ? AND company_id = ? AND status = 'PENDING' "
                "ORDER BY requested_at DESC LIMIT 5",
                (self.tenant_id, company_id),
            ).fetchall():
                pending.append(dict(item))
            for item in conn.execute(
                "SELECT mission_id, title, status, progress FROM missions "
                "WHERE tenant_id = ? AND company_id = ? "
                "AND status NOT IN ('COMPLETED','CANCELLED','FAILED') "
                "ORDER BY started_at DESC LIMIT 5",
                (self.tenant_id, company_id),
            ).fetchall():
                missions.append(dict(item))
            for item in conn.execute(
                "SELECT meeting_id, title, status, strategic_context, created_at FROM ai_ceo_meetings "
                "WHERE tenant_id = ? AND company_id = ? AND status = 'Scheduled' "
                "ORDER BY created_at DESC LIMIT 3",
                (self.tenant_id, company_id),
            ).fetchall():
                scheduled.append(dict(item))
        try:
            decisions = self._meeting_service().list_decisions(company_id)[:5]
        except Exception:
            logger.warning("Could not read decisions for the brief", exc_info=True)

        agenda: List[str] = []
        if pending:
            agenda.append(
                f"Decide {len(pending)} pending approval(s), starting with "
                f"“{str(pending[0].get('action_desc') or '')[:80]}”."
            )
        if decisions:
            agenda.append(
                f"Review {len(decisions)} recorded decision(s) since the last sessions."
            )
        if missions:
            agenda.append(
                f"Check {len(missions)} open mission(s); the least advanced is "
                f"“{str(missions[-1].get('title') or '')[:70]}” "
                f"at {int(missions[-1].get('progress') or 0)}%."
            )
        if scheduled:
            agenda.append(f"Prepare for the confirmed slot “{str(scheduled[0].get('title') or '')[:70]}”.")
        if not agenda:
            agenda.append(
                "No pending approvals, recorded decisions, open missions or confirmed "
                "slots were found. Use the session to set the next objectives."
            )

        lines = [
            f"Pre-meeting brief for {company['name']}.",
            "",
            f"- Pending approvals: {len(pending)}",
            f"- Recent decisions: {len(decisions)}",
            f"- Open missions: {len(missions)}",
            f"- Confirmed scheduled meetings: {len(scheduled)}",
            "",
            "Suggested agenda:",
            *[f"{index + 1}. {item}" for index, item in enumerate(agenda)],
        ]
        if pending:
            lines.append("")
            lines.append("Pending approvals:")
            for item in pending:
                lines.append(f"- {item['action_desc']} ({item.get('risk_level') or 'MEDIUM'} risk)")
        if decisions:
            lines.append("")
            lines.append("Recent decisions:")
            for item in decisions:
                lines.append(f"- {item.get('title')}: {item.get('status')} ({item.get('decision_id')})")
        if missions:
            lines.append("")
            lines.append("Open missions:")
            for item in missions:
                lines.append(
                    f"- {item.get('title')} — {item.get('status')} at {int(item.get('progress') or 0)}%"
                )
        return {
            "company": company,
            "generated_at": now,
            "pending_approvals": pending,
            "decisions": decisions,
            "missions": missions,
            "scheduled_meetings": scheduled,
            "agenda": agenda,
            "summary": "\n".join(lines),
            "sources": [
                {"source_type": "INTERNAL", "label": "Live approvals, decisions, missions and meetings", "verified": True}
            ],
        }

    def library(self, company_id: str, query: str = "", limit: int = 20) -> Dict[str, Any]:
        q = (query or "").strip()
        rows: List[Any] = []
        snippets: Dict[str, List[Dict[str, Any]]] = {}
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT meeting_id, title, status, strategic_context, summary, created_at "
                "FROM ai_ceo_meetings WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (self.tenant_id, company_id, max(1, min(int(limit), 50))),
            ).fetchall()
            if q:
                matches = conn.execute(
                    "SELECT meeting_id, speaker, message FROM ai_ceo_meeting_transcripts "
                    "WHERE tenant_id = ? AND company_id = ? AND LOWER(message) LIKE ? "
                    "ORDER BY timestamp DESC LIMIT 50",
                    (self.tenant_id, company_id, f"%{q.lower()}%"),
                ).fetchall()
                for match in matches:
                    snippets.setdefault(match["meeting_id"], []).append({
                        "speaker": match["speaker"],
                        "snippet": _snippet(match["message"], q),
                    })
        meetings: List[Dict[str, Any]] = []
        for row in rows:
            matches = snippets.get(row["meeting_id"]) or []
            haystack = " ".join(
                str(row[key] or "") for key in ("title", "strategic_context", "summary")
            ).lower()
            if q and q.lower() not in haystack and not matches:
                continue
            meetings.append({
                "meeting_id": row["meeting_id"],
                "title": row["title"],
                "status": row["status"],
                "strategic_context": row["strategic_context"] or "",
                "summary": row["summary"] or "",
                "created_at": row["created_at"],
                "matches": matches[:3],
            })
            if len(meetings) >= limit:
                break
        return {"meetings": meetings, "query": q, "count": len(meetings)}

    def notes(self, company_id: str, meeting_id: Optional[str] = None) -> Dict[str, Any]:
        svc = self._meeting_service()
        meeting = svc.get_meeting(meeting_id) if meeting_id else svc.get_or_create_active_meeting(company_id)
        if not meeting:
            return {"success": False, "message": "That meeting was not found.", "notes": []}
        transcripts = svc.get_transcripts(meeting["meeting_id"])
        notes = [t for t in transcripts if str(t.get("mode") or "").upper() == "NOTE"]
        recent = transcripts[-8:]
        return {
            "success": True,
            "meeting": meeting,
            "notes": notes,
            "recent": recent,
            "count": len(notes),
        }

    # ----------------------------------------------------------------- write
    def listen(self, company_id: str, user_id: str) -> Dict[str, Any]:
        adapter = get_transcription_adapter()
        notice = recording_notice(self.tenant_id, company_id)
        if not adapter.configured():
            return {
                "success": False,
                "reason": "TRANSCRIPTION_NOT_CONFIGURED",
                "message": (
                    "Transcription is not connected, so I did not open a microphone "
                    "or record anything. Configure a transcription provider first."
                ),
                "recording": notice,
                "transcription": notice["transcription"],
            }

        svc = self._meeting_service()
        meeting = svc.get_or_create_active_meeting(company_id, user_id)
        if str(meeting.get("status") or "").lower() in ("ready", "paused"):
            meeting = svc.start_meeting(meeting["meeting_id"])

        already_announced = any(
            str(entry.get("related_context") or "") == "Recording announcement"
            for entry in svc.get_transcripts(meeting["meeting_id"])
        )
        announcement_written = None
        if notice.get("enabled") and notice.get("announcement") and not already_announced:
            announcement_written = svc.add_transcript_entry(
                meeting_id=meeting["meeting_id"],
                company_id=company_id,
                speaker="SYSTEM",
                mode="NOTICE",
                message=notice["announcement"],
                related_context="Recording announcement",
            )

        try:
            segments = adapter.transcribe(meeting)
        except Exception as exc:
            return {
                "success": False,
                "reason": "TRANSCRIPTION_FAILED",
                "message": str(exc),
                "meeting": meeting,
                "recording": notice,
                "transcription": notice["transcription"],
            }

        return {
            "success": True,
            "meeting": meeting,
            "recording": notice,
            "transcription": notice["transcription"],
            "segments": segments,
            "sample": bool(adapter.is_sample),
            "announcement": announcement_written or {"message": notice.get("announcement") or ""},
            "message": (
                "Listening in sample mode. The lines below are labelled sample text, "
                "not captured audio."
                if adapter.is_sample
                else "Listening. New transcript lines are added to the meeting record."
            ),
        }

    def add_note(
        self,
        company_id: str,
        note: str,
        meeting_id: Optional[str],
        user_id: str,
    ) -> Dict[str, Any]:
        text = (note or "").strip()
        if not text:
            return {"success": False, "message": "Write the note first."}
        svc = self._meeting_service()
        meeting = svc.get_meeting(meeting_id) if meeting_id else svc.get_or_create_active_meeting(company_id, user_id)
        if not meeting:
            return {"success": False, "message": "That meeting was not found."}
        entry = svc.add_transcript_entry(
            meeting_id=meeting["meeting_id"],
            company_id=company_id,
            speaker="HOST",
            mode="NOTE",
            message=text,
            related_context="Owner live note",
        )
        return {"success": True, "meeting": meeting, "note": entry}

    def summarise(
        self,
        company_id: str,
        meeting_id: Optional[str] = None,
        end_meeting: bool = False,
        user_id: str = "usr_owner",
    ) -> Dict[str, Any]:
        svc = self._meeting_service()
        meeting = svc.get_meeting(meeting_id) if meeting_id else svc.get_or_create_active_meeting(company_id, user_id)
        if not meeting:
            return {"success": False, "message": "That meeting was not found."}
        transcripts = svc.get_transcripts(meeting["meeting_id"])
        notes = [t for t in transcripts if str(t.get("mode") or "").upper() == "NOTE"]
        decisions = [
            item for item in svc.list_decisions(company_id)
            if item.get("meeting_id") == meeting["meeting_id"]
        ]
        lines = [
            f"Meeting: {meeting['title']}",
            f"Status: {meeting['status']}",
            f"Transcript entries: {len(transcripts)}",
            "",
            "Notes:",
        ]
        if notes:
            lines.extend(f"- {entry['message']}" for entry in notes)
        else:
            lines.append("- No live notes were recorded.")
        lines.extend(["", "Decisions:"])
        if decisions:
            lines.extend(f"- {item['title']}: {item['description']}" for item in decisions)
        else:
            lines.append("- No decisions were recorded in this session.")
        summary = "\n".join(lines)

        if end_meeting:
            meeting = svc.end_meeting(meeting["meeting_id"], summary)

        minutes = None
        minutes_error = None
        try:
            minutes = svc.generate_post_meeting_records(meeting["meeting_id"])
        except Exception as exc:
            logger.warning("Could not generate meeting minutes", exc_info=True)
            minutes_error = str(exc)

        return {
            "success": True,
            "meeting": meeting,
            "summary": summary,
            "notes": notes,
            "decisions": decisions,
            "minutes": minutes,
            "minutes_error": minutes_error,
        }

    def action_item(
        self,
        company_id: str,
        title: str,
        meeting_id: Optional[str],
        user_id: str,
        requires_approval: bool = False,
    ) -> Dict[str, Any]:
        text = (title or "").strip()
        if not text:
            return {"success": False, "message": "Give the action item a short title."}
        svc = self._meeting_service()
        meeting = svc.get_meeting(meeting_id) if meeting_id else None

        if requires_approval:
            from .approvals import ApprovalPipeline

            request = ApprovalPipeline.create_request(
                tenant_id=self.tenant_id,
                company_id=company_id,
                agent_id="URA_ASSISTANT",
                action_desc=f"Meeting action: {text[:140]}",
                reason=f"Raised in the meeting by the Owner ({meeting_id or 'direct'}).",
                risk_level="MEDIUM",
                consequence="The Co-worker executes the action after Owner approval.",
            )
            kind = "APPROVAL"
        else:
            from .assistant_service import FloatingAssistantService

            task = FloatingAssistantService(tenant_id=self.tenant_id).create_coworker_task(
                prompt=f"Meeting action: {text}",
                workspace_mode="COMPANY",
                company_id=company_id,
                user_id=user_id,
            )
            request = task
            kind = "TASK"

        if meeting_id and meeting:
            svc.add_transcript_entry(
                meeting_id=meeting_id,
                company_id=company_id,
                speaker="SYSTEM",
                mode="ACTION",
                message=(
                    f"Action item {'sent for approval' if requires_approval else 'assigned to the Co-worker'}: {text}"
                ),
                related_context="Meeting action item",
            )
        return {
            "success": True,
            "kind": kind,
            "title": text,
            "meeting_id": meeting_id,
            "request": request,
        }


__all__ = [
    "ANNOUNCEMENT",
    "AssistantMeetingService",
    "NoTranscriptionAdapter",
    "RECORDING_SETTING",
    "SAMPLE_ANNOUNCEMENT",
    "SampleTranscriptionAdapter",
    "TranscriptionAdapter",
    "calendar_status",
    "get_transcription_adapter",
    "recording_notice",
    "transcription_status",
]
