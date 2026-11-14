"""
URA / ZONATA Universal Automation Fabric — Production Workflow Templates
========================================================================
Comprehensive catalog of 8 production-grade, versioned, permission-aware
workflow templates covering key business and engineering operations.

Templates:
1. Software Issue Resolution (investigation, changes, test execution, review)
2. CI/CD Pipeline with Deployment Approval (build, staging test, approval gate, deploy)
3. Sales Lead Qualification (intake, scoring, CRM sync, outreach dispatch)
4. Executive Meeting Preparation (agenda, briefing synthesis, task assignment)
5. Cloud Resource Provisioning (spec validation, provision, health verification)
6. Data Reconciliation & Executive Report (multi-source ingest, diff, Merkle report)
7. Incident Detection, Escalation & Recovery (alert triage, circuit breaker, failover)
8. Cross-System API & MCP Orchestration (API call, MCP data fetch, verified sync)
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from core.automation_fabric.contracts import WorkflowTemplate, LicenseType


class TemplateCatalog:
    """Catalog managing versioned, permission-aware workflow templates."""
    def __init__(self):
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._init_templates()

    def _init_templates(self):
        # 1. Software Issue Resolution
        self.register_template(WorkflowTemplate(
            template_id="tmpl_software_issue_resolution",
            name="Software Issue Investigation & Code Review",
            version="1.2.0",
            category="Engineering",
            purpose="Investigate software defects, execute test suites, isolate failure causes, and create reviewable PRs.",
            required_integrations=["conn_github_v3", "conn_zonata_mcp_local"],
            inputs_schema={
                "issue_id": {"type": "string", "description": "Issue tracking identifier", "required": True},
                "repository": {"type": "string", "description": "Git repository path", "required": True},
                "auto_fix": {"type": "boolean", "default": False}
            },
            workflow_spec={
                "id": "wf_software_issue_resolution",
                "namespace": "ura.engineering",
                "tasks": [
                    {"id": "fetch_issue_context", "type": "io.kestra.plugin.core.http.Request", "description": "Fetch issue description and reproduction steps"},
                    {"id": "execute_repro_tests", "type": "io.kestra.plugin.scripts.exec.Commands", "description": "Run automated reproduction test suite"},
                    {"id": "code_analysis", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "SoftwareEngineeringAgent analyzes root cause"},
                    {"id": "peer_review_gate", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Human lead approval before merge"},
                    {"id": "verify_build_green", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent verification that all tests pass"}
                ]
            },
            permissions=["repo:read", "code:analyze", "test:execute"],
            expected_outcomes=["Defect isolated", "Passing test verification artifact generated", "Pull request created"],
            compensation_strategy="Rollback candidate branch on test failure",
            verification_spec={"postcondition": "test_suite_exit_code_zero", "artifact_required": True},
            license=LicenseType.APACHE_2_0
        ))

        # 2. CI/CD Deployment Pipeline
        self.register_template(WorkflowTemplate(
            template_id="tmpl_cicd_deployment_pipeline",
            name="CI/CD Pipeline with Deployment Approval",
            version="2.0.0",
            category="DevOps",
            purpose="Build container artifacts, run staging smoke tests, require managerial sign-off, and deploy.",
            required_integrations=["conn_github_v3"],
            inputs_schema={
                "commit_sha": {"type": "string", "required": True},
                "target_environment": {"type": "string", "enum": ["staging", "production"], "default": "staging"}
            },
            workflow_spec={
                "id": "wf_cicd_deployment",
                "namespace": "ura.devops",
                "tasks": [
                    {"id": "build_container", "type": "io.kestra.plugin.scripts.exec.Commands", "description": "Build OCI image"},
                    {"id": "run_security_scan", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "SecurityPolicyAgent checks CVE thresholds"},
                    {"id": "deploy_staging", "type": "io.kestra.plugin.core.http.Request", "description": "Deploy image to staging cluster"},
                    {"id": "manager_approval", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Executive release authorization gate"},
                    {"id": "deploy_production", "type": "io.kestra.plugin.core.http.Request", "description": "Promote release to production"},
                    {"id": "verify_health_check", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent HTTP 200 health probe"}
                ]
            },
            permissions=["build:run", "deploy:staging", "deploy:production", "approval:executive"],
            expected_outcomes=["Artifact built and scanned", "Zero critical CVEs", "Production health verified"],
            compensation_strategy="Automatic rollback to previous stable GA image on health probe timeout",
            verification_spec={"postcondition": "health_check_status_200", "probe_timeout_seconds": 60.0},
            license=LicenseType.APACHE_2_0
        ))

        # 3. Sales Lead Qualification
        self.register_template(WorkflowTemplate(
            template_id="tmpl_sales_lead_qualification",
            name="Sales Lead Intake & CRM Pipeline",
            version="1.1.0",
            category="Sales",
            purpose="Process incoming inbound leads, compute qualification score, enrich company data, and sync CRM.",
            required_integrations=["conn_slack_events"],
            inputs_schema={
                "lead_email": {"type": "string", "required": True},
                "company_domain": {"type": "string", "required": True},
                "employee_count": {"type": "integer", "default": 50}
            },
            workflow_spec={
                "id": "wf_sales_lead",
                "namespace": "ura.sales",
                "tasks": [
                    {"id": "enrich_lead_data", "type": "io.kestra.plugin.core.http.Request", "description": "Query firmographic provider"},
                    {"id": "score_lead", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "SalesCRMAgent computes priority tier"},
                    {"id": "update_crm_record", "type": "io.kestra.plugin.core.http.Request", "description": "Write contact into corporate CRM"},
                    {"id": "notify_sales_rep", "type": "io.kestra.plugin.core.http.Request", "description": "Dispatch Slack notification to account executive"},
                    {"id": "verify_crm_record", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent check that CRM contact exists"}
                ]
            },
            permissions=["crm:write", "messaging:dispatch"],
            expected_outcomes=["Lead qualified and graded", "CRM record updated", "Account executive notified"],
            compensation_strategy="Archive lead in dead-letter table on CRM failure",
            verification_spec={"postcondition": "crm_record_persisted", "check_fields": ["lead_id", "email"]},
            license=LicenseType.APACHE_2_0
        ))

        # 4. Executive Meeting Preparation
        self.register_template(WorkflowTemplate(
            template_id="tmpl_meeting_prep_delegation",
            name="Meeting Preparation & Delegation",
            version="1.0.0",
            category="Executive",
            purpose="Synthesize attendee briefings, construct meeting agenda, and assign pre-meeting action items.",
            required_integrations=["conn_slack_events", "conn_zonata_mcp_local"],
            inputs_schema={
                "meeting_title": {"type": "string", "required": True},
                "attendees": {"type": "array", "required": True},
                "agenda_topics": {"type": "array", "required": True}
            },
            workflow_spec={
                "id": "wf_meeting_prep",
                "namespace": "ura.executive",
                "tasks": [
                    {"id": "compile_dossier", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "DataResearchAgent collects historical context"},
                    {"id": "generate_briefing", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "TaskPlanningAgent generates agenda briefing"},
                    {"id": "distribute_calendar_pack", "type": "io.kestra.plugin.core.http.Request", "description": "Send meeting pack to attendees"},
                    {"id": "verify_delivery", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Confirm all attendees received briefing"}
                ]
            },
            permissions=["calendar:write", "comms:dispatch"],
            expected_outcomes=["Briefing pack delivered", "Meeting agenda locked"],
            compensation_strategy="Notify meeting organizer of uncontactable attendees",
            verification_spec={"postcondition": "delivery_receipts_recorded"},
            license=LicenseType.APACHE_2_0
        ))

        # 5. Cloud Resource Provisioning
        self.register_template(WorkflowTemplate(
            template_id="tmpl_resource_provisioning",
            name="Resource Provisioning & Health Gate",
            version="1.3.0",
            category="Infrastructure",
            purpose="Provision isolated cloud compute resources within strict budget caps with post-allocation validation.",
            required_integrations=["conn_zonata_mcp_local"],
            inputs_schema={
                "resource_type": {"type": "string", "enum": ["VM", "DATABASE", "QUEUE"], "required": True},
                "region": {"type": "string", "default": "us-east-1"},
                "budget_monthly_cap_usd": {"type": "number", "default": 500.0}
            },
            workflow_spec={
                "id": "wf_resource_provision",
                "namespace": "ura.infra",
                "tasks": [
                    {"id": "check_tenant_quota", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "ResourceManagementAgent checks quota"},
                    {"id": "approval_gate_cost", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Financial spend sign-off"},
                    {"id": "dispatch_cloud_api", "type": "io.kestra.plugin.core.http.Request", "description": "Call cloud infrastructure provider API"},
                    {"id": "verify_resource_online", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent TCP handshake and status probe"}
                ]
            },
            permissions=["infra:provision", "finance:spend"],
            expected_outcomes=["Resource provisioned", "Spend ledger updated", "Handshake probe successful"],
            compensation_strategy="Deprovision allocated cloud resources if verification handshake fails",
            verification_spec={"postcondition": "tcp_probe_reachable", "expected_status": "ONLINE"},
            license=LicenseType.APACHE_2_0
        ))

        # 6. Data Reconciliation & Executive Report
        self.register_template(WorkflowTemplate(
            template_id="tmpl_data_reconciliation_reporting",
            name="Data Reconciliation & Management Report",
            version="1.0.0",
            category="Analytics",
            purpose="Extract data from disparate enterprise systems, compute reconciliation diffs, and generate signed audit reports.",
            required_integrations=["conn_zonata_mcp_local"],
            inputs_schema={
                "report_period": {"type": "string", "required": True},
                "sources": {"type": "array", "required": True}
            },
            workflow_spec={
                "id": "wf_data_reconcile",
                "namespace": "ura.analytics",
                "tasks": [
                    {"id": "ingest_source_a", "type": "io.kestra.plugin.core.http.Request", "description": "Ingest primary transaction stream"},
                    {"id": "ingest_source_b", "type": "io.kestra.plugin.core.http.Request", "description": "Ingest ledger records"},
                    {"id": "compute_reconciliation", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "DataResearchAgent computes discrepancy diffs"},
                    {"id": "executive_signoff", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "CFO / Finance signoff if variance > 0"},
                    {"id": "verify_merkle_digest", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent verification of cryptographic proof"}
                ]
            },
            permissions=["finance:read", "analytics:report"],
            expected_outcomes=["Zero unexplained variance", "Cryptographic Merkle ledger entry logged"],
            compensation_strategy="Flag variance in UnknownOutcome queue for human audit",
            verification_spec={"postcondition": "merkle_root_verified", "variance_zero": True},
            license=LicenseType.APACHE_2_0
        ))

        # 7. Incident Detection, Escalation & Recovery
        self.register_template(WorkflowTemplate(
            template_id="tmpl_incident_detection_recovery",
            name="Incident Detection, Escalation & Recovery",
            version="2.1.0",
            category="Reliability",
            purpose="Automatically detect production anomalies, trip circuit breakers, notify on-call, and execute automated recovery.",
            required_integrations=["conn_slack_events", "conn_zonata_mcp_local"],
            inputs_schema={
                "incident_id": {"type": "string", "required": True},
                "severity": {"type": "string", "enum": ["LOW", "HIGH", "CRITICAL"], "default": "HIGH"}
            },
            workflow_spec={
                "id": "wf_incident_response",
                "namespace": "ura.sre",
                "tasks": [
                    {"id": "triage_alert", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "SecurityPolicyAgent triages threat severity"},
                    {"id": "trip_circuit_breaker", "type": "io.kestra.plugin.core.flow.Pause", "description": "Halt affected traffic if critical"},
                    {"id": "page_oncall", "type": "io.kestra.plugin.core.http.Request", "description": "Dispatch PagerDuty / Slack escalation"},
                    {"id": "execute_safe_recovery", "type": "io.kestra.plugin.zonata.agent.Delegate", "description": "ExecutionRecoveryAgent restarts safe checkpoint"},
                    {"id": "verify_recovered_state", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent verification that system is healthy"}
                ]
            },
            permissions=["sre:circuit_breaker", "recovery:execute"],
            expected_outcomes=["Alert triaged within 30s", "Automated recovery initiated", "Zero silent data loss"],
            compensation_strategy="Engage KillSwitch and hold all mutations pending human takeover",
            verification_spec={"postcondition": "service_health_healthy", "reconciliation_complete": True},
            license=LicenseType.APACHE_2_0
        ))

        # 8. Cross-System API & MCP Orchestration
        self.register_template(WorkflowTemplate(
            template_id="tmpl_cross_system_mcp_api",
            name="Cross-System API & MCP Orchestration",
            version="1.0.0",
            category="Integrations",
            purpose="Coordinate actions across external REST APIs and governed local MCP tools with bi-directional synchronization.",
            required_integrations=["conn_github_v3", "conn_slack_events", "conn_zonata_mcp_local"],
            inputs_schema={
                "sync_job_name": {"type": "string", "required": True},
                "payload": {"type": "object", "required": True}
            },
            workflow_spec={
                "id": "wf_cross_system_sync",
                "namespace": "ura.integration",
                "tasks": [
                    {"id": "call_external_api", "type": "io.kestra.plugin.core.http.Request", "description": "Execute remote API integration"},
                    {"id": "call_mcp_tool", "type": "io.kestra.plugin.zonata.mcp.Call", "description": "Invoke governed MCP local tool"},
                    {"id": "sync_slack_notify", "type": "io.kestra.plugin.core.http.Request", "description": "Notify Slack of sync completion"},
                    {"id": "verify_cross_sync", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Independent state verification on both systems"}
                ]
            },
            permissions=["api:call", "mcp:invoke", "slack:post"],
            expected_outcomes=["Data synced across API and MCP", "Notification dispatched", "Both endpoints verified"],
            compensation_strategy="Issue compensation webhook to reverse remote state",
            verification_spec={"postcondition": "dual_system_state_identical"},
            license=LicenseType.APACHE_2_0
        ))

        # 9. Lead Research and CRM Updates
        self.register_template(WorkflowTemplate(
            template_id="tmpl_crm_lead_lifecycle",
            name="Lead Research & Governed CRM Update",
            version="1.0.0",
            category="Sales",
            purpose="Enrich inbound lead data, verify consent, update SuiteCRM pipeline, and notify sales team.",
            required_integrations=["conn_suitecrm_sales", "conn_matrix_synapse_comms"],
            inputs_schema={
                "lead_name": {"type": "string", "required": True},
                "email": {"type": "string", "required": True},
                "deal_value": {"type": "number", "default": 25000.0}
            },
            workflow_spec={
                "id": "wf_crm_lead_lifecycle",
                "namespace": "ura.sales",
                "tasks": [
                    {"id": "check_lead_duplicates", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Check SuiteCRM duplicates"},
                    {"id": "create_suitecrm_lead", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Create qualified lead in SuiteCRM"},
                    {"id": "notify_sales_room", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Notify Matrix sales room"}
                ]
            },
            permissions=["crm:leads", "matrix:send"],
            expected_outcomes=["Lead created with verified consent", "Sales notification dispatched"],
            compensation_strategy="Archive created lead in CRM",
            verification_spec={"postcondition": "lead_record_persisted_in_crm"},
            license=LicenseType.APACHE_2_0
        ))

        # 10. Customer Support Triage and Resolution
        self.register_template(WorkflowTemplate(
            template_id="tmpl_support_ticket_resolution",
            name="Customer Support Triage & SLA Resolution",
            version="1.0.0",
            category="Support",
            purpose="Ingest support ticket from Zammad, match against OpenSearch knowledge base, draft resolution, and track SLA.",
            required_integrations=["conn_zammad_glpi_support", "conn_opensearch_qdrant"],
            inputs_schema={
                "subject": {"type": "string", "required": True},
                "customer_email": {"type": "string", "required": True},
                "priority": {"type": "string", "default": "NORMAL"}
            },
            workflow_spec={
                "id": "wf_support_ticket_resolution",
                "namespace": "ura.support",
                "tasks": [
                    {"id": "ingest_zammad_ticket", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Create ticket in Zammad"},
                    {"id": "search_knowledge_base", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Query OpenSearch documentation"},
                    {"id": "evaluate_sla_status", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Calculate remaining SLA hours"}
                ]
            },
            permissions=["support:tickets", "search:query"],
            expected_outcomes=["Ticket categorized", "Knowledge base searched", "SLA tracking active"],
            compensation_strategy="Escalate ticket to human support lead",
            verification_spec={"postcondition": "ticket_status_open_with_sla"},
            license=LicenseType.APACHE_2_0
        ))

        # 11. Document Extraction and Review
        self.register_template(WorkflowTemplate(
            template_id="tmpl_document_ingestion_review",
            name="Document Ingestion, OCR & Policy Review",
            version="1.0.0",
            category="Operations",
            purpose="Extract text from PDF/image documents via Apache Tika/Tesseract, scan archive safety, and summarize with LiteLLM.",
            required_integrations=["conn_apache_tika_ocr", "conn_litellm_gateway"],
            inputs_schema={
                "file_name": {"type": "string", "required": True},
                "content_base64": {"type": "string", "required": True}
            },
            workflow_spec={
                "id": "wf_document_ingestion_review",
                "namespace": "ura.operations",
                "tasks": [
                    {"id": "tika_extract_text", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Extract text via Apache Tika"},
                    {"id": "verify_provenance_digest", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Compute SHA-256 provenance digest"},
                    {"id": "summarize_document", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Summarize with LiteLLM gateway"}
                ]
            },
            permissions=["document:extract", "llm:invoke"],
            expected_outcomes=["Text and metadata extracted", "Provenance hash bound to ledger", "Summary generated"],
            compensation_strategy="Quarantine file and delete extracted text",
            verification_spec={"postcondition": "sha256_provenance_verified"},
            license=LicenseType.APACHE_2_0
        ))

        # 12. Purchase Request Preparation
        self.register_template(WorkflowTemplate(
            template_id="tmpl_erp_purchase_order_preparation",
            name="ERP Purchase Request & Approval Flow",
            version="1.0.0",
            category="Finance",
            purpose="Prepare purchase order in ERPNext, check supplier verification, gate behind executive approval, and submit.",
            required_integrations=["conn_erpnext_records"],
            inputs_schema={
                "supplier_id": {"type": "string", "required": True},
                "amount": {"type": "number", "required": True},
                "item_code": {"type": "string", "default": "SRV-COMPUTE-UNIT"}
            },
            workflow_spec={
                "id": "wf_erp_purchase_order",
                "namespace": "ura.finance",
                "tasks": [
                    {"id": "verify_supplier_status", "type": "io.kestra.plugin.zonata.connector.Call", "connector_id": "conn_erpnext_records", "action": "get_supplier", "description": "Check supplier tax and verification status"},
                    {"id": "executive_approval_gate", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Executive approval gate for PO > $1,000"},
                    {"id": "create_erpnext_po", "type": "io.kestra.plugin.zonata.connector.Call", "connector_id": "conn_erpnext_records", "action": "create_purchase_order", "description": "Submit purchase order to ERPNext"}
                ]
            },
            permissions=["erp:read", "erp:write", "approval:executive"],
            expected_outcomes=["Supplier verified", "Executive approval confirmed", "ERPNext PO submitted with transaction ID"],
            compensation_strategy="Cancel purchase order in ERPNext",
            verification_spec={"postcondition": "external_transaction_id_recorded"},
            license=LicenseType.APACHE_2_0
        ))

        # 13. Invoice Reconciliation
        self.register_template(WorkflowTemplate(
            template_id="tmpl_erp_invoice_reconciliation",
            name="Three-Way Invoice Reconciliation",
            version="1.0.0",
            category="Finance",
            purpose="Reconcile supplier invoice against ERPNext purchase order lines and receiving reports (three-way match).",
            required_integrations=["conn_erpnext_records", "conn_apache_tika_ocr"],
            inputs_schema={
                "invoice_id": {"type": "string", "required": True},
                "po_number": {"type": "string", "required": True}
            },
            workflow_spec={
                "id": "wf_invoice_reconciliation",
                "namespace": "ura.finance",
                "tasks": [
                    {"id": "fetch_po_details", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Fetch PO from ERPNext"},
                    {"id": "reconcile_match", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Perform three-way match reconciliation"},
                    {"id": "record_match_evidence", "type": "io.kestra.plugin.zonata.verify.Postcondition", "description": "Seals zero-variance evidence"}
                ]
            },
            permissions=["erp:read", "erp:write"],
            expected_outcomes=["Three-way match confirmed", "Zero variance verified", "Audit record created"],
            compensation_strategy="Flag invoice for manual audit review",
            verification_spec={"postcondition": "three_way_match_verified"},
            license=LicenseType.APACHE_2_0
        ))

        # 14. Inventory Reporting
        self.register_template(WorkflowTemplate(
            template_id="tmpl_inventory_audit_report",
            name="Enterprise Inventory Balance & Audit",
            version="1.0.0",
            category="SupplyChain",
            purpose="Query inventory levels across warehouses via ERPNext and compute turnover metrics via Superset analytics.",
            required_integrations=["conn_erpnext_records", "conn_superset_dbt_analytics"],
            inputs_schema={
                "warehouse": {"type": "string", "default": "Primary Datacenter"},
                "item_code": {"type": "string", "default": "SRV-COMPUTE-UNIT"}
            },
            workflow_spec={
                "id": "wf_inventory_audit",
                "namespace": "ura.supplychain",
                "tasks": [
                    {"id": "query_erp_inventory", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Query stock balance from ERPNext"},
                    {"id": "calculate_turnover", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Calculate inventory turnover via Superset"}
                ]
            },
            permissions=["erp:read", "analytics:read"],
            expected_outcomes=["Stock balance verified", "Turnover metric computed", "Audit report recorded"],
            compensation_strategy="Log inventory query exception",
            verification_spec={"postcondition": "stock_balance_verified"},
            license=LicenseType.APACHE_2_0
        ))

        # 15. Meeting Coordination
        self.register_template(WorkflowTemplate(
            template_id="tmpl_executive_meeting_coordination",
            name="Executive Meeting Scheduling & Protocol Dispatch",
            version="1.0.0",
            category="Executive",
            purpose="Check calendar availability via Nextcloud CalDAV, schedule meeting, and dispatch Matrix notifications.",
            required_integrations=["conn_nextcloud_collaboration", "conn_matrix_synapse_comms"],
            inputs_schema={
                "event_title": {"type": "string", "required": True},
                "start_time": {"type": "string", "required": True},
                "recipients": {"type": "array", "default": ["ceo@zonata.internal"]}
            },
            workflow_spec={
                "id": "wf_meeting_coordination",
                "namespace": "ura.executive",
                "tasks": [
                    {"id": "check_free_busy", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Check attendee free/busy status in Nextcloud"},
                    {"id": "create_caldav_event", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Create calendar event in Nextcloud"},
                    {"id": "send_matrix_invite", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Send meeting confirmation via Matrix"}
                ]
            },
            permissions=["calendar:events", "matrix:send"],
            expected_outcomes=["Free/busy verified", "Calendar event created", "Notifications dispatched"],
            compensation_strategy="Cancel calendar event and notify attendees",
            verification_spec={"postcondition": "calendar_event_confirmed"},
            license=LicenseType.APACHE_2_0
        ))

        # 16. Enterprise Knowledge Research
        self.register_template(WorkflowTemplate(
            template_id="tmpl_enterprise_search_research",
            name="Enterprise Search & Knowledge Synthesis",
            version="1.0.0",
            category="Research",
            purpose="Execute permission-aware hybrid search in OpenSearch/Qdrant, sanitize retrieved passages, and synthesize briefing with LiteLLM.",
            required_integrations=["conn_opensearch_qdrant", "conn_litellm_gateway"],
            inputs_schema={
                "query": {"type": "string", "required": True},
                "collection": {"type": "string", "default": "corporate_kb"}
            },
            workflow_spec={
                "id": "wf_enterprise_search_research",
                "namespace": "ura.research",
                "tasks": [
                    {"id": "opensearch_query", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Query OpenSearch with tenant filtering"},
                    {"id": "sanitize_passages", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Screen retrieved passages for prompt injection"},
                    {"id": "synthesize_briefing", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Synthesize research briefing with LiteLLM"}
                ]
            },
            permissions=["search:query", "llm:invoke"],
            expected_outcomes=["Tenant-isolated search completed", "Prompt injections screened", "Briefing synthesized"],
            compensation_strategy="Return partial search results with caution notice",
            verification_spec={"postcondition": "passages_tenant_isolated_and_sanitized"},
            license=LicenseType.APACHE_2_0
        ))

        # 17. KPI Analysis and Report Generation
        self.register_template(WorkflowTemplate(
            template_id="tmpl_bi_kpi_analytics_report",
            name="Executive KPI Analytics & Provenance Report",
            version="1.0.0",
            category="Analytics",
            purpose="Execute governed SQL query via Superset, run dbt model transformations, verify metric calculation provenance, and seal report.",
            required_integrations=["conn_superset_dbt_analytics", "conn_meltano_sync"],
            inputs_schema={
                "metric_name": {"type": "string", "default": "MRR"},
                "sql_query": {"type": "string", "default": "SELECT SUM(amount) FROM revenue"}
            },
            workflow_spec={
                "id": "wf_bi_kpi_analytics_report",
                "namespace": "ura.analytics",
                "tasks": [
                    {"id": "validate_sql_safety", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Validate SQL read-only safety"},
                    {"id": "execute_kpi_analytics", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Compute KPI via Superset"},
                    {"id": "verify_provenance", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Verify calculation formula provenance"}
                ]
            },
            permissions=["analytics:read", "dbt:execute"],
            expected_outcomes=["SQL safety validated", "KPI calculated", "Calculation provenance bound to evidence ledger"],
            compensation_strategy="Mark KPI report as unverified draft",
            verification_spec={"postcondition": "metric_provenance_verified"},
            license=LicenseType.APACHE_2_0
        ))

        # 18. Security Incident Investigation
        self.register_template(WorkflowTemplate(
            template_id="tmpl_security_incident_investigation",
            name="Runtime Threat Investigation & Containment",
            version="1.0.0",
            category="Security",
            purpose="Ingest security alert from Falco/Wazuh, correlate threat to mission/tenant, trigger containment if critical, and open Matrix incident room.",
            required_integrations=["conn_falco_wazuh_security", "conn_matrix_synapse_comms"],
            inputs_schema={
                "severity": {"type": "string", "default": "HIGH"},
                "source_process": {"type": "string", "default": "sh"},
                "mission_id": {"type": "string", "required": True}
            },
            workflow_spec={
                "id": "wf_security_incident_investigation",
                "namespace": "ura.security",
                "tasks": [
                    {"id": "ingest_falco_event", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Ingest runtime security event"},
                    {"id": "correlate_mission", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Correlate threat with active mission"},
                    {"id": "create_matrix_incident_room", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Open Matrix incident response room"}
                ]
            },
            permissions=["security:events", "security:containment", "matrix:rooms"],
            expected_outcomes=["Threat correlated", "Incident room provisioned", "Containment policy evaluated"],
            compensation_strategy="Escalate incident to Chief Security Officer",
            verification_spec={"postcondition": "threat_logged_and_contained"},
            license=LicenseType.APACHE_2_0
        ))

        # 19. Approved Software Delivery Workflows
        self.register_template(WorkflowTemplate(
            template_id="tmpl_gitops_software_delivery",
            name="GitOps Controlled Delivery & Red-Team Gate",
            version="1.0.0",
            category="DevOps",
            purpose="Verify image signature via Argo CD, run promptfoo adversarial red-team suite, require managerial approval, and sync release.",
            required_integrations=["conn_argocd_gitops", "conn_promptfoo_eval", "conn_github_v3"],
            inputs_schema={
                "app_name": {"type": "string", "default": "zonata-production-cluster"},
                "target_revision": {"type": "string", "required": True},
                "image_digest": {"type": "string", "required": True}
            },
            workflow_spec={
                "id": "wf_gitops_software_delivery",
                "namespace": "ura.devops",
                "tasks": [
                    {"id": "verify_cosign_signature", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Verify container image signature and SLSA provenance"},
                    {"id": "run_promptfoo_tests", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Run promptfoo adversarial red-team suite"},
                    {"id": "release_approval_gate", "type": "io.kestra.plugin.zonata.approval.Gate", "description": "Managerial sign-off gate"},
                    {"id": "argocd_sync_release", "type": "io.kestra.plugin.zonata.connector.Call", "description": "Sync release to target environment via Argo CD"}
                ]
            },
            permissions=["gitops:sync", "eval:adversarial", "approval:executive"],
            expected_outcomes=["Image signature verified", "Zero adversarial vulnerabilities", "Controlled Argo CD sync"],
            compensation_strategy="Trigger Argo CD immediate release rollback",
            verification_spec={"postcondition": "argocd_sync_healthy_and_signed"},
            license=LicenseType.APACHE_2_0
        ))

    def register_template(self, template: WorkflowTemplate) -> bool:
        self._templates[template.template_id] = template
        return True

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        return self._templates.get(template_id)

    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        tmpls = list(self._templates.values())
        if category:
            tmpls = [t for t in tmpls if t.category.lower() == category.lower()]
        return [t.to_dict() for t in tmpls]

    def instantiate_template(
        self,
        template_id: str,
        user_inputs: Dict[str, Any],
        tenant_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Instantiates a template into a customized, executable workflow specification.
        """
        tmpl = self._templates.get(template_id)
        if not tmpl:
            raise KeyError(f"Template '{template_id}' not found in catalog.")

        # Validate inputs against schema
        for field_name, rules in tmpl.inputs_schema.items():
            if rules.get("required") and field_name not in user_inputs:
                raise ValueError(f"Missing required parameter '{field_name}' for template '{template_id}'.")

        customized_spec = dict(tmpl.workflow_spec)
        # Second-resolution timestamps collide when the same template is
        # instantiated twice within one second (e.g. two acceptance tests),
        # which surfaces as a UNIQUE violation on automation_workflows.
        customized_spec["id"] = (
            f"{tmpl.workflow_spec['id']}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        )
        customized_spec["labels"] = {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "instantiated_from": template_id,
            "created_at": str(time.time())
        }
        customized_spec["inputs"] = user_inputs

        return {
            "workflow_id": customized_spec["id"],
            "name": f"{tmpl.name} (Instance)",
            "version": 1,
            "category": tmpl.category,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "workflow_spec": customized_spec,
            "template_id": template_id,
            "verification_spec": tmpl.verification_spec,
            "created_at": time.time()
        }


# Singleton catalog instance
template_catalog = TemplateCatalog()
