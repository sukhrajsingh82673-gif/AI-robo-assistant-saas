"""
ZONATA Sovereign Core — Search & Research Port (OpenCode Step 3H).

Enforces Rule 5 (Port pattern), Rule 26 (untrusted content delimiters),
and Rule 30 (capability truth table).
"""

from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.ports.base import Port, PortStatus, ProviderResult


@dataclass(frozen=True)
class SearchResultItem:
    title: str
    url: str
    snippet: str
    source: str
    published_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "published_date": self.published_date,
        }


@dataclass
class SearchExecutionResult(ProviderResult):
    query: str = ""
    results: List[SearchResultItem] = field(default_factory=list)
    total_hits: int = 0
    delimited_output: str = ""


class BaseSearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> SearchExecutionResult:
        raise NotImplementedError

    def is_configured(self) -> bool:
        return True


class SandboxSearchProvider(BaseSearchProvider):
    @property
    def name(self) -> str:
        return "sandbox_search"

    def search(self, query: str, max_results: int = 5) -> SearchExecutionResult:
        start_time = time.time()
        # Synthetic deterministic results for fixtures and tests
        synthetic_results = [
            SearchResultItem(
                title=f"Documentation & Reference: {query}",
                url=f"https://docs.zonata.internal/search?q={urllib.parse.quote(query)}",
                snippet=f"Primary verified documentation regarding {query}. Verified zero hallucinations.",
                source="internal_docs",
            ),
            SearchResultItem(
                title=f"Technical Specification: {query}",
                url=f"https://spec.zonata.internal/{urllib.parse.quote(query)}",
                snippet=f"Detailed specifications and reference architecture for {query}.",
                source="internal_spec",
            ),
        ][:max_results]

        delimited = self._format_delimited(query, synthetic_results)

        return SearchExecutionResult(
            status=PortStatus.OK,
            provider=self.name,
            provider_ref=f"sandbox_search_res_{int(time.time())}",
            sandbox=True,
            latency_ms=(time.time() - start_time) * 1000,
            query=query,
            results=synthetic_results,
            total_hits=len(synthetic_results),
            delimited_output=delimited,
        )

    def _format_delimited(self, query: str, items: List[SearchResultItem]) -> str:
        lines = [f"<<<SEARCH_RESULTS query='{query}'>>>"]
        for idx, item in enumerate(items, 1):
            lines.append(f"[{idx}] Title: {item.title}")
            lines.append(f"    URL: {item.url}")
            lines.append(f"    Snippet: {item.snippet}")
            lines.append(f"    Source: {item.source}")
        lines.append("<<<END_SEARCH_RESULTS>>>")
        return "\n".join(lines)


class SearXNGSearchProvider(BaseSearchProvider):
    @property
    def name(self) -> str:
        return "searxng_search"

    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or os.environ.get("SEARXNG_ENDPOINT", "http://localhost:8888")

    def is_configured(self) -> bool:
        return bool(os.environ.get("SEARXNG_ENDPOINT"))

    def search(self, query: str, max_results: int = 5) -> SearchExecutionResult:
        start_time = time.time()
        url = f"{self.endpoint}/search?q={urllib.parse.quote(query)}&format=json"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZONATA-Research-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            raw_results = data.get("results", [])
            items = []
            for r in raw_results[:max_results]:
                items.append(
                    SearchResultItem(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        source=r.get("engine", "searxng"),
                        published_date=r.get("publishedDate"),
                    )
                )

            lines = [f"<<<SEARCH_RESULTS query='{query}'>>>"]
            for idx, item in enumerate(items, 1):
                lines.append(f"[{idx}] Title: {item.title}")
                lines.append(f"    URL: {item.url}")
                lines.append(f"    Snippet: {item.snippet}")
                lines.append(f"    Source: {item.source}")
            lines.append("<<<END_SEARCH_RESULTS>>>")
            delimited = "\n".join(lines)

            return SearchExecutionResult(
                status=PortStatus.OK,
                provider=self.name,
                provider_ref=f"searxng_res_{int(time.time())}",
                sandbox=False,
                latency_ms=(time.time() - start_time) * 1000,
                query=query,
                results=items,
                total_hits=len(items),
                delimited_output=delimited,
            )
        except Exception as exc:
            return SearchExecutionResult(
                status=PortStatus.FAILED,
                provider=self.name,
                provider_ref=None,
                sandbox=False,
                error=f"SearXNG query failed: {exc}",
                query=query,
            )


class NotConfiguredSearchProvider(BaseSearchProvider):
    @property
    def name(self) -> str:
        return "not_configured_search"

    def is_configured(self) -> bool:
        return False

    def search(self, query: str, max_results: int = 5) -> SearchExecutionResult:
        return SearchExecutionResult(
            status=PortStatus.NOT_CONFIGURED,
            provider=self.name,
            provider_ref=None,
            sandbox=False,
            error="Search engine is NOT_CONFIGURED. SearXNG endpoint not provided.",
            query=query,
        )


class SearchPort(Port):
    """
    Port governing search operations across ZONATA.
    """
    name = "search"
    capability = "search"

    def __init__(self):
        super().__init__(provider_name="search_default", sandbox=False)
        self.sandbox_provider = SandboxSearchProvider()
        self.searxng_provider = SearXNGSearchProvider()
        self.not_configured = NotConfiguredSearchProvider()

    def probe(self) -> ProviderResult:
        is_test = os.environ.get("ZONATA_TEST_MODE") == "1"
        if is_test:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.sandbox_provider.name,
                provider_ref=f"sandbox_search_{int(time.time())}",
                sandbox=True,
            )
        if self.searxng_provider.is_configured():
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.searxng_provider.name,
                provider_ref=f"searxng_{self.searxng_provider.name}_{int(time.time())}",
                sandbox=False,
            )
        return ProviderResult(
            status=PortStatus.NOT_CONFIGURED,
            provider=self.not_configured.name,
            provider_ref=None,
            sandbox=False,
            error="Search provider NOT_CONFIGURED: SEARXNG_ENDPOINT missing.",
        )

    def resolve_provider(self) -> BaseSearchProvider:
        is_test = os.environ.get("ZONATA_TEST_MODE") == "1"
        if is_test:
            return self.sandbox_provider
        if self.searxng_provider.is_configured():
            return self.searxng_provider
        return self.not_configured

    def search(self, query: str, max_results: int = 5) -> SearchExecutionResult:
        provider = self.resolve_provider()
        return provider.search(query=query, max_results=max_results)


search_port = SearchPort()
