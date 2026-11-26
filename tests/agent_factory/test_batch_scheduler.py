"""Tests for Batch Planner & Scheduler (Lifting reference/qa/batch_scheduler.py)."""

import pytest
from agent_factory.control.planner import (
    plan, next_ready, propagate_failure, batch_verdict, PlanError,
    BUILD, DELEGATE, REPORTS
)


def test_batch_planner_15_reference_tests():
    """All 15 authoritative tests from reference/qa/batch_scheduler.py."""
    N = ["supervisor", "market_research", "competitor", "customer_intel", "trend", "campaign", "reporting"]
    E = [
        ("market_research", "campaign", BUILD),
        ("competitor", "campaign", BUILD),
        ("customer_intel", "campaign", BUILD),
        ("trend", "campaign", BUILD),
        ("campaign", "supervisor", BUILD),
        ("reporting", "supervisor", BUILD),
        ("market_research", "reporting", BUILD),
        ("supervisor", "market_research", DELEGATE),
        ("supervisor", "competitor", DELEGATE),
        ("supervisor", "customer_intel", DELEGATE),
        ("supervisor", "trend", DELEGATE),
        ("supervisor", "campaign", DELEGATE),
        ("supervisor", "reporting", DELEGATE)
    ] + [(n, "supervisor", REPORTS) for n in N if n != "supervisor"]

    # 1. 7-agent marketing team plans into 3 waves
    p = plan(N, E)
    assert len(p["waves"]) == 3

    # 2. Independent specialists share wave 0 (build concurrently)
    assert {"competitor", "customer_intel", "trend", "market_research"} <= set(p["waves"][0])

    # 3. Supervisor is last
    assert p["wave"]["supervisor"] == 2 or p["wave"]["supervisor"] == max(p["wave"].values())

    # 4. Ready set honours max_parallel=4
    st = {n: "PENDING" for n in N}
    assert len(next_ready(p, st)) == 4

    # 5. Campaign becomes ready after its 4 prerequisites
    st.update({n: "CERTIFIED" for n in ["market_research", "competitor", "customer_intel", "trend"]})
    assert "campaign" in next_ready(p, st)

    # 6. Failed agent blocks transitive dependents
    st2 = propagate_failure(p, {n: "PENDING" for n in N}, "competitor")
    assert st2["campaign"] == "BLOCKED" and st2["supervisor"] == "BLOCKED"

    # 7. Independent siblings are NOT blocked
    assert st2["trend"] == "PENDING"

    # 8. Failed agent never becomes certified (atomic_team => FAILED once settled)
    settled = {**st2, "trend": "CERTIFIED", "market_research": "CERTIFIED", "customer_intel": "CERTIFIED", "reporting": "BLOCKED"}
    assert batch_verdict(settled, "atomic_team") == "FAILED"

    # 9. Independent policy reports PARTIAL, not success
    assert batch_verdict({"a": "CERTIFIED", "b": "FAILED"}, "independent") == "PARTIAL"

    # 10. All certified + atomic => proceeds to TEAM_QA
    assert batch_verdict({"a": "CERTIFIED", "b": "CERTIFIED"}, "atomic_team") == "TEAM_QA"

    # 11. Build cycle rejected
    with pytest.raises(PlanError):
        plan(["a", "b", "c"], [("a", "b", BUILD), ("b", "a", BUILD)])

    # 12. Delegation loop rejected
    with pytest.raises(PlanError):
        plan(["a", "b", "c"], [("a", "b", DELEGATE), ("b", "a", DELEGATE)])

    # 13. Two supervisors rejected
    with pytest.raises(PlanError):
        plan(["a", "b", "c"], [("a", "b", REPORTS), ("a", "c", REPORTS)])

    # 14. Unknown node rejected
    with pytest.raises(PlanError):
        plan(["a", "b", "c"], [("a", "zzz", BUILD)])

    # 15. 300-agent fleet plans in a single wave
    big = [f"a{i}" for i in range(300)]
    assert len(plan(big, [])["waves"]) == 1
