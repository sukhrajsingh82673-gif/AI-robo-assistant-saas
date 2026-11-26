"""ZONATA Sovereign Core — Agent Factory Certification Gate.

Implements OpenCode Step 2E (Requirement 4):
- Every agent spec must reference its certification status: test records proving it
  completed qualification tasks in sandbox before deployment to a company.
- Uncertified agents cannot run above SHADOW (conservative by default, Rule 19).
"""

from __future__ import annotations
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from core.db import db
from core.authority.types import AutonomyLevel


class AgentCertificationStatus:
    CERTIFIED = "CERTIFIED"
    UNCERTIFIED = "UNCERTIFIED"
    REVOKED = "REVOKED"


class AgentCertificationService:
    """Manages agent certification status and qualification records."""

    def is_certified(
        self,
        agent_id: str,
        tenant_id: str,
        spec: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Checks whether an agent is certified to operate autonomously.

        Returns (is_certified, status, qualification_records).
        """
        # 1. Check database certification records
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT certification_status, test_records, certified_at
                    FROM agent_certifications
                    WHERE agent_id = ? AND tenant_id = ?
                    LIMIT 1
                    """,
                    (agent_id, tenant_id)
                )
                row = cur.fetchone()
                if row:
                    status = str(row[0]).upper()
                    records = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or [])
                    if status == AgentCertificationStatus.CERTIFIED:
                        return True, AgentCertificationStatus.CERTIFIED, records
                    return False, status, records
        except Exception:
            pass

        # 2. Check embedded qualification tests in declarative spec
        if spec:
            tests = spec.get("tests", {})
            author_cases = tests.get("author_cases", [])
            metadata = spec.get("metadata", {})
            cert_status = metadata.get("certification_status", AgentCertificationStatus.UNCERTIFIED)

            # Requires both author_cases and explicit certification stamp
            if cert_status == AgentCertificationStatus.CERTIFIED and len(author_cases) > 0:
                return True, AgentCertificationStatus.CERTIFIED, author_cases

        return False, AgentCertificationStatus.UNCERTIFIED, []

    def record_certification(
        self,
        agent_id: str,
        tenant_id: str,
        status: str,
        test_records: List[Dict[str, Any]],
        certified_by: str = "system_qualification_harness",
        qualification_task_id: Optional[str] = None,
    ) -> None:
        """Records or updates an agent's qualification and certification record."""
        now = time.time()
        rec_json = json.dumps(test_records)
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agent_certifications (
                    id, agent_id, tenant_id, certification_status,
                    qualification_task_id, test_records, certified_at,
                    certified_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id, tenant_id) DO UPDATE SET
                    certification_status = excluded.certification_status,
                    qualification_task_id = excluded.qualification_task_id,
                    test_records = excluded.test_records,
                    certified_at = excluded.certified_at,
                    certified_by = excluded.certified_by
                """,
                (
                    f"cert_{agent_id}_{tenant_id}", agent_id, tenant_id,
                    status, qualification_task_id, rec_json, now, certified_by, now
                )
            )
            conn.commit()

    def enforce_autonomy_ceiling(
        self,
        requested_autonomy: AutonomyLevel,
        agent_id: str,
        tenant_id: str,
        spec: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AutonomyLevel, Optional[str]]:
        """Clamps autonomy level to SHADOW if the agent is not certified."""
        certified, status, _ = self.is_certified(agent_id=agent_id, tenant_id=tenant_id, spec=spec)
        if not certified:
            # Rule 19: Uncertified agents cannot run above SHADOW
            return AutonomyLevel.SHADOW, f"Agent '{agent_id}' is {status}; autonomy clamped to SHADOW"
        return requested_autonomy, None


certification_service = AgentCertificationService()
