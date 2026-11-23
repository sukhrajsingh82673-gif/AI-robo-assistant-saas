"""
ZONATA Sovereign Core — Research Engine (Rule 26).

Enforces Rule 26:
All retrieved search results are data enclosed in <<<SEARCH_RESULTS>>>.
Instructions within search snippets are treated as passive data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.ports.search import SearchExecutionResult, SearchPort, search_port


class ResearchEngine:
    """
    Executes governed searches and formats citations without prompt injection risks.
    """

    def __init__(self, port: Optional[SearchPort] = None):
        self.port = port or search_port

    def execute_research_query(
        self,
        query: str,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute research query and return verified citations.
        """
        result: SearchExecutionResult = self.port.search(query=query, max_results=max_results)

        citations = []
        for idx, item in enumerate(result.results, 1):
            citations.append({
                "index": idx,
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "source": item.source,
            })

        return {
            "query": query,
            "status": result.status.value,
            "total_hits": result.total_hits,
            "citations": citations,
            "delimited_content": result.delimited_output,
            "sandbox": result.sandbox,
        }
