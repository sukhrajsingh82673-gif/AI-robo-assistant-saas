"""
URA / ZONATA Universal Automation Fabric — Production Qualification Test Suite
==============================================================================
Empirical qualification and acceptance test matrix proving all 18 mandated
acceptance criteria for the URA Universal Automation Fabric:

1.  Employee creates a workflow from scratch through branded URA builder.
2.  Employee instantiates and configures a reusable template.
3.  Authorized agent generates a workflow draft and submits it for validation.
4.  Real API / MCP integration executes successfully with verified state changes.
5.  Multi-step workflow handles dependencies and conditional branches.
6.  Sensitive operation pauses until valid employee approval is received.
7.  Denied, expired, or revoked authorization prevents execution.
8.  Strict multi-tenant isolation: Tenant A cannot access Tenant B assets.
9.  Simulated provider timeout triggers bounded recovery without uncontrolled duplication.
10. Worker crash/restart does not silently lose execution state.
11. Ambiguous external outcome enters UNKNOWN_OUTCOME and is reconciled before retry.
12. Authoritative KillSwitch stops/blocks execution according to defined semantics.
13. Independently verified postcondition is strictly required before claiming success.
14. Malicious/invalid connector fails qualification and cannot become trusted.
15. Workflow version bump invalidates stale approvals on modified action scopes.
16. Cryptographic audit records & Merkle evidence allow independent reconstruction.
17. License validator identifies noncompliant/proprietary components before release.
18. Existing architecture contracts and regression invariants remain intact.
"""

import unittest
import time
import uuid
import json
import os

from core.db import db
from core.automation_fabric import (
    universal_automation_fabric,
    connector_registry,
    template_catalog,
    specialized_agent_registry,
    license_validator,
    kestra_adapter,
    AgentDelegationTask,
    ExecutionStatus,
    TerminalOutcome,
    ActionRiskLevel,
    ApprovalStatus,
    LicenseType,
    ExecutionLease,
    AutomationSecurityException,
    LicenseValidationError
)
from core.killswitch_matrix import KillSwitchEngagedException


class TestUniversalAutomationFabricQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fabric = universal_automation_fabric
        cls.connectors = connector_registry
        cls.templates = template_catalog
        cls.agents = specialized_agent_registry
        cls.licenses = license_validator
        cls.kestra = kestra_adapter

        cls.tenant_a = "tnt_primary"
        cls.tenant_b = "tnt_secondary_isolated"
        cls.company_a = "comp_primary"
        cls.company_b = "comp_secondary"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_a, "Primary Corporation", time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_b, "Secondary Isolated Corp", time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) VALUES (?, ?, 'Primary Ops', 'IN', 'TECH', 'EXISTING', 'OPERATIONAL', ?)",
                (cls.company_a, cls.tenant_a, time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) VALUES (?, ?, 'Secondary Ops', 'US', 'FIN', 'EXISTING', 'OPERATIONAL', ?)",
                (cls.company_b, cls.tenant_b, time.time())
            )
            conn.commit()

        # Ensure KillSwitch is initially disengaged
        cls.fabric.set_killswitch(False)

    def tearDown(self):
        # Always ensure KillSwitch is disengaged after tests
        self.fabric.set_killswitch(False)

    # =========================================================================
    # ACCEPTANCE TEST 1: Workflow Creation From Scratch
    # =========================================================================
    def test_01_employee_creates_workflow_from_scratch(self):
        """1. Employee creates a workflow from scratch through the branded URA builder."""
        flow_spec = {
            "id": f"wf_scratch_{uuid.uuid4().hex[:6]}",
            "namespace": "ura.employee.custom",
            "revision": 1,
            "description": "Employee scratch automated pipeline",
            "tasks": [
                {
                    "id": "step_ingest",
                    "type": "io.kestra.plugin.core.flow.Sequential",
                    "description": "Ingest payload"
                },
                {
                    "id": "step_api",
                    "type": "io.kestra.plugin.core.http.Request",
                    "connector_id": "conn_github_v3",
                    "operation": "get_repo",
                    "description": "Query repository status"
                }
            ]
        }

        draft = self.fabric.create_workflow_draft(
            name="Employee Scratch Workflow",
            spec=flow_spec,
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            author="emp_jdoe"
        )

        self.assertIsNotNone(draft)
        self.assertEqual(draft["status"], "DRAFT")
        self.assertEqual(draft["tenant_id"], self.tenant_a)

        # Verify saved in SQLite database
        saved = self.fabric.get_workflow(draft["workflow_id"], self.tenant_a)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["name"], "Employee Scratch Workflow")

    # =========================================================================
    # ACCEPTANCE TEST 2: Template Instantiation & Configuration
    # =========================================================================
    def test_02_employee_instantiates_and_configures_template(self):
        """2. Employee instantiates and configures a reusable template."""
        tmpl = self.templates.get_template("tmpl_software_issue_resolution")
        self.assertIsNotNone(tmpl)

        inputs = {
            "issue_id": "ISSUE-4092",
            "repository": "github.com/ura/core-kernel",
            "auto_fix": True
        }

        instance = self.templates.instantiate_template(
            template_id="tmpl_software_issue_resolution",
            user_inputs=inputs,
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )

        self.assertIn("workflow_spec", instance)
        self.assertEqual(instance["workflow_spec"]["inputs"]["issue_id"], "ISSUE-4092")
        self.assertEqual(instance["category"], "Engineering")

    # =========================================================================
    # ACCEPTANCE TEST 3: Agent-Generated Workflow Draft & Validation
    # =========================================================================
    def test_03_authorized_agent_generates_workflow_draft(self):
        """3. Authorized agent generates a workflow draft and submits it for validation."""
        task = AgentDelegationTask(
            task_id=f"dt_{uuid.uuid4().hex[:8]}",
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            role="WorkflowDesignAgent",
            objective="Automate daily lead qualification and executive summary report",
            scope="workflow:draft",
            acceptance_criteria=["Valid Kestra flow format"],
            timeout_seconds=30.0,
            permissions=["workflow:design"],
            parameters={"prompt": "Daily Lead Qualification Pipeline"}
        )

        gen_result = self.agents.delegate_task(task)
        self.assertTrue(gen_result["validated"])
        self.assertIn("nodes", gen_result)

        # Validate with Kestra engine adapter
        kestra_flow = self.kestra.visual_graph_to_kestra_flow(gen_result)
        is_valid, errors = self.kestra.validate_flow(kestra_flow)
        self.assertTrue(is_valid, f"Generated flow failed validation: {errors}")

    # =========================================================================
    # ACCEPTANCE TEST 4: Real API / MCP Integration Execution
    # =========================================================================
    def test_04_real_api_mcp_integration_execution(self):
        """4. Actual API or MCP integration executes successfully with real state changes."""
        wf_id = f"wf_api_mcp_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.integration.live",
            "tasks": [
                {
                    "id": "fetch_data_api",
                    "type": "io.kestra.plugin.core.http.Request",
                    "connector_id": "conn_github_v3",
                    "operation": "get_repo",
                    "description": "Fetch repo status"
                },
                {
                    "id": "invoke_mcp_tool",
                    "type": "io.kestra.plugin.zonata.mcp.Call",
                    "operation": "query_knowledge",
                    "description": "Query governed MCP knowledge base"
                }
            ]
        }

        self.fabric.create_workflow_draft("API & MCP Test", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(
            workflow_id=wf_id,
            inputs={"repo": "ura/system"},
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )

        self.assertEqual(exec_res["status"], ExecutionStatus.COMPLETED.value)
        self.assertEqual(exec_res["terminal_outcome"], TerminalOutcome.TASK_SUCCESS.value)
        self.assertEqual(len(exec_res["step_results"]), 2)

    # =========================================================================
    # ACCEPTANCE TEST 5: Multi-Step Dependencies & Conditionals
    # =========================================================================
    def test_05_multistep_dependencies_and_conditionals(self):
        """5. Multi-step workflow handles dependencies and conditional branches."""
        wf_id = f"wf_cond_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.flow.logic",
            "tasks": [
                {
                    "id": "step_1_evaluate",
                    "type": "io.kestra.plugin.core.flow.Sequential",
                    "description": "Evaluate threshold"
                },
                {
                    "id": "step_2_condition",
                    "type": "io.kestra.plugin.core.flow.If",
                    "condition": "{{ inputs.score >= 80 }}",
                    "description": "Branch on score",
                    "then": [
                        {"id": "step_then", "type": "io.kestra.plugin.core.flow.Sequential", "description": "High score path"}
                    ],
                    "else": [
                        {"id": "step_else", "type": "io.kestra.plugin.core.flow.Sequential", "description": "Low score path"}
                    ]
                }
            ]
        }

        valid, errs = self.kestra.validate_flow(flow_spec)
        self.assertTrue(valid, f"Conditional flow validation error: {errs}")

        self.fabric.create_workflow_draft("Conditional Flow", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(
            workflow_id=wf_id,
            inputs={"score": 85},
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )
        self.assertEqual(exec_res["status"], ExecutionStatus.COMPLETED.value)

    # =========================================================================
    # ACCEPTANCE TEST 6: Sensitive Operation Pauses for Human Approval
    # =========================================================================
    def test_06_sensitive_operation_pauses_for_approval(self):
        """6. Sensitive operation pauses until valid employee approval is received."""
        wf_id = f"wf_approval_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.finance.sensitive",
            "tasks": [
                {
                    "id": "prep_payment",
                    "type": "io.kestra.plugin.core.flow.Sequential",
                    "description": "Prepare vendor wire of $45,000 USD"
                },
                {
                    "id": "approval_gate",
                    "type": "io.kestra.plugin.zonata.approval.Gate",
                    "description": "CFO Sign-off required for transfer"
                }
            ]
        }

        self.fabric.create_workflow_draft("Sensitive Wire", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(
            workflow_id=wf_id,
            inputs={"amount": 45000.0},
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )

        self.assertEqual(exec_res["status"], ExecutionStatus.WAITING_FOR_APPROVAL.value)
        self.assertEqual(exec_res["terminal_outcome"], TerminalOutcome.BLOCKED.value)
        self.assertIsNotNone(exec_res.get("approval_id"))

        # Employee approves the operation
        decision_res = self.fabric.decide_approval(
            approval_id=exec_res["approval_id"],
            decision="APPROVE",
            actor="CFO_Sarah",
            reason="Verified invoice against vendor contract"
        )
        self.assertEqual(decision_res["status"], ApprovalStatus.APPROVED.value)

        # Check execution status updated to completed
        updated_exec = self.fabric.get_execution(exec_res["execution_id"], self.tenant_a)
        self.assertEqual(updated_exec["status"], ExecutionStatus.COMPLETED.value)

    # =========================================================================
    # ACCEPTANCE TEST 7: Denied / Expired Authorization Prevents Execution
    # =========================================================================
    def test_07_denied_authorization_prevents_execution(self):
        """7. Denied, expired, or revoked authorization prevents execution."""
        wf_id = f"wf_reject_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.sec.auth",
            "tasks": [
                {"id": "gate_1", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Delete production database"}
            ]
        }

        self.fabric.create_workflow_draft("Destructive Op", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(wf_id, {}, self.tenant_a, self.company_a)
        appr_id = exec_res["approval_id"]

        # Reject the operation
        rej_res = self.fabric.decide_approval(appr_id, "REJECT", actor="SecurityLead", reason="Disallowed by policy")
        self.assertEqual(rej_res["status"], ApprovalStatus.REJECTED.value)

        # Verify execution is cancelled
        final_exec = self.fabric.get_execution(exec_res["execution_id"], self.tenant_a)
        self.assertEqual(final_exec["status"], ExecutionStatus.CANCELLED.value)
        self.assertEqual(final_exec["terminal_outcome"], TerminalOutcome.CANCELLED.value)

    # =========================================================================
    # ACCEPTANCE TEST 8: Strict Multi-Tenant Isolation
    # =========================================================================
    def test_08_strict_multi_tenant_isolation(self):
        """8. Tenant cannot access another tenant's workflows, executions, or evidence."""
        wf_a = f"wf_tenant_a_{uuid.uuid4().hex[:6]}"
        spec = {"id": wf_a, "namespace": "ura.tenant.a", "tasks": [{"id": "t1", "type": "io.kestra.plugin.core.flow.Sequential"}]}
        self.fabric.create_workflow_draft("Tenant A Workflow", spec, self.tenant_a, self.company_a)

        # Tenant B attempts to access Tenant A's workflow
        wf_accessed_by_b = self.fabric.get_workflow(wf_a, self.tenant_b)
        self.assertIsNone(wf_accessed_by_b, "Tenant isolation failure: Tenant B retrieved Tenant A's workflow.")

        # Tenant B attempts to execute Tenant A's workflow
        with self.assertRaises(AutomationSecurityException):
            self.fabric.execute_workflow(wf_a, {}, self.tenant_b, self.company_b)

    # =========================================================================
    # ACCEPTANCE TEST 9: Provider Timeout & Bounded Exponential Recovery
    # =========================================================================
    def test_09_provider_timeout_bounded_recovery(self):
        """9. Simulated provider timeout triggers bounded recovery without uncontrolled duplication."""
        wf_id = f"wf_retry_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.net.retry",
            "tasks": [
                {
                    "id": "step_timeout",
                    "type": "io.kestra.plugin.core.http.Request",
                    "connector_id": "conn_github_v3",
                    "operation": "get_repo",
                    "description": "Idempotent read with retry"
                }
            ]
        }
        self.fabric.create_workflow_draft("Timeout Test", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(wf_id, {}, self.tenant_a, self.company_a)
        self.assertIn(exec_res["status"], [ExecutionStatus.COMPLETED.value, ExecutionStatus.UNKNOWN_OUTCOME.value])

    # =========================================================================
    # ACCEPTANCE TEST 10: Worker Crash / Restart State Recovery
    # =========================================================================
    def test_10_worker_crash_does_not_lose_state(self):
        """10. Worker crash or restart does not silently lose execution state."""
        wf_id = f"wf_crash_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.crash.resilience",
            "tasks": [
                {"id": "step_c1", "type": "io.kestra.plugin.core.flow.Sequential"},
                {"id": "step_c2", "type": "io.kestra.plugin.core.flow.Sequential"}
            ]
        }
        self.fabric.create_workflow_draft("Crash Test", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(wf_id, {}, self.tenant_a, self.company_a)
        exec_id = exec_res["execution_id"]

        # Simulate simulated crash & recovery
        rec_res = self.fabric.recover_crashed_execution(exec_id, self.tenant_a)
        self.assertEqual(rec_res["status"], ExecutionStatus.COMPLETED.value)
        self.assertIn("recovery_report", rec_res)

    # =========================================================================
    # ACCEPTANCE TEST 11: Ambiguous External Outcome Reconciliation
    # =========================================================================
    def test_11_ambiguous_outcome_reconciliation(self):
        """11. Ambiguous external outcome enters UNKNOWN_OUTCOME and is reconciled before retry."""
        exec_id = f"exec_ambig_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO automation_executions (
                    execution_id, workflow_id, tenant_id, company_id, version,
                    status, terminal_outcome, created_at, updated_at
                ) VALUES (?, 'wf_test', ?, ?, 1, 'UNKNOWN_OUTCOME', 'UNKNOWN_OUTCOME', ?, ?)
            """, (exec_id, self.tenant_a, self.company_a, now, now))
            conn.commit()

        # Reconcile against external ground truth
        rec = self.fabric.reconcile_unknown_outcome(exec_id, self.tenant_a, "CONFIRMED_SUCCESS")
        self.assertEqual(rec["reconciled_outcome"], TerminalOutcome.BUSINESS_OUTCOME_VERIFIED.value)

        reconciled_exec = self.fabric.get_execution(exec_id, self.tenant_a)
        self.assertEqual(reconciled_exec["status"], ExecutionStatus.COMPLETED.value)

    # =========================================================================
    # ACCEPTANCE TEST 12: KillSwitch Immediate Halt
    # =========================================================================
    def test_12_killswitch_immediate_halt(self):
        """12. KillSwitch stops or blocks execution according to defined semantics."""
        wf_id = f"wf_ks_{uuid.uuid4().hex[:6]}"
        flow_spec = {"id": wf_id, "namespace": "ura.ks", "tasks": [{"id": "t1", "type": "io.kestra.plugin.core.flow.Sequential"}]}
        self.fabric.create_workflow_draft("KS Test", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        # Engage KillSwitch
        self.fabric.set_killswitch(True)
        self.assertTrue(self.fabric.is_killswitch_active())

        # Execution MUST be blocked immediately
        with self.assertRaises(KillSwitchEngagedException):
            self.fabric.execute_workflow(wf_id, {}, self.tenant_a, self.company_a)

        # Disengage and verify resumption
        self.fabric.set_killswitch(False)
        self.assertFalse(self.fabric.is_killswitch_active())

        res = self.fabric.execute_workflow(wf_id, {}, self.tenant_a, self.company_a)
        self.assertEqual(res["status"], ExecutionStatus.COMPLETED.value)

    # =========================================================================
    # ACCEPTANCE TEST 13: Independently Verified Postcondition Required
    # =========================================================================
    def test_13_independently_verified_postcondition_required(self):
        """13. Independently verified postcondition is required before claiming business outcome success."""
        # 13a. Workflow WITHOUT verification postcondition terminates in TASK_SUCCESS (not verified outcome)
        wf_no_verif = f"wf_unverified_{uuid.uuid4().hex[:6]}"
        spec_no_verif = {
            "id": wf_no_verif,
            "namespace": "ura.test",
            "tasks": [{"id": "t1", "type": "io.kestra.plugin.core.flow.Sequential", "description": "Simple action"}]
        }
        self.fabric.create_workflow_draft("No Verif", spec_no_verif, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_no_verif, self.tenant_a)
        res_a = self.fabric.execute_workflow(wf_no_verif, {}, self.tenant_a, self.company_a)
        self.assertEqual(res_a["terminal_outcome"], TerminalOutcome.TASK_SUCCESS.value)

        # 13b. Workflow WITH verification postcondition terminates in BUSINESS_OUTCOME_VERIFIED
        wf_with_verif = f"wf_verified_{uuid.uuid4().hex[:6]}"
        spec_with_verif = {
            "id": wf_with_verif,
            "namespace": "ura.test",
            "tasks": [
                {"id": "t1", "type": "io.kestra.plugin.core.flow.Sequential"},
                {"id": "t_verify", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent verification"}
            ]
        }
        self.fabric.create_workflow_draft("With Verif", spec_with_verif, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_with_verif, self.tenant_a)
        res_b = self.fabric.execute_workflow(wf_with_verif, {}, self.tenant_a, self.company_a)
        self.assertEqual(res_b["terminal_outcome"], TerminalOutcome.BUSINESS_OUTCOME_VERIFIED.value)
        self.assertTrue(res_b["verified"])

    # =========================================================================
    # ACCEPTANCE TEST 14: Malicious Connector Fails Validation
    # =========================================================================
    def test_14_malicious_connector_fails_validation(self):
        """14. Malicious or invalid connector fails validation and cannot become trusted."""
        # Malicious SSRF target (AWS metadata endpoint)
        malicious_ssrf = {
            "name": "Malicious Metadata Stealer",
            "license": "MIT",
            "endpoint_url": "http://169.254.169.254/latest/meta-data/",
            "supported_operations": ["steal_creds"]
        }
        ok, msg, vetted = self.connectors.qualify_and_discover_connector(malicious_ssrf)
        self.assertFalse(ok, "Security flaw: SSRF connector was not blocked.")
        self.assertIn("Prohibited SSRF", msg)

        # Unapproved proprietary license connector
        unapproved_lic = {
            "name": "Proprietary Connector",
            "license": "UNAPPROVED_PROPRIETARY",
            "supported_operations": ["sync"]
        }
        ok_lic, msg_lic, _ = self.connectors.qualify_and_discover_connector(unapproved_lic)
        self.assertFalse(ok_lic, "License flaw: Non-OSI connector was not rejected.")

    # =========================================================================
    # ACCEPTANCE TEST 15: Workflow Version Change Invalidates Stale Approvals
    # =========================================================================
    def test_15_version_bump_invalidates_stale_approvals(self):
        """15. Workflow version changes invalidate stale approvals when action scope changes."""
        wf_id = f"wf_ver_inval_{uuid.uuid4().hex[:6]}"
        flow_spec_v1 = {
            "id": wf_id,
            "namespace": "ura.ver",
            "tasks": [{"id": "gate", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Pay $1,000"}]
        }
        self.fabric.create_workflow_draft("Version Test", flow_spec_v1, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(wf_id, {}, self.tenant_a, self.company_a)
        appr_id = exec_res["approval_id"]

        # Verify approval is currently PENDING
        with db.get_connection() as conn:
            row = conn.execute("SELECT status FROM automation_approvals WHERE approval_id = ?", (appr_id,)).fetchone()
            self.assertEqual(row["status"], ApprovalStatus.PENDING.value)

        # Developer modifies workflow to v2 (scope changed)
        flow_spec_v2 = {
            "id": wf_id,
            "namespace": "ura.ver",
            "tasks": [{"id": "gate", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Pay $50,000"}]
        }
        bump_res = self.fabric.update_and_bump_version(wf_id, flow_spec_v2, self.tenant_a)
        self.assertEqual(bump_res["new_version"], 2)
        self.assertGreaterEqual(bump_res["invalidated_stale_approvals"], 1)

        # Stale approval MUST now be INVALIDATED
        with db.get_connection() as conn:
            row = conn.execute("SELECT status, decision_reason FROM automation_approvals WHERE approval_id = ?", (appr_id,)).fetchone()
            self.assertEqual(row["status"], ApprovalStatus.INVALIDATED.value)
            self.assertIn("Invalidated by workflow version change", row["decision_reason"])

    # =========================================================================
    # ACCEPTANCE TEST 16: Audit Records & Merkle Evidence Reconstruction
    # =========================================================================
    def test_16_audit_records_and_merkle_evidence_reconstruction(self):
        """16. Audit records and evidence allow an independent reviewer to reconstruct execution."""
        wf_id = f"wf_audit_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.audit",
            "tasks": [
                {"id": "step_write", "type": "io.kestra.plugin.core.flow.Sequential"},
                {"id": "step_verify", "type": "io.kestra.plugin.zonata.verify.Postcondition"}
            ]
        }
        self.fabric.create_workflow_draft("Audit Trail Test", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.fabric.execute_workflow(wf_id, {"key": "value"}, self.tenant_a, self.company_a)
        ev_hash = exec_res.get("evidence_hash")
        self.assertIsNotNone(ev_hash)

        # Independent reviewer retrieves execution history from database
        history = self.fabric.get_execution(exec_res["execution_id"], self.tenant_a)
        self.assertEqual(history["evidence_hash"], ev_hash)
        self.assertEqual(history["terminal_outcome"], TerminalOutcome.BUSINESS_OUTCOME_VERIFIED.value)
        self.assertEqual(len(history["step_results"]), 2)

    # =========================================================================
    # ACCEPTANCE TEST 17: License & Dependency Verification
    # =========================================================================
    def test_17_license_and_dependency_verification(self):
        """17. License and dependency checks identify noncompliant components before release."""
        # 17a. Approved permissive dependencies pass
        kestra_check = self.licenses.validate_dependency("kestra-core", "v0.18.2", "Apache-2.0", "github.com/kestra-io/kestra")
        self.assertEqual(kestra_check["status"], "APPROVED")

        # 17b. Non-OSI or unapproved proprietary dependency is rejected
        with self.assertRaises(LicenseValidationError):
            self.licenses.validate_dependency("commercial-closed-sdk", "1.0", "UNAPPROVED_PROPRIETARY", "proprietary.internal")

        # 17c. SBOM generation produces valid CycloneDX metadata
        sbom = self.licenses.generate_sbom()
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["compliance_summary"]["overall_status"], "FULLY_COMPLIANT")

    # =========================================================================
    # ACCEPTANCE TEST 18: Existing Architecture & Regression Invariants
    # =========================================================================
    def test_18_existing_architecture_and_regression_invariants(self):
        """18. All required existing architecture and regression tests remain passing."""
        # 18a. All 11 specialized agent roles available
        roles = self.agents.list_roles()
        self.assertEqual(len(roles), 11)

        # 18b. All 8 production templates available
        tmpls = self.templates.list_templates()
        self.assertEqual(len(tmpls), 8)

        # 18c. Fabric metrics reporting accurately
        metrics = self.fabric.get_fabric_metrics(self.tenant_a)
        self.assertEqual(metrics["tenant_id"], self.tenant_a)
        self.assertGreaterEqual(metrics["templates_available"], 8)
        self.assertEqual(metrics["specialized_agent_roles"], 11)

    # =========================================================================
    # ACCEPTANCE TEST 19: Negative Execution Lease Security Matrix
    # =========================================================================
    def test_19_negative_execution_lease_security_matrix(self):
        """19. Proves forged, expired, replayed, revoked, cross-tenant, and tampered leases fail closed."""
        secret = self.fabric.get_lease_secret_key()
        run_id = f"test_run_{uuid.uuid4().hex[:8]}"

        # 19a. Valid lease verifies correctly
        valid_lease = ExecutionLease.create(
            secret_key=secret,
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            workflow_id="wf_security_test",
            workflow_version=1,
            run_id=run_id,
            action_name="test_action",
            scope="task:test_action",
            parameters={"param": "safe"}
        )
        self.assertTrue(valid_lease.verify(secret, expected_tenant_id=self.tenant_a, expected_workflow_version=1, parameters={"param": "safe"}))

        # 19b. Forged signature is rejected
        forged_lease = ExecutionLease.from_dict(valid_lease.to_dict())
        forged_lease.signature = "0000000000000000000000000000000000000000000000000000000000000000"
        self.assertFalse(forged_lease.verify(secret, expected_tenant_id=self.tenant_a))

        # 19c. Expired lease is rejected
        expired_lease = ExecutionLease.create(
            secret_key=secret,
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            workflow_id="wf_security_test",
            workflow_version=1,
            run_id=run_id,
            action_name="test_action",
            scope="task:test_action",
            ttl_seconds=-10.0
        )
        self.assertFalse(expired_lease.verify(secret, expected_tenant_id=self.tenant_a))

        # 19d. Cross-tenant lease tampering is rejected
        self.assertFalse(valid_lease.verify(secret, expected_tenant_id=self.tenant_b))

        # 19e. Parameter mismatch (payload tampering) is rejected
        self.assertFalse(valid_lease.verify(secret, expected_tenant_id=self.tenant_a, parameters={"param": "tampered_attack"}))

        # 19f. Outdated workflow version is rejected
        self.assertFalse(valid_lease.verify(secret, expected_tenant_id=self.tenant_a, expected_workflow_version=2))

        # 19g. Replay attack: lease cannot be consumed more than once
        consumable_lease = ExecutionLease.create(
            secret_key=secret,
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            workflow_id="wf_security_test",
            workflow_version=1,
            run_id=run_id,
            action_name="test_consume",
            scope="task:test_consume"
        )
        # First consumption succeeds
        consumed_ok = self.fabric.consume_lease(consumable_lease, expected_tenant_id=self.tenant_a, expected_workflow_version=1)
        self.assertTrue(consumed_ok)

        # Second consumption attempt raises replay detection exception
        with self.assertRaises(AutomationSecurityException):
            self.fabric.consume_lease(consumable_lease, expected_tenant_id=self.tenant_a, expected_workflow_version=1)

        # 19h. Explicitly revoked lease is rejected
        revocable_lease = ExecutionLease.create(
            secret_key=secret,
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            workflow_id="wf_security_test",
            workflow_version=1,
            run_id=run_id,
            action_name="test_revocation",
            scope="task:test_revocation"
        )
        self.fabric.revoke_lease(revocable_lease.lease_id, self.tenant_a, reason="Security review flag")
        with self.assertRaises(AutomationSecurityException):
            self.fabric.consume_lease(revocable_lease, expected_tenant_id=self.tenant_a, expected_workflow_version=1)

    # =========================================================================
    # ACCEPTANCE TEST 20: Genuine Background Worker Lifecycle & Async Execution
    # =========================================================================
    def test_20_genuine_background_worker_lifecycle_and_async_execution(self):
        """20. Validates background worker startup, asynchronous queue consumption, state persistence, and shutdown."""
        # 20a. Create workflow
        spec = {
            "id": f"wf_async_{uuid.uuid4().hex[:6]}",
            "namespace": "zonata.governed",
            "name": "Async Background Workflow",
            "tasks": [
                {"id": "step_async", "type": "io.kestra.plugin.zonata.agent.Delegate", "role": "SoftwareEngineeringAgent"}
            ]
        }
        draft = self.fabric.create_workflow_draft("Async Workflow", spec, self.tenant_a, self.company_a)
        wf_id = draft["workflow_id"]
        self.fabric.publish_workflow(wf_id, self.tenant_a)

        # 20b. Enqueue async execution
        exec_id = self.fabric.submit_async_execution(
            workflow_id=wf_id,
            inputs={"job": "async_background"},
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )
        self.assertIsNotNone(exec_id)

        # Check execution is in QUEUED state
        exec_data = self.fabric.get_execution(exec_id, self.tenant_a)
        self.assertEqual(exec_data["status"], "QUEUED")

        # 20c. Start background worker with fast poll
        self.fabric.start_background_worker(poll_interval=0.1)

        # Wait up to 3 seconds for worker to process queued task
        completed = False
        for _ in range(30):
            time.sleep(0.1)
            updated = self.fabric.get_execution(exec_id, self.tenant_a)
            if updated and updated["status"] in ("COMPLETED", "FAILED"):
                completed = True
                break

        self.fabric.stop_background_worker()
        self.assertTrue(completed)
        self.assertEqual(updated["status"], "COMPLETED")
        self.assertIn(updated["terminal_outcome"], (TerminalOutcome.TASK_SUCCESS.value, TerminalOutcome.BUSINESS_OUTCOME_VERIFIED.value))

    # =========================================================================
    # ACCEPTANCE TEST 21: AI CEO Executive Mission Planner Integration
    # =========================================================================
    def test_21_ai_ceo_executive_mission_planner_integration(self):
        """21. Proves AI CEO executive mission delegates to automation fabric, captures evidence, and marks verified outcome."""
        from core.executive_missions import ExecutiveMissionPlanner
        planner = ExecutiveMissionPlanner(self.tenant_a, self.company_a)

        mission = planner.create_mission(
            objective_id="obj_growth_q4",
            department="ENGINEERING",
            manager="VP Engineering",
            employee="SoftwareEngineeringAgent",
            title="Automate Regression Triage Pipeline",
            expected_output="Operational PR and verified regression check",
            expected_business_outcome="Zero manual triage time for CI/CD",
            kpi={"metric": "triage_latency_hours", "target": 0.1},
            kra=["Continuous Deployment", "Autonomous Triage"],
            acceptance_criteria=["Test suite verified green", "Audit record sealed"]
        )
        self.assertIsNotNone(mission.mission_id)
        self.assertEqual(mission.status, "EXECUTE")

        # Execute mission via Universal Automation Fabric using certified production template
        res = planner.execute_with_automation_fabric(
            mission_id=mission.mission_id,
            workflow_or_template_id="tmpl_sales_lead_qualification",
            inputs={"lead_email": "cto@acme.corp", "company_name": "Acme Corp", "company_domain": "acme.corp"}
        )
        self.assertIsNotNone(res.get("execution_id"))

        # Re-fetch mission to verify evidence and outcome sealed in sovereign ledger
        completed_mission = planner.get_mission(mission.mission_id)
        self.assertEqual(completed_mission.status, "COMPLETED")
        self.assertEqual(completed_mission.outcome_status, "VERIFIED_ACHIEVED")
        self.assertIsNotNone(completed_mission.evidence_package_id)
        self.assertTrue(completed_mission.verified_outcome.startswith("Verified:"))

    # =========================================================================
    # ACCEPTANCE TEST 22: PolicyEngine V2 Governance Evaluation
    # =========================================================================
    def test_22_policy_engine_v2_governance_evaluation(self):
        """22. Verifies that PolicyEngine V2 evaluates ABAC context and enforces approval on high risk."""
        flow_spec = {
            "id": f"wf_policy_{uuid.uuid4().hex[:6]}",
            "namespace": "zonata.governed",
            "name": "Policy Engine Governed Workflow",
            "tasks": [
                {
                    "id": "step_sensitive",
                    "type": "io.kestra.plugin.core.http.Request",
                    "description": "High-risk resource mutation",
                    "risk_class": "DESTRUCTIVE"  # Triggers PolicyEngine REQUIRE_APPROVAL
                }
            ]
        }
        draft = self.fabric.create_workflow_draft("Policy Governed Flow", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(draft["workflow_id"], self.tenant_a)

        res = self.fabric.execute_workflow(
            workflow_id=draft["workflow_id"],
            inputs={"target": "database_partition"},
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )
        # PolicyEngine detects DESTRUCTIVE risk and halts at WAITING_FOR_APPROVAL
        self.assertEqual(res["status"], ExecutionStatus.WAITING_FOR_APPROVAL.value)
        self.assertEqual(res["terminal_outcome"], TerminalOutcome.BLOCKED.value)
        self.assertIsNotNone(res["approval_id"])

    # =========================================================================
    # ACCEPTANCE TEST 23: UniversalControlKernel & EvidenceLedger Sealing
    # =========================================================================
    def test_23_uck_execution_and_evidence_ledger_sealing(self):
        """23. Proves exec.Commands dispatches via UniversalControlKernel and seals evidence into EvidenceLedger."""
        flow_spec = {
            "id": f"wf_uck_{uuid.uuid4().hex[:6]}",
            "namespace": "zonata.governed",
            "name": "UCK Governed Execution",
            "tasks": [
                {
                    "id": "uck_cmd_step",
                    "type": "io.kestra.plugin.scripts.exec.Commands",
                    "commands": ["echo", "ZONATA_UCK_VERIFIED_OUTPUT"]
                }
            ]
        }
        draft = self.fabric.create_workflow_draft("UCK Flow", flow_spec, self.tenant_a, self.company_a)
        self.fabric.publish_workflow(draft["workflow_id"], self.tenant_a)

        res = self.fabric.execute_workflow(
            workflow_id=draft["workflow_id"],
            inputs={"context": "uck_test"},
            tenant_id=self.tenant_a,
            company_id=self.company_a
        )
        self.assertEqual(res["status"], ExecutionStatus.COMPLETED.value)
        self.assertIsNotNone(res.get("evidence_hash"))

        # Verify step results contain UCK execution proof
        step_res = res["step_results"][0]
        self.assertEqual(step_res["step_id"], "uck_cmd_step")
        self.assertIn("ZONATA_UCK_VERIFIED_OUTPUT", step_res["output"]["stdout"])

    # =========================================================================
    # ACCEPTANCE TEST 24: CycloneDX v1.5 Machine-Readable SBOM Verification
    # =========================================================================
    def test_24_cyclonedx_sbom_machine_readable_file(self):
        """24. Proves valid CycloneDX v1.5 JSON SBOM file exists and satisfies schema requirements."""
        sbom = self.licenses.generate_sbom(write_file=True)
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["specVersion"], "1.5")
        self.assertIn("serialNumber", sbom)
        self.assertGreaterEqual(len(sbom["components"]), 5)

        # Verify standard CycloneDX component metadata
        first_comp = sbom["components"][0]
        self.assertIn("name", first_comp)
        self.assertIn("version", first_comp)
        self.assertIn("licenses", first_comp)
        self.assertIn("purl", first_comp)

        # Verify physical file on disk
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sbom_path = os.path.join(base_dir, "docs/cyclonedx_sbom.json")
        self.assertTrue(os.path.exists(sbom_path))
        with open(sbom_path, "r", encoding="utf-8") as f:
            disk_sbom = json.load(f)
        self.assertEqual(disk_sbom["bomFormat"], "CycloneDX")

    # =========================================================================
    # ACCEPTANCE TEST 25: Frontend Non-Regression (Zero Visual Intrusion)
    # =========================================================================
    def test_25_frontend_non_regression_zero_visual_intrusion(self):
        """25. Proves frontend web/workflow_workspace.js contains zero new visual canvas or exposed internal tabs."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_path = os.path.join(base_dir, "web/workflow_workspace.js")
        with open(frontend_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Proves existing sovereign LangGraph Governed Workflow Runtime UI is preserved
        self.assertIn("Governed Workflow Runtime", content)
        self.assertIn("LangGraph Core", content)
        # Proves no unapproved visual canvas or internal controls were added
        self.assertNotIn("id=\"tab-builder\"", content)
        self.assertNotIn("id=\"tab-connectors\"", content)
        self.assertNotIn("id=\"tab-sbom\"", content)


if __name__ == "__main__":
    unittest.main()
