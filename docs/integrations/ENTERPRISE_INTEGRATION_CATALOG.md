# ZONATA / URA — Enterprise Integration Catalog

This catalog documents the 18 vetted connectors and 19 production workflow templates available in the ZONATA Universal Automation Fabric.

---

## 1. Connectors Catalog

### Baseline Integrations
1. **`conn_github_v3`**: GitHub Enterprise API (MIT)
   - Operations: `create_issue`, `get_repo`, `create_pull_request`, `run_workflow`
   - Scopes: `repo`, `workflow` | RPM: 120 | Timeout: 30s | Risk: `CONFIRM`
2. **`conn_slack_events`**: Slack Enterprise Messaging (MIT)
   - Operations: `send_message`, `post_webhook`, `add_reaction`
   - Scopes: `chat:write`, `channels:read` | RPM: 60 | Timeout: 15s | Risk: `SAFE`
3. **`conn_zonata_mcp_local`**: Sovereign MCP Tool Gateway (Apache-2.0)
   - Operations: `query_knowledge`, `execute_terminal_step`, `browser_snapshot`
   - Scopes: `mcp:invoke` | RPM: 300 | Timeout: 60s | Risk: `CONFIRM`

### Enterprise Capability Integrations
4. **`conn_apache_camel`**: Apache Camel Enterprise Integration (Apache-2.0, v4.8.0)
   - Operations: `route_message`, `content_based_route`, `transform_payload`, `idempotent_consume`, `wire_tap`
   - Scopes: `camel:route`, `messaging:publish` | RPM: 300 | Timeout: 30s | Risk: `CONFIRM`
5. **`conn_litellm_gateway`**: LiteLLM / vLLM Model Gateway (MIT / Apache-2.0, v1.48.0)
   - Operations: `chat_completion`, `route_inference`, `calculate_token_cost`, `enforce_budget_ceiling`, `redact_sensitive_prompt`
   - Scopes: `llm:invoke`, `model:route` | RPM: 240 | Timeout: 60s | Risk: `SAFE`
6. **`conn_apache_tika_ocr`**: Apache Tika & Tesseract Document Extraction (Apache-2.0, v2.9.2)
   - Operations: `extract_text_and_metadata`, `ocr_image_document`, `detect_mime_type`, `scan_archive_safety`, `compute_provenance_digest`
   - Scopes: `document:extract`, `file:scan` | RPM: 120 | Timeout: 45s | Risk: `SAFE`
7. **`conn_opensearch_qdrant`**: OpenSearch & Qdrant Hybrid Retrieval (Apache-2.0, v2.17.0)
   - Operations: `index_document`, `search_documents`, `vector_search`, `verify_document_access`, `sanitize_retrieved_passage`
   - Scopes: `search:query`, `search:index` | RPM: 300 | Timeout: 20s | Risk: `SAFE`
8. **`conn_erpnext_records`**: ERPNext Governed Business Records (MIT API, v15.38.0)
   - Operations: `get_customer`, `get_supplier`, `list_purchase_orders`, `create_purchase_order`, `reconcile_invoice`, `get_inventory_balance`
   - Scopes: `erp:read`, `erp:write` | RPM: 60 | Timeout: 30s | Risk: `CRITICAL`
9. **`conn_suitecrm_sales`**: SuiteCRM Governed Sales & Pipeline (Apache-2.0 Client, v8.6.0)
   - Operations: `create_lead`, `get_lead`, `update_opportunity`, `check_duplicates`, `get_pipeline_summary`
   - Scopes: `crm:leads`, `crm:opportunities` | RPM: 90 | Timeout: 25s | Risk: `CONFIRM`
10. **`conn_zammad_glpi_support`**: Zammad & GLPI Support & ITSM (Apache-2.0 Client, v6.3.1)
    - Operations: `create_ticket`, `get_ticket`, `update_ticket_status`, `calculate_sla_status`, `escalate_ticket`
    - Scopes: `support:tickets`, `support:admin` | RPM: 120 | Timeout: 20s | Risk: `CONFIRM`
11. **`conn_nextcloud_collaboration`**: Nextcloud & Open Protocols (Apache-2.0 Client, v29.0.4)
    - Operations: `upload_file`, `get_file_metadata`, `create_calendar_event`, `check_calendar_availability`, `send_notification_email`
    - Scopes: `files:write`, `calendar:events`, `mail:send` | RPM: 100 | Timeout: 30s | Risk: `CONFIRM`
12. **`conn_superset_dbt_analytics`**: Apache Superset & dbt Core Analytics (Apache-2.0, v4.0.2)
    - Operations: `execute_kpi_query`, `run_dbt_model`, `get_dashboard_metrics`, `validate_sql_safety`, `verify_metric_provenance`
    - Scopes: `analytics:read`, `dbt:execute` | RPM: 150 | Timeout: 45s | Risk: `SAFE`
