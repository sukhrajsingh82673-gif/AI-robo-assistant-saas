"""
Tests for Sub-Step 8G: Enterprise Pilot Kit & Readiness Gate (Rule 67, 68, 74, 75, ADR 0047)
Validates passive shadow execution with zero external writes, emergency kill-switch isolation drills,
pilot data export & irreversible erasure, charter templates, and the pilot readiness gate script.
"""

import pytest
from pathlib import Path

from core.pilot.shadow_runner import (
    ShadowRunner,
    ShadowModeWriteBlockedError,
    ZeroExternalWritesSpy,
)
from core.pilot.kill_switch import (
    EmergencyKillSwitch,
    KillSwitchDrillRunner,
)
from core.pilot.exit import PilotExitManager
from scripts.pilot_readiness import evaluate_readiness, generate_report_markdown


class TestStep8GPilotReadiness:

    # 1. Passive Shadow Mode Execution & Zero External Writes (Rule 74)
    def test_01_shadow_mode_passive_observation_and_zero_writes(self):
        runner = ShadowRunner(tenant_id="TENANT-PILOT-01", pilot_id="PILOT-2026-001")

        # Business logic callback that calculates match without mutation
        def match_invoice_logic(data):
            return {
                "invoice_number": data["no"],
                "po_number": data["po"],
                "match_status": "MATCHED",
                "recommended_action": "APPROVE_PAYMENT",
            }

        rec = runner.observe_and_recommend(
            event_id="EVT-001",
            event_type="INCOMING_INVOICE",
            input_data={"no": "INV-9901", "po": "PO-1002"},
            logic_callback=match_invoice_logic
        )

        assert rec["is_committed_to_production"] is False
        assert rec["external_writes_dispatched"] == 0
        assert "seal_sha256" in rec
        assert rec["recommendation"]["match_status"] == "MATCHED"

        # Verify spy records 0 mutations
        assert runner.spy.write_count == 0

    # 2. Shadow Mode Blocks External Mutation Attempts
    def test_02_shadow_mode_blocks_external_write_attempts(self):
        runner = ShadowRunner(tenant_id="TENANT-PILOT-01", pilot_id="PILOT-2026-001")

        with pytest.raises(ShadowModeWriteBlockedError) as exc:
            runner.attempt_disallowed_external_write("https://sap.acme.corp/odata/v2/Payment", {"pay": 1000})

        assert "SHADOW_MODE_WRITE_BLOCKED" in str(exc.value)
        assert runner.spy.write_count == 1
        assert runner.spy.mutation_attempts[0]["operation"] == "HTTP_POST"

    # 3. Emergency Kill-Switch Sub-Second Isolation (Rule 75)
    def test_03_emergency_kill_switch_isolation_drill(self):
        drill = KillSwitchDrillRunner.run_isolation_drill(
            tenant_id="TENANT-PILOT-01",
            pilot_id="PILOT-2026-001",
            operator_id="SECOPS-LEAD-01"
        )
        assert drill["passed"] is True
        assert drill["trip_latency_ms"] < 1000.0  # Must be sub-second
        assert drill["workers_suspended"] is True
        assert "drill_seal_sha256" in drill

    # 4. Kill-Switch Blocks Subsequent Worker Invocations
    def test_04_kill_switch_blocks_worker_execution(self):
        switch = EmergencyKillSwitch("TENANT-PILOT-01", "PILOT-2026-001")
        switch.assert_can_execute()

        # Trip switch
        switch.trip_kill_switch("OPERATOR-01", "SECURITY_SUSPICION")

        with pytest.raises(PermissionError) as exc:
            switch.assert_can_execute()
        assert "TENANT_ISOLATED" in str(exc.value)
        assert switch.active_workers_count == 0

    # 5. Pilot Exit: Data Export & Irreversible Cryptographic Erasure
    def test_05_pilot_exit_export_and_irreversible_erasure(self):
        # 1. Export
        shadow_records = [{"rec_id": "REC-01", "recommendation": "OK"}]
        audit_events = [{"event_id": "EVT-01", "action": "LOGIN"}]

        dossier = PilotExitManager.export_pilot_dossier(
            tenant_id="TENANT-PILOT-01",
            pilot_id="PILOT-2026-001",
            shadow_records=shadow_records,
            audit_events=audit_events
        )
        assert dossier["export_status"] == "EXPORT_COMPLETE"
        assert "export_manifest_sha256" in dossier

        # 2. Irreversible erasure
        receipt = PilotExitManager.execute_irreversible_erasure(
            tenant_id="TENANT-PILOT-01",
            pilot_id="PILOT-2026-001",
            dossier_manifest_sha256=dossier["export_manifest_sha256"],
            authorized_by_client_dpo="DR_JANE_DPO_ACME"
        )
        assert receipt["erasure_status"] == "ERASURE_COMPLETE"
        assert receipt["authorized_by_dpo"] == "DR_JANE_DPO_ACME"
        assert "erasure_receipt_seal_sha256" in receipt

    # 6. Pilot Charter Template Verification
    def test_06_pilot_charter_template_contents(self):
        charter_path = Path("docs/pilot/PILOT_CHARTER_TEMPLATE.md")
        assert charter_path.exists()
        content = charter_path.read_text(encoding="utf-8")
        assert "Passive Shadow Mode Zero-Write Invariant (Rule 74)" in content
        assert "Emergency Isolation & Kill-Switch (Rule 75)" in content
        assert "Designated Human Gatekeepers" in content
        assert "30 Calendar Days" in content

    # 7. Pilot Readiness Script Invariant: Strictly NOT_READY or READY_FOR_HUMAN_GO_DECISION
    def test_07_pilot_readiness_evaluation_gate(self):
        report_data = evaluate_readiness(tenant_id="TENANT-TEST-EVAL", pilot_id="PILOT-2026-TEST")
        assert report_data["total_criteria"] == 12
        assert report_data["passed_criteria"] == 12

        # INVARIANT CHECK: Status must NOT be 'GO' or 'APPROVED'
        # Must be strictly 'READY_FOR_HUMAN_GO_DECISION'
        assert report_data["status"] == "READY_FOR_HUMAN_GO_DECISION"
        assert report_data["status"] != "GO"
        assert report_data["status"] != "PROCEED"

        # Report Markdown generation
        md = generate_report_markdown(report_data)
        assert "# Enterprise Pilot Readiness Qualification Report" in md
        assert "READY_FOR_HUMAN_GO_DECISION" in md
        assert "Report Digest (SHA-256):" in md
        assert Path("docs/reports/PILOT_READINESS_REPORT.md").exists()
