"""
Data-driven Feature & Quota Entitlements Engine (ADR 0049, Rule 78, Rule 80).
Evaluates tenant subscription tiers, feature access matrix, usage quotas, and cost-cap state.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Set


@dataclass
class EntitlementDecision:
    entitled: bool
    reason: str
    tier: str
    current_usage: int = 0
    limit: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entitled": self.entitled,
            "reason": self.reason,
            "tier": self.tier,
            "current_usage": self.current_usage,
            "limit": self.limit,
        }


class EntitlementsEngine:
    """
    Evaluates whether a tenant has entitlement to access features, endpoints, or capacity.
    """

    TIER_LEVELS = {
        "free": 0,
        "starter": 1,
        "team": 2,
        "enterprise": 3,
    }

    FEATURE_MIN_TIERS = {
        "public_api.access": "free",
        "marketplace.install": "free",
        "webhooks.basic": "free",
        "webhooks.custom": "team",
        "models.standard": "free",
        "models.premium": "team",
        "audit.streaming": "enterprise",
        "sso.saml": "enterprise",
        "support.dedicated_sla": "enterprise",
    }

    TIER_QUOTAS = {
        "free": {
            "api_rate_limit_rps": 5,
            "monthly_token_quota": 100_000,
            "webhook_endpoints_max": 1,
            "active_seats_max": 3,
        },
        "starter": {
            "api_rate_limit_rps": 20,
            "monthly_token_quota": 1_000_000,
            "webhook_endpoints_max": 5,
            "active_seats_max": 10,
        },
        "team": {
            "api_rate_limit_rps": 50,
            "monthly_token_quota": 5_000_000,
            "webhook_endpoints_max": 20,
            "active_seats_max": 50,
        },
        "enterprise": {
            "api_rate_limit_rps": 500,
            "monthly_token_quota": 50_000_000,
            "webhook_endpoints_max": 100,
            "active_seats_max": 1000,
        },
    }

    # Route prefix to required feature capability
    ROUTE_REQUIREMENTS = {
        "/api/public/v1/webhooks/custom": "webhooks.custom",
        "/api/public/v1/audit/stream": "audit.streaming",
        "/api/public/v1/admin/sso": "sso.saml",
    }

    def __init__(self):
        # tenant_id -> tier name
        self._tenant_tiers: Dict[str, str] = {}
        # tenant_id -> set of explicitly granted feature flags
        self._tenant_overrides: Dict[str, Set[str]] = {}
        # tenant_id -> bool (is billing restricted/read-only)
        self._tenant_restricted: Dict[str, bool] = {}

    def set_tenant_tier(self, tenant_id: str, tier: str):
        tier_normalized = tier.lower()
        if tier_normalized not in self.TIER_LEVELS:
            raise ValueError(f"Unknown tier: {tier}. Must be one of {list(self.TIER_LEVELS.keys())}")
        self._tenant_tiers[tenant_id] = tier_normalized

    def get_tenant_tier(self, tenant_id: str) -> str:
        return self._tenant_tiers.get(tenant_id, "free")

    def set_tenant_restricted(self, tenant_id: str, restricted: bool):
        """Used during billing past-due grace period expiry to enforce read-only mode."""
        self._tenant_restricted[tenant_id] = restricted

    def is_tenant_restricted(self, tenant_id: str) -> bool:
        return self._tenant_restricted.get(tenant_id, False)

    def grant_feature_override(self, tenant_id: str, feature_key: str):
        if tenant_id not in self._tenant_overrides:
            self._tenant_overrides[tenant_id] = set()
        self._tenant_overrides[tenant_id].add(feature_key)

    def is_feature_entitled(self, tenant_id: str, feature_key: str) -> EntitlementDecision:
        tier = self.get_tenant_tier(tenant_id)

        # Check explicit override
        if feature_key in self._tenant_overrides.get(tenant_id, set()):
            return EntitlementDecision(
                entitled=True,
                reason=f"Feature '{feature_key}' explicitly granted via tenant override.",
                tier=tier,
            )

        min_tier = self.FEATURE_MIN_TIERS.get(feature_key)
        if not min_tier:
            # If feature is unlisted, default to allowed for backwards compatibility
            return EntitlementDecision(
                entitled=True,
                reason=f"Feature '{feature_key}' has no tier restrictions.",
                tier=tier,
            )

        current_level = self.TIER_LEVELS.get(tier, 0)
        required_level = self.TIER_LEVELS.get(min_tier, 0)

        if current_level >= required_level:
            return EntitlementDecision(
                entitled=True,
                reason=f"Feature '{feature_key}' entitled at plan tier '{tier}' (requires >= '{min_tier}').",
                tier=tier,
            )
        else:
            return EntitlementDecision(
                entitled=False,
                reason=f"Feature '{feature_key}' requires minimum tier '{min_tier}', but tenant is on '{tier}'.",
                tier=tier,
            )

    def check_quota(self, tenant_id: str, metric_name: str, current_usage: int) -> EntitlementDecision:
        tier = self.get_tenant_tier(tenant_id)
        tier_quotas = self.TIER_QUOTAS.get(tier, self.TIER_QUOTAS["free"])
        limit = tier_quotas.get(metric_name, 0)

        if limit == 0:
            return EntitlementDecision(
                entitled=True,
                reason=f"Metric '{metric_name}' is unlimited for tier '{tier}'.",
                tier=tier,
                current_usage=current_usage,
                limit=limit,
            )

        if current_usage <= limit:
            return EntitlementDecision(
                entitled=True,
                reason=f"Usage {current_usage} is within limit {limit} for '{metric_name}'.",
                tier=tier,
                current_usage=current_usage,
                limit=limit,
            )
        else:
            return EntitlementDecision(
                entitled=False,
                reason=f"Usage {current_usage} exceeds quota limit {limit} for metric '{metric_name}' on tier '{tier}'.",
                tier=tier,
                current_usage=current_usage,
                limit=limit,
            )

    def check_route_access(self, tenant_id: str, path: str, headers: Dict[str, str]) -> Tuple[bool, str]:
        """Edge Gateway callback verifying route access entitlements."""
        # If tenant is marked restricted, deny state-mutating requests (POST, PUT, DELETE)
        method = headers.get("X-HTTP-Method", "GET").upper()
        if self.is_tenant_restricted(tenant_id) and method in ("POST", "PUT", "DELETE", "PATCH"):
            return False, f"Tenant '{tenant_id}' is in restricted read-only mode due to billing suspension."

        for prefix, required_feature in self.ROUTE_REQUIREMENTS.items():
            if path.startswith(prefix):
                decision = self.is_feature_entitled(tenant_id, required_feature)
                if not decision.entitled:
                    return False, decision.reason

        return True, "Route authorized."
