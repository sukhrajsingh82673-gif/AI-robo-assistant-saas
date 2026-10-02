"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Enterprise Multi-Process Resilience & High-Availability Test Suite (V3)
Validates real multi-process concurrency, dual-API horizontal scale,
multi-worker atomic queue dispatch, and HA supervisor failover takeover.
Classification: REAL_LOCAL_INFRASTRUCTURE
"""

import os
import sys
import time
import json
import uuid
import signal
import socket
import unittest
import subprocess
import urllib.request
import concurrent.futures
from typing import List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.database_engine import engine, WorkloadType
from core.action_envelope import ActionEnvelope, command_bus
from core.supervisor_ha import SupervisorHA, SupervisorRole
from core.distributed_coordination import coordination
from core.evidence_service import evidence_service
from core.agent_resource_governor import resource_governor, PlanTier

def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect((host, port))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def wait_for_port(port: int, timeout: float = 12.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port):
            return True
        time.sleep(0.2)
    return False

class TestV3MultiProcessResilience(unittest.TestCase):
    CLASSIFICATION = "REAL_LOCAL_INFRASTRUCTURE"

    @classmethod
    def setUpClass(cls):
        # Ensure database tables exist and seed parent records
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, status, plan, created_at) VALUES ('tnt_v3', 'V3 Tenant', 'ACTIVE', 'ENTERPRISE', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO companies (company_id, tenant_id, name, status, created_at) VALUES ('comp_v3', 'tnt_v3', 'V3 Company', 'OPERATIONAL', ?)", (time.time(),))

    def setUp(self):
        self.procs: List[subprocess.Popen] = []

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                try:
                    proc.send_signal(signal.SIGTERM)
                    proc.wait(timeout=2.0)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

    def test_01_dynamic_agent_quota_and_tier_enforcement(self):
        """Verify dynamic plan tiers enforce quota thresholds without hard platform ceilings."""
        tenant_id = "tnt_v3_quotas"
        
        # Starter Tier: Limit 25 agents
        resource_governor.set_tenant_tier(tenant_id, PlanTier.STARTER)
        limits = resource_governor.get_tenant_limits(tenant_id)
        self.assertEqual(limits["max_concurrent_agents"], 25)
        
        # Register 25 agents successfully
        for i in range(25):
            admitted, reason = resource_governor.register_active_agent(tenant_id, f"agt_starter_{i}")
            self.assertTrue(admitted, f"Failed at agent {i}: {reason}")
            
        # 26th agent must be rejected / queued
        admitted, reason = resource_governor.register_active_agent(tenant_id, "agt_starter_25")
        self.assertFalse(admitted)
        self.assertIn("capacity (25) reached", reason)

        # Upgrade to Enterprise Tier: Limit 500 agents
        resource_governor.set_tenant_tier(tenant_id, PlanTier.ENTERPRISE)
        limits = resource_governor.get_tenant_limits(tenant_id)
        self.assertEqual(limits["max_concurrent_agents"], 500)

        # Now 26th agent succeeds immediately
        admitted, reason = resource_governor.register_active_agent(tenant_id, "agt_starter_25")
        self.assertTrue(admitted)

        # Cleanup
        for i in range(26):
            resource_governor.unregister_active_agent(tenant_id, f"agt_starter_{i}")
        self.assertEqual(resource_governor.get_active_agent_count(tenant_id), 0)

    def test_02_dual_api_server_horizontal_concurrency(self):
        """Spawn 2 independent API servers on distinct ports and verify concurrent liveness & readiness."""
        port1 = 8185
        port2 = 8186

        # Start API Instance 1
        p1 = subprocess.Popen(
            [sys.executable, "api_server.py", str(port1)],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.procs.append(p1)

        # Start API Instance 2
        p2 = subprocess.Popen(
            [sys.executable, "api_server.py", str(port2)],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.procs.append(p2)

        # Verify both ports bind and respond
        self.assertTrue(wait_for_port(port1, timeout=45.0), f"API 1 failed to bind port {port1}")
        self.assertTrue(wait_for_port(port2, timeout=45.0), f"API 2 failed to bind port {port2}")

        # Check endpoints via HTTP client
        for p in (port1, port2):
            req = urllib.request.Request(f"http://127.0.0.1:{p}/readyz")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode())
                self.assertIn(body.get("status"), ("HEALTHY", "READY"))

    def test_03_multi_worker_atomic_queue_dispatch_zero_duplicates(self):
        """Enqueue multiple ActionEnvelopes and verify concurrent workers claim without duplicate execution."""
        tenant_id = f"tnt_v3_worker_{uuid.uuid4().hex[:6]}"
        company_id = "comp_v3"
        agent_id = "agt_v3"

        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, status, plan, created_at) VALUES (?, 'Worker Tenant', 'ACTIVE', 'ENTERPRISE', ?)", (tenant_id, time.time()))
            conn.execute("DELETE FROM async_command_queue WHERE tenant_id = ?", (tenant_id,))

        # Enqueue 6 distinct commands
        action_ids = []
        for i in range(6):
            envelope = ActionEnvelope.create(
                tenant_id=tenant_id,
                company_id=company_id,
                agent_id=agent_id,
                capability_id=f"test.mutation.{i}",
                target="system",
                intent=f"Concurrent worker task #{i}",
                parameters={"index": i, "payload": f"data_{i}"},
                risk_class="LOW_RISK"
            )
            aid = command_bus.enqueue(envelope)
            action_ids.append(aid)

        self.assertEqual(len(action_ids), 6)

        # Launch two concurrent worker threads that fetch and execute tasks
        worker_1_claimed = []
        worker_2_claimed = []

        import threading
        def worker_loop(wid: str, claimed_list: list):
            for _ in range(15):
                item = command_bus.fetch_next(worker_id=wid, tenant_id=tenant_id)
                if item:
                    claimed_list.append(item.action_id)
                    time.sleep(0.02)
                    command_bus.mark_completed(item.action_id, {"processed_by": wid})
                else:
                    time.sleep(0.02)

        t1 = threading.Thread(target=worker_loop, args=("worker_alpha", worker_1_claimed))
        t2 = threading.Thread(target=worker_loop, args=("worker_beta", worker_2_claimed))

        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        total_claimed = worker_1_claimed + worker_2_claimed
        # Invariant 1: Total processed items equals 6
        self.assertEqual(len(total_claimed), 6)

        # Invariant 2: No duplicates claimed (set length equals list length)
        self.assertEqual(len(set(total_claimed)), 6)
        self.assertEqual(set(total_claimed), set(action_ids))

        # Invariant 3: Both workers participated in processing
        self.assertGreater(len(worker_1_claimed), 0)
        self.assertGreater(len(worker_2_claimed), 0)

        # Verify all are COMPLETED in the database
        for aid in action_ids:
            status = command_bus.get_status(aid)
            self.assertIsNotNone(status)
            self.assertEqual(status["status"], "COMPLETED")

    def test_04_ha_supervisor_leader_election_and_failover_takeover(self):
        """Verify active-passive supervisor leader election, lease renewal, and instant failover on termination."""
        tenant_id = "tnt_v3"
        company_id = "comp_v3"

        # Initialize Supervisor Node 1 and Node 2 with generous lease and fast tick for robust HA testing
        node1 = SupervisorHA(
            tenant_id=tenant_id,
            company_id=company_id,
            node_id="node_1_primary",
            tick_interval_sec=0.1,
            lease_seconds=5.0
        )
        node2 = SupervisorHA(
            tenant_id=tenant_id,
            company_id=company_id,
            node_id="node_2_standby",
            tick_interval_sec=0.1,
            lease_seconds=5.0
        )

        try:
            # Start Node 1 -> should become LEADER
            node1.start()
            for _ in range(30):
                if node1.role == SupervisorRole.LEADER:
                    break
                time.sleep(0.1)
            self.assertEqual(node1.role, SupervisorRole.LEADER)

            # Start Node 2 -> should remain in STANDBY
            node2.start()
            time.sleep(0.4)
            self.assertEqual(node2.role, SupervisorRole.STANDBY)
            self.assertEqual(node1.role, SupervisorRole.LEADER)

            # Failover: Terminate Node 1 gracefully releasing lease
            node1.stop()
            self.assertEqual(node1.role, SupervisorRole.STOPPED)

            # Node 2 should detect available lease on next cycle and acquire leadership
            for _ in range(40):
                if node2.role == SupervisorRole.LEADER:
                    break
                time.sleep(0.1)
            self.assertEqual(node2.role, SupervisorRole.LEADER)
            self.assertGreaterEqual(node2.leader_acquisitions, 1)

        finally:
            node1.stop()
            node2.stop()

    def test_05_evidence_merkle_chain_integrity_under_concurrency(self):
        """Verify transactional evidence ledger maintains valid cryptographic Merkle chain under concurrent writes."""
        tenant_id = "tnt_v3"
        company_id = "comp_v3"

        def write_evidence(i: int):
            return evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="CONCURRENT_V3_STEP",
                payload={"index": i, "data": f"payload_{i}"},
                action_id=f"act_concur_{i}_{time.time()}",
                causality_id=f"caus_{i}"
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_evidence, i) for i in range(15)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 15)
        for r in results:
            cur_hash = r.get("current_hash", "")
            self.assertTrue(isinstance(cur_hash, str) and len(cur_hash) == 64)

        # Audit ledger integrity
        audit_result = evidence_service.verify_chain_integrity(tenant_id=tenant_id)
        self.assertTrue(audit_result.get("valid", False), f"Audit failed: {audit_result}")

if __name__ == "__main__":
    unittest.main()
