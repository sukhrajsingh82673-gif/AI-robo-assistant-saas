"""
ZONATA — Google Calendar provider adapter.

The assistant may only claim a meeting is scheduled when a real calendar
provider has confirmed the event.  This module performs that call with an OAuth
access token supplied by the Owner through the environment (or an injected
adapter in tests).  It never synthesises Meet links, event IDs, or dial-in
numbers.

Configuration (never committed):

    ZONATA_GOOGLE_CALENDAR_ACCESS_TOKEN   OAuth2 access token with calendar.events
    ZONATA_GOOGLE_CALENDAR_ID            calendar id, default "primary"
    ZONATA_GOOGLE_CALENDAR_TIMEOUT       optional request timeout in seconds
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class CalendarProviderError(Exception):
    """Raised when a provider is configured but the call fails."""


class GoogleCalendarProvider:
    """Minimal Google Calendar v3 client used for genuine event creation."""

    name = "GOOGLE_MEET"

    def __init__(
        self,
        access_token: Optional[str] = None,
        calendar_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.access_token = (access_token or os.environ.get("ZONATA_GOOGLE_CALENDAR_ACCESS_TOKEN", "")).strip()
        self.calendar_id = (calendar_id or os.environ.get("ZONATA_GOOGLE_CALENDAR_ID", "primary") or "primary").strip()
        self.timeout = float(
            timeout
            if timeout is not None
            else os.environ.get("ZONATA_GOOGLE_CALENDAR_TIMEOUT", "20")
        )

    def is_configured(self) -> bool:
        return bool(self.access_token)

    @staticmethod
    def _rfc3339(ts: float) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

    def create_event(
        self,
        summary: str,
        description: str,
        start_ts: float,
        end_ts: float,
        attendees: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a calendar event with a Meet conference request.

        Returns a dict with ``confirmed`` plus the provider-issued identifiers.
        Raises :class:`CalendarProviderError` when the provider call fails.
        """
        if not self.is_configured():
            raise CalendarProviderError("GOOGLE_CALENDAR_NOT_CONFIGURED")

        calendar_id = urllib.parse.quote(self.calendar_id, safe="")
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            "?conferenceDataVersion=1&sendUpdates=all"
        )
        body: Dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": self._rfc3339(start_ts), "timeZone": "UTC"},
            "end": {"dateTime": self._rfc3339(end_ts), "timeZone": "UTC"},
            "conferenceData": {
                "createRequest": {
                    "requestId": request_id or f"zonata-{int(time.time() * 1000)}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        clean_attendees = [a for a in (attendees or []) if a and "@" in a]
        if clean_attendees:
            body["attendees"] = [{"email": a} for a in clean_attendees]

        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:400]
            except Exception:
                pass
            raise CalendarProviderError(f"GOOGLE_CALENDAR_HTTP_{exc.code}: {detail}") from exc
        except Exception as exc:  # network, timeout, malformed response
            raise CalendarProviderError(f"GOOGLE_CALENDAR_CALL_FAILED: {type(exc).__name__}") from exc

        event_id = str(raw.get("id") or "")
        if not event_id:
            raise CalendarProviderError("GOOGLE_CALENDAR_NO_EVENT_ID")

        meet_url = str(raw.get("hangoutLink") or "")
        dial_in: Dict[str, Any] = {}
        conference = raw.get("conferenceData") or {}
        for entry in conference.get("entryPoints") or []:
            entry_type = str(entry.get("entryPointType") or "")
            uri = str(entry.get("uri") or "")
            if entry_type == "video" and not meet_url:
                meet_url = uri
            elif entry_type == "phone":
                dial_in = {
                    "phone": entry.get("label") or uri,
                    "pin": entry.get("pin") or "",
                    "uri": uri,
                }
                break

        return {
            "confirmed": True,
            "provider": self.name,
            "event_id": event_id,
            "html_link": str(raw.get("htmlLink") or ""),
            "meet_url": meet_url,
            "dial_in": dial_in,
            "status": str(raw.get("status") or "confirmed"),
            "raw": raw,
        }


def resolve_calendar_provider(provider: Any = None) -> Any:
    """Return the provider to use, or the environment-configured Google client."""
    if provider is not None:
        return provider
    return GoogleCalendarProvider()
