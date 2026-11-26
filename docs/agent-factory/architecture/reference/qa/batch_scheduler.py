"""Reference batch planner: DAG validation, wave assignment, ready-set scheduling, partial-failure propagation.

Edge kinds:
  build_requires        A -> B : B cannot START building until A is BUILT   (orders the build)
  runtime_delegates_to  A -> B : A may delegate to B at runtime            (must be acyclic; checked, not used for ordering)
  reports_to            A -> B : A reports to B                            (must form a forest)
OpenCode: lift into agent_factory/batch/planner.py. Run tests:  python3 -I batch_scheduler.py --selftest
"""
from __future__ import annotations
import sys
from collections import defaultdict, deque

BUILD, DELEGATE, REPORTS = "build_requires", "runtime_delegates_to", "reports_to"


class PlanError(ValueError):
    pass


def _cycle(nodes, edges):
    adj, indeg = defaultdict(list), {n: 0 for n in nodes}
    for a, b in edges:
        adj[a].append(b); indeg[b] += 1
    q, seen = deque(n for n, d in indeg.items() if d == 0), 0
    while q:
        n = q.popleft(); seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    return seen != len(nodes)


def plan(nodes: list[str], edges: list[tuple[str, str, str]], max_parallel: int = 4, max_agents: int = 500) -> dict:
    if len(nodes) != len(set(nodes)):
        raise PlanError("duplicate agent_key")
    if not 1 <= len(nodes) <= max_agents:
        raise PlanError("agent count out of range")
    for a, b, k in edges:
        if a not in nodes or b not in nodes:
            raise PlanError(f"edge references unknown node: {a}->{b}")
        if k not in (BUILD, DELEGATE, REPORTS):
            raise PlanError(f"unknown edge kind {k}")
        if a == b:
            raise PlanError("self edge")
    by = lambda kind: [(a, b) for a, b, k in edges if k == kind]
    if _cycle(nodes, by(BUILD)):
        raise PlanError("cycle in build_requires")
    if _cycle(nodes, by(DELEGATE)):
        raise PlanError("cycle in runtime_delegates_to (delegation loops are forbidden)")
    parents = defaultdict(list)
    for a, b in by(REPORTS):
        parents[a].append(b)
    if any(len(v) > 1 for v in parents.values()):
        raise PlanError("an agent may report to exactly one supervisor")
    if _cycle(nodes, by(REPORTS)):
        raise PlanError("cycle in reports_to")
    # wave = longest build_requires path from a root
    req = defaultdict(list)
    for a, b in by(BUILD):
        req[b].append(a)
    wave: dict[str, int] = {}
    def w(n):
        if n not in wave:
            wave[n] = 0 if not req[n] else 1 + max(w(p) for p in req[n])
        return wave[n]
    for n in nodes:
        w(n)
    waves = defaultdict(list)
    for n, k in wave.items():
        waves[k].append(n)
    return dict(requires=dict(req), wave=wave, waves=[sorted(waves[k]) for k in sorted(waves)], max_parallel=max_parallel)


def next_ready(p: dict, status: dict[str, str], running_limit: int | None = None) -> list[str]:
    """Agents whose build_requires are all BUILT (or later) and that are still PENDING. Respects parallelism."""
    done = {"BUILT", "UNIT_TESTED", "QA_PASSED", "CERTIFIED"}
    limit = running_limit or p["max_parallel"]
    running = sum(1 for s in status.values() if s == "BUILDING")
    out = []
    for n, s in sorted(status.items(), key=lambda kv: p["wave"][kv[0]]):
        if s != "PENDING":
            continue
        if all(status[r] in done for r in p["requires"].get(n, [])):
            if running + len(out) < limit:
                out.append(n)
    return out


def propagate_failure(p: dict, status: dict[str, str], failed: str) -> dict[str, str]:
    """A failed agent is FAILED; every transitive dependent becomes BLOCKED. Nothing is ever silently CERTIFIED."""
    st = dict(status); st[failed] = "FAILED"
    changed = True
    while changed:
        changed = False
        for n, reqs in p["requires"].items():
            if st[n] in ("PENDING", "READY") and any(st[r] in ("FAILED", "BLOCKED", "SKIPPED") for r in reqs):
                st[n] = "BLOCKED"; changed = True
    return st


