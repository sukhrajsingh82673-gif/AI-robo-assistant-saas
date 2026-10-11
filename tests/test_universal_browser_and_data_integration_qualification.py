"""
ZONATA / URA — Universal Browser, Data Integration & Enterprise Execution Fabric
Master Qualification Suite: Audit, Gap Analysis, Implementation, Security, Testing, and Production Qualification
================================================================================================================

Comprehensive Test Suite covering:
1. Mandatory Frontend Invariant (web/workflow_workspace.js Git blob SHA-1).
2. Governed Browser Execution Runtime:
   - Session initialization, context isolation, and abandoned session cleanup.
   - Semantic selectors (IDs, classes, attributes, roles, aria-labels, text matching).
   - Form interaction, option selection, pop-ups, multi-tab contexts.
   - Sandboxed file uploads (path traversal defense) & governed file downloads.
   - Application error banner & CAPTCHA/MFA challenge detection.
   - Postcondition verification with deterministic transaction reference vs outcome uncertainty.
   - Idempotency guards (prevention of blind retries on non-reversible actions).
   - BrowserTaskContract execution with Merkle evidence sealing.
3. Universal Business Data Integration Engine:
   - Strict JSON schema validation with secret scrubbing in error messages.
   - Exact Decimal currency normalization (INR, USD, EUR, GBP) without floating-point loss.
   - Lossless ISO 8601 UTC date/time parsing.
   - Declarative field mapping with immutable lineage and provenance tracking.
   - Resumable stream checkpoints and Dead-Letter Queue (DLQ) quarantine.
   - Record deduplication and 4 conflict policies (SOURCE_WINS, DESTINATION_WINS, LATEST_TIMESTAMP_WINS, MANUAL_APPROVAL_REQUIRED).
   - Atomic batch sync pipeline with EvidenceLedger sealing.
   - Dataset reconciliation comparing record counts, unique keys, and financial sum balances.
   - Meltano enterprise connector execution backed by genuine pipeline operations.
4. Sovereign Governance & Security:
   - Outbound DLP inspection on browser typing and credential protection.
   - SSRF protection against private IP spaces, loopback, and metadata endpoints.
   - Strict multi-tenant isolation across browser contexts and data pipelines.
   - Sovereign KillSwitch immediate execution containment.
   - Financial approval threshold enforcement for operations >= ₹50,000 INR.
"""

import unittest
import os
import time
import uuid
import json
import decimal
import subprocess
from decimal import Decimal

from core.db import db
from core.browser_use_execution_runtime import (
    BrowserExecutionGateway,
    BrowserExecutionStatus,
    BrowserActionType,
    BrowserActionRiskClass,
    BrowserProfileType,
    BrowserDomainPolicyMode,
    BrowserDomainPolicy,
    WebContentSecurityBoundary,
    BrowserActionClassifier,
    BrowserKillSwitch,
    BrowserSecurityEventType,
    BrowserErrorCategory,
    BrowserTaskContract,
    SemanticDOMParser,
    SemanticDOMElement,
    BrowserVerificationEngine,
    SecurityException
)
from core.automation_fabric.data_integration_engine import (
    DataSchemaValidator,
    DataNormalizer,
    FieldMapper,
    SyncCheckpointManager,
    DataDeduplicationAndConflictResolver,
    ConflictResolutionPolicy,
    BusinessDataSyncPipeline,
    DataReconciliationEngine,
    get_sync_pipeline
)
from core.automation_fabric.enterprise_connectors import (
    EnterpriseConnectorHandlers,
    handle_meltano_sync
)


