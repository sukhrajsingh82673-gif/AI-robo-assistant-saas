"""
RoboAssistant Company OS 2.0 — Browser Robot Execution Fabric
Provides structured web automation, DOM extraction, form interaction,
and session management. Prefers structured DOM/API interaction over coordinate clicking.
"""

from typing import Dict, List, Optional, Any
import time
import urllib.parse
import urllib.request
import json
import hashlib
from .models import ActionContract

class BrowserExecutionFabric:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or "sess_default"
        self.current_url: str = "about:blank"
        self.tabs: List[Dict[str, Any]] = [{"tab_id": "tab_1", "url": "about:blank", "title": "New Tab"}]
        self.active_tab_index: int = 0

    def navigate(self, url: str) -> Dict[str, Any]:
        """Performs a real HTTP GET and reports the observed status code."""
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {
                "success": False,
                "error": f"Invalid URL format: '{url}'",
                "verified": False,
            }
        if parsed.scheme not in ("http", "https"):
            return {
                "success": False,
                "error": f"Unsupported scheme '{parsed.scheme}'; only http/https are allowed",
                "verified": False,
            }

        start = time.time()
        self.current_url = url
        self.tabs[self.active_tab_index]["url"] = url
        self.tabs[self.active_tab_index]["title"] = f"Page: {parsed.netloc}"

        req = urllib.request.Request(url, headers={"User-Agent": "ZONATA-BrowserRobot/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read(200_000)
                status_code = resp.status
                content_type = resp.headers.get("Content-Type", "")
                title = self.tabs[self.active_tab_index]["title"]
                try:
                    text = body.decode("utf-8", errors="ignore")
                    import re as _re
                    m = _re.search(r"<title[^>]*>(.*?)</title>", text, _re.IGNORECASE | _re.DOTALL)
                    if m:
                        title = m.group(1).strip()[:200]
                except Exception:
                    pass
            self.tabs[self.active_tab_index]["title"] = title
            return {
                "success": True,
                "url": self.current_url,
                "title": title,
                "http_status": status_code,
                "content_type": content_type,
                "bytes_received": len(body),
                "load_time_ms": int((time.time() - start) * 1000),
                "verified": True,
                "simulated": False,
                "execution_mode": "LIVE_HTTP",
                "provenance": "REAL_HTTP_GET",
                "details": f"GET {url} returned HTTP {status_code}",
            }
        except Exception as exc:
            return {
                "success": False,
                "url": url,
                "error": f"{type(exc).__name__}: {exc}",
                "load_time_ms": int((time.time() - start) * 1000),
                "verified": False,
                "simulated": False,
                "execution_mode": "LIVE_HTTP",
                "provenance": "REAL_HTTP_GET",
                "details": f"GET {url} failed",
            }

    def extract_structured_data(self, selector_type: str = "TEXT", query: str = "") -> Dict[str, Any]:
        """No DOM engine is installed, so nothing is extracted (no fixtures)."""
        return {
            "success": False,
            "current_url": self.current_url,
            "query": query,
            "extracted_items": [],
            "error": "No DOM extraction engine is available on this host.",
            "code": "DOM_ENGINE_NOT_AVAILABLE",
            "verified": False,
            "simulated": False,
            "execution_mode": "NOT_EXECUTED",
        }

    def submit_form(self, form_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Form submission requires a browser driver, which is not configured."""
        # Invariant: Redact any password fields from the telemetry return
        safe_fields = {k: ("***REDACTED***" if "pass" in k.lower() or "secret" in k.lower() else v) for k, v in fields.items()}
        return {
            "success": False,
            "form_id": form_id,
            "fields_submitted": safe_fields,
            "status": "NOT_SUBMITTED",
            "error": "No browser driver is configured for form submission.",
            "code": "BROWSER_DRIVER_NOT_CONFIGURED",
            "verified": False,
            "simulated": False,
            "execution_mode": "NOT_EXECUTED",
        }

    def capture_viewport(self) -> Dict[str, Any]:
        return {
            "success": False,
            "current_url": self.current_url,
            "viewport": None,
            "sha256": None,
            "error": "No display server is attached; viewport capture is unavailable.",
            "code": "DISPLAY_NOT_AVAILABLE",
            "verified": False,
            "simulated": False,
            "execution_mode": "NOT_EXECUTED",
        }