def batch_verdict(status: dict[str, str], release_policy: str) -> str:
    vals = set(status.values())
    if vals == {"CERTIFIED"}:
        return "TEAM_QA" if release_policy == "atomic_team" else "RELEASABLE"
    if release_policy == "atomic_team":
        return "FAILED" if vals & {"FAILED", "BLOCKED", "KILLED", "SKIPPED"} and not vals & {"BUILDING", "PENDING", "READY"} else "BUILDING"
    return "PARTIAL" if "CERTIFIED" in vals and not vals & {"BUILDING", "PENDING", "READY"} else "BUILDING"


# --------------------------------- self tests --------------------------------
def _selftest():
    N = ["supervisor", "market_research", "competitor", "customer_intel", "trend", "campaign", "reporting"]
    E = [("market_research", "campaign", BUILD), ("competitor", "campaign", BUILD), ("customer_intel", "campaign", BUILD), ("trend", "campaign", BUILD),
         ("campaign", "supervisor", BUILD), ("reporting", "supervisor", BUILD), ("market_research", "reporting", BUILD),
         ("supervisor", "market_research", DELEGATE), ("supervisor", "competitor", DELEGATE), ("supervisor", "customer_intel", DELEGATE),
         ("supervisor", "trend", DELEGATE), ("supervisor", "campaign", DELEGATE), ("supervisor", "reporting", DELEGATE)] + \
        [(n, "supervisor", REPORTS) for n in N if n != "supervisor"]
    res = []
    t = lambda name, ok: res.append((name, bool(ok)))
    p = plan(N, E)
    t("7-agent marketing team plans into 3 waves", len(p["waves"]) == 3)
    t("independent specialists share wave 0 (build concurrently)", {"competitor", "customer_intel", "trend", "market_research"} <= set(p["waves"][0]))
    t("supervisor is last", p["wave"]["supervisor"] == 2 or p["wave"]["supervisor"] == max(p["wave"].values()))
    st = {n: "PENDING" for n in N}
    t("ready set honours max_parallel=4", len(next_ready(p, st)) == 4)
    st.update({n: "CERTIFIED" for n in ["market_research", "competitor", "customer_intel", "trend"]})
    t("campaign becomes ready after its 4 prerequisites", "campaign" in next_ready(p, st))
    st2 = propagate_failure(p, {n: "PENDING" for n in N}, "competitor")
    t("failed agent blocks transitive dependents", st2["campaign"] == "BLOCKED" and st2["supervisor"] == "BLOCKED")
    t("independent siblings are NOT blocked", st2["trend"] == "PENDING")
    t("failed agent never becomes certified (atomic_team => FAILED once settled)", batch_verdict({**st2, "trend": "CERTIFIED", "market_research": "CERTIFIED", "customer_intel": "CERTIFIED", "reporting": "BLOCKED"}, "atomic_team") == "FAILED")
    t("independent policy reports PARTIAL, not success", batch_verdict({"a": "CERTIFIED", "b": "FAILED"}, "independent") == "PARTIAL")
    t("all certified + atomic => proceeds to TEAM_QA", batch_verdict({"a": "CERTIFIED", "b": "CERTIFIED"}, "atomic_team") == "TEAM_QA")
    for name, edges in [("build cycle", [("a", "b", BUILD), ("b", "a", BUILD)]), ("delegation loop", [("a", "b", DELEGATE), ("b", "a", DELEGATE)]),
                        ("two supervisors", [("a", "b", REPORTS), ("a", "c", REPORTS)]), ("unknown node", [("a", "zzz", BUILD)])]:
        try:
            plan(["a", "b", "c"], edges); t(name + " rejected", False)
        except PlanError:
            t(name + " rejected", True)
    big = [f"a{i}" for i in range(300)]
    t("300-agent fleet plans in a single wave", len(plan(big, [])["waves"]) == 1)
    bad = 0
    for n, ok in res:
        print(("PASS " if ok else "FAIL ") + n); bad += (not ok)
    print(f"{len(res) - bad}/{len(res)} passed"); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    print(__doc__)
