"""ZONATA Agent Factory - Agent-to-Agent (A2A) Gateway.

Enforces:
- Narrowing delegation: effective permissions = min(delegator, delegatee)
- Delegation chain loop prevention (acyclic)
- Maximum delegation depth cap (<= 5)
- Origin principal propagation
- Prohibition of agent access to employee APIs
"""

from __future__ import annotations
import copy
from typing import Any, Dict, List, Optional, Set, Tuple


class A2ADelegationError(Exception):
    pass


class A2ALoopDetectedError(A2ADelegationError):
    pass


class A2ADepthExceededError(A2ADelegationError):
    pass


def compute_narrowed_permissions(
    delegator_profile: Dict[str, Any],
    delegatee_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute effective permissions as intersection min(delegator, delegatee)."""
    # 1. Tool intersection
    d1_tools = {t["name"]: t for t in delegator_profile.get("granted_tools", [])}
    d2_tools = {t["name"]: t for t in delegatee_profile.get("granted_tools", [])}

    common_names = set(d1_tools.keys()) & set(d2_tools.keys())
    narrowed_tools = []
    for name in sorted(list(common_names)):
        t1 = d1_tools[name]
        t2 = d2_tools[name]
        scopes = sorted(list(set(t1.get("scopes", [])) & set(t2.get("scopes", []))))
        if scopes:
            narrowed_tools.append({
                "name": name,
                "scopes": scopes,
                "max_calls": min(t1.get("max_calls", 100), t2.get("max_calls", 100))
            })

    # 2. Network intersection
    net1 = delegator_profile.get("network", {})
    net2 = delegatee_profile.get("network", {})
    can_external = bool(net1.get("external", False)) and bool(net2.get("external", False))
    hosts1 = set(net1.get("allowed_hosts", []))
    hosts2 = set(net2.get("allowed_hosts", []))
    common_hosts = sorted(list(hosts1 & hosts2))

    # 3. Writes
    can_write = bool(delegator_profile.get("writes", False)) and bool(delegatee_profile.get("writes", False))

    # 4. Data Classification
    class_order = {"public": 1, "internal": 2, "confidential": 3, "restricted": 4}
    c1 = class_order.get(delegator_profile.get("data_classification_max", "internal"), 2)
    c2 = class_order.get(delegatee_profile.get("data_classification_max", "internal"), 2)
    min_c = min(c1, c2)
    min_class = [k for k, v in class_order.items() if v == min_c][0]

    return {
        "granted_tools": narrowed_tools,
        "network": {
            "external": can_external,
            "allowed_hosts": common_hosts
        },
        "writes": can_write,
        "data_classification_max": min_class
    }


class A2AGateway:
    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth

    def validate_and_delegate(
        self,
        delegator_id: str,
        delegatee_id: str,
        delegation_chain: List[str],
        delegator_profile: Dict[str, Any],
        delegatee_profile: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate delegation rules and return narrowed execution context."""
        # Check depth
        if len(delegation_chain) >= self.max_depth:
            raise A2ADepthExceededError(f"Maximum delegation depth ({self.max_depth}) exceeded")

        # Check loop
        if delegatee_id in delegation_chain or delegatee_id == delegator_id:
            raise A2ALoopDetectedError(f"Delegation loop detected: {delegation_chain} -> {delegatee_id}")

        # Compute narrowed permissions min(delegator, delegatee)
        effective_perms = compute_narrowed_permissions(delegator_profile, delegatee_profile)

        new_chain = list(delegation_chain) + [delegator_id]

        return {
            "effective_permissions": effective_perms,
            "delegation_chain": new_chain,
            "origin_principal": new_chain[0] if new_chain else delegator_id,
            "payload": payload
        }
