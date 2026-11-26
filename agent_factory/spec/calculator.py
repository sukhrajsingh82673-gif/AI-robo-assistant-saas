"""ZONATA Agent Factory - Deterministic Permission Profile Calculator.

Implements compute_permission_profile() according to TEMPLATE_AND_CAPABILITY_SYSTEM.md §5.1.
Guarantees:
- Result ⊆ every input
- Idempotent
- Monotone
- Drops unknown tools and unregistered servers
- Only writer of permission_profile
"""

import copy
from typing import Any, Dict, List, Optional, Set, Tuple


DATA_CLASSIFICATION_ORDER = {
    "public": 1,
    "internal": 2,
    "confidential": 3,
    "restricted": 4
}

TIER_ORDER = {
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3
}


class PermissionProfile:
    def __init__(
        self,
        granted_tools: List[Dict[str, Any]],
        network_allowed_hosts: List[str],
        can_external_network: bool,
        can_write: bool,
        data_classification_max: str,
        risk_tier: str,
        reduction_notes: List[str],
        needs_approval: List[str]
    ):
        self.granted_tools = granted_tools
        self.network_allowed_hosts = network_allowed_hosts
        self.can_external_network = can_external_network
        self.can_write = can_write
        self.data_classification_max = data_classification_max
        self.risk_tier = risk_tier
        self.reduction_notes = reduction_notes
        self.needs_approval = needs_approval

    def to_dict(self) -> Dict[str, Any]:
        return {
            "granted_tools": self.granted_tools,
            "network": {
                "external": self.can_external_network,
                "allowed_hosts": self.network_allowed_hosts,
            },
            "writes": self.can_write,
            "data_classification_max": self.data_classification_max,
            "risk_tier": self.risk_tier,
            "reduction_notes": self.reduction_notes,
            "needs_approval": self.needs_approval,
        }

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PermissionProfile):
            return False
        return self.to_dict() == other.to_dict()


