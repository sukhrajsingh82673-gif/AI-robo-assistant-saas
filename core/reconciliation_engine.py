"""
RoboAssistant Enterprise — External Action Reconciliation Engine
Prevents duplicate external side effects and eliminates split-brain / network timeout
ambiguity by verifying remote state before retrying or escalating mutations.
"""

import time
import uuid
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from .db import db

logger = logging.getLogger("ZonataReconciliation")

class ReconciliationStatus:
    UNKNOWN = "UNKNOWN"             # Request was sent but timeout occurred; state undetermined
    MATCHED = "MATCHED"             # Remote state matches expected state exactly
    DRIFTED = "DRIFTED"             # Remote state differs from expected mutation
    NOT_FOUND = "NOT_FOUND"         # Mutation did not reach or execute on remote system
    COMPENSATED = "COMPENSATED"     # Drift was resolved via compensating mutation
    ERROR = "ERROR"                 # Reconciliation query itself failed

class ExternalActionReconciliationEngine:
    """
    Reconciles external system operations (PMS rate updates, CRM customer creates, Stripe charges)
    against recorded local intent, generating cryptographic receipts.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def reconcile_action(
        self,
        action_id: str,
        system_type: str,
        idempotency_key: str,
        expected_state: Dict[str, Any],
        remote_inspector_fn: Callable[[str], Tuple[bool, Optional[Dict[str, Any]], Optional[str]]],
        compensating_action_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], bool]] = None,
        evidence_class: str = "LOCAL_REAL_EXECUTION"
    ) -> Dict[str, Any]:
        """
        Executes a remote query to discover actual state and compares against expected state.

        remote_inspector_fn must return:
            (found: bool, actual_state: Optional[Dict], error_msg: Optional[str])
        """
        found, actual_state, err = remote_inspector_fn(idempotency_key)
        now = time.time()
        receipt_id = f"rcp_{uuid.uuid4().hex[:12]}"

        if err is not None:
            status = ReconciliationStatus.ERROR
            actual_data = {"error": err}
        elif not found:
            status = ReconciliationStatus.NOT_FOUND
            actual_data = {"status": "ABSENT_ON_REMOTE"}
        else:
            # Compare canonical normalized keys in expected_state
            is_match = True
            for k, expected_val in expected_state.items():
                if k not in actual_state or actual_state[k] != expected_val:
                    is_match = False
                    break
            
            if is_match:
                status = ReconciliationStatus.MATCHED
                actual_data = actual_state
            else:
                status = ReconciliationStatus.DRIFTED
                actual_data = actual_state
                # Attempt compensation if provided
                if compensating_action_fn:
                    try:
                        compensated = compensating_action_fn(expected_state, actual_state)
                        if compensated:
                            status = ReconciliationStatus.COMPENSATED
                    except Exception as comp_err:
                        logger.error(f"Compensating action failed for {action_id}: {comp_err}")

        # Drift is a control failure: count it so the CRITICAL alert can fire.
        if status == ReconciliationStatus.DRIFTED:
            try:
                from .observability_stack import sre_metrics
                sre_metrics.inc_counter("zonata_reconciliation_drift_total")
            except Exception:
                pass

        # Compute tamper-evident SHA-256 digest of reconciliation
        evidence_payload = {
            "action_id": action_id,
            "system_type": system_type,
            "idempotency_key": idempotency_key,
            "expected_state": expected_state,
            "actual_state": actual_data,
            "status": status,
            "evidence_classification": evidence_class,
            "timestamp": now
        }
        digest = hashlib.sha256(json.dumps(evidence_payload, sort_keys=True).encode("utf-8")).hexdigest()

        # Persist receipt
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reconciliation_receipts (
                    receipt_id, tenant_id, action_id, system_type,
                    idempotency_key, expected_state, actual_state,
                    reconciliation_status, evidence_digest,
                    evidence_classification, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    self.tenant_id,
                    action_id,
                    system_type,
                    idempotency_key,
                    json.dumps(expected_state),
                    json.dumps(actual_data),
                    status,
                    digest,
                    evidence_class,
                    now
                )
            )
            conn.commit()

        return {
            "receipt_id": receipt_id,
            "action_id": action_id,
            "status": status,
            "digest": digest,
            "evidence_classification": evidence_class,
            "matched": status == ReconciliationStatus.MATCHED,
            "requires_retry": status == ReconciliationStatus.NOT_FOUND,
            "requires_incident": status in (ReconciliationStatus.DRIFTED, ReconciliationStatus.ERROR),
            "actual_state": actual_data
        }

    def record_unknown_outcome(
        self,
        action_id: str,
        system_type: str,
        idempotency_key: str,
        expected_state: Dict[str, Any],
        error_context: str
    ) -> Dict[str, Any]:
        """
        Records an action whose remote execution status is UNKNOWN (e.g. HTTP timeout post-send).
        Never treats timeout as automatic FAILURE or automatic SUCCESS.
        """
        receipt_id = f"rcp_unk_{uuid.uuid4().hex[:8]}"
        now = time.time()
        actual_data = {"error": error_context, "resolution_pending": True}

        evidence_payload = {
            "action_id": action_id,
            "system_type": system_type,
            "idempotency_key": idempotency_key,
            "status": ReconciliationStatus.UNKNOWN,
            "timestamp": now
        }
        digest = hashlib.sha256(json.dumps(evidence_payload, sort_keys=True).encode("utf-8")).hexdigest()

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO reconciliation_receipts (
                    receipt_id, tenant_id, action_id, system_type,
                    idempotency_key, expected_state, actual_state,
                    reconciliation_status, evidence_digest,
                    evidence_classification, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'LOCAL_REAL_EXECUTION', ?)
            """, (
                receipt_id, self.tenant_id, action_id, system_type,
                idempotency_key, json.dumps(expected_state), json.dumps(actual_data),
                ReconciliationStatus.UNKNOWN, digest, now
            ))
            conn.commit()

        return {
            "receipt_id": receipt_id,
            "action_id": action_id,
            "status": ReconciliationStatus.UNKNOWN,
            "digest": digest,
            "requires_reconciliation": True
        }

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM reconciliation_receipts WHERE receipt_id = ? AND tenant_id = ?",
                (receipt_id, self.tenant_id)
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            res["expected_state"] = json.loads(res["expected_state"])
            res["actual_state"] = json.loads(res["actual_state"])
            return res

