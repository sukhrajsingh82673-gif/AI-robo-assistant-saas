"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
PostHog SaaS Product Intelligence, Funnels & Feature Flags Engine
================================================================
Provides customer journey tracking, conversion funnel analytics,
feature flag evaluations, and product telemetry across the SaaS lifecycle:
  Signup -> Company Creation -> Agent Creation -> First Mission ->
  Successful Mission -> Integration -> Paid Conversion -> Retention.

Constitutional Invariant:
  Product analytics captures behavioral events for optimization.
  Analytics must NEVER ingest raw secrets, customer passwords, or private encryption keys.
"""

import os
import time
import json
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.analytics.posthog")

@dataclass
class PostHogEvent:
    event_id: str
    event_name: str
    distinct_id: str
    properties: Dict[str, Any]
    tenant_id: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PostHogAnalyticsEngine:
    """
    PostHog SaaS Product Intelligence & Feature Flag Engine.
    Operates self-contained and bridges to upstream PostHog Cloud / Self-hosted instance.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PostHogAnalyticsEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None):
        self.api_key = api_key or os.environ.get("POSTHOG_API_KEY", "phc_zonata_mock_key")
        self.host = host or os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
        self._events: List[PostHogEvent] = []
        self._feature_flags: Dict[str, bool] = {
            "enable_temporal_workflows": True,
            "enable_openhands_runtime": True,
            "enable_browser_use": True,
            "enable_gui_sandbox": False,  # Degraded on mobile/termux
            "enable_vault_dynamic_creds": True,
            "enable_saas_metering": True,
            "enable_agent_evaluations": True,
            "enable_langfuse_tracing": True
        }
        self._tenant_flag_overrides: Dict[str, Dict[str, bool]] = {}
        self._lock = threading.RLock()

    def capture(
        self,
        event_name: str,
        distinct_id: str = "anon",
        properties: Optional[Dict[str, Any]] = None,
        tenant_id: str = "tnt_primary",
        company_id: Optional[str] = None
    ) -> PostHogEvent:
        """Captures a product analytics event with automatic sanitization."""
        # Flexible handling if distinct_id and event_name are swapped
        if event_name.startswith("usr_") and not distinct_id.startswith("usr_"):
            distinct_id, event_name = event_name, distinct_id

        props = dict(properties) if properties else {}
        if company_id and "company_id" not in props:
            props["company_id"] = company_id

        # Ensure no credential leakage in analytics
        clean_props = {}
        for k, v in props.items():
            if any(w in k.lower() for w in ["secret", "password", "token", "key"]):
                clean_props[k] = "[REDACTED]"
            else:
                clean_props[k] = v

        event = PostHogEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_name=event_name,
            distinct_id=distinct_id,
            properties=clean_props,
            tenant_id=tenant_id
        )

        with self._lock:
            self._events.append(event)
            if len(self._events) > 2000:
                self._events.pop(0)

        logger.info(f"POSTHOG EVENT: '{event_name}' (Distinct ID: {distinct_id}, Tenant: {tenant_id})")
        return event

    def is_feature_enabled(self, flag_key: str, distinct_id: str, tenant_id: str = "tnt_primary") -> bool:
        """Evaluates whether a feature flag is enabled for a given tenant."""
        with self._lock:
            # Check tenant override first
            if tenant_id in self._tenant_flag_overrides:
                if flag_key in self._tenant_flag_overrides[tenant_id]:
                    return self._tenant_flag_overrides[tenant_id][flag_key]

            # Default flag state
            return self._feature_flags.get(flag_key, False)

    def set_feature_flag(self, flag_key: str, enabled: bool, tenant_id: Optional[str] = None):
        """Sets a feature flag globally or for a specific tenant."""
        with self._lock:
            if tenant_id:
                if tenant_id not in self._tenant_flag_overrides:
                    self._tenant_flag_overrides[tenant_id] = {}
                self._tenant_flag_overrides[tenant_id][flag_key] = enabled
            else:
                self._feature_flags[flag_key] = enabled
            logger.info(f"FEATURE FLAG UPDATED: {flag_key} = {enabled} (Tenant: {tenant_id or 'GLOBAL'})")

    def set_tenant_flag_override(self, tenant_id: str, flag_key: str, enabled: bool):
        """Sets a tenant-specific feature flag override."""
        self.set_feature_flag(flag_key, enabled, tenant_id=tenant_id)


    def get_funnel_summary(self, tenant_id: Optional[str] = None) -> Dict[str, int]:
        """Calculates conversion funnel drops across standard SaaS milestones."""
        funnel_steps = [
            "signup",
            "company_created",
            "agent_created",
            "first_mission_dispatched",
            "mission_succeeded",
            "integration_connected",
            "paid_conversion",
            "retention_active"
        ]
        counts = {step: 0 for step in funnel_steps}

        with self._lock:
            for e in self._events:
                if tenant_id and e.tenant_id != tenant_id:
                    continue
                if e.event_name in counts:
                    counts[e.event_name] += 1

        return counts

# Global singleton instance
posthog_analytics = PostHogAnalyticsEngine.get_instance()

