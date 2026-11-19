"""ZONATA Agent Factory - Batch & Multi-Agent Planner.

Lifts reference/qa/batch_scheduler.py into production architecture.
Provides DAG validation, wave assignment, ready-set scheduling,
partial-failure propagation, team manifest packaging, and supervisor compilation.
"""

from __future__ import annotations
import copy
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

BUILD = "build_requires"
DELEGATE = "runtime_delegates_to"
REPORTS = "reports_to"


class PlanError(ValueError):
    """Raised when batch DAG validation fails (cycles, unknown nodes, multiple supervisors)."""
    pass


def _has_cycle(nodes: List[str], edges: List[Tuple[str, str]]) -> bool:
    """Kahn's algorithm for cycle detection."""
    adj = defaultdict(list)
    indeg = {n: 0 for n in nodes}
    for a, b in edges:
        adj[a].append(b)
        indeg[b] += 1
    q = deque(n for n, d in indeg.items() if d == 0)
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    return seen != len(nodes)


def plan(
    nodes: List[str],
    edges: List[Tuple[str, str, str]],
    max_parallel: int = 4,
    max_agents: int = 500
) -> Dict[str, Any]:
    """Validate DAG constraints and compute topological execution waves."""
    if len(nodes) != len(set(nodes)):
        raise PlanError("duplicate agent_key")
    if not (1 <= len(nodes) <= max_agents):
        raise PlanError(f"agent count out of range (1..{max_agents})")

    node_set = set(nodes)
    for a, b, k in edges:
        if a not in node_set or b not in node_set:
            raise PlanError(f"edge references unknown node: {a}->{b}")
        if k not in (BUILD, DELEGATE, REPORTS):
            raise PlanError(f"unknown edge kind {k}")
        if a == b:
            raise PlanError("self edge")

    by = lambda kind: [(a, b) for a, b, k in edges if k == kind]

    if _has_cycle(nodes, by(BUILD)):
        raise PlanError("cycle in build_requires")
    if _has_cycle(nodes, by(DELEGATE)):
        raise PlanError("cycle in runtime_delegates_to (delegation loops are forbidden)")

    parents = defaultdict(list)
    for a, b in by(REPORTS):
        parents[a].append(b)
    if any(len(v) > 1 for v in parents.values()):
        raise PlanError("an agent may report to exactly one supervisor")
    if _has_cycle(nodes, by(REPORTS)):
        raise PlanError("cycle in reports_to")

    # wave = longest build_requires path from a root
    req = defaultdict(list)
    for a, b in by(BUILD):
        req[b].append(a)

    wave: Dict[str, int] = {}

    def w(n: str) -> int:
        if n not in wave:
            wave[n] = 0 if not req[n] else 1 + max(w(p) for p in req[n])
        return wave[n]

    for n in nodes:
        w(n)

    waves = defaultdict(list)
    for n, k in wave.items():
        waves[k].append(n)

    return {
        "requires": dict(req),
        "wave": wave,
        "waves": [sorted(waves[k]) for k in sorted(waves)],
        "max_parallel": max_parallel,
        "delegates_to": by(DELEGATE),
        "reports_to": by(REPORTS)
    }


def next_ready(
    p: Dict[str, Any],
    status: Dict[str, str],
    running_limit: Optional[int] = None
) -> List[str]:
    """Agents whose prerequisites are all BUILT/CERTIFIED and that are still PENDING."""
    done = {"BUILT", "UNIT_TESTED", "QA_PASSED", "CERTIFIED", "SUCCEEDED"}
    limit = running_limit or p["max_parallel"]
    running = sum(1 for s in status.values() if s == "BUILDING")
    out = []
    for n, s in sorted(status.items(), key=lambda kv: p["wave"].get(kv[0], 0)):
        if s != "PENDING":
            continue
        if all(status.get(r) in done for r in p["requires"].get(n, [])):
            if running + len(out) < limit:
                out.append(n)
    return out


def propagate_failure(
    p: Dict[str, Any],
    status: Dict[str, str],
    failed: str
) -> Dict[str, str]:
    """A failed agent is FAILED; every transitive dependent becomes BLOCKED."""
    st = dict(status)
    st[failed] = "FAILED"
    changed = True
    while changed:
        changed = False
        for n, reqs in p["requires"].items():
            if st.get(n) in ("PENDING", "READY") and any(st.get(r) in ("FAILED", "BLOCKED", "SKIPPED") for r in reqs):
                st[n] = "BLOCKED"
                changed = True
    return st


def batch_verdict(status: Dict[str, str], release_policy: str = "atomic_team") -> str:
    """Evaluate batch terminal status according to release policy."""
    vals = set(status.values())
    if vals == {"CERTIFIED"} or vals == {"SUCCEEDED"}:
        return "TEAM_QA" if release_policy == "atomic_team" else "RELEASABLE"
    if release_policy == "atomic_team":
        if (vals & {"FAILED", "BLOCKED", "KILLED", "SKIPPED"}) and not (vals & {"BUILDING", "PENDING", "READY"}):
            return "FAILED"
        return "BUILDING"
    else:
        if ("CERTIFIED" in vals or "SUCCEEDED" in vals) and not (vals & {"BUILDING", "PENDING", "READY"}):
            return "PARTIAL"
        return "BUILDING"


def compile_team_manifest(
    team_name: str,
    batch_plan: Dict[str, Any],
    agent_specs: Dict[str, Dict[str, Any]],
    tenant_id: str,
    company_id: str
) -> Dict[str, Any]:
    """Generate team manifest connecting members with supervisor and delegation topologies."""
    supervisor_key = None
    # Identify supervisor as node with in-degree of reports_to
    reported_supervisors = {b for a, b in batch_plan.get("reports_to", [])}
    if len(reported_supervisors) == 1:
        supervisor_key = list(reported_supervisors)[0]

    members = []
    for agent_key, spec in agent_specs.items():
        members.append({
            "key": agent_key,
            "role": spec.get("role", {}).get("title", agent_key),
            "category": spec.get("metadata", {}).get("category", "custom"),
            "risk_tier": spec.get("metadata", {}).get("risk_tier", "R1"),
            "wave": batch_plan["wave"].get(agent_key, 0),
            "is_supervisor": (agent_key == supervisor_key)
        })

    team_manifest = {
        "apiVersion": "zonata.team/v1",
        "kind": "AgentTeam",
        "metadata": {
            "name": team_name,
            "tenant_id": tenant_id,
            "company_id": company_id
        },
        "topology": {
            "type": "hierarchical" if supervisor_key else "collaborative_mesh",
            "supervisor": supervisor_key,
            "waves": batch_plan["waves"],
            "delegation_graph": batch_plan["delegates_to"],
            "reporting_tree": batch_plan["reports_to"]
        },
        "members": members
    }
    return team_manifest
