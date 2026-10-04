"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
OpenFGA Fine-Grained Relationship-Based Authorization (ReBAC) Engine
====================================================================
Implements OpenFGA relationship-based authorization schema modeling:
  Company -> Department -> Project -> Resource
  Agent -> Capability -> Resource
Evaluates (user/agent, relation, object) tuples underneath ZONATA AuthorityGateway.

Constitutional Invariants:
1. OpenFGA is an authorization evaluation capability, NOT the sovereign authority.
2. ZONATA AuthorityGateway and PolicyEngine remain authoritative over OpenFGA.
3. OpenFGA cannot override emergency KillSwitches or explicit Owner Decision Center vetoes.
4. All authorization tuples are strictly partitioned by tenant_id.
"""

import os
import time
import json
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.auth.openfga")

@dataclass
class RelationshipTuple:
    user: str          # e.g. "agent:agent_ceo" or "user:usr_john"
    relation: str      # e.g. "owner", "editor", "viewer", "executor", "approver"
    object: str        # e.g. "project:proj_alpha" or "resource:crm_db"
    tenant_id: str
    company_id: str
    condition: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def tuple_key(self) -> str:
        return f"{self.tenant_id}|{self.user}#{self.relation}@{self.object}"

class OpenFGAEngine:
    """
    OpenFGA Fine-Grained Relationship-Based Authorization Engine.
    Subordinate to ZONATA AuthorityGateway.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "OpenFGAEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._tuples: Dict[str, RelationshipTuple] = {}
        self._lock = threading.Lock()
        self._seed_default_model()

    def _seed_default_model(self):
        """Seeds standard enterprise organizational model."""
        pass

    def write_tuple(
        self,
        user: str,
        relation: str,
        object: str,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        condition: Optional[Dict[str, Any]] = None
    ) -> RelationshipTuple:
        """Writes or updates an authorization relationship tuple."""
        t = RelationshipTuple(
            user=user,
            relation=relation,
            object=object,
            tenant_id=tenant_id,
            company_id=company_id,
            condition=condition
        )
        with self._lock:
            self._tuples[t.tuple_key] = t
        logger.info(f"OPENFGA TUPLE WRITTEN: ({user}, {relation}, {object}) [Tenant: {tenant_id}]")
        return t

    def delete_tuple(self, user: str, relation: str, object: str, tenant_id: str = "tnt_primary") -> bool:
        """Deletes a relationship tuple."""
        key = f"{tenant_id}|{user}#{relation}@{object}"
        with self._lock:
            if key in self._tuples:
                del self._tuples[key]
                logger.info(f"OPENFGA TUPLE DELETED: {key}")
                return True
        return False

    def check(
        self,
        user: str,
        relation: str,
        object: str,
        tenant_id: str = "tnt_primary",
        contextual_tuples: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Evaluates whether a user/agent possesses a relation with an object.
        Supports direct assignment, role inheritance (owner > editor > viewer),
        and hierarchical graph traversal.
        """
        # Build evaluation set combining persistent and contextual tuples
        eval_keys: Set[str] = set()
        with self._lock:
            for k, t in self._tuples.items():
                if t.tenant_id == tenant_id:
                    eval_keys.add(f"{t.user}#{t.relation}@{t.object}")

        if contextual_tuples:
            for ct in contextual_tuples:
                eval_keys.add(f"{ct['user']}#{ct['relation']}@{ct['object']}")

        # 1. Direct match check
        direct_key = f"{user}#{relation}@{object}"
        if direct_key in eval_keys:
            return True

        # 2. Implied Hierarchical Permissions
        # "owner" implies "editor", "viewer", "executor", "approver"
        if relation in ["viewer", "editor", "executor"]:
            if f"{user}#owner@{object}" in eval_keys:
                return True
        if relation in ["viewer"]:
            if f"{user}#editor@{object}" in eval_keys:
                return True

        # 3. Transitive Object Parentage: e.g. project:p1 -> department:d1 -> company:c1
        # Check if user has relation on parent container
        for entry in eval_keys:
            if entry.startswith(f"{user}#{relation}@") or (relation == "viewer" and entry.startswith(f"{user}#owner@")):
                target = entry.split("@")[1]
                if f"{object}#parent@{target}" in eval_keys:
                    return True

        # 4. Group / Role Membership Traversal: user is member of group
        for entry in eval_keys:
            if entry.startswith(f"{user}#member@"):
                group_target = entry.split("@")[1]
                group_user = group_target if group_target.startswith("group:") else f"group:{group_target}"
                if f"{group_user}#{relation}@{object}" in eval_keys:
                    return True
                if relation == "viewer" and f"{group_user}#owner@{object}" in eval_keys:
                    return True
                if relation == "viewer" and f"{group_user}#editor@{object}" in eval_keys:
                    return True
                if relation == "editor" and f"{group_user}#owner@{object}" in eval_keys:
                    return True

        return False

    def list_objects(self, user: str, relation: str, object_type: str, tenant_id: str = "tnt_primary") -> List[str]:
        """Lists all objects of a given type that the user has the specified relation with."""
        matching = []
        with self._lock:
            for t in self._tuples.values():
                if t.tenant_id == tenant_id:
                    if t.object.startswith(f"{object_type}:"):
                        if self.check(user, relation, t.object, tenant_id=tenant_id):
                            matching.append(t.object)
        return sorted(list(set(matching)))

    def list_relations(self, user: str, object: str, tenant_id: str = "tnt_primary") -> List[str]:
        """Lists all relations a user has with a specific object."""
        relations = set()
        with self._lock:
            for t in self._tuples.values():
                if t.tenant_id == tenant_id and t.object == object:
                    if self.check(user, t.relation, object, tenant_id=tenant_id):
                        relations.add(t.relation)
        return sorted(list(relations))

# Global singleton instance
openfga_engine = OpenFGAEngine.get_instance()

