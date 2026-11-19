"""Acceptance Tests AT-04 & AT-05: Hierarchical Multi-Agent Team and Supervisor Manifest."""

import pytest
from agent_factory.control.planner import (
    plan, compile_team_manifest, BUILD, DELEGATE, REPORTS
)


def test_at04_at05_hierarchical_team_and_supervisor_manifest():
    """Verify hierarchical team planning across 3 topological waves and supervisor compilation."""
    agents = [
        "supervisor", "market_research", "competitor_intel",
        "customer_intel", "trend_analysis", "campaign_strategy", "reporting"
    ]
    edges = [
        ("market_research", "campaign_strategy", BUILD),
        ("competitor_intel", "campaign_strategy", BUILD),
        ("customer_intel", "campaign_strategy", BUILD),
        ("trend_analysis", "campaign_strategy", BUILD),
        ("campaign_strategy", "supervisor", BUILD),
        ("reporting", "supervisor", BUILD),
        ("market_research", "reporting", BUILD),
        ("supervisor", "market_research", DELEGATE),
        ("supervisor", "competitor_intel", DELEGATE),
        ("supervisor", "customer_intel", DELEGATE),
        ("supervisor", "trend_analysis", DELEGATE),
        ("supervisor", "campaign_strategy", DELEGATE),
        ("supervisor", "reporting", DELEGATE)
    ] + [(n, "supervisor", REPORTS) for n in agents if n != "supervisor"]

    # 1. Topological planning into 3 waves
    batch_plan = plan(agents, edges, max_parallel=4)
    assert len(batch_plan["waves"]) == 3
    assert batch_plan["wave"]["supervisor"] == 2
    assert "campaign_strategy" in batch_plan["waves"][1]

    # 2. Team manifest compilation
    agent_specs = {
        name: {
            "metadata": {"category": "marketing", "risk_tier": "R1"},
            "role": {"title": f"{name.replace('_', ' ').title()} Specialist"}
        }
        for name in agents
    }

    team_manifest = compile_team_manifest(
        team_name="marketing-growth-squad",
        batch_plan=batch_plan,
        agent_specs=agent_specs,
        tenant_id="tnt_at04",
        company_id="comp_at04"
    )

    assert team_manifest["apiVersion"] == "zonata.team/v1"
    assert team_manifest["kind"] == "AgentTeam"
    assert team_manifest["metadata"]["name"] == "marketing-growth-squad"
    assert team_manifest["topology"]["type"] == "hierarchical"
    assert team_manifest["topology"]["supervisor"] == "supervisor"
    assert len(team_manifest["members"]) == 7

    # Supervisor member is identified
    sup_member = [m for m in team_manifest["members"] if m["key"] == "supervisor"][0]
    assert sup_member["is_supervisor"] is True
    assert sup_member["wave"] == 2
