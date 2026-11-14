"""
URA Assistant — web research adapters and access policy.

A web search provider is a small, typed interface.  The assistant must never
invent a source: when no provider is configured the research path fails and
says so.  A sample provider exists for demos and tests only, is enabled by an
explicit server-side flag, and every result it returns is labelled as sample
data so the UI can show that label.

Real providers read their API key from the server environment.  No key is ever
sent to the browser and no key is stored in this file.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_ACCESS = "off"  # off | allowlist | open


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str = ""
    provider: str = ""
    sample: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def domain(self) -> str:
        try:
            return urllib.parse.urlparse(self.url).netloc.lower()
        except Exception:
            return ""


class WebSearchProvider(ABC):
    """Typed web search provider.  Implementations must be honest."""

    provider_id: str = "none"
    label: str = "No provider"
    is_sample: bool = False

    @abstractmethod
    def configured(self) -> bool:
        """True when the provider has everything it needs to run."""

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[WebResult]:
        """Return real results, or raise a RuntimeError with a plain reason."""


class NoWebSearchProvider(WebSearchProvider):
    provider_id = "none"
    label = "Web access is not configured"

    def configured(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> List[WebResult]:
        raise RuntimeError(
            "Web search is not configured on this server. Set a provider and its key in "
            "the server environment; nothing was searched."
        )


class SampleWebSearchProvider(WebSearchProvider):
    """
    Clearly labelled sample results.

    This provider never pretends to have read a real page.  The URLs point at
    example.com, every result carries `sample=True`, and the UI shows
    "Sample data. Not a real source."
    """

    provider_id = "sample"
    label = "Sample web results (not connected)"
    is_sample = True

    def configured(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> List[WebResult]:
        q = (query or "").strip() or "research topic"
        results = [
            WebResult(
                title=f"Sample source: overview of {q[:60]}",
                url="https://example.com/sample/overview",
                snippet=(
                    "This is sample text, not a real page. It exists so the research "
                    "flow can be demonstrated without a web provider."
                ),
                provider=self.provider_id,
                sample=True,
            ),
            WebResult(
                title=f"Sample source: considerations for {q[:60]}",
                url="https://example.com/sample/considerations",
                snippet=(
                    "Sample data. Nothing here was fetched from the internet and it "
                    "must not be treated as a verified fact."
                ),
                provider=self.provider_id,
                sample=True,
            ),
        ]
        return results[: max(1, limit)]


class TavilySearchProvider(WebSearchProvider):
    provider_id = "tavily"
    label = "Tavily"

    def __init__(self) -> None:
        self.api_key = os.environ.get("TAVILY_API_KEY", "").strip()

    def configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 5) -> List[WebResult]:
        if not self.configured():
            raise RuntimeError("TAVILY_API_KEY is not set on the server.")
        payload = json.dumps({
            "api_key": self.api_key,
            "query": query,
            "max_results": max(1, min(limit, 10)),
            "include_answer": False,
            "include_raw_content": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Tavily search failed: {type(exc).__name__}") from exc
        out: List[WebResult] = []
        for item in (data.get("results") or [])[:limit]:
            url = str(item.get("url") or "")
            if not url.startswith(("http://", "https://")):
                continue
            out.append(WebResult(
                title=str(item.get("title") or url),
                url=url,
                snippet=str(item.get("content") or "")[:600],
                provider=self.provider_id,
            ))
        return out


class BraveSearchProvider(WebSearchProvider):
    provider_id = "brave"
    label = "Brave Search"

    def __init__(self) -> None:
        self.api_key = (
            os.environ.get("BRAVE_SEARCH_API_KEY", "")
            or os.environ.get("BRAVE_API_KEY", "")
        ).strip()

    def configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 5) -> List[WebResult]:
        if not self.configured():
            raise RuntimeError("BRAVE_SEARCH_API_KEY is not set on the server.")
        params = urllib.parse.urlencode({
            "q": query,
            "count": max(1, min(limit, 10)),
            "textDecorations": "false",
        })
        req = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Brave search failed: {type(exc).__name__}") from exc
        out: List[WebResult] = []
        for item in ((data.get("web") or {}).get("results") or [])[:limit]:
            url = str(item.get("url") or "")
            if not url.startswith(("http://", "https://")):
                continue
            out.append(WebResult(
                title=str(item.get("title") or url),
                url=url,
                snippet=str(item.get("description") or "")[:600],
                provider=self.provider_id,
            ))
        return out


def get_web_search_provider() -> WebSearchProvider:
    """Resolve the provider from the server environment only."""
    choice = os.environ.get("URA_ASSISTANT_WEB_SEARCH_PROVIDER", "auto").strip().lower()
    if choice in ("", "auto"):
        tavily = TavilySearchProvider()
        if tavily.configured():
            return tavily
        brave = BraveSearchProvider()
        if brave.configured():
            return brave
        return NoWebSearchProvider()
    if choice == "none":
        return NoWebSearchProvider()
    if choice == "sample":
        return SampleWebSearchProvider()
    if choice == "tavily":
        return TavilySearchProvider()
    if choice == "brave":
        return BraveSearchProvider()
    return NoWebSearchProvider()


# ---------------------------------------------------------------------------
# Access policy
# ---------------------------------------------------------------------------

def _normalise_domains(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        parts = [str(v) for v in value]
    else:
        parts = str(value or "").replace(";", ",").replace("\n", ",").split(",")
    out: List[str] = []
    for part in parts:
        domain = part.strip().lower()
        if not domain:
            continue
        if domain.startswith("http://") or domain.startswith("https://"):
            domain = urllib.parse.urlparse(domain).netloc.lower()
        domain = domain.split("/", 1)[0].strip(".")
        if domain.startswith("*."):
            domain = domain[2:]
        if domain and domain not in out:
            out.append(domain)
    return out


def _matches(host: str, domain: str) -> bool:
    host = (host or "").lower().strip(".")
    domain = (domain or "").lower().strip(".")
    if not host or not domain:
        return False
    return host == domain or host.endswith("." + domain)


@dataclass
class WebAccessPolicy:
    mode: str = DEFAULT_ACCESS
    allowlist: List[str] = None  # type: ignore[assignment]
    blocklist: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.mode = (self.mode or DEFAULT_ACCESS).lower()
        if self.mode not in ("off", "allowlist", "open"):
            self.mode = DEFAULT_ACCESS
        self.allowlist = _normalise_domains(self.allowlist or [])
        self.blocklist = _normalise_domains(self.blocklist or [])

    def check(self, url: str) -> Tuple[bool, str]:
        if self.mode == "off":
            return False, "Web access is off."
        host = urllib.parse.urlparse(url or "").netloc.lower()
        if not host:
            return False, "The source has no valid host."
        for domain in self.blocklist:
            if _matches(host, domain):
                return False, f"{host} is on the block list."
        if self.mode == "allowlist":
            if not any(_matches(host, domain) for domain in self.allowlist):
                return False, f"{host} is not on the allow list."
        return True, "allowed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "allowlist": list(self.allowlist),
            "blocklist": list(self.blocklist),
        }


def filter_results(
    results: List[WebResult], policy: WebAccessPolicy
) -> Tuple[List[WebResult], List[Dict[str, str]]]:
    """Return (allowed, blocked-with-reason).  Never silently drops a source."""
    allowed: List[WebResult] = []
    blocked: List[Dict[str, str]] = []
    for result in results:
        ok, reason = policy.check(result.url)
        if ok:
            allowed.append(result)
        else:
            blocked.append({"url": result.url, "title": result.title, "reason": reason})
    return allowed, blocked


def load_web_access(tenant_id: str, company_id: Optional[str]) -> WebAccessPolicy:
    """Read the web access setting from the existing settings service."""
    mode = DEFAULT_ACCESS
    allow: Any = []
    block: Any = []
    try:
        from .settings_service import settings_service
        mode = settings_service.get_effective_setting(
            tenant_id, company_id, "assistant_web_access", DEFAULT_ACCESS
        ) or DEFAULT_ACCESS
        allow = settings_service.get_effective_setting(
            tenant_id, company_id, "assistant_web_allowlist", ""
        ) or ""
        block = settings_service.get_effective_setting(
            tenant_id, company_id, "assistant_web_blocklist", ""
        ) or ""
    except Exception:
        logger.warning("Could not read web access settings; defaulting to off", exc_info=True)
    return WebAccessPolicy(mode=str(mode), allowlist=_normalise_domains(allow), blocklist=_normalise_domains(block))


def web_status(tenant_id: str, company_id: Optional[str]) -> Dict[str, Any]:
    provider = get_web_search_provider()
    policy = load_web_access(tenant_id, company_id)
    return {
        "configured": bool(provider.configured()),
        "provider": provider.provider_id,
        "provider_label": provider.label,
        "sample_provider": bool(provider.is_sample),
        "access": policy.to_dict(),
    }


__all__ = [
    "BraveSearchProvider",
    "DEFAULT_ACCESS",
    "NoWebSearchProvider",
    "SampleWebSearchProvider",
    "TavilySearchProvider",
    "WebAccessPolicy",
    "WebResult",
    "WebSearchProvider",
    "filter_results",
    "get_web_search_provider",
    "load_web_access",
    "web_status",
]
