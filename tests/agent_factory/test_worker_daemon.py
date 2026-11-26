"""ZONATA Agent Factory - Worker Daemon and AT-19 Recovery Tests.

Tests:
- Autonomous job claiming via DbQueueOrchestrator
- Lease heartbeat
- Pipeline execution & completion
- AT-19: Worker crash / heartbeat timeout detection & recovery (status LOST)
"""

import sqlite3
import pytest
import time

from agent_factory.control.orchestrator import DbQueueOrchestrator
from agent_factory.worker import FactoryWorker


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_worker.db"
    conn = sqlite3.connect(str(db_file))
    with open("migrations/sqlite/0013_agent_factory_core.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_file)


def test_worker_run_once_success(test_db):
    """Test standard single job acquisition, heartbeat, execution, and completion."""
    def get_conn():
        return sqlite3.connect(test_db)

    orchestrator = DbQueueOrchestrator(db_conn_factory=get_conn, worker_id="worker-test-01")
    
    # Enqueue a build job
    build_id = orchestrator.enqueue_build(tenant_id="tenant-w1", sandbox_profile="T0")
    assert build_id.startswith("bld_")

    executed_jobs = []
    def dummy_pipeline(job):
        executed_jobs.append(job["build_id"])
        return {"artifacts": ["art_1"]}

    worker = FactoryWorker(orchestrator=orchestrator, pipeline_executor=dummy_pipeline)
    
    # Run one cycle
    res = worker.run_once(tenant_id="tenant-w1")
    assert res is not None
    assert res["status"] == "SUCCEEDED"
    assert res["build_id"] == build_id
    assert executed_jobs == [build_id]

    # Verify DB status
    with get_conn() as conn:
        row = conn.execute("SELECT status, worker_id, finished_at FROM af_build WHERE id = ?", (build_id,)).fetchone()
        assert row[0] == "SUCCEEDED"
        assert row[1] == "worker-test-01"
        assert row[2] is not None


def test_at19_worker_crash_and_lost_job_recovery(test_db):
    """AT-19: Simulate worker crash mid-stage, verify heartbeat timeout marks job LOST."""
    def get_conn():
        return sqlite3.connect(test_db)

    orch_1 = DbQueueOrchestrator(db_conn_factory=get_conn, worker_id="worker-crashed-1")
    orch_2 = DbQueueOrchestrator(db_conn_factory=get_conn, worker_id="worker-healthy-2")

    tenant_id = "tenant-at19"
    build_id = orch_1.enqueue_build(tenant_id=tenant_id)

    # Worker 1 claims job
    claimed = orch_1.claim_next_build(tenant_id=tenant_id)
    assert claimed["build_id"] == build_id

    # Simulate worker crash mid-stage:
    # Heartbeat was 120 seconds ago (expired)
    stale_time = time.time() - 120.0
    with get_conn() as conn:
        conn.execute("UPDATE af_build SET heartbeat_at = ? WHERE id = ?", (stale_time, build_id))
        conn.commit()

    # Worker 2 sweeps lost builds
    worker_2 = FactoryWorker(orchestrator=orch_2)
    reaped = orch_2.reap_lost_builds(timeout_seconds=60.0)
    assert reaped == 1, "Orchestrator should detect and reap exactly 1 timed out job"

    with get_conn() as conn:
        status, error = conn.execute("SELECT status, error FROM af_build WHERE id = ?", (build_id,)).fetchone()
        assert status == "LOST"
        assert "Heartbeat timed out" in error
