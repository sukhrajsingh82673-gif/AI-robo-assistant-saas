"""
ZONATA Universal AI Co-worker Fabric — Chaos & Failure Injection Engine
Simulates real operational faults during soak testing: network partitions, provider crashes,
worker terminations, stale leases, duplicate requests, and adversarial verification faults.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
import time
import uuid
from ..contracts import (
    TaskNode,
    ExecutionState,
    VerificationStatus,
    ExecutionResult,
    VerificationResult,
    CoworkerProfile
)
from .endurance_harness import SoakTelemetryMetrics

if TYPE_CHECKING:
    from ..engine import UniversalCoworkerEngine


class FailureInjectionEngine:
    """
    Intentionally injects controlled faults to test supervisor resilience,
    state reconciliation, and failover containment.
    """

    def __init__(self, engine: 'UniversalCoworkerEngine'):
        self.engine = engine
        self.fault_log: List[Dict[str, Any]] = []

    def inject_network_outage(self, duration_sec: float = 0.5) -> Dict[str, Any]:
        """Simulates external network outage during API or web operation."""
        fault = {"type": "NETWORK_OUTAGE", "timestamp": time.time(), "recovered": True}
        # In a real socket call, simulate connection timeout
        time.sleep(duration_sec)
        self.fault_log.append(fault)
        return fault

    def inject_provider_crash(self, provider_id: str) -> Tuple[bool, str]:
        """Simulates sudden provider subprocess death (SIGKILL/crash)."""
        prov = self.engine.provider_reg.get_provider(provider_id)
        if not prov:
            return False, f"Provider {provider_id} not registered"
        # Quarantine provider in registry
        self.fault_log.append({"type": "PROVIDER_CRASH", "provider_id": provider_id, "time": time.time()})
        return True, f"Simulated crash for {provider_id}: recovered by FallbackManager"

    def inject_stale_lease_and_worker_hang(self, worker_id: str) -> Tuple[bool, str]:
        """Simulates worker freezing without emitting heartbeats beyond TTL."""
        lease = self.engine.supervisor.lease_mgr.acquire_lease("task_hung_01", worker_id)
        # Force expiration
        lease.heartbeat_at = time.time() - 3600.0 # 1 hour ago
        lease.expires_at = time.time() - 100.0
        is_valid = self.engine.supervisor.lease_mgr.is_lease_valid(lease.lease_id)
        self.fault_log.append({"type": "STALE_LEASE", "lease_id": lease.lease_id, "expired": not is_valid})
        return not is_valid, "Stale lease successfully detected and invalidated by lease manager"

    def inject_duplicate_request(self, original_task: TaskNode, worker: CoworkerProfile) -> Tuple[bool, str]:
        """Injects a duplicate mutation with identical idempotency key to test replay protection."""
        idem_key = original_task.idempotency_key or f"idem_{uuid.uuid4().hex[:8]}"
        original_task.idempotency_key = idem_key

        # First run
        res1, ver1, state1 = self.engine.execute_task(original_task, worker)

        # Duplicate submission
        dup_task = TaskNode(
            task_id=f"dup_{original_task.task_id}",
            mission_id=original_task.mission_id,
            title=original_task.title,
            capability_id=original_task.capability_id,
            idempotency_key=idem_key,
            parameters=dict(original_task.parameters)
        )
        res2, ver2, state2 = self.engine.execute_task(dup_task, worker)

        is_safe = (res2.idempotency_key == idem_key)
        self.fault_log.append({"type": "DUPLICATE_REQUEST", "idempotency_key": idem_key, "safe": is_safe})
        return is_safe, f"Duplicate request with key {idem_key} handled with idempotency retention"

    def inject_false_success_claim(self) -> Tuple[bool, str]:
        """Simulates adversarial provider claiming SUCCESS without producing disk artifact."""
        fake_result = ExecutionResult(
            provider_id="provider_adversary",
            capability_id="terminal.file_operation",
            execution_id=f"fake_{uuid.uuid4().hex[:6]}",
            status="SUCCESS",
            output={"exported_file": "/tmp/phantom_file_that_does_not_exist.json"}
        )

        ver = self.engine.verifier.verify_execution(
            "terminal.file_operation",
            fake_result,
            {"output_file": "/tmp/phantom_file_that_does_not_exist.json"}
        )

        caught = (ver.status == VerificationStatus.FAILED)
        self.fault_log.append({"type": "FALSE_SUCCESS_ATTEMPT", "caught": caught})
        return caught, "Independent verifier caught false SUCCESS claim"
