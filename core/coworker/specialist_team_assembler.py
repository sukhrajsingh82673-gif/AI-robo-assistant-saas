"""
ZONATA Autonomous Executive Coworker — Milestone 5: Specialist Team Assembler
Dynamically composes specialized subagent swarms from the 12 specialist archetypes
with scoped permissions, resource leasing, and independent review.
"""

from __future__ import annotations
import uuid
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .archetype_contracts import SpecialistRole, ARCHETYPE_CONTRACTS, SpecialistArchetypeContract


@dataclass
class AssembledTeamMember:
    member_id: str
    role: SpecialistRole
    contract: SpecialistArchetypeContract
    lease_id: str
    lease_expires_at: float
    allocated_ram_mb: int
    scoped_permissions: List[str]
    assigned_at: float = field(default_factory=time.time)


@dataclass
class AssembledTeam:
    team_id: str
    mission_objective: str
    members: List[AssembledTeamMember]
    created_at: float = field(default_factory=time.time)


class SpecialistTeamAssembler:
    """Assembles dynamic teams across the 12 specialist archetypes for complex missions."""

    def assemble_team(
        self,
        mission_objective: str,
        required_roles: Optional[List[SpecialistRole]] = None,
        parent_scope: Optional[List[str]] = None,
        lease_duration_sec: float = 600.0
    ) -> AssembledTeam:
        """
        Assembles a team with subordinate leases and scoped permissions.
        """
        team_id = f"team_{uuid.uuid4().hex[:8]}"
        roles = required_roles or self._infer_roles(mission_objective)
        now = time.time()
        effective_parent_scope = parent_scope or ["read_only", "execute"]

        members = []
        for role in roles:
            contract = ARCHETYPE_CONTRACTS.get(role)
            if contract:
                # Scoped permissions: subset of parent scope intersecting with role capabilities
                scoped = [c for c in contract.allowed_capabilities if c in effective_parent_scope or "all" in effective_parent_scope]
                if not scoped:
                    scoped = ["read_only"]

                members.append(AssembledTeamMember(
                    member_id=f"mem_{role.name.lower()[:6]}_{uuid.uuid4().hex[:4]}",
                    role=role,
                    contract=contract,
                    lease_id=f"lease_{uuid.uuid4().hex[:8]}",
                    lease_expires_at=now + lease_duration_sec,
                    allocated_ram_mb=contract.quota_ram_mb,
                    scoped_permissions=scoped
                ))

        return AssembledTeam(team_id=team_id, mission_objective=mission_objective, members=members)

    def conduct_independent_review(
        self,
        team: AssembledTeam,
        deliverable_artifact: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Executes independent review checks against assembled team deliverables.
        """
        issues: List[str] = []
        if not deliverable_artifact:
            issues.append("Empty deliverable artifact submitted")

        # Verify whether QA or Security checked if present in team
        has_qa = any(m.role == SpecialistRole.QA_RELIABILITY_ENGINEER for m in team.members)
        if has_qa and not deliverable_artifact.get("tests_passed", False):
            issues.append("QA & Reliability review required tests to pass before release")

        has_sec = any(m.role == SpecialistRole.CYBERSECURITY_DEFENSE_AUDITOR for m in team.members)
        if has_sec and deliverable_artifact.get("security_issues", []):
            issues.append(f"Security audit detected open issues: {deliverable_artifact.get('security_issues')}")

        approved = len(issues) == 0
        return approved, issues

    def _infer_roles(self, objective: str) -> List[SpecialistRole]:
        obj_lower = objective.lower()
        roles = [SpecialistRole.EXECUTIVE_CHIEF_OF_STAFF]

        if any(w in obj_lower for w in ["code", "python", "bug", "refactor"]):
            roles.append(SpecialistRole.PYTHON_SOFTWARE_ENGINEER)
            roles.append(SpecialistRole.QA_RELIABILITY_ENGINEER)
        if any(w in obj_lower for w in ["security", "cve", "secret", "ast"]):
            roles.append(SpecialistRole.CYBERSECURITY_DEFENSE_AUDITOR)
        if any(w in obj_lower for w in ["data", "sql", "csv", "table"]):
            roles.append(SpecialistRole.DATA_ENGINEERING_SPECIALIST)
        if any(w in obj_lower for w in ["gui", "screen", "click", "desktop"]):
            roles.append(SpecialistRole.DESKTOP_GUI_OPERATOR)

        return list(dict.fromkeys(roles))
