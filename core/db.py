"""
RoboAssistant Company OS 1.0 — Normalized Relational Database Engine
Production SQLite engine providing tenant isolation, schema migrations,
and relational persistence for all Company OS entities.
"""

import sqlite3
import os
import time
import json
from typing import Dict, List, Optional, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage/roboassistant.db")

SCHEMA_SQL = """
-- 1. Tenants & Organizations
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'ENTERPRISE',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    metadata JSON
);

-- 2. Users & IAM
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'OWNER', -- OWNER, EXECUTIVE, MANAGER, OBSERVER, AUDITOR
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 3. Companies & Operating Contexts
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'IN',
    industry TEXT NOT NULL,
    company_type TEXT NOT NULL, -- NEW, EXISTING
    status TEXT NOT NULL DEFAULT 'OPERATIONAL', -- DRAFT, ONBOARDING, OPERATIONAL, ATTENTION, SUSPENDED
    currency TEXT NOT NULL DEFAULT '₹',
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    revenue REAL NOT NULL DEFAULT 0.0,
    cost REAL NOT NULL DEFAULT 0.0,
    contribution REAL NOT NULL DEFAULT 0.0,
    understanding_pct REAL NOT NULL DEFAULT 0.0,
    operating_rules JSON,
    baseline_summary JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_companies_tenant ON companies(tenant_id);

-- 4. Departments & Control Units (CUs)
CREATE TABLE IF NOT EXISTS departments (
    department_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    manager_agent_id TEXT,
    budget_limit REAL NOT NULL DEFAULT 0.0,
    spending_limit REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_depts_company ON departments(company_id);

-- 5. AI Workforce & Employment Contracts
CREATE TABLE IF NOT EXISTS employees (
    agent_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    department_id TEXT,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT NOT NULL,
    manager TEXT NOT NULL DEFAULT 'AI CEO',
    responsibilities JSON,
    objectives JSON,
    allowed_tools JSON,
    allowed_hosts JSON,
    data_access JSON,
    budget_limit REAL NOT NULL DEFAULT 0.0,
    spending_limit REAL NOT NULL DEFAULT 0.0,
    authority_ceiling TEXT NOT NULL DEFAULT 'AUTOMATIC_IDEMPOTENT',
    decision_authority JSON,
    forbidden_actions JSON,
    working_state TEXT NOT NULL DEFAULT 'ACTIVE',
    kpis JSON,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    cost_incurred REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_emp_company ON employees(company_id);
CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees(department_id);

-- 6. Missions & Business Outcomes
CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    department_id TEXT,
    tenant_id TEXT NOT NULL,
    title TEXT NOT NULL,
    owner_agent TEXT NOT NULL,
    department TEXT NOT NULL,
    target_outcome TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DISCOVER',
    progress INTEGER NOT NULL DEFAULT 0,
    kpis JSON,
    financials JSON,
    expected_outcome TEXT,
    actual_outcome TEXT,
    verified_outcome TEXT,
    outcome_status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, VERIFIED_ACHIEVED, VERIFIED_PARTIAL, FAILED
    started_at REAL NOT NULL,
    completed_at REAL,
    verification_summary TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_missions_company ON missions(company_id);

-- 7. First-Class Approvals
CREATE TABLE IF NOT EXISTS approvals (
    request_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    agent_id TEXT NOT NULL,
    action_desc TEXT NOT NULL,
    reason TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    consequence TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
    approver_user_id TEXT,
    signed_grant_hash TEXT,
    requested_at REAL NOT NULL,
    decided_at REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approvals_company ON approvals(company_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

-- 8. Data Sources & Ingestion
CREATE TABLE IF NOT EXISTS data_sources (
    source_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- PMS, ERP, CRM, POS, API, DB, FILE
    connection_method TEXT NOT NULL,
    permission_level TEXT NOT NULL DEFAULT 'READ_ONLY_VISIBILITY',
    trust_score REAL NOT NULL DEFAULT 1.0,
    freshness TEXT,
    health TEXT NOT NULL DEFAULT 'GOOD',
    available_data JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 9. Company Truth & Knowledge Facts
CREATE TABLE IF NOT EXISTS company_knowledge (
    fact_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    category TEXT NOT NULL, -- IDENTITY, REVENUE_ENGINE, OPERATION, FINANCIAL, CUSTOMER
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_val TEXT NOT NULL,
    truth_state TEXT NOT NULL DEFAULT 'MEASURED', -- MEASURED, CALCULATED, ESTIMATED, AI_INFERRED, UNAVAILABLE, NOT_VERIFIED, CONFLICTED
    provenance_source TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_company ON company_knowledge(company_id);

-- 10. Opportunities & Operational Risks
CREATE TABLE IF NOT EXISTS business_intelligence_items (
    item_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    item_type TEXT NOT NULL, -- OPPORTUNITY, RISK
    title TEXT NOT NULL,
    evidence TEXT NOT NULL,
    potential_impact TEXT NOT NULL,
    severity_or_confidence REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'DISCOVERED', -- DISCOVERED, PROPOSED, APPROVED, MITIGATED, REJECTED
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 11. Multi-Tier Layered Organizational Memory
CREATE TABLE IF NOT EXISTS organizational_memory (
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    department_id TEXT,
    agent_id TEXT,
    mission_id TEXT,
    memory_tier TEXT NOT NULL, -- PLATFORM, COMPANY, DEPARTMENT, EMPLOYEE, MISSION
    memory_type TEXT NOT NULL, -- FACT, PREFERENCE, POLICY, DECISION, LESSON, OUTCOME
    content TEXT NOT NULL,
    provenance TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_scope ON organizational_memory(tenant_id, company_id, memory_tier);

-- 12. SaaS Metering & Usage Records
CREATE TABLE IF NOT EXISTS usage_records (
    record_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    agent_id TEXT,
    mission_id TEXT,
    model TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage_records(tenant_id);

-- 13. Executive Council & Dynamic Roles
CREATE TABLE IF NOT EXISTS executive_council_roles (
    role_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    role_type TEXT NOT NULL, -- CFO, COO, CTO, CMO, CRO, CHRO, CIO_DATA, RISK_OFFICER, CHIEF_OF_STAFF
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    current_stance TEXT,
    last_consulted_at REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_council_company ON executive_council_roles(company_id);

-- 14. Executive Council Debates & Challenge Loops
CREATE TABLE IF NOT EXISTS executive_council_debates (
    debate_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    proposal TEXT NOT NULL,
    challenger_role TEXT NOT NULL,
    counterargument TEXT NOT NULL,
    risk_analysis TEXT NOT NULL,
    consensus_outcome TEXT NOT NULL,
    timestamp REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 15. Chief of Staff Decision & Coordination Queue
CREATE TABLE IF NOT EXISTS chief_of_staff_items (
    item_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    item_type TEXT NOT NULL, -- INBOX, DECISION_QUEUE, CROSS_DEPT_CONFLICT, DEADLINE, BRIEFING
    title TEXT NOT NULL,
    details TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, URGENT
    status TEXT NOT NULL DEFAULT 'OPEN', -- OPEN, IN_REVIEW, RESOLVED, ESCALATED
    created_at REAL NOT NULL,
    resolved_at REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 16. Host Infrastructure & Registry
CREATE TABLE IF NOT EXISTS hosts (
    host_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    host_type TEXT NOT NULL, -- LINUX_CLOUD, WINDOWS_WORKSTATION, MACOS_STUDIO, ANDROID_HOST, IOS_REMOTE
    os_family TEXT NOT NULL,
    os_version TEXT NOT NULL,
    cpu_cores INTEGER NOT NULL DEFAULT 1,
    ram_mb INTEGER NOT NULL DEFAULT 1024,
    status TEXT NOT NULL DEFAULT 'ONLINE', -- ONLINE, BUSY, OFFLINE, QUARANTINED
    last_heartbeat REAL NOT NULL,
    security_posture TEXT NOT NULL DEFAULT 'SECURE',
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 17. Host Capabilities
CREATE TABLE IF NOT EXISTS host_capabilities (
    cap_id TEXT PRIMARY KEY,
    host_id TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    category TEXT NOT NULL, -- SCREEN, MOUSE, KEYBOARD, WINDOWS, FILES, PROCESS, BROWSER, INSTALLER
    authority_required TEXT NOT NULL DEFAULT 'AUTOMATIC_IDEMPOTENT',
    enabled INTEGER NOT NULL DEFAULT 1,
    verified_at REAL NOT NULL,
    FOREIGN KEY(host_id) REFERENCES hosts(host_id) ON DELETE CASCADE
);

-- 18. Host Execution Receipts
CREATE TABLE IF NOT EXISTS host_execution_receipts (
    receipt_id TEXT PRIMARY KEY,
    host_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL, -- SUCCESS, FAILED, BLOCKED
    exit_code INTEGER,
    stdout_sample TEXT,
    stderr_sample TEXT,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    sha256_hash TEXT NOT NULL,
    signature TEXT NOT NULL,
    timestamp REAL NOT NULL,
    FOREIGN KEY(host_id) REFERENCES hosts(host_id) ON DELETE CASCADE
);

-- 19. Installed Applications & Software Profiles
CREATE TABLE IF NOT EXISTS installed_applications (
    app_id TEXT PRIMARY KEY,
    host_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT,
    publisher TEXT,
    exec_path TEXT NOT NULL,
    automation_interfaces JSON, -- ["API", "CLI", "GUI", "BROWSER"]
    security_status TEXT NOT NULL DEFAULT 'VERIFIED_SAFE',
    discovered_at REAL NOT NULL,
    FOREIGN KEY(host_id) REFERENCES hosts(host_id) ON DELETE CASCADE
);

-- 20. Credential Handles (Secret-isolated)
CREATE TABLE IF NOT EXISTS credential_handles (
    handle_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    service_name TEXT NOT NULL,
    account_label TEXT NOT NULL,
    auth_type TEXT NOT NULL DEFAULT 'PASSWORD', -- PASSWORD, TOKEN, OAUTH, API_KEY
    mfa_required INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, REVOKED, EXPIRED, WAITING_FOR_OWNER
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 21. Active Application / Browser Sessions
CREATE TABLE IF NOT EXISTS active_sessions (
    session_id TEXT PRIMARY KEY,
    handle_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    session_type TEXT NOT NULL DEFAULT 'BROWSER', -- BROWSER, CLI, DESKTOP
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, TERMINATED
    expires_at REAL,
    created_at REAL NOT NULL,
    FOREIGN KEY(handle_id) REFERENCES credential_handles(handle_id) ON DELETE CASCADE,
    FOREIGN KEY(host_id) REFERENCES hosts(host_id) ON DELETE CASCADE
);

-- 22. Enterprise Continuous Events
CREATE TABLE IF NOT EXISTS enterprise_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- REVENUE_ANOMALY, COST_SPIKE, PAYMENT_FAILURE, LEAD_RECEIVED, CUSTOMER_COMPLAINT, SYSTEM_OUTAGE, INVENTORY_SHORTAGE, KPI_DEVIATION
    category TEXT NOT NULL, -- FINANCIAL, OPERATIONAL, CUSTOMER, TECHNICAL, SECURITY
    severity TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON NOT NULL,
    handled INTEGER NOT NULL DEFAULT 0,
    resulting_mission_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_company ON enterprise_events(company_id);

-- 23. Sales Leads & Opportunities
CREATE TABLE IF NOT EXISTS sales_leads (
    lead_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'WEB_CHAT', -- WHATSAPP, EMAIL, WEB_CHAT, CRM, PHONE
    intent TEXT NOT NULL,
    qualification_score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'NEW', -- NEW, QUALIFIED, NEGOTIATING, CONVERTED, LOST
    assigned_agent_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 24. Sales Interactions & Customer Dialogue
CREATE TABLE IF NOT EXISTS sales_interactions (
    interaction_id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    customer_message TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    discount_offered REAL NOT NULL DEFAULT 0.0,
    policy_checked INTEGER NOT NULL DEFAULT 1,
    converted INTEGER NOT NULL DEFAULT 0,
    timestamp REAL NOT NULL,
    FOREIGN KEY(lead_id) REFERENCES sales_leads(lead_id) ON DELETE CASCADE
);

-- 25. Voice AI Call Sessions
CREATE TABLE IF NOT EXISTS voice_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    caller_id TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'INBOUND', -- INBOUND, OUTBOUND
    call_state TEXT NOT NULL DEFAULT 'COMPLETED', -- INITIATED, ACTIVE, COMPLETED, DROPPED
    consent_given INTEGER NOT NULL DEFAULT 1,
    recording_authorized INTEGER NOT NULL DEFAULT 1,
    outcome TEXT NOT NULL DEFAULT 'PROCESSED',
    transcript JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 26. Interactive Executive Meetings
CREATE TABLE IF NOT EXISTS executive_meetings (
    meeting_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    meeting_type TEXT NOT NULL DEFAULT 'MORNING_OPERATING', -- MORNING_OPERATING, STRATEGIC_COUNCIL, EMERGENCY_REVIEW
    agenda JSON NOT NULL,
    discussion JSON NOT NULL,
    agreed_missions JSON NOT NULL,
    held_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 27. Business Causality Chains
CREATE TABLE IF NOT EXISTS business_causality_chains (
    chain_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    strategy_goal TEXT NOT NULL,
    mission_id TEXT NOT NULL,
    task_id TEXT,
    action_id TEXT,
    transaction_id TEXT,
    revenue_attributed REAL NOT NULL DEFAULT 0.0,
    cost_attributed REAL NOT NULL DEFAULT 0.0,
    verified_outcome TEXT NOT NULL DEFAULT 'PENDING_EVIDENCE', -- PENDING_EVIDENCE, VERIFIED_SUCCESS, FAILED_HYPOTHESIS
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 28. Employee Performance & Governance Tracking
CREATE TABLE IF NOT EXISTS employee_performance_records (
    record_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    missions_completed INTEGER NOT NULL DEFAULT 0,
    verification_rate REAL NOT NULL DEFAULT 1.0,
    failures INTEGER NOT NULL DEFAULT 0,
    avg_cost REAL NOT NULL DEFAULT 0.0,
    business_contribution REAL NOT NULL DEFAULT 0.0,
    recommendation TEXT NOT NULL DEFAULT 'CONTINUE_DEPLOYMENT',
    updated_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

-- 29. Zonata Discovery Sessions
CREATE TABLE IF NOT EXISTS zonata_discovery_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    completeness_score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS', -- IN_PROGRESS, READY_FOR_ORG, COMPLETED
    missing_info JSON,
    deferred_topics JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_discovery_company ON zonata_discovery_sessions(company_id);

-- 30. Zonata Epistemic Facts & Findings
CREATE TABLE IF NOT EXISTS zonata_facts (
    fact_id TEXT PRIMARY KEY,
    session_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value JSON NOT NULL,
    epistemic_state TEXT NOT NULL DEFAULT 'FACT', -- FACT, OBSERVATION, CALCULATION, ESTIMATE, PREDICTION, SIMULATION, UNVERIFIED, VERIFIED
    source TEXT NOT NULL,
    source_type TEXT NOT NULL, -- OWNER_INPUT, DOCUMENT, PMS, ERP, CRM, POS, PUBLIC_WEB, API, INFERRED
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_facts_company ON zonata_facts(company_id);
CREATE INDEX IF NOT EXISTS idx_zonata_facts_entity ON zonata_facts(entity_type, entity_id);

-- 31. Zonata Interview History
CREATE TABLE IF NOT EXISTS zonata_interviews (
    exchange_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    category TEXT NOT NULL,
    question_text TEXT NOT NULL,
    context_reason TEXT,
    answer_text TEXT,
    answer_type TEXT NOT NULL DEFAULT 'ANSWERED', -- ANSWERED, SKIPPED, NOT_AVAILABLE, ASK_LATER, BEST_EVIDENCE
    extracted_facts JSON,
    asked_at REAL NOT NULL,
    answered_at REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_interview_session ON zonata_interviews(session_id);

-- 32. Zonata Knowledge Graph Nodes
CREATE TABLE IF NOT EXISTS zonata_kg_nodes (
    node_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    properties JSON,
    epistemic_state TEXT NOT NULL DEFAULT 'FACT',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_kg_nodes ON zonata_kg_nodes(company_id, entity_type);

-- 33. Zonata Knowledge Graph Edges
CREATE TABLE IF NOT EXISTS zonata_kg_edges (
    edge_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    properties JSON,
    epistemic_state TEXT NOT NULL DEFAULT 'FACT',
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(source_node_id) REFERENCES zonata_kg_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY(target_node_id) REFERENCES zonata_kg_nodes(node_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_kg_edges ON zonata_kg_edges(company_id, source_node_id, target_node_id);

-- 34. Zonata Company Health Indicators
CREATE TABLE IF NOT EXISTS zonata_health_indicators (
    indicator_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value JSON NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'VERIFIED',
    trend TEXT NOT NULL DEFAULT 'STABLE',
    period TEXT,
    status TEXT NOT NULL DEFAULT 'HEALTHY',
    evaluated_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_health_company ON zonata_health_indicators(company_id);

-- 35. Zonata Dynamic Organization Blueprints
CREATE TABLE IF NOT EXISTS zonata_org_blueprints (
    blueprint_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    industry TEXT NOT NULL,
    rationale TEXT NOT NULL,
    executives JSON NOT NULL,
    departments JSON NOT NULL,
    workforce JSON NOT NULL,
    reporting_hierarchy JSON NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED', -- PROPOSED, APPROVED, ACTIVE
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_org_company ON zonata_org_blueprints(company_id);

-- 36. Zonata Dynamic Workforce Registry
CREATE TABLE IF NOT EXISTS zonata_workforce_members (
    agent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    blueprint_id TEXT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department_id TEXT NOT NULL,
    executive_role TEXT,
    mission_focus TEXT,
    responsibilities JSON,
    capabilities JSON,
    tools JSON,
    knowledge_sources JSON,
    model_policy JSON,
    budget_limit REAL NOT NULL DEFAULT 0.0,
    risk_class TEXT NOT NULL DEFAULT 'LOW',
    approval_policy JSON,
    kpis JSON,
    verification_policy JSON,
    working_hours TEXT,
    communication_channels JSON,
    lifecycle_state TEXT NOT NULL DEFAULT 'NEED_IDENTIFIED',
    certification JSON,
    authority_scope JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_wf_company ON zonata_workforce_members(company_id);

-- 37. Zonata Competitor Intelligence Profiles
CREATE TABLE IF NOT EXISTS zonata_competitor_profiles (
    competitor_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    website TEXT,
    products JSON,
    services JSON,
    public_pricing JSON,
    positioning TEXT,
    customer_sentiment TEXT,
    source TEXT NOT NULL DEFAULT 'PUBLIC_WEB',
    confidence REAL NOT NULL DEFAULT 0.9,
    discovered_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_zonata_comp_company ON zonata_competitor_profiles(company_id);

-- 38. Universal Schedules (SaaS-Wide Planning Layer)
CREATE TABLE IF NOT EXISTS universal_schedules (
    schedule_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    item_type TEXT NOT NULL, -- meeting, mission_milestone, deadline, process_run, budget_review, approval_deadline, coworker_task, ai_workforce_shift, customer_touchpoint, report_generation, reminder, maintenance, compliance_audit, desktop_automation, strategic_review
    start_time REAL NOT NULL,
    end_time REAL,
    recurrence TEXT NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, CRON
    priority TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, URGENT
    status TEXT NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, BLOCKED
    assigned_to TEXT,
    related_entity_type TEXT,
    related_entity_id TEXT,
    conflict_detected INTEGER NOT NULL DEFAULT 0,
    conflict_reason TEXT,
    metadata JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_schedules_company ON universal_schedules(company_id);
CREATE INDEX IF NOT EXISTS idx_schedules_time ON universal_schedules(start_time);
CREATE INDEX IF NOT EXISTS idx_schedules_type ON universal_schedules(item_type);

-- 39. AI CEO Meeting Sessions
CREATE TABLE IF NOT EXISTS ai_ceo_meetings (
    meeting_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    host_user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Ready', -- Ready, Live, Paused, Ended
    strategic_context TEXT,
    video_connected INTEGER NOT NULL DEFAULT 0,
    voice_connected INTEGER NOT NULL DEFAULT 0,
    text_connected INTEGER NOT NULL DEFAULT 1,
    summary TEXT,
    created_at REAL NOT NULL,
    ended_at REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ceo_meetings_company ON ai_ceo_meetings(company_id);
CREATE INDEX IF NOT EXISTS idx_ceo_meetings_status ON ai_ceo_meetings(status);

-- 40. AI CEO Meeting Transcripts
CREATE TABLE IF NOT EXISTS ai_ceo_meeting_transcripts (
    transcript_id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    speaker TEXT NOT NULL, -- HOST, AI CEO, SYSTEM
    mode TEXT NOT NULL DEFAULT 'TEXT', -- TEXT, VOICE, VIDEO, ACTION
    message TEXT NOT NULL,
    related_context TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(meeting_id) REFERENCES ai_ceo_meetings(meeting_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_meeting_transcripts ON ai_ceo_meeting_transcripts(meeting_id);

-- 41. AI CEO Strategic Decisions & Directives
CREATE TABLE IF NOT EXISTS ai_ceo_decisions (
    decision_id TEXT PRIMARY KEY,
    meeting_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED', -- PROPOSED, APPROVED, REJECTED, EXECUTED
    decision_type TEXT NOT NULL DEFAULT 'STRATEGIC', -- STRATEGIC, MISSION, APPROVAL, BUDGET, POLICY
    action_required TEXT,
    signed_grant_hash TEXT,
    created_at REAL NOT NULL,
    decided_at REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ceo_decisions_company ON ai_ceo_decisions(company_id);

-- 42. Floating Assistant Coworker Tasks
CREATE TABLE IF NOT EXISTS coworker_tasks (
    task_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    user_id TEXT NOT NULL,
    workspace_mode TEXT NOT NULL DEFAULT 'PERSONAL', -- PERSONAL, COMPANY
    prompt TEXT NOT NULL,
    target_outcome TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'INITIATED', -- INITIATED, PLANNING, AWAITING_APPROVAL, APPROVED, EXECUTING, OBSERVING, VERIFYING, COMPLETED, FAILED, REVERTED
    permission_tier TEXT NOT NULL DEFAULT 'SAFE_BROWSE', -- SAFE_BROWSE, DESKTOP_INPUT, FILE_WRITE, CREDENTIAL_ACCESS, FINANCIAL_ACTION
    approval_status TEXT NOT NULL DEFAULT 'AUTO', -- AUTO, PENDING, APPROVED, DENIED
    execution_log JSON,
    receipt_id TEXT,
    created_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_coworker_tasks_user ON coworker_tasks(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_coworker_tasks_status ON coworker_tasks(status);

-- 43. System Plugins Catalog & State
CREATE TABLE IF NOT EXISTS system_plugins (
    plugin_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- ANALYTICS, AUTOMATION, COMMUNICATION, SECURITY, DATA_INTELLIGENCE, STORAGE
    version TEXT NOT NULL,
    description TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'ZONATA Builtin',
    installed INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 0,
    capabilities JSON,
    config JSON,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plugins_tenant ON system_plugins(tenant_id);

-- 44. External Connections & Integrations
CREATE TABLE IF NOT EXISTS external_connections (
    connection_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    service_type TEXT NOT NULL, -- PMS, ERP, CRM, SLACK, EMAIL, BANKING, CUSTOM_API
    connector_adapter TEXT NOT NULL,
    auth_status TEXT NOT NULL DEFAULT 'CONNECTED', -- CONNECTED, DEGRADED, FAILED, DISCONNECTED
    health_score REAL NOT NULL DEFAULT 100.0,
    latency_ms INTEGER NOT NULL DEFAULT 45,
    last_sync_at REAL,
    field_mappings JSON,
    permission_scope JSON,
    endpoint_url TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_connections_company ON external_connections(company_id);

-- 45. Stateful Agent Identities & Working Memory Blocks
CREATE TABLE IF NOT EXISTS stateful_agent_identities (
    agent_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department_id TEXT,
    persona_block TEXT NOT NULL DEFAULT '',
    human_block TEXT NOT NULL DEFAULT '',
    system_instructions TEXT NOT NULL DEFAULT '',
    model_config JSON,
    tools JSON,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata JSON,
    PRIMARY KEY (tenant_id, agent_id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stateful_agent_tenant ON stateful_agent_identities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stateful_agent_comp ON stateful_agent_identities(company_id);

-- 46. Stateful Memory Records (Core, Working, Archival, Recall)
CREATE TABLE IF NOT EXISTS stateful_memory_records (
    record_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    scope TEXT NOT NULL, -- HOST, PERSONAL_WORKSPACE, TENANT, COMPANY, DEPARTMENT, WORKFORCE, AGENT, MISSION, PROJECT, MEETING
    scope_id TEXT NOT NULL,
    memory_type TEXT NOT NULL, -- CORE, WORKING, ARCHIVAL, RECALL, SYSTEM
    category TEXT NOT NULL, -- FACT, PREFERENCE, CONSTRAINT, DIRECTIVE, GOAL, CONTEXT, DECISION, SUMMARY
    memory_key TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'VERIFIED', -- VERIFIED, OBSERVED, HOST_PROVIDED, SYSTEM_DERIVED, AGENT_INFERRED, ESTIMATED, UNVERIFIED, EXPIRED
    version INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT,
    expires_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stateful_mem_lookup ON stateful_memory_records(tenant_id, scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_stateful_mem_key ON stateful_memory_records(tenant_id, memory_key);
CREATE INDEX IF NOT EXISTS idx_stateful_mem_type ON stateful_memory_records(tenant_id, memory_type);

-- 47. Stateful Memory Conflicts & Epistemic Resolutions
CREATE TABLE IF NOT EXISTS stateful_memory_conflicts (
    conflict_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    record_a_id TEXT NOT NULL,
    record_b_id TEXT NOT NULL,
    conflict_details TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN', -- OPEN, RESOLVED, DISMISSED
    resolution_choice TEXT, -- USE_A, USE_B, ASK_CEO, DISMISS
    resolved_at REAL,
    resolved_by TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stateful_conflicts_tenant ON stateful_memory_conflicts(tenant_id, scope_id);
CREATE INDEX IF NOT EXISTS idx_stateful_conflicts_status ON stateful_memory_conflicts(status);

-- 48. Stateful Conversation Sessions (Continuous Executive & Worker Dialogue)
CREATE TABLE IF NOT EXISTS stateful_conversation_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    company_id TEXT,
    session_type TEXT NOT NULL DEFAULT 'CHAT', -- MEETING, CHAT, COWORKER, WORKFORCE
    title TEXT NOT NULL,
    context_summary TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stateful_sessions_agent ON stateful_conversation_sessions(tenant_id, agent_id);

-- 49. Stateful Conversation Turns (Recall Memory Buffer with Compaction Support)
CREATE TABLE IF NOT EXISTS stateful_conversation_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL, -- HOST, USER, AGENT, SYSTEM, TOOL
    content TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    timestamp REAL NOT NULL,
    FOREIGN KEY(session_id) REFERENCES stateful_conversation_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stateful_turns_session ON stateful_conversation_turns(session_id);

-- 50. Multimodal Capabilities Registry (HAL9000 & ZONATA Native)
CREATE TABLE IF NOT EXISTS multimodal_capabilities (
    capability_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL, -- HAL9000, ZONATA_NATIVE, BROWSER_ROBOT, DESKTOP_ROBOT
    family TEXT NOT NULL, -- VISION, AUDIO_INPUT, SPEECH_TO_TEXT, TEXT_TO_SPEECH, SCREEN_OBSERVATION, SCREENSHOT, APPLICATION_CONTROL, FILE_ACCESS, CLIPBOARD, LOCAL_COMMAND, WEB_ACCESS, KNOWLEDGE, MEMORY, ARTIFACT, BACKGROUND_TASK, MCP
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.5.0',
    platform TEXT NOT NULL DEFAULT 'CROSS_PLATFORM',
    risk_level TEXT NOT NULL DEFAULT 'SAFE', -- SAFE, CONFIRM, DANGEROUS, CRITICAL
    requires_approval INTEGER NOT NULL DEFAULT 0,
    permissions JSON,
    execution_mode TEXT NOT NULL DEFAULT 'SANDBOX', -- SANDBOX, HOST, HYBRID
    evidence_requirements JSON,
    health_status TEXT NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, DEGRADED, UNAVAILABLE
    latency_ms INTEGER NOT NULL DEFAULT 15,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    metadata JSON,
    updated_at REAL NOT NULL,
    PRIMARY KEY (tenant_id, capability_id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mm_caps_tenant ON multimodal_capabilities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mm_caps_family ON multimodal_capabilities(tenant_id, family);

-- 51. Multimodal Execution Sessions & State Machine
CREATE TABLE IF NOT EXISTS multimodal_execution_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    workspace_id TEXT,
    user_id TEXT NOT NULL,
    mission_id TEXT,
    task_id TEXT,
    agent_id TEXT,
    capability_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'IDLE', -- IDLE, LISTENING, OBSERVING, UNDERSTANDING, PLANNING, WAITING_FOR_PERMISSION, WAITING_FOR_APPROVAL, PREPARING, EXECUTING, PAUSED, HOST_TAKEOVER, VERIFYING, RECONCILING, COMPLETED, FAILED, BLOCKED, CANCELLED, AMBIGUOUS, RECOVERY_REQUIRED
    host_takeover INTEGER NOT NULL DEFAULT 0,
    killswitch_active INTEGER NOT NULL DEFAULT 0,
    state_history JSON,
    last_observation JSON,
    last_verification JSON,
    evidence_id TEXT,
    started_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mm_sess_tenant ON multimodal_execution_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mm_sess_state ON multimodal_execution_sessions(state);

-- 52. Multimodal Observations Ledger (Screen, Webcam, Mic, Window with Redaction & Hashing)
CREATE TABLE IF NOT EXISTS multimodal_observations (
    observation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    session_id TEXT NOT NULL,
    task_id TEXT,
    source TEXT NOT NULL, -- WEBCAM, SCREENSHOT, MICROPHONE, APP_WINDOW, SYSTEM_METRIC
    observation_type TEXT NOT NULL, -- IMAGE, AUDIO_TRANSCRIPT, WINDOW_HIERARCHY, CLIPBOARD_TEXT, SYSTEM_STATE
    raw_hash TEXT NOT NULL,
    redacted_content TEXT,
    sensitivity_classification TEXT NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    confidence REAL NOT NULL DEFAULT 1.0,
    metadata JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mm_obs_sess ON multimodal_observations(session_id);

-- 53. Governed Multimodal Artifacts (SHA-256 Verified Outputs)
CREATE TABLE IF NOT EXISTS multimodal_artifacts (
    artifact_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    mission_id TEXT,
    task_id TEXT,
    creator_agent_id TEXT NOT NULL,
    title TEXT NOT NULL,
    artifact_type TEXT NOT NULL, -- DOCUMENT, CODE, HTML, DIAGRAM, REPORT, DATASET
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    integrity_hash TEXT NOT NULL,
    security_classification TEXT NOT NULL DEFAULT 'INTERNAL',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mm_artifacts_tenant ON multimodal_artifacts(tenant_id);

-- 54. Governed MCP Gateway Invocations (Policy & Authority Audited)
CREATE TABLE IF NOT EXISTS mcp_gateway_invocations (
    invocation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    client_id TEXT NOT NULL, -- claude_code, claude_desktop, cursor, external_mcp
    tool_name TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    policy_evaluation TEXT NOT NULL DEFAULT 'ALLOWED', -- ALLOWED, BLOCKED, APPROVAL_REQUIRED
    approval_status TEXT NOT NULL DEFAULT 'AUTO', -- AUTO, APPROVED, DENIED
    execution_status TEXT NOT NULL DEFAULT 'SUCCESS', -- SUCCESS, FAILED, BLOCKED, CANCELLED
    parameters JSON,
    result_summary TEXT,
    evidence_id TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_invocations_tenant ON mcp_gateway_invocations(tenant_id);

-- 55. Governed Durable Workflows (LangGraph Runtime Core)
CREATE TABLE IF NOT EXISTS workflows (
    workflow_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    workspace_id TEXT,
    mission_id TEXT,
    task_id TEXT,
    name TEXT NOT NULL,
    workflow_version INTEGER NOT NULL DEFAULT 1,
    runtime_provider TEXT NOT NULL DEFAULT 'LANGGRAPH', -- LANGGRAPH, ZONATA_NATIVE
    status TEXT NOT NULL DEFAULT 'DRAFT', -- DRAFT, VALIDATING, QUEUED, STARTING, RUNNING, WAITING_FOR_APPROVAL, WAITING_FOR_INPUT, PAUSED, RECOVERING, VERIFYING, RECONCILING, COMPLETED, FAILED, BLOCKED, CANCELLED, AMBIGUOUS, EXPIRED, RECOVERY_REQUIRED
    current_node TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    owner TEXT NOT NULL DEFAULT 'AI CEO',
    agent_id TEXT,
    approval_state TEXT NOT NULL DEFAULT 'NONE', -- NONE, REQUIRED, PENDING, APPROVED, REJECTED
    risk_level TEXT NOT NULL DEFAULT 'SAFE', -- SAFE, CONFIRM, DANGEROUS, CRITICAL
    graph_definition JSON NOT NULL,
    graph_definition_hash TEXT NOT NULL,
    budget JSON,
    timeout REAL DEFAULT 3600.0,
    retry_policy JSON,
    verification_policy JSON,
    evidence_policy JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wf_tenant ON workflows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_wf_company ON workflows(company_id);
CREATE INDEX IF NOT EXISTS idx_wf_status ON workflows(status);

-- 56. Governed Workflow Runs (Durable Execution Threads)
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    task_id TEXT,
    workflow_version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    current_node TEXT,
    step_count INTEGER NOT NULL DEFAULT 0,
    iteration_counts JSON,
    idempotency_keys JSON,
    budget_spent JSON,
    last_checkpoint_id TEXT,
    error_message TEXT,
    reconciliation_notes TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wfrun_wf ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_wfrun_thread ON workflow_runs(thread_id);

-- 57. Governed Workflow Checkpoints (Zero-Secret Resumable State)
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    task_id TEXT,
    graph_version INTEGER NOT NULL,
    state_version INTEGER NOT NULL,
    current_node TEXT NOT NULL,
    state_payload JSON NOT NULL,
    state_digest TEXT NOT NULL,
    step INTEGER NOT NULL DEFAULT 0,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wfchk_thread ON workflow_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_wfchk_run ON workflow_checkpoints(run_id);

-- 58. Governed Workflow Events (Audit Trail & Live Observability)
CREATE TABLE IF NOT EXISTS workflow_events (
    event_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    node_id TEXT,
    payload JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wfevt_wf ON workflow_events(workflow_id);
CREATE INDEX IF NOT EXISTS idx_wfevt_run ON workflow_events(run_id);

-- 59. Governed Workflow Approvals (Human-in-the-Loop Integration)
CREATE TABLE IF NOT EXISTS workflow_approvals (
    approval_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    proposed_action TEXT NOT NULL,
    parameters JSON NOT NULL,
    modified_parameters JSON,
    risk_level TEXT NOT NULL DEFAULT 'CONFIRM',
    status TEXT NOT NULL DEFAULT 'PENDING',
    decision_reason TEXT,
    decided_by TEXT,
    created_at REAL NOT NULL,
    decided_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wfappr_run ON workflow_approvals(run_id);
CREATE INDEX IF NOT EXISTS idx_wfappr_status ON workflow_approvals(status);

-- 60. Governed Workflow Resource Locks (Concurrency & Conflict Protection)
CREATE TABLE IF NOT EXISTS workflow_resource_locks (
    lock_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL, -- FILE, RECORD, CAPABILITY, TASK
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    acquired_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wflock_res ON workflow_resource_locks(resource_id);

-- 61. Governed Agent Interoperability Registry (A2A v1.0 Standard)
CREATE TABLE IF NOT EXISTS a2a_agents (
    agent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    provider_name TEXT,
    provider_url TEXT,
    endpoint_url TEXT NOT NULL,
    protocol_version TEXT NOT NULL DEFAULT '1.0',
    supported_interfaces JSON NOT NULL,
    capabilities JSON NOT NULL,
    skills JSON NOT NULL,
    authentication JSON,
    trust_level TEXT NOT NULL DEFAULT 'DISCOVERED', -- UNKNOWN, DISCOVERED, VALIDATED, IDENTITY_VERIFIED, TRUSTED, RESTRICTED, SUSPENDED, BLOCKED
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED', -- UNVERIFIED, VERIFIED, FAILED
    role_type TEXT NOT NULL DEFAULT 'EXTERNAL_UNKNOWN', -- INTERNAL, EXTERNAL_TRUSTED, EXTERNAL_UNKNOWN, BLOCKED
    owner TEXT,
    organization TEXT,
    environment TEXT NOT NULL DEFAULT 'PRODUCTION', -- PRODUCTION, STAGING, TEST
    status TEXT NOT NULL DEFAULT 'OFFLINE', -- ONLINE, OFFLINE, DEGRADED, SUSPENDED, BLOCKED
    last_health_check REAL,
    reputation_metrics JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_agent_tenant ON a2a_agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_a2a_agent_trust ON a2a_agents(trust_level);
CREATE INDEX IF NOT EXISTS idx_a2a_agent_role ON a2a_agents(role_type);

-- 62. Governed A2A Skills & Capability Governance
CREATE TABLE IF NOT EXISTS a2a_skills (
    skill_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    tags JSON,
    risk_level TEXT NOT NULL DEFAULT 'SAFE', -- SAFE, CONFIRM, DANGEROUS, CRITICAL
    permissions JSON,
    approval_required INTEGER NOT NULL DEFAULT 0,
    evidence_required INTEGER NOT NULL DEFAULT 1,
    timeout REAL DEFAULT 300.0,
    budget REAL DEFAULT 0.0,
    allowed_companies JSON,
    allowed_tenants JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(agent_id) REFERENCES a2a_agents(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_skill_agent ON a2a_skills(agent_id);

-- 63. Governed A2A Remote Tasks (Dual Correlation & Invariants)
CREATE TABLE IF NOT EXISTS a2a_tasks (
    task_id TEXT PRIMARY KEY,
    zonata_request_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    workspace_id TEXT,
    mission_id TEXT,
    zonata_task_id TEXT,
    workflow_id TEXT,
    run_id TEXT,
    agent_id TEXT NOT NULL,
    skill_id TEXT,
    requested_by TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    a2a_state TEXT NOT NULL DEFAULT 'TASK_STATE_SUBMITTED', -- TASK_STATE_SUBMITTED, TASK_STATE_WORKING, TASK_STATE_COMPLETED, TASK_STATE_FAILED, TASK_STATE_CANCELED, TASK_STATE_INPUT_REQUIRED, TASK_STATE_REJECTED, TASK_STATE_AUTH_REQUIRED
    zonata_state TEXT NOT NULL DEFAULT 'SUBMITTED', -- DISCOVERED, VALIDATING, AUTHORIZED, SUBMITTED, WORKING, INPUT_REQUIRED, COMPLETED, FAILED, CANCELLED, REJECTED, AMBIGUOUS, RECONCILED
    data_classification TEXT NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, PERSONAL, FINANCIAL, SECURITY_SENSITIVE
    cost_spent REAL DEFAULT 0.0,
    evidence_hash TEXT,
    reconciliation_notes TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(agent_id) REFERENCES a2a_agents(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_task_tenant ON a2a_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_a2a_task_agent ON a2a_tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_a2a_task_zonata ON a2a_tasks(zonata_request_id);

-- 64. Governed A2A Message Exchange Audit
CREATE TABLE IF NOT EXISTS a2a_messages (
    message_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    context_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    role TEXT NOT NULL, -- ROLE_USER, ROLE_AGENT
    parts JSON NOT NULL,
    sanitized_content TEXT,
    data_classification TEXT NOT NULL DEFAULT 'INTERNAL',
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES a2a_tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_msg_task ON a2a_messages(task_id);

-- 65. Governed A2A Artifacts & Quarantine Repository
CREATE TABLE IF NOT EXISTS a2a_artifacts (
    artifact_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    media_type TEXT,
    sha256_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    security_scan_status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, CLEAN, QUARANTINED, REJECTED
    quarantine_reason TEXT,
    parts JSON NOT NULL,
    storage_path TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES a2a_tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_art_task ON a2a_artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_a2a_art_hash ON a2a_artifacts(sha256_hash);

-- 66. Governed A2A Security Events Audit Ledger
CREATE TABLE IF NOT EXISTS a2a_security_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    agent_id TEXT,
    task_id TEXT,
    event_type TEXT NOT NULL, -- PROMPT_INJECTION, SSRF_ATTEMPT, REPLAY_ATTEMPT, CROSS_TENANT_ATTEMPT, MALFORMED_AGENT_CARD, INVALID_SIGNATURE, AUTH_FAILURE, POLICY_VIOLATION, MALICIOUS_ARTIFACT, CREDENTIAL_LEAK_ATTEMPT
    severity TEXT NOT NULL DEFAULT 'HIGH', -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON NOT NULL,
    source_ip TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_sec_tenant ON a2a_security_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_a2a_sec_type ON a2a_security_events(event_type);

-- 67. Governed A2A Inbound Published Agents
CREATE TABLE IF NOT EXISTS a2a_published_agents (
    published_id TEXT PRIMARY KEY,
    internal_agent_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'PRIVATE', -- PUBLIC, PARTNER, PRIVATE
    allowed_organizations JSON,
    allowed_tenants JSON,
    allowed_skills JSON NOT NULL,
    rate_limit_per_min INTEGER NOT NULL DEFAULT 60,
    cost_per_task REAL DEFAULT 0.0,
    approval_required INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, SUSPENDED
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_a2a_pub_tenant ON a2a_published_agents(tenant_id);
"""

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

# Global Singleton Database Instance
db = Database()