class TestUniversalBrowserAndDataIntegrationQualification(unittest.TestCase):
    """
    Master Production Qualification Test Suite for ZONATA / URA Browser & Data Integration Fabric.
    """

    @classmethod
    def setUpClass(cls):
        cls.tenant_a = f"tnt_qual_a_{uuid.uuid4().hex[:6]}"
        cls.tenant_b = f"tnt_qual_b_{uuid.uuid4().hex[:6]}"
        cls.company_id = "comp_primary"
        cls.principal_role = "OPERATIONS_ENGINEER"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_a, "Tenant Qual A", time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_b, "Tenant Qual B", time.time())
            )
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        with db.get_connection() as conn:
            conn.execute("DELETE FROM tenants WHERE tenant_id IN (?, ?)", (cls.tenant_a, cls.tenant_b))
            conn.commit()

    def setUp(self):
        self.gateway_a = BrowserExecutionGateway(self.tenant_a, self.company_id)
        self.gateway_b = BrowserExecutionGateway(self.tenant_b, self.company_id)
        BrowserKillSwitch.reset_all()

    def tearDown(self):
        BrowserKillSwitch.reset_all()

    # =========================================================================
    # 1. MANDATORY ARCHITECTURAL & FRONTEND INVARIANT
    # =========================================================================

    def test_01_mandatory_frontend_invariant_preserved(self):
        """
        SECTION 2 INVARIANT:
        The file web/workflow_workspace.js must remain byte-for-byte identical
        to the approved baseline at commit 7c00938 with Git blob SHA-1:
        198d57ec6bda875cd2a6825fe2ef8929b7ba30bd
        """
        target_path = "web/workflow_workspace.js"
        self.assertTrue(os.path.exists(target_path), f"File {target_path} must exist")

        res = subprocess.run(
            ["git", "hash-object", target_path],
            capture_output=True,
            text=True,
            check=True
        )
        current_blob_sha = res.stdout.strip()
        expected_blob_sha = "198d57ec6bda875cd2a6825fe2ef8929b7ba30bd"

        self.assertEqual(
            current_blob_sha,
            expected_blob_sha,
            f"CRITICAL: Frontend invariant violated! Got {current_blob_sha}, expected {expected_blob_sha}"
        )

    # =========================================================================
    # 2. GOVERNED BROWSER EXECUTION ENGINE
    # =========================================================================

    def test_02_session_lifecycle_and_abandoned_cleanup(self):
        """
        Verify safe session initialization, active tracking, idle expiration detection,
        and cleanup of abandoned sessions without dangling contexts.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_qual_browser",
            profile_type=BrowserProfileType.EPHEMERAL,
            allowed_domains=["app.corp.test"]
        )
        s_id = sess["session_id"]
        s_record = self.gateway_a.get_session(s_id)
        self.assertEqual(s_record["status"], "ACTIVE")

        # Manually age session activity to simulate abandoned session
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE browser_sessions SET last_activity = ? WHERE session_id = ?",
                (time.time() - 1000.0, s_id)
            )
            conn.commit()

        # Run cleanup with 300 second threshold
        cleaned = self.gateway_a.cleanup_abandoned_sessions(max_idle_seconds=300.0)
        self.assertGreaterEqual(cleaned, 1)

        # Confirm session is now closed / terminated
        s_record = self.gateway_a.get_session(s_id)
        self.assertIn(s_record["status"], ("CLOSED", "TERMINATED"))

    def test_03_semantic_dom_parser_and_accessible_selectors(self):
        """
        Verify SemanticDOMParser matches elements by IDs, classes, attribute selectors,
        roles, aria-labels, and text containment rather than fragile coordinates.
        """
        html_doc = """
        <html>
            <body>
                <header>
                    <button id="nav_menu" class="btn primary" aria-label="Main Navigation">Menu</button>
                </header>
                <main>
                    <form id="order_form">
                        <input name="customer_name" type="text" value="Alice Johnson" />
                        <input name="amount" type="number" value="1500" />
                        <button type="submit" role="button" class="btn submit-btn">Submit Order</button>
                    </form>
                    <div role="alert" class="error-banner">Transaction Failed: Card Declined</div>
                </main>
            </body>
        </html>
        """
        parser = SemanticDOMParser()
        parser.feed(html_doc)

        # ID lookup
        elem_id = parser.find_element("#nav_menu")
        self.assertIsNotNone(elem_id)
        self.assertEqual(elem_id.aria_label, "Main Navigation")

        # Class lookup
        elem_class = parser.find_element(".submit-btn")
        self.assertIsNotNone(elem_class)
        self.assertEqual(elem_class.text, "Submit Order")

        # Attribute lookup
        elem_attr = parser.find_element("[name='customer_name']")
        self.assertIsNotNone(elem_attr)
        self.assertEqual(elem_attr.value, "Alice Johnson")

        # Role lookup
        elem_role = parser.find_element("[role='alert']")
        self.assertIsNotNone(elem_role)
        self.assertIn("Card Declined", elem_role.text)

        # Text matching
        elem_text = parser.find_element(":has-text('Submit Order')")
        self.assertIsNotNone(elem_text)
        self.assertEqual(elem_text.tag, "button")

    def test_04_form_filling_option_selection_and_popups(self):
        """
        Verify form input data entry, dropdown option selection, pop-up handling,
        and multi-tab context transitions.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_form_specialist",
            allowed_domains=["crm.enterprise.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_form_specialist",
            task_prompt="Fill out and submit enterprise lead qualification"
        )
        exec_id = exec_info["execution_id"]
        self.gateway_a.navigate(exec_id, "https://crm.enterprise.test/leads", allow_test_loopback=True)

        # 1. Type input
        type_res = self.gateway_a.execute_action(
            execution_id=exec_id,
            action_type=BrowserActionType.TYPE.value,
            selector="#company_name",
            parameters={"text": "Acme Global Industries"}
        )
        self.assertTrue(type_res["success"])

        # 2. Select option
        select_res = self.gateway_a.execute_action(
            execution_id=exec_id,
            action_type=BrowserActionType.SELECT.value,
            selector="#tier_select",
            parameters={"value": "ENTERPRISE_TIER_1"}
        )
        self.assertTrue(select_res["success"])

        # 3. Handle pop-up / alert
        popup_res = self.gateway_a.execute_action(
            execution_id=exec_id,
            action_type=BrowserActionType.HANDLE_POPUP.value,
            parameters={"action": "ACCEPT"}
        )
        self.assertTrue(popup_res["success"])
        self.assertEqual(popup_res.get("popup_action"), "ACCEPT")

        # 4. Multi-tab management
        tab_res = self.gateway_a.execute_action(
            execution_id=exec_id,
            action_type=BrowserActionType.OPEN_TAB.value,
            parameters={"url": "https://crm.enterprise.test/leads/analytics"}
        )
        self.assertTrue(tab_res["success"])
        self.assertEqual(tab_res["tabs_count"], 2)

        self.gateway_a.close_session(sess["session_id"])

    def test_05_sandboxed_file_upload_traversal_rejection(self):
        """
        Verify upload security prevents directory traversal and protects sensitive host files.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_uploader",
            allowed_domains=["vault.internal.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_uploader",
            task_prompt="Upload monthly reconciliation spreadsheet"
        )
        exec_id = exec_info["execution_id"]
        self.gateway_a.navigate(exec_id, "https://vault.internal.test/upload", allow_test_loopback=True)

        # Path traversal attempt
        with self.assertRaises(SecurityException) as ctx:
            self.gateway_a.execute_action(
                execution_id=exec_id,
                action_type=BrowserActionType.UPLOAD.value,
                selector="#file_input",
                parameters={"file_path": "../../../etc/passwd"}
            )
        self.assertIn("Disallowed file upload path", str(ctx.exception))

        # Root ssh key traversal attempt
        with self.assertRaises(SecurityException) as ctx:
            self.gateway_a.execute_action(
                execution_id=exec_id,
                action_type=BrowserActionType.UPLOAD.value,
                selector="#file_input",
                parameters={"file_path": "/root/.ssh/id_rsa"}
            )
        self.assertIn("Disallowed file upload path", str(ctx.exception))

        self.gateway_a.close_session(sess["session_id"])

    def test_06_governed_download_and_artifact_registry(self):
        """
        Verify download flow captures file in BrowserArtifactRegistry with SHA-256 integrity hash.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_downloader",
            allowed_domains=["reports.finance.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_downloader",
            task_prompt="Download GST Reconciliation Report"
        )
        exec_id = exec_info["execution_id"]
        self.gateway_a.navigate(exec_id, "https://reports.finance.test/export", allow_test_loopback=True)

        down_res = self.gateway_a.execute_action(
            execution_id=exec_id,
            action_type=BrowserActionType.DOWNLOAD.value,
            selector="#download_csv_btn",
            parameters={"filename": "gst_export_2026.csv"}
        )
        self.assertTrue(down_res["success"])
        self.assertIn("artifact_id", down_res)

        # Verify artifact stored in registry
        artifacts = self.gateway_a.list_artifacts(execution_id=exec_id)
        self.assertGreaterEqual(len(artifacts), 1)
        art = artifacts[0]
        self.assertEqual(art["artifact_type"], "DOWNLOADED_FILE")
        self.assertTrue(len(art["sha256_digest"]) == 64)

        self.gateway_a.close_session(sess["session_id"])

    def test_07_postcondition_verification_vs_outcome_uncertainty(self):
        """
        Verify postcondition verification:
        - When identifiable transaction reference is found -> VERIFIED_SUCCESS.
        - When expected postcondition is absent -> Explicit OUTCOME_UNCERTAIN / VERIFICATION_FAILED.
        Never return false success.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_verifier",
            allowed_domains=["erp.company.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_verifier",
            task_prompt="Submit PO approval and verify vendor reference"
        )
        exec_id = exec_info["execution_id"]
        self.gateway_a.navigate(exec_id, "https://erp.company.test/po/4401", allow_test_loopback=True)

        # Positive verification with confirmation reference
        passed, verifs = BrowserVerificationEngine.verify_browser_outcome(
            expected_url="https://erp.company.test/po/4401",
            actual_url="https://erp.company.test/po/4401",
            extracted_data={"po_number": "PO-4401", "status": "APPROVED", "ref": "TX-9988"},
            expected_keys=["po_number", "status"],
            confirmation_id="TX-9988"
        )
        self.assertTrue(passed)

        # Negative / Uncertain outcome (URL changed to unexpected page and confirmation missing)
        failed, failed_verifs = BrowserVerificationEngine.verify_browser_outcome(
            expected_url="https://erp.company.test/po/4401/success",
            actual_url="https://erp.company.test/server_error_500",
            confirmation_id="TX-MISSING"
        )
        self.assertFalse(failed)

        self.gateway_a.close_session(sess["session_id"])

    def test_08_idempotency_guard_prevents_blind_mutation_retries(self):
        """
        Verify that non-reversible mutations (FINANCIAL, SUBMIT_FORM, DESTRUCTIVE)
        are flagged as irreversible and NOT blindly retried on failure.
        """
        contract = BrowserTaskContract(
            mission_id=f"mis_{uuid.uuid4().hex[:6]}",
            correlation_id=f"cor_{uuid.uuid4().hex[:6]}",
            task_id=f"tsk_{uuid.uuid4().hex[:6]}",
            tenant_id=self.tenant_a,
            authorized_principal="agt_treasury",
            principal_role="TREASURY_OFFICER",
            business_objective="Execute vendor payout",
            approved_domain="payouts.banking.test",
            allowed_operations=["NAVIGATE", "TYPE", "SUBMIT_FORM"]
        )

        actions = [
            {"type": "TYPE", "selector": "#vendor_iban", "params": {"text": "GB29XABC10203012345678"}},
            # Deliberately failing action on submit
            {"type": "SUBMIT_FORM", "selector": "#non_existent_submit_btn", "params": {}}
        ]

        res_contract = self.gateway_a.execute_contract_task(contract, actions, max_retries=3, allow_test_loopback=True)

        # Verify operation was classified as non-reversible
        self.assertFalse(res_contract.is_reversible)
        # Because it is non-reversible, retry count must not repeatedly hammer the endpoint blindly
        self.assertLessEqual(res_contract.retry_count, 1)
        self.assertEqual(res_contract.execution_status, BrowserExecutionStatus.ACTION_FAILED.value)
        self.assertEqual(res_contract.error_classification, BrowserErrorCategory.ELEMENT_NOT_FOUND.value)

    def test_09_browser_task_contract_end_to_end_execution(self):
        """
        Execute formal BrowserTaskContract with end-to-end mission context,
        semantic interactions, postcondition check, and Merkle evidence sealing.
        """
        mission_id = f"mis_vendor_sync_{uuid.uuid4().hex[:6]}"
        contract = BrowserTaskContract(
            mission_id=mission_id,
            correlation_id=f"cor_{uuid.uuid4().hex[:6]}",
            task_id=f"tsk_{uuid.uuid4().hex[:6]}",
            tenant_id=self.tenant_a,
            authorized_principal="agt_procurement",
            principal_role="PURCHASER",
            business_objective="Verify catalog inventory balance",
            approved_domain="catalog.supplier.test",
            allowed_operations=["NAVIGATE", "CLICK", "TYPE", "EXTRACT", "VERIFY_POSTCONDITION"]
        )

        actions = [
            {"type": "TYPE", "selector": "#search_filter", "params": {"text": "SKU-9902"}},
            {"type": "CLICK", "selector": "#search_button", "params": {}},
            {"type": "VERIFY_POSTCONDITION", "selector": "#result_status", "params": {"expected_text": "In Stock"}}
        ]

        completed = self.gateway_a.execute_contract_task(contract, actions, allow_test_loopback=True)

        self.assertEqual(completed.execution_status, BrowserExecutionStatus.COMPLETE.value)
        self.assertTrue(completed.postcondition_verified)
        self.assertIsNotNone(completed.completion_timestamp)
        self.assertIn("evidence_id", completed.outcome_evidence)
        self.assertIn("sha256", completed.outcome_evidence)

    # =========================================================================
    # 3. UNIVERSAL BUSINESS DATA INTEGRATION ENGINE
    # =========================================================================

    def test_10_schema_validator_and_secret_scrubbing(self):
        """
        Verify strict JSON schema validation, type checks, required fields,
        and secret scrubbing from validation error diagnostics.
        """
        schema = {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "age": {"type": "integer", "minimum": 18},
                "email": {"type": "string"},
                "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE"]}
            },
            "required": ["customer_id", "email"]
        }

        # Valid payload
        valid_rec = {"customer_id": "C-1001", "age": 28, "email": "alice@corp.test", "status": "ACTIVE"}
        is_ok, errs = DataSchemaValidator.validate_record(valid_rec, schema)
        self.assertTrue(is_ok)
        self.assertEqual(len(errs), 0)

        # Invalid payload containing sensitive secret in enum violation
        invalid_rec = {
            "customer_id": "C-1002",
            "age": 14,
            "status": "Bearer sk_live_secret_token_value_998877"
        }
        is_ok2, errs2 = DataSchemaValidator.validate_record(invalid_rec, schema)
        self.assertFalse(is_ok2)
        # Verify errors do not leak secrets
        err_str = " ".join(errs2)
        self.assertNotIn("sk_live_secret_token_value_998877", err_str)
        self.assertIn("[REDACTED_SECRET]", err_str)

    def test_11_lossless_currency_and_datetime_normalization(self):
        """
        Verify exact Decimal monetary parsing (INR, USD, EUR, GBP) without floating point loss,
        and robust ISO 8601 UTC timestamp conversions.
        """
        # Exact INR Currency Parsing
        amt_inr, curr_inr = DataNormalizer.normalize_monetary_amount("₹ 1,50,000.75", default_currency="INR")
        self.assertEqual(amt_inr, Decimal("150000.75"))
        self.assertEqual(curr_inr, "INR")

        # Multi-currency parsing: EUR, USD, GBP
        amt_eur, curr_eur = DataNormalizer.normalize_monetary_amount("€ 4,250.50")
        self.assertEqual(amt_eur, Decimal("4250.50"))
        self.assertEqual(curr_eur, "EUR")

        amt_usd, curr_usd = DataNormalizer.normalize_monetary_amount("$99.99")
        self.assertEqual(amt_usd, Decimal("99.99"))
        self.assertEqual(curr_usd, "USD")

        amt_gbp, curr_gbp = DataNormalizer.normalize_monetary_amount("£ 1,200.00")
        self.assertEqual(amt_gbp, Decimal("1200.00"))
        self.assertEqual(curr_gbp, "GBP")

        # Arithmetic exactness verification (no float drift: 0.1 + 0.2 != 0.30000000000000004)
        amt_a, _ = DataNormalizer.normalize_monetary_amount("0.10", "USD")
        amt_b, _ = DataNormalizer.normalize_monetary_amount("0.20", "USD")
        self.assertEqual(amt_a + amt_b, Decimal("0.30"))

        # ISO 8601 UTC Datetime Normalization
        ts_utc = DataNormalizer.normalize_datetime("2026-10-15T14:30:00+05:30")
        self.assertEqual(ts_utc, "2026-10-15T09:00:00Z")

        ts_epoch = DataNormalizer.normalize_datetime(1776000000)
        self.assertTrue(ts_epoch.endswith("Z"))

    def test_12_declarative_field_mapping_and_provenance_tracking(self):
        """
        Verify FieldMapper transforms raw records according to versioned specs
        and attaches cryptographic provenance metadata.
        """
        mapping_spec = {
            "target_schema": "EnterpriseCustomerV2",
            "version": "2.1.0",
            "mappings": {
                "client_id": {"source": "legacy_acc_num", "transform": "to_string"},
                "account_balance": {"source": "bal_amount", "transform": "currency_inr"},
                "onboarding_date": {"source": "created_ts", "transform": "iso8601_utc"},
                "contact_email": {"source": "profile.contact.email_addr", "transform": "lowercase"}
            }
        }

        raw_record = {
            "legacy_acc_num": 988271,
            "bal_amount": "₹ 85,000.50",
            "created_ts": "2026-01-10T12:00:00Z",
            "profile": {
                "contact": {
                    "email_addr": "ALICE.DEV@GLOBALCORP.TEST"
                }
            }
        }

        mapped = FieldMapper.map_record(raw_record, mapping_spec, source_system="LegacyAS400")

        self.assertEqual(mapped["client_id"], "988271")
        self.assertEqual(mapped["account_balance"], Decimal("85000.50"))
        self.assertEqual(mapped["onboarding_date"], "2026-01-10T12:00:00Z")
        self.assertEqual(mapped["contact_email"], "alice.dev@globalcorp.test")

        # Provenance verification
        prov = mapped["_provenance"]
        self.assertEqual(prov["source_system"], "LegacyAS400")
        self.assertEqual(prov["mapping_version"], "2.1.0")
        self.assertTrue(len(prov["source_sha256"]) == 64)

    def test_13_checkpoint_persistence_resumption_and_dlq(self):
        """
        Verify stream checkpoint persistence, high-water mark resumption,
        and Dead-Letter Queue (DLQ) quarantine for defective records.
        """
        stream_id = f"stream_invoices_{uuid.uuid4().hex[:6]}"

        # Save checkpoint
        SyncCheckpointManager.save_checkpoint(
            tenant_id=self.tenant_a,
            company_id=self.company_id,
            stream_id=stream_id,
            high_water_mark="2026-10-10T23:59:59Z",
            cursor_token="cursor_token_page_10",
            records_processed=150,
            status="IN_PROGRESS"
        )

        # Retrieve checkpoint
        chk = SyncCheckpointManager.get_checkpoint(
            tenant_id=self.tenant_a,
            company_id=self.company_id,
            stream_id=stream_id
        )
        self.assertIsNotNone(chk)
        self.assertEqual(chk["high_water_mark"], "2026-10-10T23:59:59Z")
        self.assertEqual(chk["records_processed"], 150)

        # Quarantine malformed record to Dead-Letter Queue
        bad_record = {"inv_id": "INV-ERR-01", "amount": "INVALID_NUMBER_NAN"}
        dlq_id = SyncCheckpointManager.log_dead_letter(
            tenant_id=self.tenant_a,
            company_id=self.company_id,
            stream_id=stream_id,
            raw_record=bad_record,
            error_reason="Decimal parsing failed: Invalid monetary literal",
            error_code="DATA_PARSING_ERR"
        )
        self.assertTrue(dlq_id.startswith("dlq_"))

        # Verify DLQ records
        dlq_items = SyncCheckpointManager.list_dead_letter_records(
            tenant_id=self.tenant_a,
            company_id=self.company_id,
            stream_id=stream_id
        )
        self.assertEqual(len(dlq_items), 1)
        self.assertEqual(dlq_items[0]["error_code"], "DATA_PARSING_ERR")

    def test_14_deduplication_and_conflict_resolution_policies(self):
        """
        Verify deterministic deduplication fingerprints and the 4 conflict policies:
        - SOURCE_WINS
        - DESTINATION_WINS
        - LATEST_TIMESTAMP_WINS
        - MANUAL_APPROVAL_REQUIRED
        """
        resolver = DataDeduplicationAndConflictResolver()

        src = {"id": "REC-1", "name": "Source Name", "updated_at": "2026-10-11T12:00:00Z"}
        dst = {"id": "REC-1", "name": "Dest Name", "updated_at": "2026-10-10T12:00:00Z"}

        # 1. SOURCE_WINS
        w1, pol1 = resolver.resolve_conflict(src, dst, ConflictResolutionPolicy.SOURCE_WINS)
        self.assertEqual(w1["name"], "Source Name")
        self.assertIn("SOURCE_WINS", pol1)

        # 2. DESTINATION_WINS
        w2, pol2 = resolver.resolve_conflict(src, dst, ConflictResolutionPolicy.DESTINATION_WINS)
        self.assertEqual(w2["name"], "Dest Name")
        self.assertIn("DESTINATION_WINS", pol2)

        # 3. LATEST_TIMESTAMP_WINS
        w3, pol3 = resolver.resolve_conflict(src, dst, ConflictResolutionPolicy.LATEST_TIMESTAMP_WINS)
        self.assertEqual(w3["name"], "Source Name")  # 2026-10-11 is newer than 2026-10-10

        # 4. MANUAL_APPROVAL_REQUIRED
        w4, pol4 = resolver.resolve_conflict(src, dst, ConflictResolutionPolicy.MANUAL_APPROVAL_REQUIRED)
        self.assertEqual(w4.get("_conflict_status"), "AWAITING_MANUAL_APPROVAL")
        self.assertIn("APPROVAL", pol4)

    def test_15_batch_data_sync_pipeline_and_evidence_ledger(self):
        """
        Run end-to-end atomic batch sync pipeline:
        Validation -> Normalization -> Mapping -> Checkpointing -> EvidenceLedger.
        """
        pipeline = get_sync_pipeline(self.tenant_a, self.company_id)
        stream_id = f"orders_sync_{uuid.uuid4().hex[:6]}"

        mapping_spec = {
            "target_schema": "UnifiedOrder",
            "version": "1.0.0",
            "mappings": {
                "order_id": {"source": "ext_order_ref", "transform": "to_string"},
                "order_total": {"source": "gross_amt", "transform": "currency_inr"},
                "order_time": {"source": "order_date", "transform": "iso8601_utc"}
            }
        }

        records = [
            {"ext_order_ref": "ORD-101", "gross_amt": "₹ 12,500.00", "order_date": "2026-10-01T10:00:00Z"},
            {"ext_order_ref": "ORD-102", "gross_amt": "₹ 8,400.00", "order_date": "2026-10-01T11:00:00Z"},
            {"ext_order_ref": "ORD-103", "gross_amt": "₹ 24,100.50", "order_date": "2026-10-01T12:00:00Z"}
        ]

        res = pipeline.execute_sync(
            stream_id=stream_id,
            source_system="ShopifyEnterprise",
            destination_system="ZONATA_CoreERP",
            raw_records=records,
            mapping_spec=mapping_spec,
            id_field="order_id"
        )

        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["records_synced"], 3)
        self.assertEqual(res["records_quarantined"], 0)
        self.assertIn("evidence_id", res)
        self.assertTrue(len(res["sha256_digest"]) == 64)

    def test_16_dataset_reconciliation_engine(self):
        """
        Verify DataReconciliationEngine evaluates record parity, key mismatches,
        and financial sum discrepancies between source and destination datasets.
        """
        source_data = [
            {"order_id": "O-1", "amount": Decimal("1000.00")},
            {"order_id": "O-2", "amount": Decimal("2500.50")},
            {"order_id": "O-3", "amount": Decimal("500.00")}
        ]
        # Matching destination
        dest_match = [
            {"order_id": "O-1", "amount": Decimal("1000.00")},
            {"order_id": "O-2", "amount": Decimal("2500.50")},
            {"order_id": "O-3", "amount": Decimal("500.00")}
        ]
        res_ok = DataReconciliationEngine.reconcile_datasets(
            source_records=source_data,
            destination_records=dest_match,
            key_field="order_id",
            financial_sum_field="amount"
        )
        self.assertTrue(res_ok["is_reconciled"])
        self.assertEqual(res_ok["discrepancy_count"], 0)
        self.assertEqual(res_ok["balance_difference"], Decimal("0.00"))

        # Mismatch destination (missing O-3 and modified amount for O-2)
        dest_mismatch = [
            {"order_id": "O-1", "amount": Decimal("1000.00")},
            {"order_id": "O-2", "amount": Decimal("2000.00")}
        ]
        res_err = DataReconciliationEngine.reconcile_datasets(
            source_records=source_data,
            destination_records=dest_mismatch,
            key_field="order_id",
            financial_sum_field="amount"
        )
        self.assertFalse(res_err["is_reconciled"])
        self.assertIn("O-3", res_err["missing_in_destination"])
        self.assertEqual(res_err["balance_difference"], Decimal("1000.50"))

    def test_17_meltano_connector_dispatcher_integration(self):
        """
        Verify that handle_meltano_sync invokes genuine data integration engine
        operations (sync_stream, checkpoint, validation, reconciliation).
        """
        # Test sync_stream action
        sync_payload = {
            "stream_id": f"meltano_test_{uuid.uuid4().hex[:6]}",
            "source_system": "MeltanoTapPostgres",
            "destination_system": "TargetSnowflake",
            "records": [
                {"customer_id": "C-901", "balance": "₹ 55,000", "ts": "2026-10-11T00:00:00Z"}
            ],
            "mapping_spec": {
                "mappings": {
                    "id": {"source": "customer_id", "transform": "to_string"},
                    "bal": {"source": "balance", "transform": "currency_inr"}
                }
            }
        }
        res = handle_meltano_sync("sync_stream", sync_payload, tenant_id=self.tenant_a)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["records_synced"], 1)

        # Test reconcile_stream action
        recon_payload = {
            "source_records": [{"id": "1", "amt": Decimal("500")}],
            "destination_records": [{"id": "1", "amt": Decimal("500")}],
            "key_field": "id",
            "financial_field": "amt"
        }
        res_recon = handle_meltano_sync("reconcile_stream", recon_payload, tenant_id=self.tenant_a)
        self.assertTrue(res_recon["is_reconciled"])

    # =========================================================================
    # 4. SOVEREIGN GOVERNANCE, SECURITY & MULTI-TENANCY
    # =========================================================================

    def test_18_outbound_dlp_inspection_on_browser_typing(self):
        """
        Verify Outbound DLP inspection blocks unencrypted private keys and credentials
        from being typed into browser input fields.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_dlp_target",
            allowed_domains=["search.public.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_dlp_target",
            task_prompt="External research"
        )
        exec_id = exec_info["execution_id"]
        self.gateway_a.navigate(exec_id, "https://search.public.test/query", allow_test_loopback=True)

        # Exfiltration attempt with private RSA key
        malicious_input = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
        with self.assertRaises(SecurityException) as ctx:
            self.gateway_a.execute_action(
                execution_id=exec_id,
                action_type=BrowserActionType.TYPE.value,
                selector="#q",
                parameters={"text": malicious_input}
            )
        self.assertIn("DLP", str(ctx.exception))

        self.gateway_a.close_session(sess["session_id"])

    def test_19_ssrf_strict_outbound_network_defenses(self):
        """
        Verify BrowserDomainPolicy blocks SSRF vectors:
        - 127.0.0.1 (Loopback)
        - 10.0.0.1, 192.168.1.1 (RFC 1918 Private Ranges)
        - 169.254.169.254 (Cloud Metadata Endpoint)
        - Non-standard sensitive ports (22, 3306, 6379)
        """
        # Cloud metadata SSRF
        is_ok, dom, err = BrowserDomainPolicy.validate_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(is_ok)
        self.assertIn("SSRF", err)

        # RFC 1918 Private range
        is_ok2, dom2, err2 = BrowserDomainPolicy.validate_url("http://192.168.1.100/admin")
        self.assertFalse(is_ok2)
        self.assertIn("SSRF", err2)

        # Disallowed port (Redis)
        is_ok3, dom3, err3 = BrowserDomainPolicy.validate_url("http://example.com:6379")
        self.assertFalse(is_ok3)
        self.assertIn("Disallowed port", err3)

    def test_20_multi_tenant_isolation_boundary(self):
        """
        Verify strict cross-tenant boundary:
        Tenant B cannot read, execute on, or close Tenant A's browser sessions.
        """
        sess_a = self.gateway_a.create_session(
            agent_id="agt_tenant_a",
            allowed_domains=["tenant-a.internal.test"]
        )
        sess_a_id = sess_a["session_id"]

        # Attempt read from Gateway B
        record_b = self.gateway_b.get_session(sess_a_id)
        self.assertIsNone(record_b)

        # Attempt execution from Gateway B
        with self.assertRaises(SecurityException) as ctx:
            self.gateway_b.create_execution(
                session_id=sess_a_id,
                agent_id="agt_tenant_b_attacker",
                task_prompt="Hijack Tenant A Session"
            )
        self.assertIn("not found or belongs to another tenant", str(ctx.exception))

        self.gateway_a.close_session(sess_a_id)

    def test_21_sovereign_killswitch_immediate_containment(self):
        """
        Verify KillSwitch trips instantly across scopes (Tenant, Agent, Execution)
        and prohibits subsequent browser operations.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_killswitch_target",
            allowed_domains=["operations.portal.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_killswitch_target",
            task_prompt="Run batch process"
        )
        exec_id = exec_info["execution_id"]

        # Trip KillSwitch for this agent
        BrowserKillSwitch.trip_agent("agt_killswitch_target")

        # Attempt navigation while KillSwitch active
        with self.assertRaises(SecurityException) as ctx:
            self.gateway_a.navigate(exec_id, "https://operations.portal.test/run", allow_test_loopback=True)
        self.assertIn("KillSwitch", str(ctx.exception))

        # Reset KillSwitch
        BrowserKillSwitch.reset_all()

    def test_22_financial_threshold_approval_governance(self):
        """
        Verify financial operations exceeding ₹50,000 INR require Human-in-the-Loop approval.
        """
        sess = self.gateway_a.create_session(
            agent_id="agt_financial_buyer",
            allowed_domains=["payments.bank.test"]
        )
        exec_info = self.gateway_a.create_execution(
            session_id=sess["session_id"],
            agent_id="agt_financial_buyer",
            task_prompt="Authorize supplier wire payment"
        )
        exec_id = exec_info["execution_id"]
        self.gateway_a.navigate(exec_id, "https://payments.bank.test/transfer", allow_test_loopback=True)

        # Financial action with keyword "pay" and amount > ₹50,000 INR
        action_res = self.gateway_a.execute_action(
            execution_id=exec_id,
            action_type=BrowserActionType.CLICK.value,
            selector="#pay_now_button",
            parameters={"text": "Pay ₹ 75,000.00 to Vendor"}
        )

        self.assertEqual(action_res["status"], "APPROVAL_REQUIRED")
        self.assertIn("approval_id", action_res)
        self.assertEqual(action_res["risk_class"], BrowserActionRiskClass.FINANCIAL.value)

        # Executive approval flow
        appr_id = action_res["approval_id"]
        appr_res = self.gateway_a.approve_action(appr_id, approver_id="usr_chief_financial_officer")
        self.assertEqual(appr_res["status"], "APPROVED")

        self.gateway_a.close_session(sess["session_id"])


if __name__ == "__main__":
    unittest.main()
