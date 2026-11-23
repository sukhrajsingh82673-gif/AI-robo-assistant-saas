"""
ZONATA SOP Definition & Versioning Service
Governs SOP schemas, pack stub compilation, immutable version pinning, and SHA-256 sealing.
"""

from __future__ import annotations

import time
import uuid
import json
import hashlib
from typing import Dict, Any, List, Optional

from core.db import db
from core.evidence_service import evidence_service
from core.sop.types import (
    SOPVersionStatus,
    SOPNotFoundError,
    SOPVersionNotFoundError,
    SOPNotExecutableError,
)


class SOPDefinitionService:
    """
    Manages SOP definitions, immutable versions, and pack stub compilations.
    """

    @classmethod
    def register_sop(
        cls,
        tenant_id: str,
        company_id: str,
        department_id: str,
        code: str,
        title: str,
        category: str = "OPERATIONAL",
        objective: str = "",
        risk_level: str = "MEDIUM",
    ) -> Dict[str, Any]:
        """Registers a new SOP parent definition."""
        sop_code = code.strip().upper()
        sop_id = f"sop_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with db.get_connection() as conn:
            # Check duplicate code
            existing = conn.execute(
                "SELECT sop_id FROM sop_definitions WHERE company_id = ? AND sop_code = ?",
                (company_id, sop_code)
            ).fetchone()
            if existing:
                return cls.get_sop(tenant_id, company_id, existing[0])

            conn.execute(
                """
                INSERT INTO sop_definitions (
                    sop_id, tenant_id, company_id, department_id, sop_code, title,
                    category, cadence, risk_level, objective, trigger_conditions,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'EVENT_DRIVEN', ?, ?, '[]', 1, ?, ?)
                """,
                (
                    sop_id, tenant_id, company_id, department_id, sop_code, title,
                    category, risk_level, objective or title, now, now
                )
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="SOP_REGISTERED",
            payload={"sop_id": sop_id, "sop_code": sop_code, "title": title},
            action_id=f"reg_sop_{sop_id}"
        )

        return cls.get_sop(tenant_id, company_id, sop_id)

    @classmethod
    def get_sop(cls, tenant_id: str, company_id: str, sop_id: str) -> Dict[str, Any]:
        """Fetches an SOP definition by ID."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sop_definitions WHERE sop_id = ? AND tenant_id = ? AND company_id = ?",
                (sop_id, tenant_id, company_id)
            ).fetchone()
        if not row:
            raise SOPNotFoundError(f"SOP definition '{sop_id}' not found.")
        return dict(row)

    @classmethod
    def publish_version(
        cls,
        tenant_id: str,
        company_id: str,
        sop_id: str,
        semver: str,
        steps: List[Dict[str, Any]],
        author_employee_id: str,
        required_authority_level: str = "DELEGATED",
        evidence_requirements: Optional[List[str]] = None,
        approved_by_role: Optional[str] = "EXEC_COO",
    ) -> Dict[str, Any]:
        """
        Publishes an immutable SOP version.
        If steps is empty, marks the version status as NOT_EXECUTABLE.
        """
        sop = cls.get_sop(tenant_id, company_id, sop_id)
        version_id = f"sopv_{uuid.uuid4().hex[:12]}"
        now = time.time()

        is_executable = bool(steps and len(steps) > 0)
        status = SOPVersionStatus.NOT_EXECUTABLE.value if not is_executable else (
            SOPVersionStatus.APPROVED.value if approved_by_role else SOPVersionStatus.DRAFT.value
        )

        payload_bytes = json.dumps({"steps": steps or [], "authority": required_authority_level}, sort_keys=True).encode()
        sha256_hash = hashlib.sha256(payload_bytes).hexdigest()

        with db.get_connection() as conn:
            # Check unique version_semver for this sop
            existing_ver = conn.execute(
                "SELECT version_id FROM sop_versions WHERE sop_id = ? AND version_semver = ?",
                (sop_id, semver)
            ).fetchone()
            if existing_ver:
                raise ValueError(f"SOP version '{semver}' already exists. SOP versions are immutable.")

            conn.execute(
                """
                INSERT INTO sop_versions (
                    version_id, sop_id, tenant_id, version_semver, status, steps_definition,
                    input_schema, output_schema, anti_gaming_rules, required_authority_level,
                    evidence_requirements, author_employee_id, approved_by_role, approved_at,
                    sha256_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, '{}', '{}', '[]', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id, sop_id, tenant_id, semver, status,
                    json.dumps(steps or []), required_authority_level,
                    json.dumps(evidence_requirements or []), author_employee_id,
                    approved_by_role, now if approved_by_role else None,
                    sha256_hash, now
                )
            )
            conn.execute("UPDATE sop_definitions SET updated_at = ? WHERE sop_id = ?", (now, sop_id))
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="SOP_VERSION_PUBLISHED",
            payload={
                "sop_id": sop_id,
                "version_id": version_id,
                "semver": semver,
                "status": status,
                "is_executable": is_executable,
                "sha256_hash": sha256_hash,
            },
            action_id=f"pub_sopv_{version_id}"
        )

        return cls.get_version(tenant_id, company_id, version_id)

    @classmethod
    def get_version(cls, tenant_id: str, company_id: str, version_id: str) -> Dict[str, Any]:
        """Fetches an SOP version by ID."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sop_versions WHERE version_id = ? AND tenant_id = ?",
                (version_id, tenant_id)
            ).fetchone()
        if not row:
            raise SOPVersionNotFoundError(f"SOP version '{version_id}' not found.")

        data = dict(row)
        if isinstance(data.get("steps_definition"), str):
            try:
                data["steps_definition"] = json.loads(data["steps_definition"])
            except Exception:
                pass
        return data

    @classmethod
    def get_latest_version(cls, tenant_id: str, company_id: str, sop_id: str) -> Dict[str, Any]:
        """Retrieves the latest version for an SOP definition."""
        with db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM sop_versions
                WHERE sop_id = ? AND tenant_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (sop_id, tenant_id)
            ).fetchone()
        if not row:
            raise SOPVersionNotFoundError(f"No versions found for SOP '{sop_id}'.")

        data = dict(row)
        if isinstance(data.get("steps_definition"), str):
            try:
                data["steps_definition"] = json.loads(data["steps_definition"])
            except Exception:
                pass
        return data


sop_definition_service = SOPDefinitionService()
