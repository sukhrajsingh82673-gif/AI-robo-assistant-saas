"""
Public API V1 Router implementation (ADR 0050, Rule 80).
Implements RFC 9457 errors, Idempotency-Key deduplication, and cursor pagination.
"""

import json
import uuid
import time
from typing import Dict, Any, Optional, Tuple, List
from core.billing.plans import PlanRegistry
from core.webhooks.standard_webhooks import SSRFValidator, StandardWebhooksSigner


class PublicApiRouter:
    """
    Handles requests under /api/public/v1/*.
    """

    def __init__(self):
        # In-memory store for registered webhooks: tenant_id -> list of webhook dicts
        self._webhooks: Dict[str, List[Dict[str, Any]]] = {}
        # In-memory store for tasks: task_id -> task dict
        self._tasks: Dict[str, Dict[str, Any]] = {}
        # Idempotency cache: (tenant_id, idempotency_key) -> (status_code, headers, body)
        self._idempotency_cache: Dict[Tuple[str, str], Tuple[int, Dict[str, str], str]] = {}

    def _paginate(self, items: List[Any], limit: int, cursor: Optional[str]) -> Dict[str, Any]:
        """Cursor pagination helper using index-based opaque tokens."""
        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except ValueError:
                start_idx = 0

        end_idx = start_idx + limit
        page_items = items[start_idx:end_idx]
        has_more = end_idx < len(items)
        next_cursor = str(end_idx) if has_more else None

        return {
            "items": page_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    def dispatch(
        self, method: str, path: str, headers: Dict[str, str], body: Optional[str] = None
    ) -> Tuple[int, Dict[str, str], str]:
        """
        Dispatches public API request. Returns (status_code, response_headers, body_str).
        """
        tenant_id = headers.get("X-Tenant-ID", "tenant_default")
        idempotency_key = headers.get("Idempotency-Key")

        # Check idempotency cache on state-mutating requests
        if method in ("POST", "PUT", "DELETE") and idempotency_key:
            cache_key = (tenant_id, idempotency_key)
            if cache_key in self._idempotency_cache:
                status, cached_headers, cached_body = self._idempotency_cache[cache_key]
                resp_headers = dict(cached_headers)
                resp_headers["X-Cache-Lookup"] = "HIT-IDEMPOTENT"
                return status, resp_headers, cached_body

        res_status, res_headers, res_body = self._handle_route(method, path, headers, tenant_id, body)

        # Cache idempotent responses
        if method in ("POST", "PUT", "DELETE") and idempotency_key and 200 <= res_status < 300:
            self._idempotency_cache[(tenant_id, idempotency_key)] = (res_status, res_headers, res_body)

        return res_status, res_headers, res_body

    def _handle_route(
        self, method: str, path: str, headers: Dict[str, str], tenant_id: str, body: Optional[str]
    ) -> Tuple[int, Dict[str, str], str]:
        normalized_path = path.rstrip("/")

        # GET /api/public/v1/plans
        if method == "GET" and normalized_path == "/api/public/v1/plans":
            plans = [
                {
                    "plan_id": p.plan_id,
                    "code": p.code,
                    "name": p.name,
                    "tier": p.tier,
                    "base_fee_cents": p.base_fee_cents,
                    "included_tokens": p.included_tokens,
                    "currency": p.currency,
                }
                for p in PlanRegistry.list_plans()
            ]
            return 200, {"Content-Type": "application/json"}, json.dumps({"plans": plans})

        # GET /api/public/v1/usage
        if method == "GET" and normalized_path == "/api/public/v1/usage":
            usage_payload = {
                "tenant_id": tenant_id,
                "tier": "team",
                "tokens_used": 1250000,
                "token_quota": 5000000,
                "spend_cents": 9900,
                "hard_cap_cents": 50000,
            }
            return 200, {"Content-Type": "application/json"}, json.dumps(usage_payload)

        # GET /api/public/v1/webhooks
        if method == "GET" and normalized_path == "/api/public/v1/webhooks":
            webhooks_list = self._webhooks.get(tenant_id, [])
            paginated = self._paginate(webhooks_list, limit=20, cursor=headers.get("X-Cursor"))
            return 200, {"Content-Type": "application/json"}, json.dumps(paginated)

        # POST /api/public/v1/webhooks
        if method == "POST" and normalized_path == "/api/public/v1/webhooks":
            if not body:
                return 400, {"Content-Type": "application/problem+json"}, json.dumps({
                    "type": "https://zonata.ai/errors/bad-request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": "Missing request body.",
                    "instance": f"urn:uuid:{uuid.uuid4()}",
                })

            data = json.loads(body)
            target_url = data.get("url")
            event_types = data.get("event_types", [])

            # SSRF check (allow localhost in test mode if X-Test-Mode is passed)
            is_test = headers.get("X-Test-Mode") == "1"
            safe, ssrf_reason = SSRFValidator.is_url_safe(target_url, allow_private_for_tests=is_test)
            if not safe:
                return 400, {"Content-Type": "application/problem+json"}, json.dumps({
                    "type": "https://zonata.ai/errors/ssrf-prohibited",
                    "title": "Invalid Webhook Destination",
                    "status": 400,
                    "detail": ssrf_reason,
                    "instance": f"urn:uuid:{uuid.uuid4()}",
                })

            wh_id = f"wh_{uuid.uuid4().hex[:12]}"
            secret = f"whsec_{uuid.uuid4().hex}"
            record = {
                "webhook_id": wh_id,
                "url": target_url,
                "event_types": event_types,
                "secret": secret,
                "created_at": time.time(),
            }
            self._webhooks.setdefault(tenant_id, []).append(record)
            return 201, {"Content-Type": "application/json"}, json.dumps(record)

        # POST /api/public/v1/tasks
        if method == "POST" and normalized_path == "/api/public/v1/tasks":
            data = json.loads(body or "{}")
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            task = {
                "task_id": task_id,
                "tenant_id": tenant_id,
                "instruction": data.get("instruction", "Execute autonomous mission"),
                "status": "ACCEPTED",
                "created_at": time.time(),
            }
            self._tasks[task_id] = task
            return 202, {"Content-Type": "application/json"}, json.dumps(task)

        # GET /api/public/v1/tasks/{id}
        if method == "GET" and normalized_path.startswith("/api/public/v1/tasks/"):
            task_id = normalized_path.split("/")[-1]
            task = self._tasks.get(task_id)
            if not task:
                return 404, {"Content-Type": "application/problem+json"}, json.dumps({
                    "type": "https://zonata.ai/errors/task-not-found",
                    "title": "Task Not Found",
                    "status": 404,
                    "detail": f"Task '{task_id}' does not exist.",
                    "instance": f"urn:uuid:{uuid.uuid4()}",
                })
            return 200, {"Content-Type": "application/json"}, json.dumps(task)

        # 404 Not Found
        return 404, {"Content-Type": "application/problem+json"}, json.dumps({
            "type": "https://zonata.ai/errors/not-found",
            "title": "Not Found",
            "status": 404,
            "detail": f"Public API endpoint not found: {path}",
            "instance": f"urn:uuid:{uuid.uuid4()}",
        })
