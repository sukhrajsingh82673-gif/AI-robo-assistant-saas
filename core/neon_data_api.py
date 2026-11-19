"""
ZONATA Enterprise SaaS — Neon Data API (PostgREST) Client
Enables HTTP-based REST queries against PostgreSQL tables via Neon Data API.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

from core.neon_env import get_neon_data_api_url


class NeonDataApiClient:
    """Client for querying PostgreSQL via Neon PostgREST Data API."""

    def __init__(self):
        pass

    @property
    def base_url(self) -> str:
        return get_neon_data_api_url()

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of Neon Data API."""
        return {
            "configured": self.is_configured(),
            "url": self.base_url,
            "type": "PostgREST REST API"
        }

    def query_table(
        self,
        table: str,
        jwt_token: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Query rows from a public schema table using REST API."""
        if not self.is_configured():
            return {"success": False, "error": "Neon Data API URL not configured"}

        url = f"{self.base_url.rstrip('/')}/{table}?limit={limit}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "ZONATA-Enterprise/1.0"
        }
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "table": table, "data": data}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            return {"success": False, "status_code": e.code, "error": err_body}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
neon_data_api = NeonDataApiClient()
