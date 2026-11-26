# audit_scan — /data/data/com.termux/files/home/AI-robo-assistant-saas

**This is a map of where to look, not a verdict.** Mentions are not implementations; stub markers are not proof of stubs.

- Files by extension: {'.py': 635, '.md': 455, '.json': 108, '.js': 75, '.sql': 24, '.tf': 21, '.yaml': 19, '.ts': 14, '.yml': 13, '.sh': 7, '': 1, '.ini': 1, '.txt': 1}
- Frameworks detected in manifests: ['pytest']
- API version prefixes seen in code: {'v8': 269, 'v1': 222, 'v2': 46}  (use the **highest in active use** for the factory namespace)
- Routes found: 11 · tables found: 194 · test files: 164 · migration files: 24

## Component mentions (files / occurrences)

| component | files | occurrences | top file |
|---|---|---|---|
| company_kernel | 28 | 32 | docs/architecture/ZONATA_COWORKER_ARCHITECTURE.md |
| constitution | 321 | 662 | core/v8_api_handler.py |
| policy_engine | 129 | 216 | tests/test_universal_automation_fabric_qualification.py |
| authority_gateway | 69 | 101 | docs/qualification/ZONATA_NON_DESTRUCTIVE_INTEGRATION_AND_ACCEPTANCE_REPORT.md |
| approval_engine | 81 | 118 | core/aic_organization_constitution.py |
| evidence_ledger | 440 | 1398 | core/coworker/evidence_reporting.py |
| kill_switch | 300 | 1575 | api_server.py |
| ai_ceo | 381 | 1404 | web/app.js |
| agency_swarm | 56 | 130 | core/aic_ceo_constitution.py |
| langgraph | 67 | 203 | api_server.py |
| letta | 42 | 63 | zonata/hal_multimodal_adapter.py |
| hal | 35 | 127 | core/multimodal_capability_runtime.py |
| mcp | 188 | 859 | web/mcp_workspace.js |
| a2a | 111 | 481 | web/agent_network_workspace.js |
| openhands | 133 | 776 | core/openhands_execution_runtime.py |
| browser_use | 72 | 205 | zonata/browser_use_adapter.py |
| terminal | 81 | 251 | docs/reports/ZONATA_UNIVERSAL_LINUX_TERMINAL_FABRIC_REPORT.md |
| automation_fabric | 72 | 292 | api_server.py |
| temporal | 106 | 331 | api_server.py |
| vault | 124 | 290 | docs/qualification/ZONATA_NON_DESTRUCTIVE_INTEGRATION_AND_ACCEPTANCE_REPORT.md |
| keycloak | 18 | 102 | core/keycloak_idp.py |
| openfga | 18 | 78 | tests/test_saas_platform_integration.py |
| nats | 36 | 180 | tests/test_saas_failure_injection_and_qualification.py |
| s3_minio | 48 | 147 | k8s/14-minio-storage.yaml |
| otel | 39 | 120 | core/opentelemetry_engine.py |
| langfuse | 30 | 187 | tests/test_ai_ceo_intelligence_enhancement_qualification.py |
| posthog | 13 | 61 | core/posthog_analytics.py |
| model_gateway | 141 | 396 | core/coworker/local_inference_adapter.py |
| rls_tenant | 643 | 8874 | api_server.py |
| agent_factory_existing | 104 | 345 | api_server.py |
| workforce | 605 | 4816 | core/workforce_architecture.py |
| dlp | 260 | 884 | core/model_data_firewall.py |

## Likely stubs / mocks / placeholders (highest density first)

| score | file | markers |
|---|---|---|
| 78 | web/company_workspace.js | {'stub_word': 77, 'scripted': 1} |
| 31 | core/db.py | {'pass_body': 31} |
| 22 | web/app.js | {'todo': 2, 'stub_word': 20} |
| 21 | core/coworker/runtimes/base_runtime.py | {'pass_body': 21} |
| 21 | api_server.py | {'stub_word': 1, 'pass_body': 20} |
| 17 | core/browser_use_execution_runtime.py | {'pass_body': 17} |
| 15 | core/coworker/universal_worker_contract.py | {'pass_body': 15} |
| 15 | core/cognitive_model_provider.py | {'pass_body': 15} |
| 14 | core/mcp_interoperability_runtime.py | {'not_implemented': 4, 'pass_body': 10} |
| 14 | core/coworker/provider_base.py | {'pass_body': 14} |
| 14 | core/automation_fabric/fabric.py | {'pass_body': 14} |
| 13 | core/workforce_runtime.py | {'pass_body': 13} |
| 12 | web/ai_ceo_workspace.js | {'stub_word': 12} |
| 10 | core/universal_terminal/runtime_adapters.py | {'pass_body': 10} |
| 10 | core/database_engine.py | {'pass_body': 10} |
| 9 | core/a2a_interoperability_runtime.py | {'not_implemented': 3, 'stub_word': 4, 'pass_body': 2} |
| 8 | core/settings_service.py | {'stub_word': 1, 'pass_body': 7} |
| 8 | core/saas_billing.py | {'pass_body': 8} |
| 8 | core/auth.py | {'pass_body': 8} |
| 7 | web/ura_assistant.js | {'stub_word': 4, 'scripted': 3} |
| 7 | web/company_setup_existing.js | {'stub_word': 7} |
| 7 | tests/schema_bootstrap.py | {'pass_body': 7} |
| 7 | core/nango_integration_runtime.py | {'not_implemented': 5, 'pass_body': 2} |
| 7 | core/coworker/runtime_supervisor.py | {'pass_body': 7} |
| 7 | core/ceo_chat.py | {'pass_body': 7} |