13. **`conn_meltano_sync`**: Meltano Incremental Data Synchronization (MIT, v3.5.0)
    - Operations: `sync_stream`, `get_sync_status`, `checkpoint_stream`, `validate_schema`, `log_dead_letter_record`
    - Scopes: `data:sync`, `pipelines:run` | RPM: 60 | Timeout: 90s | Risk: `CONFIRM`
14. **`conn_falco_wazuh_security`**: Falco & Wazuh Runtime Threat Monitoring (Apache-2.0, v0.38.1)
    - Operations: `ingest_security_event`, `list_active_alerts`, `trigger_containment_policy`, `correlate_mission_threat`
    - Scopes: `security:events`, `security:containment` | RPM: 300 | Timeout: 15s | Risk: `CRITICAL`
15. **`conn_argocd_gitops`**: Argo CD GitOps Delivery & Sync (Apache-2.0, v2.12.0)
    - Operations: `get_app_sync_status`, `sync_application`, `rollback_release`, `verify_image_signature`
    - Scopes: `gitops:sync`, `gitops:rollback` | RPM: 60 | Timeout: 60s | Risk: `DANGEROUS`
16. **`conn_promptfoo_eval`**: promptfoo Adversarial AI Evaluation (MIT, v0.82.0)
    - Operations: `run_adversarial_suite`, `eval_prompt_injection`, `verify_quality_threshold`, `generate_eval_report`
    - Scopes: `eval:adversarial`, `eval:quality` | RPM: 120 | Timeout: 60s | Risk: `SAFE`
17. **`conn_matrix_synapse_comms`**: Matrix Synapse Communications (Apache-2.0 Client, v1.111.0)
    - Operations: `send_room_message`, `create_incident_room`, `send_approval_prompt`, `get_message_receipt`
    - Scopes: `matrix:send`, `matrix:rooms` | RPM: 180 | Timeout: 15s | Risk: `SAFE`
18. **`conn_openfeature_flags`**: OpenFeature Governed Feature Flags (Apache-2.0, v0.7.0)
    - Operations: `evaluate_flag`, `set_tenant_flag`, `get_all_flags`, `rollback_flag`
    - Scopes: `flags:evaluate`, `flags:admin` | RPM: 300 | Timeout: 10s | Risk: `CONFIRM`

---

## 2. Production Workflow Templates Catalog

1. `tmpl_software_issue_resolution`: Software defect investigation and code review PR.
2. `tmpl_cicd_deployment_pipeline`: Container build, staging verification, executive sign-off, and production deployment.
3. `tmpl_sales_lead_qualification`: Inbound lead intake, scoring, CRM synchronization, and outreach dispatch.
4. `tmpl_executive_meeting_prep`: Agenda synthesis, briefing generation, and executive task assignment.
5. `tmpl_cloud_resource_provisioning`: Infrastructure validation, resource provisioning, and health probing.
6. `tmpl_data_reconciliation_report`: Multi-source data ingestion, diff calculation, and Merkle audit report.
7. `tmpl_incident_recovery`: Anomaly detection, circuit breaker isolation, and automated failover.
8. `tmpl_cross_system_orchestration`: Cross-system API & MCP data synchronization.
9. `tmpl_crm_lead_lifecycle`: Governed lead enrichment, consent verification, SuiteCRM pipeline update, and Matrix notification.
10. `tmpl_support_ticket_resolution`: Zammad support ticket triage, OpenSearch knowledge retrieval, and SLA monitoring.
11. `tmpl_document_ingestion_review`: Document text extraction via Apache Tika, archive bomb check, and LiteLLM summary.
12. `tmpl_erp_purchase_order_preparation`: Supplier verification, approval gate, and ERPNext purchase order creation.
13. `tmpl_erp_invoice_reconciliation`: Three-way matching between ERPNext PO lines, receiving slips, and supplier invoices.
14. `tmpl_inventory_audit_report`: Stock balance queries across warehouses and turnover analytics via Superset.
15. `tmpl_executive_meeting_coordination`: Nextcloud CalDAV availability check, event creation, and Matrix invitations.
16. `tmpl_enterprise_search_research`: Permission-aware OpenSearch hybrid search, prompt injection screening, and research briefing.
17. `tmpl_bi_kpi_analytics_report`: Parameterized analytical SQL query execution, dbt model transformations, and metric provenance.
18. `tmpl_security_incident_investigation`: Falco threat ingestion, mission correlation, containment signaling, and incident room creation.
19. `tmpl_gitops_software_delivery`: Argo CD image signature verification, promptfoo adversarial red-teaming, and controlled deployment.
