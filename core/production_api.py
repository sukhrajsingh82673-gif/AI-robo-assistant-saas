"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production API Control Plane & Asynchronous Dispatch Handler
Stateless, rate-limited, multi-tenant HTTP/ASGI handler enforcing zero-trust ingress.
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("zonata.api")

class ProductionAPIHandler:
    """
    Stateless control-plane request handler.
    Validates tenant credentials, checks distributed rate limits, verifies idempotency,
    and dispatches mutating requests asynchronously to the command bus.
    """
    def __init__(self):
        from core.action_envelope import command_bus
        from core.distributed_coordination import coordination
        from core.database_engine import engine
        from core.auth import token_manager
        self.command_bus = command_bus
        self.coordination = coordination
        self.engine = engine
        self.token_manager = token_manager

    def handle_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body_bytes: bytes
    ) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
        """
        Process incoming HTTP request and return (status_code, response_headers, response_body_dict).
        """
        start_time = time.time()
        request_id = headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
        correlation_id = headers.get("X-Correlation-ID", request_id)
        causality_id = headers.get("X-Causality-ID", f"caus_{uuid.uuid4().hex[:12]}")

        resp_headers = {
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "X-Request-ID": request_id,
            "X-Correlation-ID": correlation_id,
            "X-Causality-ID": causality_id
        }

        # 1. Health / Liveness / Readiness Probes (Unauthenticated)
        if path in ("/health", "/api/v1/health", "/healthz"):
            db_health = self.engine.health_check()
            is_healthy = db_health.get("status") == "HEALTHY"
            return (
                200 if is_healthy else 503,
                resp_headers,
                {
                    "status": "HEALTHY" if is_healthy else "UNHEALTHY",
                    "timestamp": time.time(),
                    "server_mode": "DISTRIBUTED_ASGI_V2",
                    "database": db_health
                }
            )

        if path == "/livez":
            return (200, resp_headers, {"status": "ALIVE", "timestamp": time.time()})

        if path == "/readyz":
            db_health = self.engine.health_check()
            if db_health.get("status") != "HEALTHY":
                return (503, resp_headers, {"status": "NOT_READY", "reason": "DATABASE_UNAVAILABLE"})
            return (200, resp_headers, {"status": "READY", "timestamp": time.time()})

        # 2. Authenticate Request
        auth_header = headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

        if not token:
            # Allow token generation endpoint
            if path == "/api/auth/token" and method == "POST":
                try:
                    data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                    tenant_id = data.get("tenant_id")
                    user_id = data.get("user_id", "admin")
                    role = data.get("role", "OWNER")
                    if not tenant_id:
                        return (400, resp_headers, {"error": "tenant_id required"})
                    new_token = self.token_manager.create_session_token(tenant_id, user_id, role)
                    return (201, resp_headers, {"token": new_token, "tenant_id": tenant_id, "user_id": user_id, "role": role})
                except Exception as e:
                    return (400, resp_headers, {"error": str(e)})

            return (401, resp_headers, {"error": "UNAUTHORIZED", "message": "Missing Bearer token."})

        claims = self.token_manager.verify_token(token)
        if not claims:
            return (401, resp_headers, {"error": "UNAUTHORIZED", "message": "Invalid or revoked token."})

        tenant_id = claims["tenant_id"]

        # Anti-Spoofing: Check optional X-Tenant-ID header consistency
        header_tenant = headers.get("X-Tenant-ID")
        if header_tenant and header_tenant != tenant_id:
            return (403, resp_headers, {
                "error": "FORBIDDEN",
                "code": "TENANT_SPOOFING_ATTEMPT",
                "message": f"Header tenant '{header_tenant}' does not match authenticated token tenant '{tenant_id}'."
            })

        # 3. Distributed Rate Limiting
        allowed, remaining, reset_at = self.coordination.check_rate_limit(f"api:{tenant_id}", max_requests=1000, window_seconds=60.0)
        resp_headers["X-RateLimit-Remaining"] = str(remaining)
        resp_headers["X-RateLimit-Reset"] = str(int(reset_at))
        if not allowed:
            resp_headers["Retry-After"] = str(max(1, int(reset_at - time.time())))
            return (429, resp_headers, {"error": "TOO_MANY_REQUESTS", "message": "Tenant rate limit exceeded."})

        # 4. Asynchronous Command Enqueue Endpoint
        if path == "/api/v2/commands/enqueue" and method == "POST":
            try:
                body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                from core.action_envelope import ActionEnvelope

                # Check Idempotency Key
                idemp_key = headers.get("Idempotency-Key") or body.get("idempotency_key")
                if idemp_key:
                    cached_action_id = self.coordination.get_idempotency_key(f"{tenant_id}:{idemp_key}")
                    if cached_action_id:
                        # Return previously enqueued action without re-executing
                        return (200, resp_headers, {
                            "status": "DUPLICATE_MUTATION_SUPPRESSED",
                            "action_id": cached_action_id,
                            "idempotency_key": idemp_key,
                            "tracking_url": f"/api/v2/commands/{cached_action_id}"
                        })

                envelope = ActionEnvelope.create(
                    tenant_id=tenant_id,
                    company_id=body.get("company_id", "default_company"),
                    agent_id=body.get("agent_id", "agt_orchestrator"),
                    capability_id=body.get("capability_id", "universal.action"),
                    target=body.get("target", "system"),
                    intent=body.get("intent", "Execute background task"),
                    parameters=body.get("parameters", {}),
                    risk_class=body.get("risk_class", "LOW_RISK"),
                    mission_id=body.get("mission_id"),
                    workflow_id=body.get("workflow_id"),
                    idempotency_key=idemp_key,
                    causality_id=causality_id
                )

                action_id = self.command_bus.enqueue(envelope)

                if idemp_key:
                    self.coordination.set_idempotency_key(f"{tenant_id}:{idemp_key}", action_id, ttl_seconds=86400.0)

                return (202, resp_headers, {
                    "status": "ACCEPTED",
                    "action_id": action_id,
                    "tracking_url": f"/api/v2/commands/{action_id}",
                    "causality_id": causality_id
                })
            except Exception as e:
                logger.error(f"Command enqueue error: {e}")
                return (500, resp_headers, {"error": "COMMAND_ENQUEUE_FAILED", "message": str(e)})

        # 5. Command Status Polling Endpoint
        if path.startswith("/api/v2/commands/") and method == "GET":
            action_id = path.split("/")[-1]
            status_data = self.command_bus.get_status(action_id)
            if not status_data:
                return (404, resp_headers, {"error": "COMMAND_NOT_FOUND", "action_id": action_id})
            return (200, resp_headers, status_data)

        # Fallback 404
        return (404, resp_headers, {"error": "NOT_FOUND", "path": path})

# Global handler instance
api_handler = ProductionAPIHandler()
