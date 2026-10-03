"""
ZONATA Enterprise Production Reality — Hardening, Chaos & Validation Suite
Validates transactional outbox, external action reconciliation, executive incidents,
machine-enforced CEO policy matrix, hospitality connector contracts, disaster recovery,
and multi-tenant isolation.
"""

import unittest
import time
import os
import json
import uuid
import hashlib
import sqlite3
from core.db import db
from core.transactional_outbox import TransactionalOutboxManager
from core.reconciliation_engine import ExternalActionReconciliationEngine, ReconciliationStatus
from core.incident_engine import ExecutiveIncidentEngine, IncidentSeverity, IncidentState, IncidentCategory
from core.ceo_policy_matrix import (
    ExecutivePolicyMatrixEnforcer,
    GovernanceViolationException,
    ActorRole,
    ActionCategory
)
from core.hospitality_production_connector import (
    HospitalityProductionConnector,
    CircuitBreakerOpenException,
    RateLimitExceededException
)
from core.disaster_recovery import DisasterRecoveryManager

class TestProductionRealityHardening(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tenant_id = f"tnt_reality_{uuid.uuid4().hex[:8]}"
        cls.company_id = f"comp_reality_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_id, "Reality Enterprise", time.time())
            )
            conn.execute(
                """
                INSERT INTO companies (
                    company_id, tenant_id, name, country, industry,
                    company_type, status, revenue, cost, contribution,
                    understanding_pct, created_at
                ) VALUES (?, ?, 'Royal Orchid Sovereign Resort', 'IN', 'Hospitality', 'EXISTING', 'OPERATIONAL', 0.0, 0.0, 0.0, 100.0, ?)
                """,
                (cls.company_id, cls.tenant_id, time.time())
            )
            conn.commit()

    # =========================================================================
    # 1. Machine-Enforced CEO Policy & Decision Boundary Enforcement
    # =========================================================================
    def test_01_ceo_policy_matrix_zero_ai_privilege_escalation(self):
        """Verify AI CEO and agents cannot execute forbidden destructive actions."""
        enforcer = ExecutivePolicyMatrixEnforcer(tenant_id=self.tenant_id)

        # AI CEO attempting DROP_TABLE
        with self.assertRaises(GovernanceViolationException) as ctx:
            enforcer.validate_action(
                actor_role=ActorRole.AI_CEO,
                action_name="DROP_TABLE",
                action_category=ActionCategory.IRREVERSIBLE_ACTION
            )
        self.assertIn("strictly forbidden for AI agent role", str(ctx.exception))

        # Specialist attempting PURGE_AUDIT_LOGS
        with self.assertRaises(GovernanceViolationException) as ctx:
            enforcer.validate_action(
                actor_role=ActorRole.SPECIALIST,
                action_name="PURGE_AUDIT_LOGS",
                action_category=ActionCategory.IRREVERSIBLE_ACTION
            )
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_02_ceo_policy_matrix_financial_thresholds(self):
        """Verify code-enforced financial spend ceilings per role."""
        enforcer = ExecutivePolicyMatrixEnforcer(tenant_id=self.tenant_id)

        # Specialist spending ₹5,000 (limit is ₹2,000)
        with self.assertRaises(GovernanceViolationException) as ctx:
            enforcer.validate_action(
                actor_role=ActorRole.SPECIALIST,
                action_name="ORDER_SUPPLIES",
                action_category=ActionCategory.FINANCIAL_MUTATION,
                amount_inr=5000.0
            )
        self.assertIn("Specialist spend limit", str(ctx.exception))

        # AI CEO spending ₹75,000 (limit is ₹50,000) -> Requires Human Owner approval
        res = enforcer.validate_action(
            actor_role=ActorRole.AI_CEO,
            action_name="AD_CAMPAIGN_EXPANSION",
            action_category=ActionCategory.FINANCIAL_MUTATION,
            amount_inr=75000.0
        )
        self.assertFalse(res["authorized"])
        self.assertTrue(res["requires_owner_approval"])

        # Human Owner with dual-key cryptographic authorization
        owner_res = enforcer.validate_action(
            actor_role=ActorRole.HUMAN_OWNER,
            action_name="ENTERPRISE_ACQUISITION",
            action_category=ActionCategory.IRREVERSIBLE_ACTION,
            amount_inr=5000000.0,
            owner_signature="sig_owner_secp256k1_abc123",
            dual_key_signature="sig_dual_yubikey_def456"
        )
        self.assertTrue(owner_res["authorized"])

    # =========================================================================
    # 2. Transactional Outbox Consistency & Crash Recovery
    # =========================================================================
    def test_03_transactional_outbox_atomic_commit_and_rollback(self):
        """Verify outbox events only commit when the surrounding DB transaction commits."""
        outbox = TransactionalOutboxManager(tenant_id=self.tenant_id)

        # Test Transaction Rollback
        with db.get_connection() as conn:
            try:
                outbox.stage_event(
                    conn=conn,
                    aggregate_type="MISSION",
                    aggregate_id="msn_aborted_01",
                    event_type="MISSION_ABORTED",
                    payload={"status": "ABORTED"}
                )
                conn.rollback()
            except Exception:
                pass

        # Verify not persisted
        pending = outbox.fetch_pending_events()
        aborted = [e for e in pending if e["aggregate_id"] == "msn_aborted_01"]
        self.assertEqual(len(aborted), 0)

        # Test Transaction Commit
        with db.get_connection() as conn:
            idem_key = f"idem_commit_{uuid.uuid4().hex[:8]}"
            outbox.stage_event(
                conn=conn,
                aggregate_type="MISSION",
                aggregate_id="msn_committed_01",
                event_type="MISSION_CREATED",
                payload={"status": "CREATED", "budget": 12000.0},
                idempotency_key=idem_key
            )
            conn.commit()

        pending = outbox.fetch_pending_events()
        committed = [e for e in pending if e["aggregate_id"] == "msn_committed_01"]
        self.assertEqual(len(committed), 1)
        self.assertEqual(committed[0]["status"], "PENDING")

    def test_04_transactional_outbox_publish_and_crash_recovery(self):
        """Verify worker publishing, dead-letter routing, and crash recovery."""
        outbox = TransactionalOutboxManager(tenant_id=self.tenant_id, max_attempts=2)

        # Stage test event
        with db.get_connection() as conn:
            obx_id = outbox.stage_event(
                conn=conn,
                aggregate_type="DECISION",
                aggregate_id="dec_crash_01",
                event_type="DECISION_APPROVED",
                payload={"decision": "Approve yield adjustment"}
            )
            conn.commit()

        # Simulate Worker Crash: Manually mark event PROCESSING with an old timestamp
        old_time = time.time() - 400.0
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE transactional_outbox SET status = 'PROCESSING', updated_at = ? WHERE outbox_id = ?",
                (old_time, obx_id)
            )
            conn.commit()

        # Run crash recovery
        recovered = outbox.recover_hung_processing(timeout_seconds=300.0)
        self.assertGreaterEqual(recovered, 1)

        # Verify status is back to PENDING
        with db.get_connection() as conn:
            row = conn.execute("SELECT status FROM transactional_outbox WHERE outbox_id = ?", (obx_id,)).fetchone()
            self.assertEqual(row["status"], "PENDING")

        # Now publish successfully
        published_events = []
        def mock_sink(event):
            published_events.append(event["aggregate_id"])
            return True

        metrics = outbox.process_all_pending(mock_sink)
        self.assertGreaterEqual(metrics["succeeded"], 1)
        self.assertIn("dec_crash_01", published_events)

    # =========================================================================
    # 3. External Action Reconciliation & Anti-Split-Brain
    # =========================================================================
    def test_05_external_action_reconciliation_exact_match(self):
        """Verify matched remote state produces cryptographic receipt without retry."""
        engine = ExternalActionReconciliationEngine(tenant_id=self.tenant_id)
        expected = {"rate": 5300.0, "currency": "INR", "status": "CONFIRMED"}

        def mock_remote_match(idempotency_token):
            return (True, {"rate": 5300.0, "currency": "INR", "status": "CONFIRMED"}, None)

        receipt = engine.reconcile_action(
            action_id="act_pms_rate_01",
            system_type="PMS",
            idempotency_key="idem_pms_5300",
            expected_state=expected,
            remote_inspector_fn=mock_remote_match,
            evidence_class="LOCAL_REAL_EXECUTION"
        )

        self.assertEqual(receipt["status"], ReconciliationStatus.MATCHED)
        self.assertTrue(receipt["matched"])
        self.assertFalse(receipt["requires_retry"])
        self.assertIsNotNone(receipt["digest"])

    def test_06_external_action_reconciliation_drift_detection(self):
        """Verify drifted state triggers compensation and does not blindly overwrite."""
        engine = ExternalActionReconciliationEngine(tenant_id=self.tenant_id)
        expected = {"rate": 5300.0, "currency": "INR"}

        # Remote has drifted rate 4800.0
        def mock_remote_drift(idempotency_token):
            return (True, {"rate": 4800.0, "currency": "INR"}, None)

        compensated_calls = []
        def mock_compensate(exp, act):
            compensated_calls.append((exp, act))
            return True

        receipt = engine.reconcile_action(
            action_id="act_pms_drift_01",
            system_type="PMS",
            idempotency_key="idem_pms_drift",
            expected_state=expected,
            remote_inspector_fn=mock_remote_drift,
            compensating_action_fn=mock_compensate,
            evidence_class="LOCAL_REAL_EXECUTION"
        )

        self.assertEqual(receipt["status"], ReconciliationStatus.COMPENSATED)
        self.assertEqual(len(compensated_calls), 1)

    # =========================================================================
    # 4. Executive Incident Management Lifecycle
    # =========================================================================
    def test_07_executive_incident_critical_auto_containment(self):
        """Verify CRITICAL incidents automatically trigger containment state."""
        inc_engine = ExecutiveIncidentEngine(tenant_id=self.tenant_id)
        incident = inc_engine.create_incident(
            company_id=self.company_id,
            title="Unauthorized API Rate Modification Attempt",
            severity=IncidentSeverity.CRITICAL,
            category=IncidentCategory.SECURITY,
            description="Attempted mass modification of room rates exceeding authority ceiling."
        )

        self.assertEqual(incident["current_state"], IncidentState.CONTAINED)
        self.assertIn("AUTOMATIC_KILLSWITCH_TRIGGERED", incident["containment_action"])

    def test_08_executive_incident_lifecycle_and_postmortem(self):
        """Verify full incident state transition progression and postmortem attachment."""
        inc_engine = ExecutiveIncidentEngine(tenant_id=self.tenant_id)
        inc = inc_engine.create_incident(
            company_id=self.company_id,
            title="Folio Payment Reconciliation Variance",
            severity=IncidentSeverity.MEDIUM,
            category=IncidentCategory.FINANCIAL_VARIANCE,
            description="Minor ₹450 gateway fee discrepancy detected in daily night audit."
        )
        inc_id = inc["incident_id"]
        self.assertEqual(inc["current_state"], IncidentState.DETECTED)

        # DETECTED -> TRIAGED
        t1 = inc_engine.transition_state(inc_id, IncidentState.TRIAGED, "Triaged by Financial Controller")
        self.assertEqual(t1["current_state"], IncidentState.TRIAGED)

        # TRIAGED -> INVESTIGATING
        t2 = inc_engine.transition_state(inc_id, IncidentState.INVESTIGATING, "Investigating payment gateway log")
        self.assertEqual(t2["current_state"], IncidentState.INVESTIGATING)

        # INVESTIGATING -> RECOVERING
        t3 = inc_engine.transition_state(inc_id, IncidentState.RECOVERING, "Applying fee classification adjustment")
        self.assertEqual(t3["current_state"], IncidentState.RECOVERING)

        # RECOVERING -> VERIFIED
        t4 = inc_engine.transition_state(inc_id, IncidentState.VERIFIED, "Audit ledger balance verified to ₹0.00 variance")
        self.assertEqual(t4["current_state"], IncidentState.VERIFIED)

        # VERIFIED -> POSTMORTEM_REQUIRED
        t5 = inc_engine.transition_state(inc_id, IncidentState.POSTMORTEM_REQUIRED, "Preparing executive postmortem")
        self.assertEqual(t5["current_state"], IncidentState.POSTMORTEM_REQUIRED)

        # Attach Postmortem -> CLOSED
        pm = inc_engine.attach_postmortem(
            incident_id=inc_id,
            root_cause="Payment gateway updated fee tier without automated webhook notification",
            corrective_actions=["Reconciled ledger and credited ₹450 fee rebate"],
            preventive_controls=["Added gateway fee schedule validation rule in connector"]
        )
        self.assertEqual(pm["status"], "CLOSED")

        # Verify illegal transition from CLOSED raises ValueError
        with self.assertRaises(ValueError):
            inc_engine.transition_state(inc_id, IncidentState.DETECTED, "Illegal backtrack")

    # =========================================================================
    # 5. Hospitality Production Connector Contract & Idempotency
    # =========================================================================
    def test_09_hospitality_connector_idempotency_100x(self):
        """Verify identical idempotency_key returns cached side effect 100 times without re-mutation."""
        conn = HospitalityProductionConnector(tenant_id=self.tenant_id)
        conn.connect({"provider": "OracleOperaCloud", "environment": "sovereign_local"})
        conn.authenticate()

        # Check initial rate
        init_res = conn.read("ROOM_RATES", {"category": "DELUXE_SUITE"})
        self.assertEqual(init_res["data"]["rate"], 4500.0)

        # First write: update to 5300.0
        key = "idem_hotel_wedding_season_5300"
        res1 = conn.write("UPDATE_ROOM_RATE", {"category": "DELUXE_SUITE", "new_rate": 5300.0}, idempotency_key=key)
        self.assertEqual(res1["new_rate"], 5300.0)
        self.assertEqual(res1["status"], "COMMITTED")
        self.assertNotIn("cached_idempotent", res1)

        # Repeat 100 times with identical key
        for _ in range(100):
            res_cached = conn.write("UPDATE_ROOM_RATE", {"category": "DELUXE_SUITE", "new_rate": 5300.0}, idempotency_key=key)
            self.assertTrue(res_cached.get("cached_idempotent"))
            self.assertEqual(res_cached["transaction_id"], res1["transaction_id"])
            self.assertEqual(res_cached["new_rate"], 5300.0)

        # Verify table still has exactly 5300.0
        final_read = conn.read("ROOM_RATES", {"category": "DELUXE_SUITE"})
        self.assertEqual(final_read["data"]["rate"], 5300.0)

    def test_10_hospitality_connector_hmac_webhook_verification(self):
        """Verify cryptographic HMAC-SHA256 signature validation on webhook ingest."""
        conn = HospitalityProductionConnector(tenant_id=self.tenant_id)
        secret = "whsec_prod_live_8fbc29a39f0183"
        payload = b'{"event":"payment_intent.succeeded","amount":1500000,"currency":"inr"}'

        # Compute valid signature
        valid_sig = hashlib.new("sha256", payload)
        import hmac
        valid_hmac = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Test valid
        self.assertTrue(conn.validate_webhook_signature(payload, valid_hmac, secret))

        # Test tampered payload
        tampered_payload = b'{"event":"payment_intent.succeeded","amount":1500,"currency":"inr"}'
        self.assertFalse(conn.validate_webhook_signature(tampered_payload, valid_hmac, secret))

        # Test forged signature
        self.assertFalse(conn.validate_webhook_signature(payload, "forged_hex_signature", secret))

    def test_11_hospitality_connector_circuit_breaker(self):
        """Verify circuit breaker trips to OPEN after consecutive failures."""
        conn = HospitalityProductionConnector(tenant_id=self.tenant_id, max_consecutive_failures=3)
        conn.connect({"provider": "OracleOperaCloud"})
        conn.authenticate()

        # Trigger 3 failures
        for i in range(3):
            with self.assertRaises(ValueError):
                conn.write("UPDATE_ROOM_RATE", {"category": "NON_EXISTENT_CATEGORY", "new_rate": 9999.0}, idempotency_key=f"fail_{i}")

        self.assertEqual(conn.circuit_state, "OPEN")

        # Next call blocked immediately by CircuitBreakerOpenException
        with self.assertRaises(CircuitBreakerOpenException):
            conn.read("ROOM_RATES", {})

    # =========================================================================
    # 6. Multi-Tenant Negative Authorization & Isolation
    # =========================================================================
    def test_12_multi_tenant_negative_authorization_isolation(self):
        """Verify Tenant A cannot access, read, or reconcile Tenant B's data."""
        tenant_a = f"tnt_alpha_{uuid.uuid4().hex[:6]}"
        tenant_b = f"tnt_beta_{uuid.uuid4().hex[:6]}"

        with db.get_connection() as conn:
            conn.execute("INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Tenant A', ?)", (tenant_a, time.time()))
            conn.execute("INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Tenant B', ?)", (tenant_b, time.time()))
            conn.commit()

        # Tenant A creates an incident
        engine_a = ExecutiveIncidentEngine(tenant_id=tenant_a)
        inc_a = engine_a.create_incident(
            company_id="comp_a",
            title="Tenant A Private Security Incident",
            severity=IncidentSeverity.HIGH,
            category=IncidentCategory.SECURITY,
            description="Confidential data breach probe"
        )

        # Tenant B queries incidents -> Must be empty
        engine_b = ExecutiveIncidentEngine(tenant_id=tenant_b)
        incidents_b = engine_b.list_incidents(active_only=False)
        self.assertEqual(len(incidents_b), 0)

        # Tenant B queries receipt from Tenant A
        reconcil_a = ExternalActionReconciliationEngine(tenant_id=tenant_a)
        rcp_a = reconcil_a.reconcile_action(
            action_id="act_priv_01",
            system_type="PMS",
            idempotency_key="key_priv_a",
            expected_state={"confidential": True},
            remote_inspector_fn=lambda k: (True, {"confidential": True}, None)
        )

        reconcil_b = ExternalActionReconciliationEngine(tenant_id=tenant_b)
        rcp_b_view = reconcil_b.get_receipt(rcp_a["receipt_id"])
        self.assertIsNone(rcp_b_view)

    # =========================================================================
    # 7. Disaster Recovery & Hot Snapshot Point-in-Time Restore
    # =========================================================================
    def test_13_disaster_recovery_hot_backup_and_restore(self):
        """Verify online hot database snapshot, SHA-256 manifest, and point-in-time restore."""
        dr = DisasterRecoveryManager(tenant_id=self.tenant_id, backup_dir="storage/backups")
        
        # 1. Take hot snapshot
        manifest = dr.create_hot_snapshot(backup_type="FULL_SNAPSHOT")
        self.assertIsNotNone(manifest["manifest_id"])
        self.assertTrue(os.path.exists(manifest["file_path"]))
        self.assertGreater(manifest["size_bytes"], 0)
        self.assertIsNotNone(manifest["sha256_checksum"])
        self.assertIsNotNone(manifest["merkle_root"])

        # 2. Perform restore verification drill into a test target path
        target_restore = f"storage/backups/restored_test_{uuid.uuid4().hex[:6]}.db"
        restore_receipt = dr.verify_and_restore_snapshot(manifest["manifest_id"], target_restore)

        self.assertTrue(restore_receipt["checksum_verified"])
        self.assertTrue(restore_receipt["sqlite_integrity_ok"])
        self.assertTrue(restore_receipt["record_counts_match"])

        # Clean test restore file
        if os.path.exists(target_restore):
            os.remove(target_restore)

    # =========================================================================
    # 8. Real Hospitality Pilot Workload Scenarios (H001 - H030)
    # =========================================================================
    def test_14_hospitality_pilot_closed_loop_execution(self):
        """
        Executes canonical real-world pilot operational cycle:
        Yield Management -> PMS Mutation -> Reconciliation -> Verification -> Ledger Digest.
        """
        conn = HospitalityProductionConnector(tenant_id=self.tenant_id)
        conn.connect({"provider": "OracleOperaCloud"})
        conn.authenticate()

        # Step 1: Read baseline
        rates = conn.read("ROOM_RATES", {"category": "DELUXE_SUITE"})
        baseline_rate = rates["data"]["rate"]
        self.assertEqual(baseline_rate, 4500.0)

        # Step 2: Yield optimization calculation
        target_rate = 5250.0  # +16.6% yield optimization for peak occupancy
        idem_key = f"pilot_h01_{uuid.uuid4().hex[:8]}"

        # Step 3: Governed execution with connector
        write_result = conn.write(
            "UPDATE_ROOM_RATE",
            {"category": "DELUXE_SUITE", "new_rate": target_rate},
            idempotency_key=idem_key
        )
        self.assertEqual(write_result["status"], "COMMITTED")
        self.assertEqual(write_result["new_rate"], target_rate)

        # Step 4: Verify transaction audit receipt
        verification = conn.verify(write_result["transaction_id"])
        self.assertTrue(verification["verified"])
        self.assertIsNotNone(verification["sha256_digest"])

        # Step 5: External Reconciliation Engine verifies zero drift
        reconcil = ExternalActionReconciliationEngine(tenant_id=self.tenant_id)
        rcp = reconcil.reconcile_action(
            action_id=write_result["transaction_id"],
            system_type="PMS",
            idempotency_key=idem_key,
            expected_state={"category": "DELUXE_SUITE", "rate": target_rate},
            remote_inspector_fn=lambda k: (True, {"category": "DELUXE_SUITE", "rate": target_rate}, None),
            evidence_class="LOCAL_REAL_EXECUTION"
        )
        self.assertEqual(rcp["status"], ReconciliationStatus.MATCHED)

if __name__ == "__main__":
    unittest.main()
