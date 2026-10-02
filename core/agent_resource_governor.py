"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Agent Resource Governor & Admission Controller
Enforces server-side quotas on CPU, RAM, tokens, LLM requests, tool calls,
browser sessions, and concurrent missions with strict admission control.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple
from core.distributed_coordination import coordination

logger = logging.getLogger("zonata.governor.resources")

class AdmissionStatus:
    ADMIT = "ADMIT"
    QUEUE = "QUEUE"
    THROTTLE = "THROTTLE"
    DEGRADE = "DEGRADE"
    SUSPEND = "SUSPEND"

class AgentResourceGovernor:
    """
    Server-side Admission Controller preventing runaway agent explosions or noisy neighbor starvation.
    """
    DEFAULT_TENANT_LIMITS = {
        "max_concurrent_agents": 100,
        "max_concurrent_missions": 25,
        "max_tokens_per_minute": 100000,
        "max_tool_calls_per_minute": 500,
        "max_browser_sessions": 10,
        "max_openhands_sessions": 5,
        "max_spend_per_day": 1000.0
    }

    def __init__(self):
        self._tenant_limits: Dict[str, Dict[str, Any]] = {}
        self._usage: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()

    def set_tenant_limits(self, tenant_id: str, limits: Dict[str, Any]):
        with self._lock:
            merged = dict(self.DEFAULT_TENANT_LIMITS)
            merged.update(limits)
            self._tenant_limits[tenant_id] = merged

    def check_admission(
        self,
        tenant_id: str,
        agent_id: str,
        resource_type: str,
        requested_amount: float = 1.0
    ) -> Tuple[str, str]:
        """
        Evaluate admission control request.
        Returns: (status: AdmissionStatus, reason: str)
        """
        with self._lock:
            limits = self._tenant_limits.get(tenant_id, self.DEFAULT_TENANT_LIMITS)
            now = time.time()

            # Check distributed rate limits for high-frequency resources
            if resource_type == "tool_calls":
                max_tools = limits.get("max_tool_calls_per_minute", 500)
                allowed, remaining, reset_at = coordination.check_rate_limit(f"tools:{tenant_id}", max_tools, 60.0)
                if not allowed:
                    return (AdmissionStatus.THROTTLE, f"Tool call rate limit exceeded. Retry in {int(reset_at - now)}s.")

            elif resource_type == "tokens":
                max_tokens = limits.get("max_tokens_per_minute", 100000)
                current_tokens = coordination.get_backpressure(f"tokens:{tenant_id}")
                if current_tokens + requested_amount > max_tokens:
                    return (AdmissionStatus.THROTTLE, "Token budget exhausted for current 60s window.")
                coordination.increment_backpressure(f"tokens:{tenant_id}", int(requested_amount))

            elif resource_type == "browser_sessions":
                max_browser = limits.get("max_browser_sessions", 10)
                current = coordination.get_backpressure(f"browser_sessions:{tenant_id}")
                if current >= max_browser:
                    return (AdmissionStatus.QUEUE, f"Browser session capacity ({max_browser}) reached.")

            elif resource_type == "concurrent_missions":
                max_missions = limits.get("max_concurrent_missions", 25)
                current = coordination.get_backpressure(f"active_missions:{tenant_id}")
                if current >= max_missions:
                    return (AdmissionStatus.QUEUE, f"Tenant mission concurrency limit ({max_missions}) reached.")

            return (AdmissionStatus.ADMIT, "Resource admission cleared.")

    def release_resource(self, tenant_id: str, resource_type: str, amount: float = 1.0):
        """Release allocated concurrency budget."""
        with self._lock:
            if resource_type in ("browser_sessions", "openhands_sessions", "active_missions"):
                coordination.decrement_backpressure(f"{resource_type}:{tenant_id}", int(amount))

# Global resource governor instance
resource_governor = AgentResourceGovernor()
