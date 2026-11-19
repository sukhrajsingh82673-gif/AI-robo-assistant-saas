"""Acceptance Tests AT-06 & AT-07: Batch Concurrency and DAG Dependency Propagation."""

import pytest
from agent_factory.control.planner import (
    plan, next_ready, propagate_failure, batch_verdict, BUILD, DELEGATE, REPORTS
)


def test_at06_concurrent_build_parallelism_limit():
    """AT-06: Verify ready-set scheduling strictly honours max_parallel concurrency limit."""
    agents = [f"agent_{i:02d}" for i in range(12)]
    # No dependencies -> all 12 are candidate roots
    batch_plan = plan(agents, [], max_parallel=4)

    status = {a: "PENDING" for a in agents}
    ready_1 = next_ready(batch_plan, status)
    assert len(ready_1) == 4

    # Simulate wave 1 running
    for a in ready_1:
        status[a] = "BUILDING"

    # Attempting to fetch next ready when 4 are already running yields empty list
    ready_2 = next_ready(batch_plan, status)
    assert len(ready_2) == 0

    # Once 2 agents complete, exactly 2 more can start
    status[ready_1[0]] = "SUCCEEDED"
    status[ready_1[1]] = "SUCCEEDED"
    ready_3 = next_ready(batch_plan, status)
    assert len(ready_3) == 2


def test_at07_dag_dependency_and_failure_propagation():
    """AT-07: Prerequisite must succeed before downstream can start; failure blocks dependents."""
    agents = ["db_connector", "data_transformer", "report_exporter"]
    edges = [
        ("db_connector", "data_transformer", BUILD),
        ("data_transformer", "report_exporter", BUILD)
    ]
    batch_plan = plan(agents, edges, max_parallel=2)

    status = {a: "PENDING" for a in agents}

    # Only db_connector is ready initially
    ready = next_ready(batch_plan, status)
    assert ready == ["db_connector"]

    # If db_connector fails, failure propagates: data_transformer and report_exporter are BLOCKED
    status_failed = propagate_failure(batch_plan, status, failed="db_connector")
    assert status_failed["db_connector"] == "FAILED"
    assert status_failed["data_transformer"] == "BLOCKED"
    assert status_failed["report_exporter"] == "BLOCKED"

    # In atomic_team policy, the entire batch verdict becomes FAILED
    verdict = batch_verdict(status_failed, release_policy="atomic_team")
    assert verdict == "FAILED"
