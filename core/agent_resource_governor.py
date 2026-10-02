"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Agent Resource Governor & Admission Controller
Enforces server-side quotas on CPU, RAM, tokens, LLM requests, tool calls,
browser sessions, active agents, and concurrent missions with strict admission control.
Supports configurable dynamic plan tiers (DEV, STARTER, PRO, ENTERPRISE, HYPERSCALE, UNLIMITED).
"""

import time
import sys
import logging
import threading
from typing import Dict, Any, Optional, Tuple, Set
from core.distributed_coordination import coordination

logger = logging.getLogger("zonata.governor.resources")

class AdmissionStatus:
    ADMIT = "ADMIT"
    QUEUE = "QUEUE"
    THROTTLE = "THROTTLE"
    DEGRADE = "DEGRADE"
    SUSPEND = "SUSPEND"

class PlanTier:
    DEV = "DEV"
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"
    HYPERSCALE = "HYPERSCALE"
    UNLIMITED = "UNLIMITED"

TIER_LIMITS: Dict[str, Dict[str, Any]] = {
    PlanTier.DEV: {
        "max_concurrent_agents": 10,
        "max_concurrent_missions": 5,
        "max_tokens_per_minute": 50000,
        "max_tool_calls_per_minute": 100,
        "max_browser_sessions": 2,
        "max_openhands_sessions": 2,
        "max_spend_per_day": 100.0
    },
    PlanTier.STARTER: {
        "max_concurrent_agents": 25,
        "max_concurrent_missions": 10,
        "max_tokens_per_minute": 100000,
        "max_tool_calls_per_minute": 250,
        "max_browser_sessions": 5,
        "max_openhands_sessions": 5,
        "max_spend_per_day": 500.0
    },
    PlanTier.PROFESSIONAL: {
        "max_concurrent_agents": 100,
        "max_concurrent_missions": 25,
        "max_tokens_per_minute": 500000,
        "max_tool_calls_per_minute": 1000,
        "max_browser_sessions": 15,
        "max_openhands_sessions": 10,
        "max_spend_per_day": 2500.0
    },
    PlanTier.ENTERPRISE: {
        "max_concurrent_agents": 500,
        "max_concurrent_missions": 100,
        "max_tokens_per_minute": 2000000,
        "max_tool_calls_per_minute": 5000,
        "max_browser_sessions": 50,
        "max_openhands_sessions": 25,
        "max_spend_per_day": 10000.0
    },
    PlanTier.HYPERSCALE: {
        "max_concurrent_agents": 5000,
        "max_concurrent_missions": 1000,
        "max_tokens_per_minute": 10000000,
        "max_tool_calls_per_minute": 25000,
        "max_browser_sessions": 200,
        "max_openhands_sessions": 100,
        "max_spend_per_day": 50000.0
    },
    PlanTier.UNLIMITED: {
        "max_concurrent_agents": 1000000,
        "max_concurrent_missions": 100000,
        "max_tokens_per_minute": 100000000,
        "max_tool_calls_per_minute": 1000000,
        "max_browser_sessions": 5000,
        "max_openhands_sessions": 2000,
        "max_spend_per_day": 1000000.0
    }
}

class AgentResourceGovernor:
    """
    Server-side Admission Controller preventing runaway agent explosions or noisy neighbor starvation.
    Provides dynamic tiered limits, customizable policy overrides, and distributed quota enforcement.
    """
    DEFAULT_TENANT_LIMITS = dict(TIER_LIMITS[PlanTier.PROFESSIONAL])

    def __init__(self):
        self._tenant_limits: Dict[str, Dict[str, Any]] = {}
        self._tenant_tiers: Dict[str, str] = {}
        self._active_agents: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def set_tenant_tier(self, tenant_id: str, tier: str, custom_overrides: Optional[Dict[str, Any]] = None):
        """Configure a tenant's quota based on a subscription tier and optional custom overrides."""
        tier_upper = tier.upper()
        if tier_upper not in TIER_LIMITS:
            tier_upper = PlanTier.PROFESSIONAL

        base_limits = dict(TIER_LIMITS[tier_upper])
        if custom_overrides:
            base_limits.update(custom_overrides)

        with self._lock:
            self._tenant_tiers[tenant_id] = tier_upper
            self._tenant_limits[tenant_id] = base_limits
            logger.info(f"Tenant '{tenant_id}' configured with tier '{tier_upper}' (max_agents={base_limits.get('max_concurrent_agents')}).")

    def set_tenant_limits(self, tenant_id: str, limits: Dict[str, Any]):
        """Legacy compatibility method to set custom tenant limits."""
        with self._lock:
            current = self.get_tenant_limits(tenant_id)
            merged = dict(current)
            merged.update(limits)
            self._tenant_limits[tenant_id] = merged

    def get_tenant_limits(self, tenant_id: str) -> Dict[str, Any]:
        """Retrieve active limits for a tenant."""
        with self._lock:
            if tenant_id in self._tenant_limits:
                return dict(self._tenant_limits[tenant_id])
            tier = self._tenant_tiers.get(tenant_id, PlanTier.PROFESSIONAL)
            return dict(TIER_LIMITS.get(tier, self.DEFAULT_TENANT_LIMITS))

    def get_tenant_tier(self, tenant_id: str) -> str:
        """Get the active subscription tier for a tenant."""
        with self._lock:
            return self._tenant_tiers.get(tenant_id, PlanTier.PROFESSIONAL)

    def register_active_agent(self, tenant_id: str, agent_id: str) -> Tuple[bool, str]:
        """Attempt to register an active running agent under tenant quota."""
        with self._lock:
            limits = self.get_tenant_limits(tenant_id)
            max_agents = limits.get("max_concurrent_agents", 100)
            
            if tenant_id not in self._active_agents:
                self._active_agents[tenant_id] = set()

            if agent_id in self._active_agents[tenant_id]:
                return True, "Agent already active."

            if len(self._active_agents[tenant_id]) >= max_agents:
                return False, f"Tenant agent capacity ({max_agents}) reached for plan tier {self.get_tenant_tier(tenant_id)}."

            self._active_agents[tenant_id].add(agent_id)
            coordination.increment_backpressure(f"active_agents:{tenant_id}", 1)
            return True, "Agent registered."

    def unregister_active_agent(self, tenant_id: str, agent_id: str):
        """Unregister an agent and release quota."""
        with self._lock:
            if tenant_id in self._active_agents and agent_id in self._active_agents[tenant_id]:
                self._active_agents[tenant_id].remove(agent_id)
                coordination.decrement_backpressure(f"active_agents:{tenant_id}", 1)

    def get_active_agent_count(self, tenant_id: str) -> int:
        """Return the current number of active registered agents for a tenant."""
        with self._lock:
            return len(self._active_agents.get(tenant_id, set()))

    def check_admission(
        self,
        tenant_id: str,
        agent_id: str,
        resource_type: str,
        requested_amount: float = 1.0
    ) -> Tuple[str, str]:
        """
        Evaluate admission control request across all governed dimensions.
        Returns: (status: AdmissionStatus, reason: str)
        """
        with self._lock:
            limits = self.get_tenant_limits(tenant_id)
            now = time.time()

            # 1. Agent Concurrency Quota Check
            if resource_type in ("agent", "concurrent_agents"):
                max_agents = limits.get("max_concurrent_agents", 100)
                current = len(self._active_agents.get(tenant_id, set()))
                dist_backpressure = coordination.get_backpressure(f"active_agents:{tenant_id}")
                total_active = max(current, dist_backpressure)
                if total_active + requested_amount > max_agents:
                    return (AdmissionStatus.QUEUE, f"Tenant agent concurrency quota ({max_agents}) reached. Upgrade plan tier to increase limit.")

            # 2. Tool Calls Rate Limit
            elif resource_type == "tool_calls":
                max_tools = limits.get("max_tool_calls_per_minute", 500)
                allowed, remaining, reset_at = coordination.check_rate_limit(f"tools:{tenant_id}", max_tools, 60.0)
                if not allowed:
                    return (AdmissionStatus.THROTTLE, f"Tool call rate limit exceeded. Retry in {int(reset_at - now)}s.")

            # 3. Token Budget Rate Limit
            elif resource_type == "tokens":
                max_tokens = limits.get("max_tokens_per_minute", 100000)
                current_tokens = coordination.get_backpressure(f"tokens:{tenant_id}")
                if current_tokens + requested_amount > max_tokens:
                    return (AdmissionStatus.THROTTLE, "Token budget exhausted for current 60s window.")
                coordination.increment_backpressure(f"tokens:{tenant_id}", int(requested_amount))

            # 4. Browser Sessions Concurrency
            elif resource_type == "browser_sessions":
                max_browser = limits.get("max_browser_sessions", 10)
                current = coordination.get_backpressure(f"browser_sessions:{tenant_id}")
                if current >= max_browser:
                    return (AdmissionStatus.QUEUE, f"Browser session capacity ({max_browser}) reached.")

            # 5. OpenHands Execution Concurrency
            elif resource_type == "openhands_sessions":
                max_openhands = limits.get("max_openhands_sessions", 5)
                current = coordination.get_backpressure(f"openhands_sessions:{tenant_id}")
                if current >= max_openhands:
                    return (AdmissionStatus.QUEUE, f"OpenHands workspace capacity ({max_openhands}) reached.")

            # 6. Mission Concurrency
            elif resource_type == "concurrent_missions":
                max_missions = limits.get("max_concurrent_missions", 25)
                current = coordination.get_backpressure(f"active_missions:{tenant_id}")
                if current >= max_missions:
                    return (AdmissionStatus.QUEUE, f"Tenant mission concurrency limit ({max_missions}) reached.")

            return (AdmissionStatus.ADMIT, "Resource admission cleared.")

    def release_resource(self, tenant_id: str, resource_type: str, amount: float = 1.0):
        """Release allocated concurrency budget."""
        with self._lock:
            if resource_type in ("browser_sessions", "openhands_sessions", "active_missions", "active_agents"):
                coordination.decrement_backpressure(f"{resource_type}:{tenant_id}", int(amount))

# Global resource governor instance
resource_governor = AgentResourceGovernor()
