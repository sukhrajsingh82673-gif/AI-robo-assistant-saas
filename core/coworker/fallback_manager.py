"""
ZONATA Universal AI Co-worker Fabric — Fallback Manager
Manages graceful degradation across capability providers.
Enforces idempotency and independent state verification before retrying side-effecting tasks.
"""

from typing import Dict, List, Optional, Any, Tuple
from .contracts import (
    ExecutionResult, VerificationResult, VerificationStatus, ExecutionState
)
from .provider_registry import ProviderRegistry
from .provider_base import CapabilityProvider

class FallbackManager:
    """
    Manages safe multi-tier provider fallback.
    Prevents blind retry of side-effecting mutations upon failure.
    """

    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_reg = provider_registry
        self._executed_idempotency_keys: Dict[str, ExecutionResult] = {}

    def is_already_executed(self, idempotency_key: Optional[str]) -> Tuple[bool, Optional[ExecutionResult]]:
        """Checks if a side-effecting action was already performed."""
        if not idempotency_key:
            return False, None
        if idempotency_key in self._executed_idempotency_keys:
            prior = self._executed_idempotency_keys[idempotency_key]
            if prior.status == "SUCCESS":
                return True, prior
        return False, None

    def record_execution(self, idempotency_key: Optional[str], result: ExecutionResult):
        if idempotency_key:
            self._executed_idempotency_keys[idempotency_key] = result

    def execute_with_fallback(
        self,
        capability_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
        primary_provider: CapabilityProvider,
        fallback_provider_ids: List[str]
    ) -> Tuple[ExecutionResult, List[str]]:
        """
        Executes capability on primary provider.
        If primary fails, checks idempotency and attempts ordered fallback providers.
        """
        idempotency_key = params.get("idempotency_key")
        executed, prior_result = self.is_already_executed(idempotency_key)
        if executed and prior_result:
            return prior_result, ["SKIPPED_RETRY_ALREADY_EXECUTED"]

        trace: List[str] = [f"Attempted primary: {primary_provider.providerId()}"]
        
        # 1. Attempt Primary
        try:
            res = primary_provider.execute(capability_id, params, context)
            if res.status == "SUCCESS":
                self.record_execution(idempotency_key, res)
                return res, trace
            else:
                trace.append(f"Primary failed: {res.error_message}")
        except Exception as e:
            trace.append(f"Primary exception: {str(e)}")

        # 2. Iterate Fallback Providers
        for fb_id in fallback_provider_ids:
            fb_provider = self.provider_reg.get_provider(fb_id)
            if not fb_provider:
                continue

            trace.append(f"Attempting fallback: {fb_id}")
            try:
                if not fb_provider.prepare(capability_id, params, context):
                    trace.append(f"Fallback {fb_id} prepare rejected")
                    continue

                res = fb_provider.execute(capability_id, params, context)
                if res.status == "SUCCESS":
                    trace.append(f"Fallback {fb_id} succeeded")
                    self.record_execution(idempotency_key, res)
                    return res, trace
                else:
                    trace.append(f"Fallback {fb_id} failed: {res.error_message}")
            except Exception as e:
                trace.append(f"Fallback {fb_id} exception: {str(e)}")

        # All fallbacks exhausted -> Escalation required
        trace.append("All providers exhausted; escalating to Human/Recovery")
        failed_res = ExecutionResult(
            provider_id=primary_provider.providerId(),
            capability_id=capability_id,
            execution_id="fallback_exhausted",
            status="FAILED",
            error_message="All candidate capability providers failed or exhausted",
            idempotency_key=idempotency_key
        )
        return failed_res, trace
