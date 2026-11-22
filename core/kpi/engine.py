"""
ZONATA KPI & Goal Engine Service
OpenCode Step 2I: Deterministic arithmetic KPI trees, snapshots with computation proofs, and threshold escalations.
"""

from __future__ import annotations

import time
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional

from core.db import db, tenant_scope, tenant_scoped_class
from core.evidence_service import evidence_service
from core.work.inbox import human_inbox_service, InboxItemType
from core.kpi.types import (
    KPIScopeLevel,
    KPIMetricType,
    KPIDirection,
    KPICadence,
    KPIStatus,
    KPIDefinitionCreateRequest,
    KPISnapshotModel,
    KPIAlertModel,
    KPINotFoundError,
    MissingComputationProofError,
)
from core.kpi.calculator import KPICalculator


@tenant_scoped_class
class KPIEngine:
    """
    Manages KPI hierarchy, deterministic calculations, snapshot proofs,
    breach escalations, and automated playbooks.
    """

    @classmethod
    def register_kpi(
        cls,
        tenant_id: str,
        company_id: str,
        request: KPIDefinitionCreateRequest,
    ) -> Dict[str, Any]:
        """Registers a new KPI definition node in the organizational tree."""
        kpi_id = f"kpi_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with tenant_scope(tenant_id, company_id):
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO kpi_tree_definitions (
                        id, tenant_id, company_id, code, name, description,
                        scope_level, scope_id, metric_type, target_value,
                        warning_threshold, critical_threshold, direction,
                        unit, cadence, parent_kpi_id, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        kpi_id, tenant_id, company_id, request.code, request.name,
                        request.description, request.scope_level.value, request.scope_id,
                        request.metric_type.value, request.target_value,
                        request.warning_threshold, request.critical_threshold,
                        request.direction.value, request.unit, request.cadence.value,
                        request.parent_kpi_id, now, now
                    )
                )
                conn.commit()

            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="KPI_REGISTERED",
                payload={"kpi_id": kpi_id, "code": request.code, "name": request.name},
                action_id=f"reg_kpi_{kpi_id}"
            )

            return cls.get_kpi(tenant_id, company_id, kpi_id)

    @classmethod
    def create_tree_definition(cls, request: KPIDefinitionCreateRequest, tenant_id: Optional[str] = None, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Convenience alias for register_kpi."""
        t_id = tenant_id or getattr(request, "tenant_id", "default_tenant")
        c_id = company_id or getattr(request, "company_id", "default_company")
        return cls.register_kpi(t_id, c_id, request)

    @classmethod
    def approve_kpi(cls, tenant_id: str, company_id: str, kpi_id: str, approver_principal_id: str = "usr_owner") -> Dict[str, Any]:
        """Approves a KPI definition node in the tree."""
        with tenant_scope(tenant_id, company_id):
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE kpi_tree_definitions SET is_active = 1, updated_at = ? WHERE id = ? AND tenant_id = ? AND company_id = ?",
                    (time.time(), kpi_id, tenant_id, company_id)
                )
                conn.commit()
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="KPI_APPROVED",
                payload={"kpi_id": kpi_id, "approver": approver_principal_id},
                action_id=f"appr_kpi_{kpi_id}"
            )
            return cls.get_kpi(tenant_id, company_id, kpi_id)

    @classmethod
    def approve_tree_definition(cls, kpi_id: str, tenant_id: Optional[str] = None, company_id: Optional[str] = None, approver_principal_id: str = "usr_owner") -> Dict[str, Any]:
        """Convenience alias for approve_kpi."""
        t_id = tenant_id
        c_id = company_id
        if not t_id or not c_id:
            with db.get_connection() as conn:
                row = conn.execute("SELECT tenant_id, company_id FROM kpi_tree_definitions WHERE id = ?", (kpi_id,)).fetchone()
                if row:
                    t_id = row[0]
                    c_id = row[1]
        return cls.approve_kpi(t_id or "default_tenant", c_id or "default_company", kpi_id, approver_principal_id)

    @classmethod
    def compute_snapshot(cls, kpi_id: str, tenant_id: Optional[str] = None, company_id: Optional[str] = None) -> KPISnapshotModel:
        """Convenience alias for compute_kpi_snapshot looking up tenant/company scope if omitted."""
        t_id = tenant_id
        c_id = company_id
        if not t_id or not c_id:
            with db.get_connection() as conn:
                row = conn.execute("SELECT tenant_id, company_id FROM kpi_tree_definitions WHERE id = ?", (kpi_id,)).fetchone()
                if row:
                    t_id = row[0]
                    c_id = row[1]
        return cls.compute_kpi_snapshot(t_id or "default_tenant", c_id or "default_company", kpi_id)

    @classmethod
    def get_kpi(cls, tenant_id: str, company_id: str, kpi_id: str) -> Dict[str, Any]:
        """Retrieves a KPI definition by ID."""
        with tenant_scope(tenant_id, company_id):
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM kpi_tree_definitions WHERE id = ? AND tenant_id = ? AND company_id = ?",
                    (kpi_id, tenant_id, company_id)
                ).fetchone()
            if not row:
                raise KPINotFoundError(f"KPI definition '{kpi_id}' not found.")
            return dict(row)

    @classmethod
    def compute_kpi_snapshot(
        cls,
        tenant_id: str,
        company_id: str,
        kpi_id: str,
        effective_date: Optional[str] = None,
        playbook_on_breach: Optional[str] = None,
    ) -> KPISnapshotModel:
        """
        Computes metric strictly from database data, evaluates thresholds,
        verifies computation proof & inputs_hash, and records historical snapshot.
        """
        with tenant_scope(tenant_id, company_id):
            kpi = cls.get_kpi(tenant_id, company_id, kpi_id)
            metric_type = KPIMetricType(kpi["metric_type"])
            scope_level = KPIScopeLevel(kpi["scope_level"])
            scope_id = kpi["scope_id"]
            direction = KPIDirection(kpi["direction"])
            target_val = float(kpi["target_value"])
            warn_val = float(kpi["warning_threshold"])
            crit_val = float(kpi["critical_threshold"])

            # 1. Deterministic Calculation from Stored Data
            val, proof, inputs_hash = KPICalculator.compute_metric(
                tenant_id=tenant_id,
                company_id=company_id,
                metric_type=metric_type,
                scope_level=scope_level,
                scope_id=scope_id,
            )

            # Invariant: No KPI score is stored without its inputs hash
            if not inputs_hash or not inputs_hash.strip():
                raise MissingComputationProofError("No KPI score is stored without its inputs hash.")

            # 2. Evaluate Thresholds
            if proof.get("count") == 0:
                status = KPIStatus.INSUFFICIENT_MEASUREMENTS
            else:
                status = KPIStatus.ON_TRACK
                if direction == KPIDirection.HIGHER_IS_BETTER:
                    if val < crit_val:
                        status = KPIStatus.CRITICAL
                    elif val < warn_val:
                        status = KPIStatus.WARNING
                else:  # LOWER_IS_BETTER
                    if val > crit_val:
                        status = KPIStatus.CRITICAL
                    elif val > warn_val:
                        status = KPIStatus.WARNING

            snapshot_id = f"kpis_{uuid.uuid4().hex[:12]}"
            now = time.time()
            eff_date = effective_date or datetime.date.today().isoformat()

            # 3. Store Snapshot
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO kpi_snapshots (
                        id, tenant_id, company_id, kpi_id, scope_level, scope_id,
                        current_value, target_value, warning_threshold, critical_threshold,
                        status, computation_proof, inputs_hash, effective_date, computed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id, tenant_id, company_id, kpi_id, scope_level.value, scope_id,
                        val, target_val, warn_val, crit_val, status.value,
                        json.dumps(proof), inputs_hash, eff_date, now
                    )
                )
                conn.commit()

            # 4. Handle Breach Escalations & Playbooks
            if status in (KPIStatus.WARNING, KPIStatus.CRITICAL):
                alert_id = f"kpia_{uuid.uuid4().hex[:12]}"
                thresh = crit_val if status == KPIStatus.CRITICAL else warn_val
                with db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO kpi_alerts (
                            id, tenant_id, company_id, kpi_id, snapshot_id, severity,
                            observed_value, threshold_value, escalated_to_role, status,
                            playbook_triggered, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'EXEC_COO', 'OPEN', ?, ?)
                        """,
                        (
                            alert_id, tenant_id, company_id, kpi_id, snapshot_id,
                            status.value, val, thresh, playbook_on_breach, now
                        )
                    )
                    conn.commit()

                # Enqueue alert into human inbox
                human_inbox_service.create_item(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    item_type=InboxItemType.TASK_INTERVENTION,
                    title=f"KPI Breach Alert: {kpi['name']} ({status.value})",
                    context_data={
                        "kpi": kpi,
                        "snapshot": {"value": val, "threshold": thresh, "status": status.value},
                        "playbook": playbook_on_breach,
                    },
                    target_principal_type="OWNER",
                    target_principal_id="principal_owner",
                    decision_needed="ACKNOWLEDGE_OR_INTERVENE",
                )

                evidence_service.record_event(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    event_type="KPI_BREACH_ALERT",
                    payload={"kpi_id": kpi_id, "snapshot_id": snapshot_id, "severity": status.value, "value": val},
                    action_id=alert_id,
                )

            return KPISnapshotModel(
                id=snapshot_id,
                tenant_id=tenant_id,
                company_id=company_id,
                kpi_id=kpi_id,
                scope_level=scope_level,
                scope_id=scope_id,
                current_value=val,
                target_value=target_val,
                warning_threshold=warn_val,
                critical_threshold=crit_val,
                status=status,
                computation_proof=proof,
                inputs_hash=inputs_hash,
                effective_date=eff_date,
                computed_at=now,
            )


kpi_engine = KPIEngine()
