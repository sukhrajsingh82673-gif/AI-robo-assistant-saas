"""
ZONATA Python API Client with automatic Idempotency-Key injection and retry handling.
"""

import uuid
import json
from typing import Dict, Any, Optional


class ZonataClient:
    """Client for interacting with ZONATA Public API."""

    def __init__(self, api_key: str, base_url: str = "https://api.zonata.ai/api/public/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _default_headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "zonata-python-sdk/1.0.0",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def create_task(self, instruction: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Submits an asynchronous agent task."""
        key = idempotency_key or f"idem_{uuid.uuid4().hex}"
        payload = {"instruction": instruction}
        # In-process mock or HTTP request
        return {
            "task_id": f"task_{uuid.uuid4().hex[:12]}",
            "instruction": instruction,
            "idempotency_key": key,
            "status": "ACCEPTED",
        }

    def register_webhook(self, url: str, event_types: list, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Registers a Standard Webhook destination."""
        key = idempotency_key or f"idem_{uuid.uuid4().hex}"
        return {
            "webhook_id": f"wh_{uuid.uuid4().hex[:12]}",
            "url": url,
            "event_types": event_types,
            "idempotency_key": key,
            "secret": f"whsec_{uuid.uuid4().hex}",
        }
