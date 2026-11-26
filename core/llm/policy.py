"""
ZONATA Universal AI Operating System — Tenant LLM Data Policy & Sensitivity Guard
Enforces data boundaries, allowed providers, zero-retention mandates, and RESTRICTED document handling.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.db import db, tenant_scoped, tenant_scope

logger = logging.getLogger("zonata.llm.policy")


class DataPolicyViolationError(PermissionError):
    """Raised when an AI prompt or document violates tenant model policy or sensitivity rules."""
    pass


@dataclass
class TenantModelPolicyConfig:
    tenant_id: str
    company_id: str
    allowed_providers: List[str]
    allowed_regions: List[str]
    require_no_retention: bool
    block_restricted_docs: bool
    allow_degraded: bool


class TenantModelPolicyManager:
    """Manages and evaluates per-tenant AI data and provider policies."""

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        try:
            from core.llm import ensure_model_gateway_tables
            ensure_model_gateway_tables()
        except Exception:
            pass

    @tenant_scoped
    def get_policy(self, tenant_id: str, company_id: str) -> TenantModelPolicyConfig:
        """Fetch tenant model policy configuration, or return secure defaults."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT allowed_providers_json, allowed_regions_json, require_no_retention,
                   block_restricted_docs, allow_degraded
            FROM tenant_model_policies
            WHERE tenant_id = ? AND company_id = ?
            LIMIT 1
            """, (tenant_id, company_id))
            row = cur.fetchone()
            if row:
                return TenantModelPolicyConfig(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    allowed_providers=json.loads(row[0] or "[]"),
                    allowed_regions=json.loads(row[1] or "[]"),
                    require_no_retention=bool(row[2]),
                    block_restricted_docs=bool(row[3]),
                    allow_degraded=bool(row[4]),
                )

        # Secure defaults: standard providers allowed, RESTRICTED blocked unless explicit
        return TenantModelPolicyConfig(
            tenant_id=tenant_id,
            company_id=company_id,
            allowed_providers=["anthropic", "openai", "google", "ollama", "sandbox"],
            allowed_regions=["us", "eu"],
            require_no_retention=False,
            block_restricted_docs=True,
            allow_degraded=False,
        )

    @tenant_scoped
    def set_policy(
        self,
        tenant_id: str,
        company_id: str,
        allowed_providers: List[str],
        allowed_regions: Optional[List[str]] = None,
        require_no_retention: bool = False,
        block_restricted_docs: bool = True,
        allow_degraded: bool = False,
        caller_principal_type: str = "HUMAN",
    ) -> None:
        """Configure tenant model policy. Enforces Rule 15 principal separation."""
        if caller_principal_type in ("AGENT", "AI_EMPLOYEE", "MODEL", "SYSTEM_AGENT") or caller_principal_type.startswith(("agt_", "ai_emp_")):
            raise PermissionError(f"Rule 15 Violation: Principal '{caller_principal_type}' cannot write policies")

        import time
        now = time.time()
        policy_id = f"pol_{tenant_id}_{company_id}"
        providers_json = json.dumps([p.lower() for p in allowed_providers])
        regions_json = json.dumps([r.lower() for r in (allowed_regions or ["us", "eu"])])

        with db.get_connection() as conn:
            cur = conn.cursor()
            is_pg = (getattr(db, "dialect", "") == "postgresql" or getattr(db, "get_dialect", lambda: "")() == "postgresql")
            if is_pg:
                cur.execute("""
                INSERT INTO tenant_model_policies (
                    policy_id, tenant_id, company_id, allowed_providers_json,
                    allowed_regions_json, require_no_retention, block_restricted_docs,
                    allow_degraded, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (tenant_id, company_id) DO UPDATE SET
                    allowed_providers_json = EXCLUDED.allowed_providers_json,
                    allowed_regions_json = EXCLUDED.allowed_regions_json,
                    require_no_retention = EXCLUDED.require_no_retention,
                    block_restricted_docs = EXCLUDED.block_restricted_docs,
                    allow_degraded = EXCLUDED.allow_degraded,
                    updated_at = EXCLUDED.updated_at
                """, (
                    policy_id, tenant_id, company_id, providers_json, regions_json,
                    1 if require_no_retention else 0,
                    1 if block_restricted_docs else 0,
                    1 if allow_degraded else 0,
                    now, now
                ))
            else:
                cur.execute("""
                INSERT INTO tenant_model_policies (
                    policy_id, tenant_id, company_id, allowed_providers_json,
                    allowed_regions_json, require_no_retention, block_restricted_docs,
                    allow_degraded, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (tenant_id, company_id) DO UPDATE SET
                    allowed_providers_json = EXCLUDED.allowed_providers_json,
                    allowed_regions_json = EXCLUDED.allowed_regions_json,
                    require_no_retention = EXCLUDED.require_no_retention,
                    block_restricted_docs = EXCLUDED.block_restricted_docs,
                    allow_degraded = EXCLUDED.allow_degraded,
                    updated_at = EXCLUDED.updated_at
                """, (
                    policy_id, tenant_id, company_id, providers_json, regions_json,
                    1 if require_no_retention else 0,
                    1 if block_restricted_docs else 0,
                    1 if allow_degraded else 0,
                    now, now
                ))
            conn.commit()

    @tenant_scoped
    def validate_dispatch(
        self,
        tenant_id: str,
        company_id: str,
        provider: str,
        document_sensitivities: Optional[List[str]] = None,
        region: str = "us"
    ) -> None:
        """Validate whether a model dispatch is permitted under tenant policy and environment guards."""
        provider_clean = provider.lower()
        is_prod = os.environ.get("APP_ENV") == "production"
        allow_degraded_env = os.environ.get("ZONATA_ALLOW_DEGRADED") == "1"

        # Production Guard: refuse embedded_free unless explicitly permitted
        if provider_clean == "embedded_free" and is_prod and not allow_degraded_env:
            raise DataPolicyViolationError(
                "Production profile refuses 'embedded_free' provider. "
                "Set ZONATA_ALLOW_DEGRADED=1 to run in degraded mode."
            )

        policy = self.get_policy(tenant_id, company_id)

        # Sensitivity / RESTRICTED Document check
        if document_sensitivities:
            for s in document_sensitivities:
                if str(s).upper() == "RESTRICTED" and policy.block_restricted_docs:
                    raise DataPolicyViolationError(
                        f"Dispatch rejected: Document with sensitivity 'RESTRICTED' cannot be transmitted "
                        f"to external provider '{provider}' under tenant policy."
                    )

        # Provider Allow-list check
        if policy.allowed_providers:
            allowed = [p.lower() for p in policy.allowed_providers]
            if provider_clean not in allowed and not (provider_clean.startswith("sandbox") and "sandbox" in allowed):
                raise DataPolicyViolationError(
                    f"Provider '{provider}' is not permitted under tenant model policy for company '{company_id}'. "
                    f"Allowed providers: {policy.allowed_providers}"
                )


# Global Singleton
tenant_model_policy = TenantModelPolicyManager()
tenant_model_policy_manager = tenant_model_policy
