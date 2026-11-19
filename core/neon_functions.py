"""
ZONATA Enterprise SaaS — Neon Serverless Functions Client
Enables invocation and orchestration of long-running serverless Node.js HTTP functions
deployed to Neon compute, located next to Lakebase Postgres.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

from core.neon_env import get_neon_function_url


class NeonFunctionsClient:
    """Client for invoking deployed Neon Functions."""

    def __init__(self):
        pass

    def get_url(self, function_name: str = "hello") -> str:
        """Resolve invocation URL for the given function name."""
        return get_neon_function_url(function_name)

    def is_configured(self, function_name: str = "hello") -> bool:
        return bool(self.get_url(function_name))

    def invoke(
        self,
        function_name: str = "hello",
        path: str = "",
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Invoke a deployed Neon Function via HTTPS.
        Supports GET and POST with JSON payloads and custom headers.
        """
        base_url = self.get_url(function_name)
        if not base_url:
            return {
                "success": False,
                "error": f"Function '{function_name}' has no configured NEON_FUNCTION_{function_name.upper()}_BASE_URL"
            }

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        req_headers = {
            "User-Agent": "ZONATA-Enterprise/1.0",
            "Accept": "application/json, text/plain, */*"
        }
        if headers:
            req_headers.update(headers)

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw_body = resp.read().decode("utf-8")
                if "application/json" in content_type:
                    parsed_body = json.loads(raw_body)
                else:
                    parsed_body = raw_body

                return {
                    "success": True,
                    "status_code": resp.status,
                    "function": function_name,
                    "url": url,
                    "body": parsed_body
                }
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8") if e.fp else str(e)
            return {
                "success": False,
                "status_code": e.code,
                "function": function_name,
                "url": url,
                "error": raw_err
            }
        except Exception as e:
            return {
                "success": False,
                "function": function_name,
                "url": url,
                "error": str(e)
            }


# Singleton instance
neon_functions = NeonFunctionsClient()