def _intersect_tools(
    tools_a: List[Dict[str, Any]],
    tools_b: Optional[List[Dict[str, Any]]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Intersect two tool lists on name, intersecting scopes and taking min(max_calls)."""
    if tools_b is None:
        return [copy.deepcopy(t) for t in tools_a], []

    b_map = {t["name"]: t for t in tools_b}
    res: List[Dict[str, Any]] = []
    notes: List[str] = []

    for ta in tools_a:
        name = ta["name"]
        if name not in b_map:
            notes.append(f"Tool '{name}' removed by authority boundary")
            continue
        tb = b_map[name]
        # Intersect scopes
        scopes_a = set(ta.get("scopes", ["read"]))
        scopes_b = set(tb.get("scopes", ["read"]))
        common_scopes = sorted(list(scopes_a.intersection(scopes_b)))
        if not common_scopes:
            notes.append(f"Tool '{name}' removed because scopes had no overlap ({scopes_a} vs {scopes_b})")
            continue

        calls_a = ta.get("max_calls", 100)
        calls_b = tb.get("max_calls", 100)
        min_calls = min(calls_a, calls_b)

        res.append({
            "name": name,
            "scopes": common_scopes,
            "max_calls": min_calls
        })

    return res, notes


def _intersect_hosts(hosts_a: List[str], hosts_b: Optional[List[str]]) -> List[str]:
    if hosts_b is None:
        return list(hosts_a)
    set_b = set(hosts_b)
    # Check exact match or domain wildcards
    res = []
    for ha in hosts_a:
        if ha in set_b or "*" in set_b:
            res.append(ha)
    return sorted(list(set(res)))


def compute_permission_profile(
    requested_permissions: Dict[str, Any],
    template_max_grantable: Optional[Dict[str, Any]] = None,
    requester_delegable: Optional[Dict[str, Any]] = None,
    tenant_policy: Optional[Dict[str, Any]] = None,
    ceo_policy: Optional[Dict[str, Any]] = None,
    constitution: Optional[Dict[str, Any]] = None,
    registry: Optional[Set[str]] = None,
    requested_capabilities: Optional[List[Dict[str, Any]]] = None
) -> PermissionProfile:
    """Deterministically compute effective permission profile through intersections."""
    notes: List[str] = []

    # 1. Starting tools from request
    raw_tools = requested_permissions.get("tools", [])
    if isinstance(raw_tools, list):
        current_tools = [copy.deepcopy(t) for t in raw_tools if isinstance(t, dict) and "name" in t]
    else:
        current_tools = []

    # 2. Intersect with template ceiling
    if template_max_grantable:
        t_tools = template_max_grantable.get("tools")
        current_tools, n = _intersect_tools(current_tools, t_tools)
        notes.extend(n)

    # 3. Intersect with requester delegable authority
    if requester_delegable:
        r_tools = requester_delegable.get("tools")
        current_tools, n = _intersect_tools(current_tools, r_tools)
        notes.extend(n)

    # 4. Intersect with tenant policy
    if tenant_policy:
        tp_tools = tenant_policy.get("allowed_tools")
        if tp_tools is not None:
            # can be list of names or tool dicts
            if tp_tools and isinstance(tp_tools[0], str):
                tp_tool_objs = [{"name": n, "scopes": ["read", "write", "execute"], "max_calls": 9999} for n in tp_tools]
            else:
                tp_tool_objs = tp_tools
            current_tools, n = _intersect_tools(current_tools, tp_tool_objs)
            notes.extend(n)

    # 5. Intersect with CEO policy (autonomy mode tightening)
    if ceo_policy:
        ceo_tools = ceo_policy.get("allowed_tools")
        if ceo_tools is not None:
            if ceo_tools and isinstance(ceo_tools[0], str):
                ceo_tool_objs = [{"name": n, "scopes": ["read", "write", "execute"], "max_calls": 9999} for n in ceo_tools]
            else:
                ceo_tool_objs = ceo_tools
            current_tools, n = _intersect_tools(current_tools, ceo_tool_objs)
            notes.extend(n)

    # 6. Intersect with Constitution (non-negotiable denials: e.g. direct prod DB, employee use)
    denied_tools = set()
    if constitution:
        denied_tools = set(constitution.get("forbidden_tools", []))
    filtered_tools = []
    for t in current_tools:
        if t["name"] in denied_tools or t["name"].startswith("internal.employee_"):
            notes.append(f"Tool '{t['name']}' rejected by ZONATA Constitution")
        else:
            filtered_tools.append(t)
    current_tools = filtered_tools

    # 7. Drop unregistered tools
    if registry is not None:
        valid_tools = []
        for t in current_tools:
            if t["name"] in registry:
                valid_tools.append(t)
            else:
                notes.append(f"Tool '{t['name']}' dropped: not found in capability registry")
        current_tools = valid_tools

    # Sort tools deterministically by name
    current_tools = sorted(current_tools, key=lambda x: x["name"])

    # 8. Network permissions intersection
    req_net = requested_permissions.get("network", {})
    can_external = bool(req_net.get("external", False))
    req_hosts = req_net.get("allowed_hosts", [])

    if template_max_grantable and not template_max_grantable.get("network", {}).get("external", True):
        can_external = False
        notes.append("External network access disabled by template ceiling")

    if requester_delegable and not requester_delegable.get("network", {}).get("external", True):
        can_external = False
        notes.append("External network access disabled: requester lacks network authority")

    if tenant_policy and not tenant_policy.get("network_allowed", True):
        can_external = False
        notes.append("External network access disabled by tenant policy")

    if ceo_policy and not ceo_policy.get("network_allowed", True):
        can_external = False
        notes.append("External network access disabled by CEO policy")

    if constitution and not constitution.get("network_allowed", True):
        can_external = False

    hosts = req_hosts
    if template_max_grantable and "allowed_hosts" in template_max_grantable.get("network", {}):
        hosts = _intersect_hosts(hosts, template_max_grantable["network"]["allowed_hosts"])
    if tenant_policy and "allowed_hosts" in tenant_policy:
        hosts = _intersect_hosts(hosts, tenant_policy["allowed_hosts"])

    # 9. Writes permission intersection
    req_writes = bool(requested_permissions.get("writes", False))
    can_write = req_writes
    if template_max_grantable and not template_max_grantable.get("writes", True):
        can_write = False
        notes.append("Write permission removed by template ceiling")
    if requester_delegable and not requester_delegable.get("writes", True):
        can_write = False
        notes.append("Write permission removed: requester lacks write authority")
    if tenant_policy and not tenant_policy.get("writes_allowed", True):
        can_write = False
    if ceo_policy and not ceo_policy.get("writes_allowed", True):
        can_write = False
    if constitution and not constitution.get("writes_allowed", True):
        can_write = False

    # 10. Data Classification Ceiling
    d_class = requested_permissions.get("data_classification_max", "internal")
    candidates = [d_class]
    if template_max_grantable and "data_classification_max" in template_max_grantable:
        candidates.append(template_max_grantable["data_classification_max"])
    if tenant_policy and "data_classification_max" in tenant_policy:
        candidates.append(tenant_policy["data_classification_max"])
    if requester_delegable and "data_classification_max" in requester_delegable:
        candidates.append(requester_delegable["data_classification_max"])

    min_class_level = min(DATA_CLASSIFICATION_ORDER.get(c, 2) for c in candidates)
    effective_class = [k for k, v in DATA_CLASSIFICATION_ORDER.items() if v == min_class_level][0]

    # 11. Determine Risk Tier and Approval Requirements
    tier_candidates = ["R0"]
    if can_write:
        tier_candidates.append("R1")
    if can_external:
        tier_candidates.append("R1")
    if effective_class in ("confidential", "restricted"):
        tier_candidates.append("R2")
    if any(t["name"].startswith("code.") or t["name"].startswith("db.") for t in current_tools):
        tier_candidates.append("R2")
    if any(t["name"].startswith("payment.") or t["name"].startswith("admin.") for t in current_tools):
        tier_candidates.append("R3")

    max_tier_num = max(TIER_ORDER[t] for t in tier_candidates)
    effective_risk_tier = [k for k, v in TIER_ORDER.items() if v == max_tier_num][0]

    # Tenant auto-grant ceiling
    auto_grant_max = "R1"
    if tenant_policy and "auto_grant_tier" in tenant_policy:
        auto_grant_max = tenant_policy["auto_grant_tier"]

    needs_approval: List[str] = []
    if TIER_ORDER[effective_risk_tier] > TIER_ORDER.get(auto_grant_max, 1):
        needs_approval.append(f"Risk tier {effective_risk_tier} exceeds tenant auto-grant ceiling ({auto_grant_max})")

    return PermissionProfile(
        granted_tools=current_tools,
        network_allowed_hosts=hosts,
        can_external_network=can_external,
        can_write=can_write,
        data_classification_max=effective_class,
        risk_tier=effective_risk_tier,
        reduction_notes=notes,
        needs_approval=needs_approval
    )
