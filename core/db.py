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