## Tables detected

a2a_agents, a2a_artifacts, a2a_messages, a2a_published_agents, a2a_security_events, a2a_skills, a2a_tasks, action_approval_nonces, active_sessions, agent_evaluation_runs, agent_packages, ai_ceo_decisions, ai_ceo_meeting_transcripts, ai_ceo_meetings, approvals, arena_decisions, async_command_queue, auth_credentials, auth_rate_limits, auth_revoked_tokens, billing_webhook_events, browser_actions, browser_approvals, browser_artifacts, browser_events, browser_executions, browser_runtimes, browser_security_events, browser_sessions, business_causality_chains, business_intelligence_items, chief_of_staff_items, companies, company_admin_grants, company_audit_events, company_build_runs, company_deletion_requests, company_drafts, company_files, company_knowledge, company_legal_items, company_processes, corporate_data_objects, corporate_objectives, coworker_tasks, credential_handles, crm_customers, crm_deals, data_sources, department_objectives, departments, disaster_recovery_manifests, employee_performance_records, employees, enterprise_budget_reservations, enterprise_budgets, enterprise_events, executive_approval_queue, executive_council_debates, executive_council_roles, executive_decision_evidence, executive_decisions, executive_incidents, executive_meetings, executive_observations, executive_opportunities, executive_policy_rules, executive_reports, executive_resource_allocations, executive_risks, executive_state, external_connections, external_idp_directory, governed_agents, governed_memory_records, governed_tools, host_capabilities, host_execution_receipts, hosts, immutable_agent_packages, installed_applications, knowledge_index_chunks, lineage_edges, lineage_nodes, mcp_executions, mcp_gateway_invocations, mcp_prompts, mcp_published_capabilities, mcp_resources, mcp_security_events, mcp_servers, mcp_tasks, mcp_tools, mission_tasks, missions, multimodal_artifacts, multimodal_capabilities, multimodal_execution_sessions, multimodal_observations, nango_capabilities, nango_connections, nango_executions, nango_providers, nango_rate_limits, nango_reconciliations, nango_runtimes, nango_security_events, nango_sync_jobs, nango_sync_records, nango_webhooks, openhands_approvals, openhands_artifacts, openhands_commands, openhands_events, openhands_executions, openhands_runtimes, openhands_security_events, openhands_workspaces, optimistic_lock_registry, organization_edges, organization_nodes, organizational_memory, permissions, production_audit_logs, reconciliation_receipts, role_permissions, roles, sales_interactions, sales_leads, schema_migrations, secrets, security_incidents, settings_approvals, settings_audit, settings_environments, settings_presets, settings_revision, settings_values, settings_values_tenant_keys, skill_runs, stateful_agent_identities, stateful_conversation_sessions, stateful_conversation_turns, stateful_memory_conflicts, stateful_memory_records, strategic_plans, strategic_priorities, strategy_versions, supervisor_heartbeats, system_plugins, temporal_activity_executions, temporal_approvals, temporal_compensations, temporal_reconciliations, temporal_runtimes, temporal_schedules, temporal_security_events, temporal_task_queues, temporal_workers, temporal_workflow_events, temporal_workflows, tenant_agent_quotas, tenant_concurrency_leases, tenant_invoices, tenant_isolation_audit, tenant_rate_limits, tenant_resource_quotas, tenant_subscriptions, tenants, tool_packages, transactional_outbox, universal_schedules, unknown_outcomes, usage_records, user_company_roles, user_two_step, users, voice_sessions, workflow_approvals, workflow_checkpoints, workflow_events, workflow_resource_locks, workflow_runs, workflows, workforce_scheduler_queue, zonata_competitor_profiles, zonata_discovery_sessions, zonata_facts, zonata_health_indicators, zonata_interviews, zonata_kg_edges, zonata_kg_nodes, zonata_org_blueprints, zonata_workforce_members

## Manifests

- Dockerfile
- package.json
- render.yaml
- requirements.txt
