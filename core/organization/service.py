"""
ZONATA Organization Model Service (OpenCode Step 2D)

Governs seats, positions, occupants (human vs AI), acyclic reporting hierarchies,
single-CEO invariance, empirical handover packs, and dynamic org chart computation.
"""

from __future__ import annotations
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from core.db import db, DatabaseDialect
from core.evidence_service import evidence_service
from core.organization.types import (
    OrgLevel,
    OccupantType,
    AssignmentStatus,
    HandoverStatus,
    OrganizationError,
    SingleCEOViolationError,
    ReportingCycleError,
    AgentHierarchyViolationError,
    AIOrganizationSelfEditError,
    VacantPositionError,
    PositionNotFoundError,
    DepartmentNotFoundError,
)
from core.organization.pack_roles import resolve_org_template_for_pack

logger = logging.getLogger("zonata.organization")


class OrganizationService:
    """Enterprise organizational model and hierarchy controller."""

    # -------------------------------------------------------------------------
    # Rule 15 Principal Separation Guard
    # -------------------------------------------------------------------------

    def _verify_human_or_governance_authority(self, caller_principal_type: Optional[str], action_desc: str) -> None:
        """Enforces Rule 15: AI employees and agents cannot modify org structure, positions, or reporting lines."""
        if caller_principal_type in ("AI_EMPLOYEE", "AGENT", "ai_employee", "agent"):
            raise AIOrganizationSelfEditError(
                f"Rule 15 Violation: Principal type '{caller_principal_type}' is prohibited from {action_desc}"
            )

    # -------------------------------------------------------------------------
    # 1. Department Management
    # -------------------------------------------------------------------------

    def create_department(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        code: str,
        lead_position_id: Optional[str] = None,
        budget_minor_units: int = 0,
        caller_principal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a functional department within a company."""
        self._verify_human_or_governance_authority(caller_principal_type, "creating departments")
        dept_id = f"dept_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO departments (
                    department_id, company_id, tenant_id, name, code,
                    lead_position_id, budget_minor_units, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (dept_id, company_id, tenant_id, name, code.upper(), lead_position_id, budget_minor_units, now, now),
            )
            conn.commit()

        return {
            "department_id": dept_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "name": name,
            "code": code.upper(),
            "lead_position_id": lead_position_id,
            "budget_minor_units": budget_minor_units,
            "status": "ACTIVE",
            "created_at": now,
        }

    def get_department(self, tenant_id: str, company_id: str, department_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves department record by ID within tenant and company."""
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT department_id, tenant_id, company_id, name, code, lead_position_id, budget_minor_units, status, created_at
                FROM departments
                WHERE tenant_id = ? AND company_id = ? AND department_id = ?
                """,
                (tenant_id, company_id, department_id),
            )
            row = c.fetchone()
            if not row:
                return None
            return {
                "department_id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "name": row[3],
                "code": row[4],
                "lead_position_id": row[5],
                "budget_minor_units": row[6],
                "status": row[7],
                "created_at": row[8],
            }

    def list_departments(self, tenant_id: str, company_id: str) -> List[Dict[str, Any]]:
        """Lists all departments for a company."""
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT department_id, tenant_id, company_id, name, code, lead_position_id, budget_minor_units, status, created_at
                FROM departments
                WHERE tenant_id = ? AND company_id = ?
                ORDER BY name ASC
                """,
                (tenant_id, company_id),
            )
            return [
                {
                    "department_id": r[0],
                    "tenant_id": r[1],
                    "company_id": r[2],
                    "name": r[3],
                    "code": r[4],
                    "lead_position_id": r[5],
                    "budget_minor_units": r[6],
                    "status": r[7],
                    "created_at": r[8],
                }
                for r in c.fetchall()
            ]

    # -------------------------------------------------------------------------
    # 2. Position Management (Seats separate from occupants)
    # -------------------------------------------------------------------------

    def create_position(
        self,
        tenant_id: str,
        company_id: str,
        title: str,
        level: OrgLevel | str,
        department_id: Optional[str] = None,
        job_description_doc_id: Optional[str] = None,
        authority_profile_id: Optional[str] = None,
        kra_kpi_set: Optional[List[str]] = None,
        sop_set: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
        spend_limit_minor_units: int = 0,
        caller_principal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new organizational seat. Enforces exactly one CEO per company and Rule 15."""
        self._verify_human_or_governance_authority(caller_principal_type, "creating positions")

        level_val = level.value if isinstance(level, OrgLevel) else str(level).upper()
        clean_title = title.strip()
        is_ceo = level_val == OrgLevel.CEO.value or clean_title.upper() in (
            "CEO", "CHIEF EXECUTIVE OFFICER", "EXECUTIVE_CEO", "MANAGING DIRECTOR", "MEDICAL DIRECTOR & PRACTICE PRINCIPAL"
        )

        with db.get_connection() as conn:
            c = conn.cursor()

            # Rule: Exactly one CEO position per company
            if is_ceo:
                c.execute(
                    """
                    SELECT position_id, title FROM positions
                    WHERE tenant_id = ? AND company_id = ? AND (level = 'CEO' OR UPPER(title) LIKE '%CHIEF EXECUTIVE OFFICER%') AND is_active = 1
                    """,
                    (tenant_id, company_id),
                )
                existing_ceo = c.fetchone()
                if existing_ceo:
                    raise SingleCEOViolationError(
                        f"Company '{company_id}' already has an active CEO position ('{existing_ceo[0]}': {existing_ceo[1]}). "
                        "A company cannot have more than one CEO."
                    )
                level_val = OrgLevel.CEO.value

            pos_id = f"pos_{uuid.uuid4().hex[:12]}"
            now = time.time()
            kra_json = json.dumps(kra_kpi_set or [])
            sop_json = json.dumps(sop_set or [])
            tools_json = json.dumps(allowed_tools or [])

            c.execute(
                """
                INSERT INTO positions (
                    position_id, tenant_id, company_id, department_id, title, level,
                    job_description_doc_id, authority_profile_id, kra_kpi_set, sop_set,
                    allowed_tools, spend_limit_minor_units, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    pos_id, tenant_id, company_id, department_id, clean_title, level_val,
                    job_description_doc_id, authority_profile_id, kra_json, sop_json,
                    tools_json, spend_limit_minor_units, now, now
                ),
            )
            conn.commit()

        return {
            "position_id": pos_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "department_id": department_id,
            "title": clean_title,
            "level": level_val,
            "job_description_doc_id": job_description_doc_id,
            "authority_profile_id": authority_profile_id,
            "kra_kpi_set": kra_kpi_set or [],
            "sop_set": sop_set or [],
            "allowed_tools": allowed_tools or [],
            "spend_limit_minor_units": spend_limit_minor_units,
            "is_active": True,
            "created_at": now,
        }

    def update_position(
        self,
        tenant_id: str,
        company_id: str,
        position_id: str,
        title: Optional[str] = None,
        level: Optional[OrgLevel | str] = None,
        department_id: Optional[str] = None,
        authority_profile_id: Optional[str] = None,
        spend_limit_minor_units: Optional[int] = None,
        is_active: Optional[bool] = None,
        caller_principal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates position attributes. Refuses AI principal edits and enforces single CEO."""
        self._verify_human_or_governance_authority(caller_principal_type, "updating positions")
        now = time.time()

        with db.get_connection() as conn:
            c = conn.cursor()
            existing = self.get_position(tenant_id, company_id, position_id)
            if not existing:
                raise PositionNotFoundError(f"Position '{position_id}' not found in company '{company_id}'")

            # Check single CEO rule if elevating to CEO
            if level is not None:
                new_level = level.value if isinstance(level, OrgLevel) else str(level).upper()
                if new_level == OrgLevel.CEO.value and existing["level"] != OrgLevel.CEO.value:
                    c.execute(
                        """
                        SELECT position_id, title FROM positions
                        WHERE tenant_id = ? AND company_id = ? AND level = 'CEO' AND position_id != ? AND is_active = 1
                        """,
                        (tenant_id, company_id, position_id),
                    )
                    other_ceo = c.fetchone()
                    if other_ceo:
                        raise SingleCEOViolationError(
                            f"Cannot change position '{position_id}' to CEO: Company already has CEO '{other_ceo[0]}'"
                        )

            set_clauses: List[str] = ["updated_at = ?"]
            params: List[Any] = [now]

            if title is not None:
                set_clauses.append("title = ?")
                params.append(title.strip())
            if level is not None:
                set_clauses.append("level = ?")
                params.append(level.value if isinstance(level, OrgLevel) else str(level).upper())
            if department_id is not None:
                set_clauses.append("department_id = ?")
                params.append(department_id)
            if authority_profile_id is not None:
                set_clauses.append("authority_profile_id = ?")
                params.append(authority_profile_id)
            if spend_limit_minor_units is not None:
                set_clauses.append("spend_limit_minor_units = ?")
                params.append(spend_limit_minor_units)
            if is_active is not None:
                set_clauses.append("is_active = ?")
                params.append(1 if is_active else 0)

            params.extend([tenant_id, company_id, position_id])
            query = f"UPDATE positions SET {', '.join(set_clauses)} WHERE tenant_id = ? AND company_id = ? AND position_id = ?"
            c.execute(query, tuple(params))
            conn.commit()

        return self.get_position(tenant_id, company_id, position_id)

    def get_position(self, tenant_id: str, company_id: str, position_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves position by ID."""
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT position_id, tenant_id, company_id, department_id, title, level,
                       job_description_doc_id, authority_profile_id, kra_kpi_set, sop_set,
                       allowed_tools, spend_limit_minor_units, is_active, created_at, updated_at
                FROM positions
                WHERE tenant_id = ? AND company_id = ? AND position_id = ?
                """,
                (tenant_id, company_id, position_id),
            )
            row = c.fetchone()
            if not row:
                return None
            return {
                "position_id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "department_id": row[3],
                "title": row[4],
                "level": row[5],
                "job_description_doc_id": row[6],
                "authority_profile_id": row[7],
                "kra_kpi_set": json.loads(row[8] or "[]"),
                "sop_set": json.loads(row[9] or "[]"),
                "allowed_tools": json.loads(row[10] or "[]"),
                "spend_limit_minor_units": row[11],
                "is_active": bool(row[12]),
                "created_at": row[13],
                "updated_at": row[14],
            }

    def list_positions(
        self,
        tenant_id: str,
        company_id: str,
        department_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Lists positions in a company."""
        with db.get_connection() as conn:
            c = conn.cursor()
            query = """
                SELECT position_id, tenant_id, company_id, department_id, title, level,
                       job_description_doc_id, authority_profile_id, kra_kpi_set, sop_set,
                       allowed_tools, spend_limit_minor_units, is_active, created_at, updated_at
                FROM positions
                WHERE tenant_id = ? AND company_id = ?
            """
            params: List[Any] = [tenant_id, company_id]
            if department_id:
                query += " AND department_id = ?"
                params.append(department_id)
            if active_only:
                query += " AND is_active = 1"
            query += " ORDER BY level ASC, title ASC"

            c.execute(query, tuple(params))
            return [
                {
                    "position_id": r[0],
                    "tenant_id": r[1],
                    "company_id": r[2],
                    "department_id": r[3],
                    "title": r[4],
                    "level": r[5],
                    "job_description_doc_id": r[6],
                    "authority_profile_id": r[7],
                    "kra_kpi_set": json.loads(r[8] or "[]"),
                    "sop_set": json.loads(r[9] or "[]"),
                    "allowed_tools": json.loads(r[10] or "[]"),
                    "spend_limit_minor_units": r[11],
                    "is_active": bool(r[12]),
                    "created_at": r[13],
                    "updated_at": r[14],
                }
                for r in c.fetchall()
            ]

    # -------------------------------------------------------------------------
    # 3. Position Assignments (Occupants: Human vs AI Employee)
    # -------------------------------------------------------------------------

    def assign_position(
        self,
        tenant_id: str,
        company_id: str,
        position_id: str,
        occupant_type: OccupantType | str,
        occupant_id: str,
        caller_principal_type: Optional[str] = None,
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Assigns an occupant (human or AI employee) to a seat. Refuses AI principal assignment."""
        self._verify_human_or_governance_authority(caller_principal_type, "assigning positions")

        pos = self.get_position(tenant_id, company_id, position_id)
        if not pos:
            raise PositionNotFoundError(f"Position '{position_id}' not found")

        occ_type_val = occupant_type.value if isinstance(occupant_type, OccupantType) else str(occupant_type).upper()
        now = time.time()
        start = start_date or time.strftime("%Y-%m-%d", time.gmtime(now))
        assignment_id = f"asgn_{uuid.uuid4().hex[:12]}"

        with db.get_connection() as conn:
            c = conn.cursor()

            # Supersede any existing active assignment for this position
            c.execute(
                """
                UPDATE position_assignments
                SET status = 'TERMINATED', end_date = ?, updated_at = ?
                WHERE tenant_id = ? AND company_id = ? AND position_id = ? AND status = 'ACTIVE'
                """,
                (start, now, tenant_id, company_id, position_id),
            )

            # Insert new active assignment
            c.execute(
                """
                INSERT INTO position_assignments (
                    assignment_id, tenant_id, company_id, position_id,
                    occupant_type, occupant_id, start_date, end_date,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (assignment_id, tenant_id, company_id, position_id, occ_type_val, occupant_id, start, now, now),
            )
            conn.commit()

        return {
            "assignment_id": assignment_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "position_id": position_id,
            "occupant_type": occ_type_val,
            "occupant_id": occupant_id,
            "start_date": start,
            "end_date": None,
            "status": "ACTIVE",
            "created_at": now,
        }

    def get_active_assignment(self, tenant_id: str, company_id: str, position_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the current active occupant assignment for a seat."""
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT assignment_id, tenant_id, company_id, position_id, occupant_type, occupant_id, start_date, status, created_at
                FROM position_assignments
                WHERE tenant_id = ? AND company_id = ? AND position_id = ? AND status = 'ACTIVE'
                ORDER BY created_at DESC LIMIT 1
                """,
                (tenant_id, company_id, position_id),
            )
            row = c.fetchone()
            if not row:
                return None
            return {
                "assignment_id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "position_id": row[3],
                "occupant_type": row[4],
                "occupant_id": row[5],
                "start_date": row[6],
                "status": row[7],
                "created_at": row[8],
            }

    def is_position_vacant(self, tenant_id: str, company_id: str, position_id: str) -> bool:
        """Returns True if the position seat has no active occupant."""
        return self.get_active_assignment(tenant_id, company_id, position_id) is None

    # -------------------------------------------------------------------------
    # 4. Reporting Lines & Acyclic Graph Enforcement
    # -------------------------------------------------------------------------

    def set_reporting_line(
        self,
        tenant_id: str,
        company_id: str,
        position_id: str,
        reports_to_position_id: str,
        caller_principal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sets a reporting line from subordinate to supervisor. Enforces strict acyclic graph invariance."""
        self._verify_human_or_governance_authority(caller_principal_type, "setting reporting lines")

        if position_id == reports_to_position_id:
            raise ReportingCycleError(f"Self-reporting cycle rejected: Position '{position_id}' cannot report to itself")

        # Verify both positions exist
        sub = self.get_position(tenant_id, company_id, position_id)
        if not sub:
            raise PositionNotFoundError(f"Subordinate position '{position_id}' not found")
        sup = self.get_position(tenant_id, company_id, reports_to_position_id)
        if not sup:
            raise PositionNotFoundError(f"Supervisor position '{reports_to_position_id}' not found")

        # Cycle detection: Starting from reports_to_position_id, walk up the hierarchy.
        # If we reach position_id, setting this line creates a directed cycle!
        visited: Set[str] = set()
        curr_pos: Optional[str] = reports_to_position_id

        while curr_pos:
            if curr_pos == position_id:
                raise ReportingCycleError(
                    f"Illegal reporting cycle detected: Position '{position_id}' reporting to '{reports_to_position_id}' "
                    f"creates an invalid cycle in the organizational hierarchy."
                )
            if curr_pos in visited:
                break
            visited.add(curr_pos)
            curr_pos = self.get_supervisor(tenant_id, company_id, curr_pos)

        now = time.time()
        line_id = f"line_{uuid.uuid4().hex[:12]}"

        with db.get_connection() as conn:
            c = conn.cursor()
            # Upsert into reporting_lines
            c.execute(
                """
                DELETE FROM reporting_lines
                WHERE tenant_id = ? AND company_id = ? AND position_id = ?
                """,
                (tenant_id, company_id, position_id),
            )
            c.execute(
                """
                INSERT INTO reporting_lines (
                    reporting_line_id, tenant_id, company_id, position_id,
                    reports_to_position_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (line_id, tenant_id, company_id, position_id, reports_to_position_id, now, now),
            )
            conn.commit()

        return {
            "reporting_line_id": line_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "position_id": position_id,
            "reports_to_position_id": reports_to_position_id,
            "created_at": now,
        }

    def get_supervisor(self, tenant_id: str, company_id: str, position_id: str) -> Optional[str]:
        """Returns the supervisor position ID for a given position."""
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT reports_to_position_id FROM reporting_lines
                WHERE tenant_id = ? AND company_id = ? AND position_id = ?
                """,
                (tenant_id, company_id, position_id),
            )
            row = c.fetchone()
            return row[0] if row else None

    def resolve_effective_assignee(
        self,
        tenant_id: str,
        company_id: str,
        position_id: str,
    ) -> Dict[str, Any]:
        """
        Resolves effective assignee for a position seat.
        Rule: A vacant seat is flagged and its work routes to its supervisor (and up the chain if vacant).
        """
        curr_pos: Optional[str] = position_id
        route_chain: List[str] = []
        is_routed = False

        while curr_pos:
            route_chain.append(curr_pos)
            active_assign = self.get_active_assignment(tenant_id, company_id, curr_pos)
            if active_assign:
                return {
                    "effective_position_id": curr_pos,
                    "target_position_id": position_id,
                    "occupant_type": active_assign["occupant_type"],
                    "occupant_id": active_assign["occupant_id"],
                    "is_routed": is_routed,
                    "is_vacant": False,
                    "route_chain": route_chain,
                }
            # Seat is vacant, climb to supervisor
            is_routed = True
            curr_pos = self.get_supervisor(tenant_id, company_id, curr_pos)

        # Reached root and all ancestor seats are vacant
        return {
            "effective_position_id": position_id,
            "target_position_id": position_id,
            "occupant_type": None,
            "occupant_id": None,
            "is_routed": True,
            "is_vacant": True,
            "route_chain": route_chain,
        }

    # -------------------------------------------------------------------------
    # 5. Org Chart Dynamic Query Computation
    # -------------------------------------------------------------------------

    def compute_org_chart(self, tenant_id: str, company_id: str) -> Dict[str, Any]:
        """
        Computes the organizational tree by SQL query at request time.
        Rule: Org chart is computed by query, never stored as text.
        """
        positions = self.list_positions(tenant_id, company_id, active_only=True)
        depts = {d["department_id"]: d for d in self.list_departments(tenant_id, company_id)}

        # Map supervisor lines
        supervisors: Dict[str, str] = {}
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT position_id, reports_to_position_id FROM reporting_lines
                WHERE tenant_id = ? AND company_id = ?
                """,
                (tenant_id, company_id),
            )
            for r in c.fetchall():
                supervisors[r[0]] = r[1]

        # Build node representations
        nodes: Dict[str, Dict[str, Any]] = {}
        for p in positions:
            pid = p["position_id"]
            assign = self.get_active_assignment(tenant_id, company_id, pid)
            dept = depts.get(p["department_id"]) if p["department_id"] else None

            nodes[pid] = {
                "position_id": pid,
                "title": p["title"],
                "level": p["level"],
                "department": dept["name"] if dept else None,
                "department_code": dept["code"] if dept else None,
                "authority_profile_id": p["authority_profile_id"],
                "spend_limit_minor_units": p["spend_limit_minor_units"],
                "is_vacant": assign is None,
                "occupant": {
                    "occupant_type": assign["occupant_type"],
                    "occupant_id": assign["occupant_id"],
                    "start_date": assign["start_date"],
                } if assign else None,
                "direct_reports": [],
            }

        # Wire parent-child relationships
        roots: List[Dict[str, Any]] = []
        for pid, node in nodes.items():
            sup_id = supervisors.get(pid)
            if sup_id and sup_id in nodes:
                nodes[sup_id]["direct_reports"].append(node)
            else:
                roots.append(node)

        return {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "total_positions": len(positions),
            "vacant_positions_count": sum(1 for n in nodes.values() if n["is_vacant"]),
            "hierarchy": roots,
            "generated_at": time.time(),
        }

    # -------------------------------------------------------------------------
    # 6. Empirical Handover Pack Generation
    # -------------------------------------------------------------------------

    def generate_handover_pack(
        self,
        tenant_id: str,
        company_id: str,
        position_id: str,
        previous_occupant_type: OccupantType | str,
        previous_occupant_id: str,
        successor_occupant_type: Optional[OccupantType | str] = None,
        successor_occupant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates an empirical handover pack from stored records when an AI employee is replaced or suspended.
        Rule: Handover pack contains exactly the open items from the database. No hidden memory is carried.
        """
        prev_type_val = previous_occupant_type.value if isinstance(previous_occupant_type, OccupantType) else str(previous_occupant_type)
        succ_type_val = successor_occupant_type.value if isinstance(successor_occupant_type, OccupantType) else (str(successor_occupant_type) if successor_occupant_type else None)

        now = time.time()
        pack_id = f"hop_{uuid.uuid4().hex[:12]}"

        with db.get_connection() as conn:
            c = conn.cursor()

            # 1. Open tasks query: retrieve uncompleted tasks assigned to previous occupant
            open_tasks: List[Dict[str, Any]] = []
            try:
                c.execute(
                    """
                    SELECT task_id, title, state, stage, created_at FROM mission_tasks
                    WHERE tenant_id = ? AND company_id = ? AND assigned_agent = ? AND state NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')
                    ORDER BY created_at ASC
                    """,
                    (tenant_id, company_id, previous_occupant_id),
                )
                for r in c.fetchall():
                    open_tasks.append({
                        "task_id": r[0],
                        "title": r[1],
                        "state": r[2],
                        "stage": r[3],
                        "created_at": r[4],
                    })
            except Exception:
                pass

            # 2. Pending approvals query: retrieve pending approvals involving previous occupant
            pending_approvals: List[Dict[str, Any]] = []
            try:
                c.execute(
                    """
                    SELECT approval_id, action_class, status, created_at FROM action_approvals
                    WHERE tenant_id = ? AND company_id = ? AND status = 'PENDING'
                      AND (requester_id = ? OR approver_id = ?)
                    ORDER BY created_at ASC
                    """,
                    (tenant_id, company_id, previous_occupant_id, previous_occupant_id),
                )
                for r in c.fetchall():
                    pending_approvals.append({
                        "approval_id": r[0],
                        "action_class": r[1],
                        "status": r[2],
                        "created_at": r[3],
                    })
            except Exception:
                pass

            # 3. Context documents query: relevant company documents
            context_docs: List[Dict[str, Any]] = []
            try:
                c.execute(
                    """
                    SELECT doc_id, title, doc_type, sensitivity, created_at FROM document_records
                    WHERE tenant_id = ? AND company_id = ?
                    ORDER BY created_at DESC LIMIT 5
                    """,
                    (tenant_id, company_id),
                )
                for r in c.fetchall():
                    context_docs.append({
                        "doc_id": r[0],
                        "title": r[1],
                        "doc_type": r[2],
                        "sensitivity": r[3],
                        "created_at": r[4],
                    })
            except Exception:
                pass

            # 4. Recent policy decisions query
            recent_decisions: List[Dict[str, Any]] = []
            try:
                c.execute(
                    """
                    SELECT decision_id, action_class, allowed, rule_id, created_at FROM policy_decisions
                    WHERE tenant_id = ? AND company_id = ? AND principal_id = ?
                    ORDER BY created_at DESC LIMIT 5
                    """,
                    (tenant_id, company_id, previous_occupant_id),
                )
                for r in c.fetchall():
                    recent_decisions.append({
                        "decision_id": r[0],
                        "action_class": r[1],
                        "allowed": bool(r[2]),
                        "rule_id": r[3],
                        "created_at": r[4],
                    })
            except Exception:
                pass

            # Seal evidence in Merkle evidence ledger
            evidence_id = None
            try:
                evidence_res = evidence_service.seal_evidence(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    event_type="HANDOVER_PACK_GENERATED",
                    payload={
                        "pack_id": pack_id,
                        "position_id": position_id,
                        "previous_occupant_id": previous_occupant_id,
                        "open_tasks_count": len(open_tasks),
                        "pending_approvals_count": len(pending_approvals),
                    },
                )
                evidence_id = evidence_res.get("evidence_id")
            except Exception:
                pass

            # Insert into handover_packs table
            c.execute(
                """
                INSERT INTO handover_packs (
                    pack_id, tenant_id, company_id, position_id,
                    previous_occupant_type, previous_occupant_id,
                    successor_occupant_type, successor_occupant_id,
                    open_tasks, context_documents, decisions, pending_approvals,
                    status, evidence_id, generated_at, acknowledged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'GENERATED', ?, ?, NULL)
                """,
                (
                    pack_id, tenant_id, company_id, position_id,
                    prev_type_val, previous_occupant_id,
                    succ_type_val, successor_occupant_id,
                    json.dumps(open_tasks), json.dumps(context_docs),
                    json.dumps(recent_decisions), json.dumps(pending_approvals),
                    evidence_id, now
                ),
            )
            conn.commit()

        return {
            "pack_id": pack_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "position_id": position_id,
            "previous_occupant_type": prev_type_val,
            "previous_occupant_id": previous_occupant_id,
            "successor_occupant_type": succ_type_val,
            "successor_occupant_id": successor_occupant_id,
            "open_tasks": open_tasks,
            "context_documents": context_docs,
            "decisions": recent_decisions,
            "pending_approvals": pending_approvals,
            "evidence_id": evidence_id,
            "status": "GENERATED",
            "generated_at": now,
        }

    # -------------------------------------------------------------------------
    # 7. Industry Pack Role Mapping Bootstrap
    # -------------------------------------------------------------------------

    def bootstrap_org_from_pack(
        self,
        tenant_id: str,
        company_id: str,
        pack_id: str,
        owner_user_id: str,
    ) -> Dict[str, Any]:
        """
        Initializes the company structure based on the installed industry pack.
        Rule: Two companies with different packs get different initial structures with identical code.
        """
        tpl = resolve_org_template_for_pack(pack_id)
        created_depts: Dict[str, str] = {}
        created_positions: Dict[str, str] = {}
        reporting_lines_created: List[Tuple[str, str]] = []

        # 1. Create departments
        for d in tpl["departments"]:
            dept_res = self.create_department(
                tenant_id=tenant_id,
                company_id=company_id,
                name=d["name"],
                code=d["code"],
                budget_minor_units=d.get("budget_minor_units", 0),
                caller_principal_type="HUMAN",
            )
            created_depts[d["code"]] = dept_res["department_id"]

        # 2. Create positions
        for p in tpl["positions"]:
            dept_id = created_depts.get(p["dept_code"])
            pos_res = self.create_position(
                tenant_id=tenant_id,
                company_id=company_id,
                title=p["title"],
                level=p["level"],
                department_id=dept_id,
                authority_profile_id=p.get("authority_grade"),
                kra_kpi_set=p.get("kra_kpi_set"),
                allowed_tools=p.get("allowed_tools"),
                spend_limit_minor_units=p.get("spend_limit_minor_units", 0),
                caller_principal_type="HUMAN",
            )
            created_positions[p["pos_key"]] = pos_res["position_id"]

        # 3. Wire reporting lines
        for p in tpl["positions"]:
            reports_to_key = p.get("reports_to_key")
            if reports_to_key and reports_to_key in created_positions:
                sub_id = created_positions[p["pos_key"]]
                sup_id = created_positions[reports_to_key]
                self.set_reporting_line(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    position_id=sub_id,
                    reports_to_position_id=sup_id,
                    caller_principal_type="HUMAN",
                )
                reporting_lines_created.append((sub_id, sup_id))

        return {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "pack_id": pack_id,
            "industry_name": tpl.get("industry_name"),
            "departments_created": len(created_depts),
            "positions_created": len(created_positions),
            "reporting_lines_created": len(reporting_lines_created),
            "created_positions_map": created_positions,
        }


# Global Singleton
organization_service = OrganizationService()
