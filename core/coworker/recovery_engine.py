"""
ZONATA Universal AI Co-worker Fabric — Self-Healing Recovery Engine
Manages controlled crash recovery and session restoration across Browser, Desktop,
and Worker runtimes without entering infinite retry loops.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
from .contracts import TaskNode, ExecutionResult, ExecutionState, ProviderHealthStatus
from .provider_registry import ProviderRegistry
from .provider_base import CapabilityProvider

class RecoveryEngine:
    """
    Self-healing coordinator for crashed providers, interrupted sessions, and transient failures.
    """

    def __init__(self, provider_registry: ProviderRegistry, max_recovery_attempts: int = 3):
        self.provider_reg = provider_registry
        self.max_attempts = max_recovery_attempts
        self._recovery_history: Dict[str, int] = {}

    def attempt_recovery(
        self,
        task: TaskNode,
        provider: CapabilityProvider,
        error_context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Attempts self-healing on a failed task or crashed provider:
        1. Checks maximum recovery attempts to prevent infinite loops.
        2. Invokes provider.recover(execution_id, error).
        3. Restores session state if available.
        """
        task_key = f"{task.mission_id}_{task.task_id}"
        attempts = self._recovery_history.get(task_key, 0)

        if attempts >= self.max_attempts:
            return False, f"Maximum recovery attempts ({self.max_attempts}) reached for task {task.task_id}; escalation required"

        self._recovery_history[task_key] = attempts + 1
        provider_id = provider.providerId()

        # Execute provider-level recovery
        try:
            success = provider.recover(task.task_id, Exception(error_context.get("error", "Unknown error")))
            if success:
                # Reset provider health if it was marked crashed
                if hasattr(provider, "set_health"):
                    provider.set_health(ProviderHealthStatus.AVAILABLE)
                return True, f"Successfully recovered provider {provider_id} on attempt {attempts + 1}"
            else:
                return False, f"Provider {provider_id} reported recovery failure"
        except Exception as e:
            return False, f"Recovery procedure raised exception: {str(e)}"

    def reset_recovery_counter(self, task_key: str):
        self._recovery_history.pop(task_key, None)
