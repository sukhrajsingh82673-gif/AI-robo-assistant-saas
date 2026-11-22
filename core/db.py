"""
RoboAssistant Company OS 1.0 — Normalized Relational Database Engine
Production SQLite engine providing tenant isolation, schema migrations,
and relational persistence for all Company OS entities.
"""

import contextlib
import contextvars
import functools
import inspect
import sqlite3
import os
import time
import json
import re
import urllib.parse
import threading
import sys
from typing import Optional, Any, Dict, List, Tuple, Set

# Request-scoped tenant/company context used to drive PostgreSQL fail-closed RLS.
_current_tenant_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "zonata_current_tenant_id", default=None
)
_current_company_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "zonata_current_company_id", default=None
)


@contextlib.contextmanager
def tenant_scope(tenant_id: Optional[str], company_id: Optional[str] = None):
    """Binds the tenant/company used to set transactional RLS session settings."""
    tenant_token = _current_tenant_id.set(tenant_id)
    company_token = _current_company_id.set(company_id)
    try:
        yield
    finally:
        _current_tenant_id.reset(tenant_token)
        _current_company_id.reset(company_token)


def tenant_scoped(func):
    """Decorator that binds tenant_id/company_id arguments to the RLS context."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            tenant_id = bound.arguments.get("tenant_id")
            company_id = bound.arguments.get("company_id")
        except (TypeError, ValueError):
            tenant_id = company_id = None
        if tenant_id is None:
            return func(*args, **kwargs)
        with tenant_scope(tenant_id, company_id):
            return func(*args, **kwargs)
    return wrapper

# Automatically load Neon environment configuration (.env.local / .env)
try:
    from core.neon_env import load_neon_env
    load_neon_env()
except Exception:
    pass

def sanitize_db_url(raw_input: str) -> str:
    """Safely sanitizes database connection strings and diagnostic error strings.
    Parses connection URLs via urllib.parse to redact userinfo passwords and query secrets,
    with defensive multi-layer fallbacks for irregular strings, punctuation, URL-encoded
    characters, and exception traces.
    """
    if not raw_input:
        return ""
    text = str(raw_input).strip()

    def _sanitize_single_url(url: str) -> str:
        try:
            parsed = urllib.parse.urlsplit(url)
            netloc = parsed.netloc
            if "@" in netloc:
                userinfo, hostinfo = netloc.rsplit("@", 1)
                if ":" in userinfo:
                    username, _ = userinfo.split(":", 1)
                    new_userinfo = f"{username}:***"
                else:
                    new_userinfo = userinfo
                netloc = f"{new_userinfo}@{hostinfo}"

            query = parsed.query
            if query:
                q_pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
                new_pairs = []
                for k, v in q_pairs:
                    if k.lower() in ("password", "pwd", "secret", "token", "auth", "key"):
                        new_pairs.append((k, "***"))
                    else:
                        new_pairs.append((k, v))
                query = urllib.parse.urlencode(new_pairs)
            return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))
        except Exception:
            return url

    # 1. If raw input is directly a URL:
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', text):
        cleaned = _sanitize_single_url(text)
    else:
        cleaned = text

    # 2. Secondary defense: sanitize any embedded URLs in error messages
    def _sub_embedded(m):
        return _sanitize_single_url(m.group(0))

    cleaned = re.sub(r'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\'"`,;)]+', _sub_embedded, cleaned)

    # 3. Tertiary defense: sanitize any remaining :<password>@ patterns
    cleaned = re.sub(r':([^:@/\s\'"`,;)]+)@', r':***@', cleaned)

    # 4. Quaternary defense: query parameters in strings
    cleaned = re.sub(r'([?&](?:password|pwd|secret|token|auth)=)[^&\s\'"`,;)]+', r'\g<1>***', cleaned, flags=re.IGNORECASE)

    return cleaned

def get_default_db_path() -> str:
    env_path = os.environ.get("ZONATA_DB_PATH") or os.environ.get("ROBOASSISTANT_DB_PATH")
    if env_path:
        return os.path.abspath(env_path)
    storage_root = os.environ.get("ZONATA_STORAGE_DIR")
    if storage_root:
        return os.path.abspath(os.path.join(storage_root, "roboassistant.db"))
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "storage", "roboassistant.db")

DB_PATH = get_default_db_path()

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

-- 1b. Restricted Pilot Organizations Registry (Milestone J Operating Envelope)
CREATE TABLE IF NOT EXISTS pilot_organizations (
    tenant_id TEXT PRIMARY KEY,
    org_name TEXT NOT NULL,
    contact_email TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    registered_at REAL NOT NULL,
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_pilot_orgs_status ON pilot_organizations(status);

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

-- 2b. Authentication Credentials & Password Hashes
CREATE TABLE IF NOT EXISTS auth_credentials (
    user_id TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_auth_credentials_user ON auth_credentials(user_id);

-- 2c. Authentication Revoked Tokens
CREATE TABLE IF NOT EXISTS auth_revoked_tokens (
    token_id TEXT PRIMARY KEY,
    revoked_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_revoked_tokens ON auth_revoked_tokens(token_id);

-- 2d. Distributed Rate Limit Events
CREATE TABLE IF NOT EXISTS auth_rate_limits (
    rate_key TEXT NOT NULL,
    attempt_timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_key ON auth_rate_limits(rate_key, attempt_timestamp);
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_ts ON auth_rate_limits(attempt_timestamp);

-- 2e. Distributed Tenant Rate Limits & Fairness Windows
CREATE TABLE IF NOT EXISTS tenant_rate_limits (
    rate_key TEXT NOT NULL,
    attempt_timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_key ON tenant_rate_limits(rate_key, attempt_timestamp);
CREATE INDEX IF NOT EXISTS idx_tenant_rate_limits_ts ON tenant_rate_limits(attempt_timestamp);

-- 2f. Distributed Tenant Concurrency Leases
CREATE TABLE IF NOT EXISTS tenant_concurrency_leases (
    lease_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    lease_type TEXT NOT NULL, -- WORKFLOW, AGENT_MISSION, AI_GENERATION
    acquired_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tenant_leases_tenant ON tenant_concurrency_leases(tenant_id, expires_at);

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
    decision_reason TEXT,
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

-- 14b. Enterprise Skill Arena Decisions
CREATE TABLE IF NOT EXISTS arena_decisions (
    decision_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    requester_role TEXT NOT NULL,
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    judges_json TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    winner_option_id TEXT,
    winner_title TEXT,
    consensus_outcome TEXT NOT NULL,
    status TEXT NOT NULL,
    agreement REAL NOT NULL DEFAULT 0.0,
    confidence REAL NOT NULL DEFAULT 0.0,
    risk_level TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    required_authority TEXT NOT NULL, -- EMPLOYEE, MANAGER, EXECUTIVE, OWNER
    requester_authority TEXT NOT NULL,
    authority_granted INTEGER NOT NULL DEFAULT 0,
    policy_decision TEXT NOT NULL,
    approval_id TEXT,
    evidence_id TEXT,
    evidence_status TEXT,
    notes TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_arena_decisions_scope ON arena_decisions(tenant_id, company_id, created_at);

-- 14c. Executable Skill Contract Runs
CREATE TABLE IF NOT EXISTS skill_runs (
    run_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    requester_role TEXT NOT NULL,
    status TEXT NOT NULL, -- SATISFIED, ESCALATED, CONTRACT_FAILED
    required_authority TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    result_json TEXT,
    evidence_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_skill_runs_scope ON skill_runs(tenant_id, company_id, created_at);

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

-- 42b. Durable Coworker Background Missions (searchable, tenant-scoped)
CREATE TABLE IF NOT EXISTS coworker_background_missions (
    mission_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    initiator TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL,
    progress_percent REAL NOT NULL DEFAULT 0,
    current_stage TEXT NOT NULL DEFAULT 'INITIATED',
    subworkers_json TEXT NOT NULL DEFAULT '[]',
    runtimes_json TEXT NOT NULL DEFAULT '[]',
    deliverables_json TEXT NOT NULL DEFAULT '[]',
    evidence_id TEXT,
    notification_message TEXT,
    timeline_json TEXT NOT NULL DEFAULT '[]',
    human_control INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL
);

CREATE INDEX IF NOT EXISTS idx_bg_missions_tenant ON coworker_background_missions(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bg_missions_company ON coworker_background_missions(company_id);

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

-- 68. Governed MCP Servers Registry
CREATE TABLE IF NOT EXISTS mcp_servers (
    server_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    endpoint TEXT NOT NULL,
    transport TEXT NOT NULL DEFAULT 'STREAMABLE_HTTP', -- STREAMABLE_HTTP, STDIO
    protocol_version TEXT NOT NULL DEFAULT '2026-07-28',
    server_version TEXT DEFAULT '1.0.0',
    identity TEXT,
    authentication_type TEXT DEFAULT 'NONE', -- NONE, BEARER, OAUTH2, API_KEY
    credential_reference TEXT,
    trust_state TEXT NOT NULL DEFAULT 'DISCOVERED', -- UNKNOWN, DISCOVERED, VALIDATING, VALIDATED, IDENTITY_VERIFIED, TRUSTED, RESTRICTED, SUSPENDED, BLOCKED
    risk_classification TEXT NOT NULL DEFAULT 'READ_ONLY', -- READ_ONLY, LOW_RISK_MUTATION, BUSINESS_MUTATION, FINANCIAL, PRIVILEGED, SECURITY_SENSITIVE, DESTRUCTIVE, IRREVERSIBLE
    data_classification TEXT NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, FINANCIAL, SECURITY_SENSITIVE
    allowed_tools JSON,
    allowed_resources JSON,
    allowed_prompts JSON,
    allowed_operations JSON,
    allowed_companies JSON,
    allowed_agents JSON,
    allowed_workflows JSON,
    rate_limit INTEGER DEFAULT 60,
    budget_limit REAL DEFAULT 0.0,
    timeout_policy REAL DEFAULT 30.0,
    approval_policy TEXT DEFAULT 'STANDARD',
    verification_policy TEXT DEFAULT 'PHYSICAL_VERIFICATION',
    status TEXT NOT NULL DEFAULT 'ONLINE', -- ONLINE, OFFLINE, QUARANTINED, SUSPENDED
    health_status TEXT NOT NULL DEFAULT 'HEALTHY',
    reputation_metrics JSON,
    last_seen REAL NOT NULL,
    last_verified REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_tenant ON mcp_servers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_trust ON mcp_servers(trust_state);

-- 69. Governed MCP Tools
CREATE TABLE IF NOT EXISTS mcp_tools (
    tool_id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    input_schema JSON,
    output_schema JSON,
    risk_class TEXT NOT NULL DEFAULT 'READ_ONLY',
    data_classification TEXT NOT NULL DEFAULT 'INTERNAL',
    required_scopes JSON,
    required_permissions JSON,
    allowed_agents JSON,
    allowed_workflows JSON,
    approval_requirement INTEGER NOT NULL DEFAULT 0,
    verification_requirement INTEGER NOT NULL DEFAULT 1,
    cost_model REAL DEFAULT 0.0,
    rate_limit INTEGER DEFAULT 60,
    timeout REAL DEFAULT 30.0,
    reversibility INTEGER NOT NULL DEFAULT 1,
    idempotency INTEGER NOT NULL DEFAULT 1,
    side_effect_class TEXT DEFAULT 'NONE',
    status TEXT NOT NULL DEFAULT 'AVAILABLE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(server_id) REFERENCES mcp_servers(server_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_tools_server ON mcp_tools(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_tenant ON mcp_tools(tenant_id);

-- 70. Governed MCP Resources
CREATE TABLE IF NOT EXISTS mcp_resources (
    resource_id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    uri TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    mime_type TEXT DEFAULT 'application/json',
    data_classification TEXT NOT NULL DEFAULT 'INTERNAL',
    required_scopes JSON,
    approval_required INTEGER NOT NULL DEFAULT 0,
    metadata JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(server_id) REFERENCES mcp_servers(server_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_resources_server ON mcp_resources(server_id);

-- 71. Governed MCP Prompts
CREATE TABLE IF NOT EXISTS mcp_prompts (
    prompt_id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    arguments_schema JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(server_id) REFERENCES mcp_servers(server_id) ON DELETE CASCADE
);

-- 72. Governed MCP Long-Running Tasks (Tasks Extension)
CREATE TABLE IF NOT EXISTS mcp_tasks (
    task_id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    tool_id TEXT NOT NULL,
    client_task_id TEXT,
    status TEXT NOT NULL DEFAULT 'SUBMITTED', -- SUBMITTED, WORKING, COMPLETED, FAILED, CANCELLED, INPUT_REQUIRED
    external_ref TEXT,
    progress REAL DEFAULT 0.0,
    input_payload JSON,
    result JSON,
    error_message TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(server_id) REFERENCES mcp_servers(server_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_tasks_server ON mcp_tasks(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tasks_tenant ON mcp_tasks(tenant_id);

-- 73. Governed MCP Execution Traces & Invocations
CREATE TABLE IF NOT EXISTS mcp_executions (
    execution_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    workflow_id TEXT,
    thread_id TEXT,
    agent_id TEXT NOT NULL,
    server_id TEXT NOT NULL,
    tool_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSON,
    sanitized_arguments JSON,
    policy_decision TEXT NOT NULL, -- ALLOW, REQUIRE_HUMAN_APPROVAL, DENY
    authority_decision TEXT NOT NULL, -- AUTHORIZED, DENIED, SUSPENDED_FOR_APPROVAL
    approval_id TEXT,
    execution_status TEXT NOT NULL, -- DISCOVERY_FAILED, AUTH_FAILED, POLICY_DENIED, AUTHORITY_DENIED, APPROVAL_REQUIRED, APPROVAL_EXPIRED, CONNECTION_FAILED, TOOL_FAILED, TIMEOUT, CANCELLED, UNKNOWN, RECONCILIATION_REQUIRED, VERIFICATION_FAILED, VERIFIED
    response_raw JSON,
    response_sanitized JSON,
    verification_id TEXT,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    evidence_id TEXT,
    sha256_digest TEXT,
    causality_chain_id TEXT,
    business_outcome TEXT,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    cost_spent REAL DEFAULT 0.0,
    error_message TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_exec_tenant ON mcp_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mcp_exec_server ON mcp_executions(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_exec_tool ON mcp_executions(tool_id);

-- 74. Governed MCP Security Center Events
CREATE TABLE IF NOT EXISTS mcp_security_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    server_id TEXT,
    tool_id TEXT,
    event_type TEXT NOT NULL, -- UNTRUSTED_SERVER, INVALID_AUTH, EXPIRED_TOKEN, INVALID_ISSUER, SCOPE_VIOLATION, UNAUTHORIZED_TOOL, PROMPT_INJECTION, MALICIOUS_RESOURCE, UNEXPECTED_DATA, CREDENTIAL_EXPOSURE_ATTEMPT, TOOL_SCHEMA_ANOMALY, SERVER_IDENTITY_CHANGE, PROTOCOL_MISMATCH, POLICY_VIOLATION, TENANT_ISOLATION_VIOLATION, SSRF_ATTEMPT
    severity TEXT NOT NULL DEFAULT 'HIGH', -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON NOT NULL,
    source_ip TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_sec_tenant ON mcp_security_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mcp_sec_type ON mcp_security_events(event_type);

-- 75. Governed ZONATA Inbound Published MCP Capabilities
CREATE TABLE IF NOT EXISTS mcp_published_capabilities (
    published_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    schema_definition JSON NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'PRIVATE', -- PUBLIC, PARTNER, PRIVATE
    allowed_clients JSON,
    rate_limit_per_min INTEGER NOT NULL DEFAULT 60,
    approval_required INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, SUSPENDED
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_pub_tenant ON mcp_published_capabilities(tenant_id);

-- 76. Governed OpenHands Execution Runtimes
CREATE TABLE IF NOT EXISTS openhands_runtimes (
    runtime_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    runtime_type TEXT NOT NULL, -- LOCAL_HOST, REMOTE_LINUX, CONTAINER, VM, CLOUD_WORKER
    host_id TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ONLINE', -- ONLINE, BUSY, OFFLINE, QUARANTINED
    health_status TEXT NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, DEGRADED, UNHEALTHY
    resource_capacity JSON,
    active_executions INTEGER NOT NULL DEFAULT 0,
    security_profile JSON,
    last_heartbeat REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_runtime_tenant ON openhands_runtimes(tenant_id);

-- 77. Governed OpenHands Isolated Workspaces
CREATE TABLE IF NOT EXISTS openhands_workspaces (
    workspace_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    workflow_id TEXT,
    task_id TEXT,
    agent_id TEXT NOT NULL,
    runtime_id TEXT NOT NULL,
    workspace_type TEXT NOT NULL DEFAULT 'EPHEMERAL', -- EPHEMERAL, PERSISTENT
    workspace_class TEXT NOT NULL DEFAULT 'SANDBOX', -- READ_ONLY, SANDBOX, DEVELOPMENT, TEST, STAGING, PRODUCTION
    path TEXT NOT NULL,
    base_image TEXT,
    filesystem_scope JSON,
    network_scope TEXT NOT NULL DEFAULT 'RESTRICTED', -- NONE, ALLOWLIST, RESTRICTED, FULL
    credential_scope JSON,
    resource_limits JSON,
    expires_at REAL,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, EXPIRED, DESTROYED
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_ws_tenant ON openhands_workspaces(tenant_id);
CREATE INDEX IF NOT EXISTS idx_oh_ws_company ON openhands_workspaces(company_id);

-- 78. Governed OpenHands Executions
CREATE TABLE IF NOT EXISTS openhands_executions (
    execution_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    workflow_id TEXT,
    task_id TEXT,
    agent_id TEXT NOT NULL,
    runtime_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    execution_status TEXT NOT NULL, -- REQUESTED, POLICY_CHECK, AUTHORITY_CHECK, APPROVAL_CHECK, WORKSPACE_PREPARING, INITIALIZING, RUNNING, WAITING, VERIFYING, COMPLETED, DENIED, CANCELLED, TIMEOUT, FAILED, TERMINATED, UNKNOWN, RECONCILIATION_REQUIRED, VERIFICATION_FAILED
    policy_decision TEXT NOT NULL, -- ALLOW, REQUIRE_HUMAN_APPROVAL, DENY
    authority_decision TEXT NOT NULL, -- AUTHORIZED, DENIED, SUSPENDED_FOR_APPROVAL
    approval_id TEXT,
    task_prompt TEXT NOT NULL,
    scoped_context JSON,
    result_summary TEXT,
    files_changed JSON,
    tests_passed INTEGER NOT NULL DEFAULT 0,
    tests_failed INTEGER NOT NULL DEFAULT 0,
    verification_id TEXT,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED', -- UNVERIFIED, VERIFIED, VERIFICATION_FAILED
    evidence_id TEXT,
    sha256_digest TEXT,
    causality_chain_id TEXT,
    business_outcome TEXT,
    cost_tokens INTEGER NOT NULL DEFAULT 0,
    cost_spent REAL NOT NULL DEFAULT 0.0,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    loop_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_exec_tenant ON openhands_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_oh_exec_ws ON openhands_executions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_oh_exec_status ON openhands_executions(execution_status);

-- 79. Governed OpenHands Terminal Commands
CREATE TABLE IF NOT EXISTS openhands_commands (
    command_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    command TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    risk_class TEXT NOT NULL, -- READ_ONLY, LOW_RISK, MUTATING, PRIVILEGED, DESTRUCTIVE, IRREVERSIBLE
    policy_decision TEXT NOT NULL, -- ALLOW, REQUIRE_HUMAN_APPROVAL, DENY
    authority_decision TEXT NOT NULL, -- AUTHORIZED, DENIED, SUSPENDED_FOR_APPROVAL
    exit_code INTEGER,
    stdout_sample TEXT,
    stderr_sample TEXT,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    sha256_digest TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_cmd_exec ON openhands_commands(execution_id);

-- 80. Governed OpenHands Event Stream
CREATE TABLE IF NOT EXISTS openhands_events (
    event_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- agent_started, workspace_created, tool_requested, tool_started, tool_completed, command_started, command_completed, file_created, file_modified, file_deleted, test_started, test_completed, artifact_created, error, warning, approval_requested, approval_granted, approval_denied, verification_started, verification_completed, execution_completed, execution_failed
    payload JSON NOT NULL,
    correlation_id TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_ev_exec ON openhands_events(execution_id);
CREATE INDEX IF NOT EXISTS idx_oh_ev_type ON openhands_events(event_type);

-- 81. Governed OpenHands Artifact Registry
CREATE TABLE IF NOT EXISTS openhands_artifacts (
    artifact_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    artifact_type TEXT NOT NULL, -- CODE, PATCH, DIFF, REPORT, LOG, DATA, TEST_REPORT, BUILD
    path TEXT NOT NULL,
    sha256_digest TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    classification TEXT NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED', -- UNVERIFIED, VERIFIED, REJECTED
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_art_exec ON openhands_artifacts(execution_id);
CREATE INDEX IF NOT EXISTS idx_oh_art_tenant ON openhands_artifacts(tenant_id);

-- 82. Governed OpenHands Security Events
CREATE TABLE IF NOT EXISTS openhands_security_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    execution_id TEXT,
    workspace_id TEXT,
    event_type TEXT NOT NULL, -- COMMAND_BLOCKED, TOOL_BLOCKED, WORKSPACE_ESCAPE_ATTEMPT, PATH_TRAVERSAL, SECRET_DETECTION, PROMPT_INJECTION, MALICIOUS_REPOSITORY, UNAUTHORIZED_NETWORK, CREDENTIAL_ATTEMPT, RESOURCE_EXHAUSTION, RUNTIME_FAILURE, POLICY_VIOLATION, KILLSWITCH_TRIGGERED
    severity TEXT NOT NULL DEFAULT 'HIGH', -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON NOT NULL,
    source TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_sec_tenant ON openhands_security_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_oh_sec_type ON openhands_security_events(event_type);

-- 83. Governed OpenHands Human-in-the-Loop Approvals
CREATE TABLE IF NOT EXISTS openhands_approvals (
    approval_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    operation_type TEXT NOT NULL, -- COMMAND_EXECUTION, FILE_MUTATION, DEPLOYMENT, GIT_PUSH, PACKAGE_INSTALLATION
    details JSON NOT NULL,
    risk_level TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED
    requested_by TEXT NOT NULL,
    approved_by TEXT,
    approval_scope TEXT NOT NULL DEFAULT 'SINGLE_EXECUTION', -- SINGLE_EXECUTION, SCOPED, PERMANENT
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oh_appr_exec ON openhands_approvals(execution_id);
CREATE INDEX IF NOT EXISTS idx_oh_appr_status ON openhands_approvals(status);

-- 84. Governed Browser Execution Runtimes
CREATE TABLE IF NOT EXISTS browser_runtimes (
    runtime_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    browser_type TEXT NOT NULL DEFAULT 'chromium', -- chromium, firefox, webkit, cdp
    browser_version TEXT NOT NULL DEFAULT 'latest',
    playwright_version TEXT NOT NULL DEFAULT '1.49.0',
    host TEXT NOT NULL DEFAULT 'localhost',
    endpoint_url TEXT,
    security_profile TEXT NOT NULL DEFAULT 'ISOLATED', -- ISOLATED, HARDENED, CUSTOM
    capacity INTEGER NOT NULL DEFAULT 10,
    active_sessions INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, DEGRADED, UNHEALTHY, DRAINING
    created_at REAL NOT NULL,
    last_health_check REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_rt_tenant ON browser_runtimes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_br_rt_status ON browser_runtimes(status);

-- 85. Governed Browser Sessions
CREATE TABLE IF NOT EXISTS browser_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    mission_id TEXT,
    workflow_id TEXT,
    task_id TEXT,
    profile_id TEXT NOT NULL DEFAULT 'EPHEMERAL', -- EPHEMERAL, PERSONAL, COMPANY, APPLICATION, AUTOMATION
    runtime_id TEXT NOT NULL,
    browser_type TEXT NOT NULL DEFAULT 'chromium',
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, CLOSED, EXPIRED, TERMINATED
    current_url TEXT NOT NULL DEFAULT 'about:blank',
    current_domain TEXT NOT NULL DEFAULT '',
    active_tab_id TEXT NOT NULL DEFAULT 'tab_primary',
    tabs_json JSON NOT NULL DEFAULT '[]',
    auth_state TEXT NOT NULL DEFAULT 'UNAUTHENTICATED', -- UNAUTHENTICATED, AUTHENTICATED, PRIVILEGED_AUTHENTICATED
    credential_scope TEXT,
    domain_policy TEXT NOT NULL DEFAULT 'ALLOWLIST', -- BLOCK_ALL, ALLOWLIST, APPROVED_DOMAINS, RESTRICTED, FULL
    allowed_domains_json JSON NOT NULL DEFAULT '[]',
    navigation_count INTEGER NOT NULL DEFAULT 0,
    action_count INTEGER NOT NULL DEFAULT 0,
    max_duration_seconds INTEGER NOT NULL DEFAULT 3600,
    max_tabs INTEGER NOT NULL DEFAULT 5,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    last_activity REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_sess_tenant ON browser_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_br_sess_status ON browser_sessions(status);
CREATE INDEX IF NOT EXISTS idx_br_sess_agent ON browser_sessions(agent_id);

-- 86. Governed Browser Executions
CREATE TABLE IF NOT EXISTS browser_executions (
    execution_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    mission_id TEXT,
    workflow_id TEXT,
    task_prompt TEXT NOT NULL,
    execution_status TEXT NOT NULL DEFAULT 'REQUESTED', -- REQUESTED, POLICY_CHECK, AUTHORITY_CHECK, APPROVAL_CHECK, SESSION_PREPARATION, BROWSER_INITIALIZATION, NAVIGATION, OBSERVE, PLAN, ACTION, OBSERVE_POST, VERIFY, COMPLETE, DENIED, AUTH_FAILED, NAVIGATION_FAILED, ACTION_FAILED, TIMEOUT, CANCELLED, BLOCKED, UNKNOWN, RECONCILIATION_REQUIRED, VERIFICATION_FAILED
    current_stage TEXT NOT NULL DEFAULT 'REQUESTED',
    current_url TEXT NOT NULL DEFAULT 'about:blank',
    actions_planned INTEGER NOT NULL DEFAULT 0,
    actions_completed INTEGER NOT NULL DEFAULT 0,
    actions_blocked INTEGER NOT NULL DEFAULT 0,
    approval_status TEXT NOT NULL DEFAULT 'NONE', -- NONE, PENDING, APPROVED, REJECTED
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED', -- UNVERIFIED, VERIFIED, VERIFICATION_FAILED, UNKNOWN, RECONCILIATION_REQUIRED
    evidence_id TEXT,
    result_summary TEXT,
    error_message TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_exec_tenant ON browser_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_br_exec_status ON browser_executions(execution_status);
CREATE INDEX IF NOT EXISTS idx_br_exec_session ON browser_executions(session_id);

-- 87. Governed Browser Actions
CREATE TABLE IF NOT EXISTS browser_actions (
    action_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action_type TEXT NOT NULL, -- NAVIGATE, CLICK, DOUBLE_CLICK, TYPE, SELECT, SCROLL, PRESS_KEY, SWITCH_TAB, OPEN_TAB, CLOSE_TAB, UPLOAD, DOWNLOAD, WAIT, EXTRACT, SCREENSHOT, SUBMIT_FORM
    target_selector TEXT,
    target_url TEXT,
    parameters_json JSON NOT NULL DEFAULT '{}',
    risk_class TEXT NOT NULL DEFAULT 'READ_ONLY', -- READ_ONLY, LOW_RISK_INTERACTION, DATA_ENTRY, BUSINESS_MUTATION, FINANCIAL, PRIVILEGED, DESTRUCTIVE, IRREVERSIBLE
    policy_decision TEXT NOT NULL DEFAULT 'PERMITTED', -- PERMITTED, BLOCKED, APPROVAL_REQUIRED
    approval_id TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, RUNNING, COMPLETED, FAILED, BLOCKED, CANCELLED
    result_data_json JSON,
    error TEXT,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_act_exec ON browser_actions(execution_id);
CREATE INDEX IF NOT EXISTS idx_br_act_type ON browser_actions(action_type);

-- 88. Governed Browser Events
CREATE TABLE IF NOT EXISTS browser_events (
    event_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- SESSION_CREATED, NAVIGATION, ACTION_EXECUTED, OBSERVATION, APPROVAL_REQUESTED, KILLSWITCH_TRIGGERED, VERIFIED, STATE_CHANGED
    payload_json JSON NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_evt_exec ON browser_events(execution_id);

-- 89. Governed Browser Artifacts
CREATE TABLE IF NOT EXISTS browser_artifacts (
    artifact_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL, -- SCREENSHOT, DOWNLOADED_FILE, EXTRACTED_DATA, DOM_SNAPSHOT, HAR_RECORDING
    rel_path TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    sha256_digest TEXT NOT NULL,
    redacted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_art_exec ON browser_artifacts(execution_id);

-- 90. Governed Browser Security Events
CREATE TABLE IF NOT EXISTS browser_security_events (
    event_id TEXT PRIMARY KEY,
    execution_id TEXT,
    session_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- UNAUTHORIZED_DOMAIN, PROMPT_INJECTION, SSRF_ATTEMPT, CREDENTIAL_HARVESTING_ATTEMPT, LOCALHOST_ACCESS_ATTEMPT, DANGEROUS_DOWNLOAD, SENSITIVE_UPLOAD_BLOCKED, TENANT_ISOLATION_VIOLATION, KILLSWITCH_TERMINATION, DOM_MANIPULATION_ANOMALY
    severity TEXT NOT NULL DEFAULT 'HIGH', -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON NOT NULL,
    source TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_sec_tenant ON browser_security_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_br_sec_type ON browser_security_events(event_type);

-- 91. Governed Browser Human-in-the-Loop Approvals
CREATE TABLE IF NOT EXISTS browser_approvals (
    approval_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    target_url TEXT NOT NULL,
    action_description TEXT NOT NULL,
    risk_class TEXT NOT NULL, -- FINANCIAL, PRIVILEGED, DESTRUCTIVE, IRREVERSIBLE, BUSINESS_MUTATION
    financial_exposure REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED
    decision_by TEXT,
    decision_reason TEXT,
    created_at REAL NOT NULL,
    decided_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_br_appr_exec ON browser_approvals(execution_id);
CREATE INDEX IF NOT EXISTS idx_br_appr_status ON browser_approvals(status);

-- 62. Temporal Durable Execution Runtime (Project 09)
CREATE TABLE IF NOT EXISTS temporal_runtimes (
    cluster_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    server_address TEXT NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'default',
    version TEXT NOT NULL DEFAULT '1.26.2',
    status TEXT NOT NULL DEFAULT 'ONLINE',
    tls_enabled INTEGER NOT NULL DEFAULT 0,
    metrics JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS temporal_workers (
    worker_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_queue TEXT NOT NULL,
    capability_scope JSON,
    status TEXT NOT NULL DEFAULT 'ONLINE', -- ONLINE, BUSY, PAUSED, OFFLINE, QUARANTINED
    runtime_version TEXT NOT NULL,
    worker_version TEXT NOT NULL,
    supported_activities JSON,
    max_concurrent_activities INTEGER NOT NULL DEFAULT 10,
    max_concurrent_workflows INTEGER NOT NULL DEFAULT 10,
    heartbeat_at REAL NOT NULL,
    created_at REAL NOT NULL,
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_worker_tenant ON temporal_workers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_temp_worker_queue ON temporal_workers(task_queue);
CREATE INDEX IF NOT EXISTS idx_temp_worker_status ON temporal_workers(status);

CREATE TABLE IF NOT EXISTS temporal_task_queues (
    queue_name TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    workload_type TEXT NOT NULL, -- BROWSER, OPENHANDS, MCP, A2A, AI, FINANCIAL, DOCUMENTS, RESEARCH, INTERNAL
    security_level TEXT NOT NULL DEFAULT 'STANDARD', -- STANDARD, HIGH_RISK, PRIVILEGED, FINANCIAL
    concurrency_limit INTEGER NOT NULL DEFAULT 20,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 600,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    description TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_queue_tenant ON temporal_task_queues(tenant_id);

CREATE TABLE IF NOT EXISTS temporal_workflows (
    workflow_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    task_id TEXT,
    workflow_type TEXT NOT NULL,
    task_queue TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING', -- RUNNING, COMPLETED, FAILED, CANCELLED, TERMINATED, CONTINUED_AS_NEW, TIMED_OUT, PAUSED, AWAITING_APPROVAL, RECONCILIATION_REQUIRED, UNKNOWN_OUTCOME
    workflow_version TEXT NOT NULL DEFAULT 'v1.0.0',
    runtime_version TEXT NOT NULL DEFAULT '1.26.2',
    input_payload JSON,
    result_payload JSON,
    error_message TEXT,
    idempotency_key TEXT,
    execution_budget JSON,
    resource_usage JSON,
    verification_status TEXT DEFAULT 'UNVERIFIED', -- UNVERIFIED, VERIFIED, FAILED
    evidence_package_id TEXT,
    parent_workflow_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_wf_tenant ON temporal_workflows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_temp_wf_comp ON temporal_workflows(company_id);
CREATE INDEX IF NOT EXISTS idx_temp_wf_mission ON temporal_workflows(mission_id);
CREATE INDEX IF NOT EXISTS idx_temp_wf_status ON temporal_workflows(status);
CREATE INDEX IF NOT EXISTS idx_temp_wf_idemp ON temporal_workflows(idempotency_key);

CREATE TABLE IF NOT EXISTS temporal_activity_executions (
    activity_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    task_queue TEXT NOT NULL,
    worker_id TEXT,
    status TEXT NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, STARTED, COMPLETED, FAILED, TIMED_OUT, CANCELLED, AWAITING_APPROVAL, RECONCILING, UNKNOWN_OUTCOME
    risk_class TEXT NOT NULL DEFAULT 'SAFE_RETRY', -- READ_ONLY, SAFE_RETRY, IDEMPOTENT_MUTATION, NON_IDEMPOTENT_MUTATION, FINANCIAL_MUTATION, DESTRUCTIVE, IRREVERSIBLE
    attempt INTEGER NOT NULL DEFAULT 1,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    backoff_seconds REAL NOT NULL DEFAULT 1.0,
    timeout_seconds REAL NOT NULL DEFAULT 30.0,
    heartbeat_timeout_seconds REAL NOT NULL DEFAULT 10.0,
    idempotency_key TEXT,
    input_payload JSON,
    result_payload JSON,
    error_message TEXT,
    requires_approval INTEGER NOT NULL DEFAULT 0,
    approval_id TEXT,
    outcome_status TEXT DEFAULT 'PENDING',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(workflow_id) REFERENCES temporal_workflows(workflow_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_act_wf ON temporal_activity_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_temp_act_status ON temporal_activity_executions(status);
CREATE INDEX IF NOT EXISTS idx_temp_act_idemp ON temporal_activity_executions(idempotency_key);

CREATE TABLE IF NOT EXISTS temporal_workflow_events (
    event_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_index INTEGER NOT NULL,
    payload JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(workflow_id) REFERENCES temporal_workflows(workflow_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_ev_wf ON temporal_workflow_events(workflow_id);
CREATE INDEX IF NOT EXISTS idx_temp_ev_idx ON temporal_workflow_events(workflow_id, event_index);

CREATE TABLE IF NOT EXISTS temporal_approvals (
    approval_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    activity_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    required_role TEXT NOT NULL DEFAULT 'OWNER',
    risk_level TEXT NOT NULL DEFAULT 'HIGH',
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, CANCELLED, TIMED_OUT
    requested_action JSON,
    decided_by TEXT,
    decision_reason TEXT,
    requested_at REAL NOT NULL,
    decided_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(workflow_id) REFERENCES temporal_workflows(workflow_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_appr_wf ON temporal_approvals(workflow_id);
CREATE INDEX IF NOT EXISTS idx_temp_appr_status ON temporal_approvals(status);

CREATE TABLE IF NOT EXISTS temporal_reconciliations (
    reconciliation_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    activity_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    external_ref TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, RECONCILED, ESCALATED, FAILED
    pre_state JSON,
    external_observed_state JSON,
    post_reconciled_state JSON,
    resolution TEXT,
    created_at REAL NOT NULL,
    resolved_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_rec_wf ON temporal_reconciliations(workflow_id);
CREATE INDEX IF NOT EXISTS idx_temp_rec_status ON temporal_reconciliations(status);

CREATE TABLE IF NOT EXISTS temporal_compensations (
    compensation_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    activity_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    saga_step TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, EXECUTED, FAILED, CANCELLED
    action_type TEXT NOT NULL,
    compensation_payload JSON,
    result JSON,
    created_at REAL NOT NULL,
    executed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_comp_wf ON temporal_compensations(workflow_id);

CREATE TABLE IF NOT EXISTS temporal_security_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    workflow_id TEXT,
    activity_id TEXT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_sec_tenant ON temporal_security_events(tenant_id);

CREATE TABLE IF NOT EXISTS temporal_schedules (
    schedule_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    cron_expression TEXT,
    interval_seconds INTEGER,
    workflow_type TEXT NOT NULL,
    task_queue TEXT NOT NULL,
    input_payload JSON,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, DELETED
    last_run_at REAL,
    next_run_at REAL,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_sched_tenant ON temporal_schedules(tenant_id);

-- ============================================================================
-- 10. Nango External System Connectivity & Integration Layer (Project 10)
-- ============================================================================

CREATE TABLE IF NOT EXISTS nango_runtimes (
    runtime_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ONLINE', -- ONLINE, OFFLINE, DEGRADED, MAINTENANCE
    version TEXT NOT NULL DEFAULT '0.64.0',
    adapter_version TEXT NOT NULL DEFAULT '1.0.0',
    nango_host TEXT DEFAULT 'http://localhost:3003',
    secret_key_ref TEXT,
    config JSON,
    last_heartbeat REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_rt_tenant ON nango_runtimes(tenant_id);

CREATE TABLE IF NOT EXISTS nango_providers (
    provider_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- CRM, ERP, HRIS, ACCOUNTING, MARKETING, COMMUNICATION, PAYMENTS, STORAGE, TICKETING, DEVOPS, ECOMMERCE
    auth_mode TEXT NOT NULL DEFAULT 'OAUTH2', -- OAUTH2, OAUTH1, API_KEY, BASIC
    docs_url TEXT,
    supported_scopes JSON,
    default_config JSON,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nango_prov_cat ON nango_providers(category);

CREATE TABLE IF NOT EXISTS nango_connections (
    connection_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    connection_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- DISCOVER, INSTALL, AUTHORIZE, CONNECT, VALIDATE, ACTIVE, DEGRADED, REAUTH_REQUIRED, DISCONNECTED, REVOKED
    auth_type TEXT NOT NULL DEFAULT 'OAUTH2',
    credential_ref TEXT NOT NULL,
    granted_scopes JSON,
    metadata JSON,
    health_status TEXT NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, DEGRADED, AUTH_REQUIRED, RATE_LIMITED, PROVIDER_ERROR, CONFIGURATION_ERROR, DISCONNECTED, REVOKED, UNKNOWN
    last_health_check REAL NOT NULL,
    last_sync_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(provider_id) REFERENCES nango_providers(provider_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_conn_tenant ON nango_connections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_nango_conn_comp ON nango_connections(company_id);
CREATE INDEX IF NOT EXISTS idx_nango_conn_prov ON nango_connections(provider_id);
CREATE INDEX IF NOT EXISTS idx_nango_conn_status ON nango_connections(status);

CREATE TABLE IF NOT EXISTS nango_capabilities (
    capability_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    action_name TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_class TEXT NOT NULL DEFAULT 'LOW_RISK', -- READ_ONLY, LOW_RISK, DATA_ENTRY, BUSINESS_MUTATION, FINANCIAL, PRIVILEGED, DESTRUCTIVE, IRREVERSIBLE
    required_scope TEXT,
    required_role TEXT NOT NULL DEFAULT 'OPERATOR',
    idempotency_strategy TEXT NOT NULL DEFAULT 'IDEMPOTENCY_KEY', -- IDEMPOTENCY_KEY, EXTERNAL_ID, DEDUPLICATION, NONE
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    FOREIGN KEY(provider_id) REFERENCES nango_providers(provider_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_cap_prov ON nango_capabilities(provider_id);
CREATE INDEX IF NOT EXISTS idx_nango_cap_risk ON nango_capabilities(risk_class);

CREATE TABLE IF NOT EXISTS nango_executions (
    execution_id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    capability_id TEXT,
    action_name TEXT NOT NULL,
    risk_class TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, IN_PROGRESS, SUCCESS, FAILED, TIMED_OUT, UNKNOWN_OUTCOME, AWAITING_APPROVAL, CANCELLED
    idempotency_key TEXT,
    input_payload JSON,
    response_payload JSON,
    error_message TEXT,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    evidence_ledger_id TEXT,
    outcome_status TEXT DEFAULT 'PENDING',
    created_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(connection_id) REFERENCES nango_connections(connection_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_exec_conn ON nango_executions(connection_id);
CREATE INDEX IF NOT EXISTS idx_nango_exec_status ON nango_executions(status);
CREATE INDEX IF NOT EXISTS idx_nango_exec_idemp ON nango_executions(idempotency_key);

CREATE TABLE IF NOT EXISTS nango_webhooks (
    webhook_id TEXT PRIMARY KEY,
    connection_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    signature TEXT,
    payload_digest TEXT NOT NULL,
    payload_data JSON,
    status TEXT NOT NULL DEFAULT 'RECEIVED', -- RECEIVED, VERIFIED, REJECTED, PROCESSED, DEAD_LETTER
    error_reason TEXT,
    mission_id TEXT,
    temporal_workflow_id TEXT,
    created_at REAL NOT NULL,
    processed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_wh_tenant ON nango_webhooks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_nango_wh_status ON nango_webhooks(status);

CREATE TABLE IF NOT EXISTS nango_sync_jobs (
    sync_job_id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    sync_type TEXT NOT NULL DEFAULT 'INCREMENTAL', -- INITIAL, INCREMENTAL, WEBHOOK_TRIGGERED, SCHEDULED, MANUAL
    status TEXT NOT NULL DEFAULT 'IDLE', -- IDLE, RUNNING, COMPLETED, FAILED, PAUSED, RECONCILING
    cursor TEXT,
    frequency_seconds INTEGER NOT NULL DEFAULT 3600,
    last_run_at REAL,
    next_run_at REAL,
    records_processed INTEGER NOT NULL DEFAULT 0,
    records_created INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(connection_id) REFERENCES nango_connections(connection_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_sync_conn ON nango_sync_jobs(connection_id);
CREATE INDEX IF NOT EXISTS idx_nango_sync_status ON nango_sync_jobs(status);

CREATE TABLE IF NOT EXISTS nango_sync_records (
    record_id TEXT PRIMARY KEY,
    sync_job_id TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    object_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    data_payload JSON,
    provenance_meta JSON, -- SOURCE_SYSTEM, SOURCE_PROVIDER, SOURCE_OBJECT, SOURCE_ID, SOURCE_CONNECTION, SYNC_TIME, SYNC_RUN, TENANT, COMPANY
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(sync_job_id) REFERENCES nango_sync_jobs(sync_job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_rec_sync ON nango_sync_records(sync_job_id);
CREATE INDEX IF NOT EXISTS idx_nango_rec_ext ON nango_sync_records(external_id);

CREATE TABLE IF NOT EXISTS nango_rate_limits (
    rate_limit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    window_seconds INTEGER NOT NULL DEFAULT 60,
    max_requests INTEGER NOT NULL DEFAULT 120,
    current_requests INTEGER NOT NULL DEFAULT 0,
    remaining_quota INTEGER NOT NULL DEFAULT 120,
    reset_at REAL NOT NULL,
    backoff_seconds REAL NOT NULL DEFAULT 0.0,
    last_throttled_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_rl_tenant ON nango_rate_limits(tenant_id);

CREATE TABLE IF NOT EXISTS nango_security_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    connection_id TEXT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    details JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_sec_tenant ON nango_security_events(tenant_id);

CREATE TABLE IF NOT EXISTS nango_reconciliations (
    reconciliation_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    external_id TEXT,
    idempotency_key TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, RECONCILED, ESCALATED, FAILED
    pre_state JSON,
    observed_state JSON,
    post_state JSON,
    resolution TEXT,
    created_at REAL NOT NULL,
    resolved_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nango_rec_conn ON nango_reconciliations(connection_id);
CREATE INDEX IF NOT EXISTS idx_nango_rec_status ON nango_reconciliations(status);

-- =========================================================================
-- ZONATA V8: AI CEO Executive Operating Layer & Corporate Operating System
-- =========================================================================

-- 1. Corporate Objectives
CREATE TABLE IF NOT EXISTS corporate_objectives (
    objective_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    provenance TEXT NOT NULL DEFAULT 'OWNER_DEFINED', -- OWNER_DEFINED, CEO_PROPOSED, DATA_DERIVED, AI_INFERRED
    time_horizon TEXT NOT NULL DEFAULT 'QUARTERLY', -- IMMEDIATE, TODAY, MONTHLY, QUARTERLY, ANNUAL, STRATEGIC
    target_dimensions JSON,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- PROPOSED, ACTIVE, ACHIEVED, DEVIATED, CANCELLED, REVISED
    parent_objective_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata JSON,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_corp_obj_tc ON corporate_objectives(tenant_id, company_id);

-- 2. Strategic Plans
CREATE TABLE IF NOT EXISTS strategic_plans (
    strategy_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    objective_id TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    title TEXT NOT NULL,
    rationale TEXT,
    assumptions JSON,
    constraints JSON,
    dependencies JSON,
    required_capabilities JSON,
    required_workforce JSON,
    required_budget REAL DEFAULT 0.0,
    expected_outcomes JSON,
    milestones JSON,
    risks JSON,
    review_date REAL,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- DRAFT, PROPOSED, ACTIVE, SUPERSEDED, ACHIEVED, ABANDONED
    owner TEXT NOT NULL DEFAULT 'AI_CEO',
    evidence_refs JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_strat_plans_tc ON strategic_plans(tenant_id, company_id);

-- 3. Strategy Versions (Never overwrite strategic history)
CREATE TABLE IF NOT EXISTS strategy_versions (
    version_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    previous_version TEXT,
    new_version TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence JSON,
    affected_objectives JSON,
    affected_departments JSON,
    affected_workforce JSON,
    affected_missions JSON,
    approval_id TEXT,
    ceo_version TEXT NOT NULL DEFAULT 'V8.0.0',
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_strat_vers_strat ON strategy_versions(strategy_id);

-- 4. Strategic Priorities (P0 Critical, P1 Strategic, P2 Operational, P3 Opportunistic)
CREATE TABLE IF NOT EXISTS strategic_priorities (
    priority_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    item_type TEXT NOT NULL, -- OBJECTIVE, STRATEGY, MISSION, DEPARTMENT
    item_id TEXT NOT NULL,
    priority_level TEXT NOT NULL, -- P0, P1, P2, P3
    reason TEXT,
    evidence_ref TEXT,
    decision_record_id TEXT,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_strat_prio_tc ON strategic_priorities(tenant_id, company_id);

-- 5. Department Objectives
CREATE TABLE IF NOT EXISTS department_objectives (
    dept_obj_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    corporate_objective_id TEXT NOT NULL,
    department TEXT NOT NULL,
    chief_officer_role TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    kpi_targets JSON,
    kra_targets JSON,
    allocated_budget REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_dept_obj_tc ON department_objectives(tenant_id, company_id);

-- 6. Executive State Persistence
CREATE TABLE IF NOT EXISTS executive_state (
    state_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    snapshot JSON NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    last_loop_stage TEXT NOT NULL DEFAULT 'OBSERVE',
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_exec_state_tc ON executive_state(tenant_id, company_id);

-- 7. Executive Decisions
CREATE TABLE IF NOT EXISTS executive_decisions (
    decision_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    problem_statement TEXT,
    alternatives_considered JSON,
    selected_option TEXT,
    rationale TEXT,
    constraints JSON,
    authority_required TEXT,
    approval_status TEXT NOT NULL DEFAULT 'PROPOSED', -- PROPOSED, PENDING_APPROVAL, APPROVED, REJECTED, EXECUTING, EXECUTED, VERIFIED, FAILED, ESCALATED, UNKNOWN
    approval_id TEXT,
    execution_status TEXT NOT NULL DEFAULT 'PENDING',
    evidence_refs JSON,
    outcome JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_dec_tc ON executive_decisions(tenant_id, company_id);

-- 8. Executive Decision Evidence
CREATE TABLE IF NOT EXISTS executive_decision_evidence (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'VERIFIED', -- VERIFIED, PARTIAL, UNVERIFIED, CONFLICTING, STALE, UNKNOWN
    evidence_data JSON,
    sha256_digest TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_evid_dec ON executive_decision_evidence(decision_id);

-- 9. Executive Risks
CREATE TABLE IF NOT EXISTS executive_risks (
    risk_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    probability REAL NOT NULL DEFAULT 0.5,
    impact REAL NOT NULL DEFAULT 0.5,
    severity TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    affected_objective_id TEXT,
    affected_mission_id TEXT,
    owner TEXT NOT NULL,
    mitigation TEXT,
    contingency TEXT,
    status TEXT NOT NULL DEFAULT 'IDENTIFIED', -- IDENTIFIED, MONITORED, MITIGATED, ACCEPTED, ESCALATED, MATERIALIZED, CLOSED
    evidence_ref TEXT,
    review_date REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_risks_tc ON executive_risks(tenant_id, company_id);

-- 10. Executive Opportunities
CREATE TABLE IF NOT EXISTS executive_opportunities (
    opportunity_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    estimated_value REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.5,
    required_resources JSON,
    strategic_alignment TEXT,
    risks JSON,
    deadline REAL,
    owner TEXT,
    status TEXT NOT NULL DEFAULT 'DISCOVERED', -- DISCOVERED, ASSESSED, PROPOSED, APPROVED, PURSUING, REALIZED, ABANDONED
    evidence_ref TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_opps_tc ON executive_opportunities(tenant_id, company_id);

-- 11. Executive Resource Allocations
CREATE TABLE IF NOT EXISTS executive_resource_allocations (
    allocation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    scope_type TEXT NOT NULL, -- COMPANY, DEPARTMENT, MISSION, EMPLOYEE
    scope_id TEXT NOT NULL,
    parent_allocation_id TEXT,
    budget_limit REAL NOT NULL DEFAULT 0.0,
    committed_spend REAL NOT NULL DEFAULT 0.0,
    actual_spend REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT '₹',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_res_tc ON executive_resource_allocations(tenant_id, company_id);

-- 12. Executive Observations
CREATE TABLE IF NOT EXISTS executive_observations (
    observation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    observation_type TEXT NOT NULL, -- NORMAL, DEVIATION, RISK, OPPORTUNITY, BLOCKED, UNKNOWN, STALE_DATA
    category TEXT NOT NULL,
    metric_name TEXT,
    baseline_value REAL,
    target_value REAL,
    actual_value REAL,
    variance REAL,
    trend TEXT,
    summary TEXT NOT NULL,
    details JSON,
    confidence TEXT NOT NULL DEFAULT 'VERIFIED',
    evidence_ref TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_obs_tc ON executive_observations(tenant_id, company_id);

-- 13. Executive Reports
CREATE TABLE IF NOT EXISTS executive_reports (
    report_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    report_type TEXT NOT NULL, -- DAILY_BRIEF, WEEKLY_REVIEW, MONTHLY_STRATEGIC, INCIDENT_ANALYSIS, END_TO_END_ACCEPTANCE
    title TEXT NOT NULL,
    content JSON NOT NULL,
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT', -- DRAFT, PUBLISHED, ARCHIVED
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_reports_tc ON executive_reports(tenant_id, company_id);

-- 14. Executive Approval Queue
CREATE TABLE IF NOT EXISTS executive_approval_queue (
    approval_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    decision_id TEXT,
    action_type TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    summary TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
    parameters JSON,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, EXPIRED
    resolved_by TEXT,
    resolution_reason TEXT,
    created_at REAL NOT NULL,
    resolved_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exec_appr_tc ON executive_approval_queue(tenant_id, company_id);

-- 15. Transactional Outbox for Reliable Event & Mutation Publishing
CREATE TABLE IF NOT EXISTS transactional_outbox (
    outbox_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSON NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    published_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON transactional_outbox(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_outbox_idempotency ON transactional_outbox(idempotency_key);

-- 16. External Action Reconciliation Receipts
CREATE TABLE IF NOT EXISTS reconciliation_receipts (
    receipt_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    system_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    expected_state JSON NOT NULL,
    actual_state JSON NOT NULL,
    reconciliation_status TEXT NOT NULL,
    evidence_digest TEXT NOT NULL,
    evidence_classification TEXT NOT NULL DEFAULT 'LOCAL_REAL_EXECUTION',
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_reconcil_tc ON reconciliation_receipts(tenant_id, system_type);

-- 17. Executive Incident Engine
CREATE TABLE IF NOT EXISTS executive_incidents (
    incident_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    current_state TEXT NOT NULL DEFAULT 'DETECTED',
    description TEXT NOT NULL,
    evidence_ref TEXT,
    containment_action TEXT,
    postmortem JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    closed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_incidents_tc ON executive_incidents(tenant_id, current_state);

-- 18. Executive Policy / Decision Boundary Rules
CREATE TABLE IF NOT EXISTS executive_policy_rules (
    rule_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL,
    action_category TEXT NOT NULL,
    max_amount_inr REAL NOT NULL DEFAULT 0.0,
    requires_human_approval INTEGER NOT NULL DEFAULT 0,
    dual_key_required INTEGER NOT NULL DEFAULT 0,
    is_forbidden INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_policy_rules ON executive_policy_rules(tenant_id, role, action_category);



-- Additional Canonical Subsystem Tables
CREATE TABLE IF NOT EXISTS company_processes (
        process_id TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT,
        trigger_type TEXT,
        sla TEXT,
        owner_role TEXT,
        stages TEXT,
        status TEXT,
        created_at REAL
    );

CREATE TABLE IF NOT EXISTS mission_tasks (
        task_id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        title TEXT NOT NULL,
        assigned_agent TEXT,
        stage TEXT,
        dependencies TEXT,
        state TEXT,
        tool_requirements TEXT,
        evidence_hash TEXT,
        created_at REAL,
        completed_at REAL
    );

CREATE TABLE IF NOT EXISTS auth_revoked_tokens (
            token_id TEXT PRIMARY KEY,
            revoked_at REAL NOT NULL,
            reason TEXT DEFAULT 'LOGOUT_OR_REVOCATION'
        );

CREATE TABLE IF NOT EXISTS supervisor_heartbeats (
            heartbeat_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            company_id TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            health_score REAL,
            active_schedules INTEGER DEFAULT 0,
            active_workers INTEGER DEFAULT 0,
            disk_status TEXT,
            anomalies_detected INTEGER DEFAULT 0,
            timestamp REAL NOT NULL
        );

CREATE TABLE IF NOT EXISTS governed_agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT DEFAULT '1.0.0',
            tenant_id TEXT NOT NULL,
            company_id TEXT NOT NULL,
            role TEXT NOT NULL,
            parent_agent_id TEXT,
            delegation_depth INTEGER DEFAULT 0,
            capabilities TEXT DEFAULT '[]',
            allowed_tools TEXT DEFAULT '[]',
            resource_budget TEXT DEFAULT '{}',
            lifecycle_state TEXT NOT NULL,
            health_status TEXT DEFAULT 'HEALTHY',
            is_quarantined INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
        );

CREATE TABLE IF NOT EXISTS governed_tools (
            tool_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT DEFAULT '1.0.0',
            tenant_id TEXT NOT NULL,
            company_id TEXT NOT NULL,
            source_type TEXT DEFAULT 'SYNTHESIZED',
            risk_class TEXT NOT NULL,
            input_schema TEXT DEFAULT '{}',
            output_schema TEXT DEFAULT '{}',
            filesystem_policy TEXT DEFAULT 'SANDBOX_ONLY',
            network_policy TEXT DEFAULT 'BLOCKED',
            lifecycle_state TEXT NOT NULL,
            security_status TEXT DEFAULT 'PENDING_SCAN',
            created_at REAL NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
        );

CREATE TABLE IF NOT EXISTS tenant_agent_quotas (
            tenant_id TEXT PRIMARY KEY,
            max_agents INTEGER DEFAULT 100,
            max_child_per_parent INTEGER DEFAULT 5,
            max_delegation_depth INTEGER DEFAULT 4,
            max_concurrent_missions INTEGER DEFAULT 20,
            max_tool_calls INTEGER DEFAULT 100,
            max_runtime_sec INTEGER DEFAULT 3600,
            max_token_budget INTEGER DEFAULT 1000000,
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
        );

CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at REAL NOT NULL,
            execution_time_ms REAL NOT NULL,
            status TEXT NOT NULL
        );

CREATE TABLE IF NOT EXISTS optimistic_lock_registry (
    table_name TEXT PRIMARY KEY,
    version_column TEXT NOT NULL DEFAULT 'version',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS async_command_queue (
                action_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                mission_id TEXT,
                workflow_id TEXT,
                agent_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED, ASSIGNED, EXECUTING, COMPLETED, FAILED, TIMED_OUT, UNKNOWN_OUTCOME
                envelope_payload JSON NOT NULL,
                worker_id TEXT,
                result_payload JSON,
                error_message TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL
            );

CREATE TABLE IF NOT EXISTS agent_packages (
                package_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                version TEXT NOT NULL,
                role TEXT NOT NULL,
                package_payload JSON NOT NULL,
                package_hash TEXT NOT NULL,
                signature TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CANDIDATE', -- CANDIDATE, CANARY, ACTIVE, DEPRECATED, ROLLED_BACK
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS tool_packages (
                tool_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                source_code TEXT NOT NULL,
                sandbox_profile JSON NOT NULL,
                signature TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CANDIDATE', -- CANDIDATE, TESTING, ACTIVE, REVOKED
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS organization_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                parent_id TEXT,
                metadata JSON,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS organization_edges (
                edge_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL, -- REPORTS_TO, MEMBER_OF, MANAGES, SHARED_SERVICE_WITH
                metadata JSON,
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS corporate_data_objects (
                object_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                data_class TEXT NOT NULL,
                source_system TEXT NOT NULL,
                source_object_id TEXT NOT NULL,
                classification_level TEXT NOT NULL,
                sensitivity_categories JSON NOT NULL,
                owner_identity_id TEXT NOT NULL,
                acl JSON NOT NULL,
                content_hash TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                residency_region TEXT NOT NULL DEFAULT 'US-EAST',
                retention_days INTEGER NOT NULL DEFAULT 365,
                legal_hold INTEGER NOT NULL DEFAULT 0,
                deletion_state TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                provenance JSON
            );

CREATE TABLE IF NOT EXISTS knowledge_index_chunks (
                chunk_id TEXT PRIMARY KEY,
                object_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text_content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                classification_level TEXT NOT NULL,
                allowed_departments JSON NOT NULL,
                allowed_roles JSON NOT NULL,
                allowed_identities JSON NOT NULL,
                source_system TEXT NOT NULL,
                deletion_state TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS lineage_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                label TEXT NOT NULL,
                attributes JSON NOT NULL,
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS lineage_edges (
                edge_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                metadata JSON,
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS enterprise_budgets (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                allocated_usd REAL NOT NULL,
                spent_usd REAL NOT NULL DEFAULT 0.0,
                reserved_usd REAL NOT NULL DEFAULT 0.0,
                allocated_tokens BIGINT NOT NULL DEFAULT 0,
                spent_tokens BIGINT NOT NULL DEFAULT 0,
                reserved_tokens BIGINT NOT NULL DEFAULT 0,
                soft_limit_pct REAL NOT NULL DEFAULT 80.0,
                hard_limit_pct REAL NOT NULL DEFAULT 100.0,
                is_frozen INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS enterprise_budget_reservations (
                reservation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                scope_key TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                reserved_usd REAL NOT NULL DEFAULT 0.0,
                reserved_tokens BIGINT NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'RESERVED',
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                settled_at REAL,
                actual_usd REAL DEFAULT 0.0,
                actual_tokens BIGINT DEFAULT 0,
                metadata JSON,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
CREATE INDEX IF NOT EXISTS idx_budget_res_tenant ON enterprise_budget_reservations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_budget_res_entity ON enterprise_budget_reservations(entity_id);
CREATE INDEX IF NOT EXISTS idx_budget_res_status ON enterprise_budget_reservations(status);

CREATE TABLE IF NOT EXISTS action_approval_nonces (
                nonce TEXT PRIMARY KEY,
                approval_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                action_digest TEXT NOT NULL,
                approver_id TEXT NOT NULL,
                approver_role TEXT NOT NULL,
                signature TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                consumed_at REAL,
                consumed_by_action_id TEXT,
                metadata JSON,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
CREATE INDEX IF NOT EXISTS idx_appr_nonce_tenant ON action_approval_nonces(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appr_nonce_status ON action_approval_nonces(status);
CREATE INDEX IF NOT EXISTS idx_appr_nonce_digest ON action_approval_nonces(action_digest);

CREATE TABLE IF NOT EXISTS tenant_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'STARTER',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                current_period_start REAL NOT NULL,
                current_period_end REAL NOT NULL,
                grace_period_end REAL,
                cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
                payment_provider TEXT NOT NULL DEFAULT 'internal',
                provider_customer_id TEXT,
                provider_subscription_id TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata JSON,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
CREATE INDEX IF NOT EXISTS idx_tenant_sub_tenant ON tenant_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_sub_status ON tenant_subscriptions(status);

CREATE TABLE IF NOT EXISTS billing_webhook_events (
                event_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload JSON,
                processed_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PROCESSED',
                error_message TEXT
            );
CREATE INDEX IF NOT EXISTS idx_bwh_provider_event ON billing_webhook_events(provider, event_id);
CREATE INDEX IF NOT EXISTS idx_bwh_status ON billing_webhook_events(status);

CREATE TABLE IF NOT EXISTS tenant_invoices (
                invoice_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                subscription_id TEXT,
                amount_due_usd REAL NOT NULL,
                amount_paid_usd REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'PAID',
                period_start REAL NOT NULL,
                period_end REAL NOT NULL,
                line_items JSON,
                created_at REAL NOT NULL,
                paid_at REAL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
CREATE INDEX IF NOT EXISTS idx_invoice_tenant ON tenant_invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON tenant_invoices(status);

CREATE TABLE IF NOT EXISTS security_incidents (
                incident_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                description TEXT NOT NULL,
                details JSON NOT NULL,
                is_mitigated INTEGER NOT NULL DEFAULT 0,
                timestamp REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS governed_memory_records (
                record_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                trust_state TEXT NOT NULL DEFAULT 'UNVERIFIED',
                content TEXT NOT NULL,
                confidence_score REAL NOT NULL DEFAULT 0.5,
                source_reference TEXT,
                is_authoritative INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                expires_at REAL
            );

CREATE TABLE IF NOT EXISTS agent_evaluation_runs (
                eval_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                version TEXT NOT NULL,
                security_score REAL NOT NULL,
                policy_compliance_score REAL NOT NULL,
                hallucination_rate REAL NOT NULL,
                cost_efficiency_score REAL NOT NULL,
                passed_all_safety_gates INTEGER NOT NULL,
                evaluation_details JSON NOT NULL,
                evaluated_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS immutable_agent_packages (
                package_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                agent_version TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                model_version TEXT NOT NULL,
                tool_package_hashes JSON NOT NULL,
                policy_version TEXT NOT NULL,
                composite_package_hash TEXT NOT NULL,
                certified_for_production INTEGER NOT NULL,
                created_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS unknown_outcomes (
                record_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                target_system TEXT NOT NULL,
                mutation_type TEXT NOT NULL,
                parameters JSON NOT NULL,
                idempotency_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_RECONCILIATION',
                reconciliation_attempts INTEGER NOT NULL DEFAULT 0,
                reconciliation_result JSON,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS external_idp_directory (
                scim_id TEXT PRIMARY KEY,
                external_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                username TEXT NOT NULL,
                display_name TEXT NOT NULL,
                email TEXT NOT NULL,
                groups JSON NOT NULL,
                roles JSON NOT NULL,
                department TEXT NOT NULL,
                active INTEGER NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

CREATE TABLE IF NOT EXISTS workforce_scheduler_queue (
                task_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                department TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, SUSPENDED, TIMED_OUT
                assigned_employee_id TEXT,
                budget_usd REAL NOT NULL,
                dependencies JSON NOT NULL,
                created_at REAL NOT NULL,
                dispatched_at REAL,
                completed_at REAL
            );

CREATE TABLE IF NOT EXISTS tenant_resource_quotas (
                tenant_id TEXT PRIMARY KEY,
                max_active_missions INTEGER NOT NULL DEFAULT 100,
                max_ai_employees INTEGER NOT NULL DEFAULT 50,
                max_tokens_per_minute INTEGER NOT NULL DEFAULT 500000,
                max_tool_calls_daily INTEGER NOT NULL DEFAULT 50000,
                max_storage_bytes INTEGER NOT NULL DEFAULT 53687091200,
                current_active_missions INTEGER NOT NULL DEFAULT 0,
                current_ai_employees INTEGER NOT NULL DEFAULT 0,
                tokens_used_this_minute INTEGER NOT NULL DEFAULT 0,
                minute_window_epoch INTEGER NOT NULL DEFAULT 0,
                daily_tool_calls INTEGER NOT NULL DEFAULT 0,
                day_window_epoch INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            );

-- 19. Disaster Recovery Manifests
CREATE TABLE IF NOT EXISTS disaster_recovery_manifests (
    manifest_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    backup_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256_checksum TEXT NOT NULL,
    merkle_root TEXT NOT NULL,
    record_counts JSON NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dr_manifests ON disaster_recovery_manifests(tenant_id, created_at);

-- 20. CRM & Commercial Pipeline
CREATE TABLE IF NOT EXISTS crm_customers (
    customer_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    legal_name TEXT,
    tier TEXT NOT NULL DEFAULT 'STANDARD',
    industry TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    health_score REAL NOT NULL DEFAULT 100.0,
    arr REAL NOT NULL DEFAULT 0.0,
    ltv REAL NOT NULL DEFAULT 0.0,
    gstin TEXT,
    address TEXT,
    sla_level TEXT NOT NULL DEFAULT 'Standard 99.9%',
    renewal_date TEXT,
    assigned_agent TEXT,
    contacts JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_crm_customers ON crm_customers(tenant_id, company_id);

CREATE TABLE IF NOT EXISTS crm_deals (
    deal_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    customer_id TEXT,
    title TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'discovery',
    value REAL NOT NULL DEFAULT 0.0,
    probability REAL NOT NULL DEFAULT 0.5,
    closing_date TEXT,
    owner TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_crm_deals ON crm_deals(tenant_id, company_id);

-- ============================================================================
-- 11. URA / ZONATA Enterprise AI Corporate Workforce Architecture (25 Tables)
-- ============================================================================

-- 1. Organizations (Enterprise Root Entity)
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    parent_org_id TEXT,
    legal_name TEXT NOT NULL,
    trade_name TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'US-DE',
    tax_identifier TEXT,
    incorporation_date REAL,
    fiscal_year_start_month INTEGER NOT NULL DEFAULT 1,
    base_currency TEXT NOT NULL DEFAULT 'USD',
    governance_model TEXT NOT NULL DEFAULT 'AUTONOMOUS_EXECUTIVE_HYBRID',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    metadata JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_org_id) REFERENCES organizations(org_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_org_tenant ON organizations(tenant_id);

-- 2. Corporate Departments (Control Units / Cost Centers)
CREATE TABLE IF NOT EXISTS corporate_departments (
    department_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    parent_department_id TEXT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    cost_center_code TEXT NOT NULL,
    head_position_id TEXT,
    operating_budget_usd REAL NOT NULL DEFAULT 0.0,
    headcount_ceiling INTEGER NOT NULL DEFAULT 10,
    current_headcount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_department_id) REFERENCES corporate_departments(department_id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dept_code ON corporate_departments(company_id, code);

-- 3. Corporate Positions (Organizational Roles)
CREATE TABLE IF NOT EXISTS corporate_positions (
    position_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    department_id TEXT NOT NULL,
    reports_to_position_id TEXT,
    position_code TEXT NOT NULL,
    title TEXT NOT NULL,
    hierarchy_level TEXT NOT NULL,
    job_family TEXT NOT NULL,
    headcount_limit INTEGER NOT NULL DEFAULT 1,
    current_filled_count INTEGER NOT NULL DEFAULT 0,
    default_authority_profile_id TEXT,
    is_executive INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES corporate_departments(department_id) ON DELETE CASCADE,
    FOREIGN KEY (reports_to_position_id) REFERENCES corporate_positions(position_id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pos_code ON corporate_positions(company_id, position_code);

-- 4. Corporate Employees (AI, Human, and Hybrid Fleet)
CREATE TABLE IF NOT EXISTS corporate_employees (
    employee_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    department_id TEXT NOT NULL,
    identity_type TEXT NOT NULL DEFAULT 'AI_EMPLOYEE',
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    work_email TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'PROPOSED',
    authority_profile_id TEXT,
    knowledge_profile_id TEXT,
    performance_rating REAL NOT NULL DEFAULT 100.0,
    total_tokens_used INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0.0,
    allocated_monthly_budget_usd REAL NOT NULL DEFAULT 500.0,
    spent_monthly_budget_usd REAL NOT NULL DEFAULT 0.0,
    emergency_killswitch INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (position_id) REFERENCES corporate_positions(position_id) ON DELETE RESTRICT,
    FOREIGN KEY (department_id) REFERENCES corporate_departments(department_id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_emp_pos ON corporate_employees(position_id);
CREATE INDEX IF NOT EXISTS idx_emp_state ON corporate_employees(lifecycle_state);

-- 5. Employee Reporting Relationships (Explicit Multi-Type Hierarchy DAG)
CREATE TABLE IF NOT EXISTS employee_reporting_relationships (
    relationship_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    manager_employee_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'SOLID_LINE',
    effective_from REAL NOT NULL,
    effective_to REAL,
    delegation_scope JSON,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES corporate_employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (manager_employee_id) REFERENCES corporate_employees(employee_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rep_rel ON employee_reporting_relationships(employee_id, manager_employee_id);

-- 6. Employee Authority Profiles (Machine-Enforceable Delegation of Authority DoA)
CREATE TABLE IF NOT EXISTS employee_authority_profiles (
    profile_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    max_spend_single_usd REAL NOT NULL DEFAULT 0.0,
    max_spend_monthly_usd REAL NOT NULL DEFAULT 0.0,
    max_risk_level TEXT NOT NULL DEFAULT 'LOW',
    can_hire INTEGER NOT NULL DEFAULT 0,
    can_fire INTEGER NOT NULL DEFAULT 0,
    can_enter_contracts INTEGER NOT NULL DEFAULT 0,
    can_delegate INTEGER NOT NULL DEFAULT 0,
    can_modify_sops INTEGER NOT NULL DEFAULT 0,
    dual_approval_required INTEGER NOT NULL DEFAULT 0,
    allowed_data_classifications JSON NOT NULL,
    forbidden_tool_patterns JSON NOT NULL,
    approved_tools JSON NOT NULL,
    signature_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

-- 7. Employee Knowledge Profiles (Clearance & Data Boundaries)
CREATE TABLE IF NOT EXISTS employee_knowledge_profiles (
    profile_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    clearance_level TEXT NOT NULL DEFAULT 'INTERNAL',
    permitted_domains JSON NOT NULL,
    permitted_systems JSON NOT NULL,
    forbidden_topics JSON NOT NULL,
    max_retrieval_tokens INTEGER NOT NULL DEFAULT 8192,
    data_residency_jurisdictions JSON NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

-- 8. SOP Definitions (Standard Operating Procedure Registry)
CREATE TABLE IF NOT EXISTS sop_definitions (
    sop_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    department_id TEXT NOT NULL,
    sop_code TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'EVENT_DRIVEN',
    risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
    objective TEXT NOT NULL,
    trigger_conditions JSON NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES corporate_departments(department_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sop_code ON sop_definitions(company_id, sop_code);

-- 9. SOP Versions (Immutable Version History & Executable Steps)
CREATE TABLE IF NOT EXISTS sop_versions (
    version_id TEXT PRIMARY KEY,
    sop_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    version_semver TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    steps_definition JSON NOT NULL,
    input_schema JSON NOT NULL,
    output_schema JSON NOT NULL,
    anti_gaming_rules JSON NOT NULL,
    required_authority_level TEXT NOT NULL DEFAULT 'DELEGATED',
    evidence_requirements JSON NOT NULL,
    author_employee_id TEXT NOT NULL,
    approved_by_role TEXT,
    approved_at REAL,
    sha256_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (sop_id) REFERENCES sop_definitions(sop_id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sop_ver ON sop_versions(sop_id, version_semver);

-- 10. Employee SOP Assignments (Contractual Assignment of Executable Playbooks)
CREATE TABLE IF NOT EXISTS employee_sop_assignments (
    assignment_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    sop_version_id TEXT NOT NULL,
    assignment_status TEXT NOT NULL DEFAULT 'ACTIVE',
    compliance_score REAL NOT NULL DEFAULT 100.0,
    total_executions INTEGER NOT NULL DEFAULT 0,
    failed_executions INTEGER NOT NULL DEFAULT 0,
    last_executed_at REAL,
    assigned_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES corporate_employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (sop_version_id) REFERENCES sop_versions(version_id) ON DELETE RESTRICT
);

-- 11. Employee KRAs (Key Result Areas)
CREATE TABLE IF NOT EXISTS employee_kras (
    kra_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    strategic_objective_id TEXT,
    name TEXT NOT NULL,
    weight_percentage REAL NOT NULL DEFAULT 25.0,
    accountability_statement TEXT NOT NULL,
    responsibility TEXT,
    associated_workflows JSON,
    associated_kpi_ids JSON,
    allowed_tools JSON,
    authority_scope JSON,
    escalation_rules JSON,
    expected_outcomes JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
    -- No FKs here: KRA rows are shared by the canonical corporate_employees
    -- registry and the V7 ai_employees registry, which have independent
    -- tenant/employee lifecycles. Referential checks are enforced in code.
);

-- 12. KPI Definitions (Anti-Gaming Paired Metrics Catalog)
CREATE TABLE IF NOT EXISTS kpi_definitions (
    kpi_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kra_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    unit TEXT NOT NULL,
    polarity TEXT NOT NULL DEFAULT 'HIGHER_IS_BETTER',
    target_value REAL NOT NULL,
    threshold_warning REAL NOT NULL,
    threshold_critical REAL NOT NULL,
    paired_counter_metric_id TEXT,
    counter_metric_weight REAL NOT NULL DEFAULT 0.5,
    data_source_feed TEXT NOT NULL,
    verification_method TEXT NOT NULL DEFAULT 'TRANSACTION_RECONCILIATION',
    measurement_frequency TEXT NOT NULL DEFAULT 'DAILY',
    created_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (kra_id) REFERENCES employee_kras(kra_id) ON DELETE CASCADE,
    FOREIGN KEY (paired_counter_metric_id) REFERENCES kpi_definitions(kpi_id) ON DELETE SET NULL
);

-- 13. KPI Measurements (Evidence-Sealed Real Measurements)
CREATE TABLE IF NOT EXISTS kpi_measurements (
    measurement_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    kpi_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    mission_id TEXT,
    measured_value REAL NOT NULL,
    counter_metric_value REAL,
    anti_gaming_passed INTEGER NOT NULL DEFAULT 1,
    variance_percentage REAL NOT NULL DEFAULT 0.0,
    score_contribution REAL NOT NULL DEFAULT 100.0,
    raw_evidence_json JSON NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    measured_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (kpi_id) REFERENCES kpi_definitions(kpi_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES corporate_employees(employee_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_kpi_meas ON kpi_measurements(kpi_id, employee_id, measured_at);

-- 14. Employee Performance Reviews (Explainable 4-Factor Evaluations)
CREATE TABLE IF NOT EXISTS employee_performance_reviews (
    review_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    review_period_start REAL NOT NULL,
    review_period_end REAL NOT NULL,
    kpi_achievement_score REAL NOT NULL,
    sop_compliance_score REAL NOT NULL,
    anti_gaming_compliance_score REAL NOT NULL,
    collaboration_sla_score REAL NOT NULL,
    composite_performance_score REAL NOT NULL,
    evaluator_role TEXT NOT NULL DEFAULT 'EXEC_CHRO',
    recommendation TEXT NOT NULL DEFAULT 'RETAIN',
    mathematical_proof_json JSON NOT NULL,
    is_sealed INTEGER NOT NULL DEFAULT 1,
    sealed_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES corporate_employees(employee_id) ON DELETE CASCADE
);

-- 15. Workforce Requisitions (CHRO Workforce Intelligence Pipeline)
CREATE TABLE IF NOT EXISTS workforce_requisitions (
    requisition_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    department_id TEXT NOT NULL,
    requested_position_title TEXT NOT NULL,
    requesting_executive_role TEXT NOT NULL,
    justification TEXT NOT NULL,
    gap_analysis_evidence JSON NOT NULL,
    proposed_monthly_budget_usd REAL NOT NULL DEFAULT 200.0,
    target_agent_template_id TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    chro_decision_notes TEXT,
    approved_position_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES corporate_departments(department_id) ON DELETE CASCADE
);

-- 16. Agent Capabilities (Atomic Execution Registry)
CREATE TABLE IF NOT EXISTS agent_capabilities (
    capability_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    input_schema JSON NOT NULL,
    output_schema JSON NOT NULL,
    risk_class TEXT NOT NULL DEFAULT 'READ_ONLY',
    cost_per_call_usd REAL NOT NULL DEFAULT 0.001,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cap_code ON agent_capabilities(tenant_id, code);

-- 17. Agent Templates (Reusable Capability Packages)
CREATE TABLE IF NOT EXISTS agent_templates (
    template_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT NOT NULL,
    role_category TEXT NOT NULL,
    default_capabilities JSON NOT NULL,
    default_toolset JSON NOT NULL,
    sandbox_requirements JSON NOT NULL,
    created_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tpl_slug ON agent_templates(tenant_id, slug);

-- 18. Agent Template Versions (Cryptographically Signed Blueprints)
CREATE TABLE IF NOT EXISTS agent_template_versions (
    version_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    semver TEXT NOT NULL,
    system_prompt_scaffold TEXT NOT NULL,
    capability_manifest JSON NOT NULL,
    tool_manifest JSON NOT NULL,
    resource_limits JSON NOT NULL,
    sbom_hash TEXT NOT NULL,
    signature TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    FOREIGN KEY (template_id) REFERENCES agent_templates(template_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tpl_ver ON agent_template_versions(template_id, semver);

-- 19. Agent Instances (Running Ephemeral or Persistent Execution Workers)
CREATE TABLE IF NOT EXISTS agent_instances (
    instance_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    template_version_id TEXT NOT NULL,
    bound_employee_id TEXT,
    host_runtime_id TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'IDLE',
    current_lease_id TEXT,
    allocated_tokens INTEGER NOT NULL DEFAULT 100000,
    used_tokens INTEGER NOT NULL DEFAULT 0,
    cost_incurred_usd REAL NOT NULL DEFAULT 0.0,
    last_heartbeat REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (template_version_id) REFERENCES agent_template_versions(version_id) ON DELETE RESTRICT
);

-- 20. Agent Leases (Concurrency Control & Mutex Locks)
CREATE TABLE IF NOT EXISTS agent_leases (
    lease_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    leased_by_employee_id TEXT NOT NULL,
    mission_id TEXT,
    task_id TEXT,
    lease_state TEXT NOT NULL DEFAULT 'ACTIVE',
    acquired_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    released_at REAL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES agent_instances(instance_id) ON DELETE CASCADE,
    FOREIGN KEY (leased_by_employee_id) REFERENCES corporate_employees(employee_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_lease_lookup ON agent_leases(instance_id, lease_state, expires_at);

-- 21. Agent Execution Sessions (Zero-Leakage Execution Sandboxes)
CREATE TABLE IF NOT EXISTS agent_execution_sessions (
    session_id TEXT PRIMARY KEY,
    lease_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    session_token_hash TEXT NOT NULL,
    memory_scope_id TEXT NOT NULL,
    isolation_tier TEXT NOT NULL DEFAULT 'EPHEMERAL_CONTAINER',
    credential_handle_ids JSON NOT NULL,
    execution_status TEXT NOT NULL DEFAULT 'RUNNING',
    tokens_consumed INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    started_at REAL NOT NULL,
    ended_at REAL,
    FOREIGN KEY (lease_id) REFERENCES agent_leases(lease_id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES agent_instances(instance_id) ON DELETE CASCADE
);

-- 22. Corporate Missions (Cross-Functional Strategic Initiatives)
CREATE TABLE IF NOT EXISTS corporate_missions (
    mission_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    objective_statement TEXT NOT NULL,
    lead_employee_id TEXT NOT NULL,
    sponsor_executive_role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PLANNING',
    priority_level TEXT NOT NULL DEFAULT 'P1',
    budget_limit_usd REAL NOT NULL DEFAULT 1000.0,
    spent_budget_usd REAL NOT NULL DEFAULT 0.0,
    progress_percentage REAL NOT NULL DEFAULT 0.0,
    target_delivery_timestamp REAL NOT NULL,
    completed_at REAL,
    outcome_evidence_hash TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (lead_employee_id) REFERENCES corporate_employees(employee_id) ON DELETE RESTRICT
);

-- 23. Employee Tasks (Atomic Delegated Units of Work)
CREATE TABLE IF NOT EXISTS employee_tasks (
    task_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    assigned_employee_id TEXT NOT NULL,
    delegator_employee_id TEXT NOT NULL,
    parent_task_id TEXT,
    sop_version_id TEXT,
    task_order INTEGER NOT NULL DEFAULT 1,
    dependency_task_ids JSON NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    evidence_receipt_id TEXT,
    started_at REAL,
    completed_at REAL,
    created_at REAL NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES corporate_missions(mission_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_employee_id) REFERENCES corporate_employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (parent_task_id) REFERENCES employee_tasks(task_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_task_mission ON employee_tasks(mission_id, status);

-- 24. Cross-Department Collaborations (Formal Multi-Department SLAs)
CREATE TABLE IF NOT EXISTS cross_department_collaborations (
    collab_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    initiator_dept_id TEXT NOT NULL,
    target_dept_id TEXT NOT NULL,
    deliverable_description TEXT NOT NULL,
    sla_turnaround_hours REAL NOT NULL DEFAULT 24.0,
    shared_budget_usd REAL NOT NULL DEFAULT 0.0,
    escalation_owner_role TEXT NOT NULL DEFAULT 'EXEC_COO',
    status TEXT NOT NULL DEFAULT 'REQUESTED',
    accepted_at REAL,
    fulfilled_at REAL,
    created_at REAL NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES corporate_missions(mission_id) ON DELETE CASCADE,
    FOREIGN KEY (initiator_dept_id) REFERENCES corporate_departments(department_id) ON DELETE RESTRICT,
    FOREIGN KEY (target_dept_id) REFERENCES corporate_departments(department_id) ON DELETE RESTRICT
);

-- 25. Corporate Knowledge Assets (6-Tier Data Vault)
CREATE TABLE IF NOT EXISTS corporate_knowledge_assets (
    asset_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    department_id TEXT,
    title TEXT NOT NULL,
    classification_level TEXT NOT NULL DEFAULT 'INTERNAL',
    dlp_inspection_status TEXT NOT NULL DEFAULT 'CLEAN',
    allowed_roles JSON NOT NULL,
    content_hash TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    is_customer_safe INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_asset_class ON corporate_knowledge_assets(tenant_id, classification_level);

-- 47b. Persistent Assistant Messages & Conversational Memory
CREATE TABLE IF NOT EXISTS assistant_messages (
    message_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    sender TEXT NOT NULL, -- 'user', 'assistant', 'system'
    workspace_mode TEXT NOT NULL DEFAULT 'PERSONAL', -- 'PERSONAL', 'COMPANY'
    content TEXT NOT NULL,
    intent_category TEXT, -- 'PERSONAL_TASK', 'COMPANY_DELEGATION', 'DOCUMENT_REQUEST', 'MEETING_REQUEST', 'INFORMATIONAL'
    deliverables JSON,
    citations JSON,
    timestamp REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_asst_msg_session ON assistant_messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_asst_msg_tenant_user ON assistant_messages(tenant_id, user_id);

-- 48a. Assistant explicit memory (the owner's saved preferences and facts)
CREATE TABLE IF NOT EXISTS assistant_memory (
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'PERSONAL', -- 'PERSONAL' | 'COMPANY'
    content TEXT NOT NULL,
    source_session_id TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assistant_memory_user
    ON assistant_memory(tenant_id, user_id, created_at);

-- 48b. Assistant background jobs (survive reload; max 3 active per user)
CREATE TABLE IF NOT EXISTS assistant_jobs (
    job_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    user_id TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL DEFAULT 'research',
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    workspace_mode TEXT NOT NULL DEFAULT 'PERSONAL',
    status TEXT NOT NULL DEFAULT 'QUEUED',
    progress REAL NOT NULL DEFAULT 0,
    step TEXT NOT NULL DEFAULT 'Queued',
    steps JSON,
    result JSON,
    citations JSON,
    error TEXT,
    notification_seen INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    finished_at REAL
);
CREATE INDEX IF NOT EXISTS idx_assistant_jobs_user
    ON assistant_jobs(tenant_id, user_id, created_at);

-- 48b. Assistant Generated Deliverables & Documents (Personal & Company Isolated)
CREATE TABLE IF NOT EXISTS assistant_generated_documents (
    doc_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    user_id TEXT NOT NULL,
    storage_boundary TEXT NOT NULL DEFAULT 'PERSONAL', -- 'PERSONAL', 'COMPANY'
    title TEXT NOT NULL,
    format TEXT NOT NULL, -- 'PDF', 'DOCX', 'XLSX', 'PPTX', 'CSV', 'JSON'
    category TEXT NOT NULL, -- 'REPORT', 'SUMMARY', 'FINANCIAL', 'CONTRACT', 'MEETING_MINUTES', 'MEMO', 'PRESENTATION', 'SPREADSHEET'
    file_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL,
    metadata JSON,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_asst_docs_user ON assistant_generated_documents(tenant_id, user_id, storage_boundary);
CREATE INDEX IF NOT EXISTS idx_asst_docs_company ON assistant_generated_documents(tenant_id, company_id);

-- 49b. External Calendar & Google Meet Integration Records
CREATE TABLE IF NOT EXISTS meeting_integrations (
    integration_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    meeting_id TEXT NOT NULL,
    schedule_id TEXT,
    provider TEXT NOT NULL DEFAULT 'GOOGLE_MEET', -- 'GOOGLE_MEET', 'INTERNAL_ROOM'
    meet_url TEXT NOT NULL,
    dial_in_info JSON,
    calendar_event_id TEXT,
    ai_representative_enabled INTEGER NOT NULL DEFAULT 1,
    statutory_disclosure_signed INTEGER NOT NULL DEFAULT 1,
    briefing_dossier_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mtg_int_comp ON meeting_integrations(tenant_id, company_id);
"""

class DatabaseDialect:
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class DictRow(tuple):
    """Row wrapper that supports both index and column name access."""
    def __new__(cls, values, col_names):
        inst = super().__new__(cls, values)
        inst._col_map = {name: val for name, val in zip(col_names, values)}
        return inst

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._col_map.get(key, None)
        try:
            return super().__getitem__(key)
        except (IndexError, TypeError):
            return 0

    def get(self, key, default=None):
        return self._col_map.get(key, default)

    def keys(self):
        return list(self._col_map.keys())

    def values(self):
        return list(self._col_map.values())

    def items(self):
        return list(self._col_map.items())


class PostgresCursorWrapper:
    """Cursor wrapper providing sqlite3.Row / DictCursor parity and method chaining for PostgreSQL."""
    def __init__(self, raw_cursor, normalize_fn=None):
        self._raw_cursor = raw_cursor
        self._normalize_fn = normalize_fn or normalize_sql_for_postgres

    def __getattr__(self, name):
        return getattr(self._raw_cursor, name)

    def execute(self, sql: str, params: Any = ()):
        norm = self._normalize_fn(sql)
        if norm:
            if not params:
                self._raw_cursor.execute(norm)
            else:
                self._raw_cursor.execute(norm, params)
        return self

    def executemany(self, sql: str, params_seq: Any = ()):
        norm = self._normalize_fn(sql)
        if norm:
            self._raw_cursor.executemany(norm, params_seq)
        return self

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row

    def fetchone(self):
        row = self._raw_cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, DictRow):
            return row
        if hasattr(self._raw_cursor, "description") and self._raw_cursor.description:
            col_names = [col[0] for col in self._raw_cursor.description]
            return DictRow(row, col_names)
        return row

    def fetchall(self):
        rows = self._raw_cursor.fetchall()
        if not rows:
            return []
        if rows and isinstance(rows[0], DictRow):
            return rows
        if hasattr(self._raw_cursor, "description") and self._raw_cursor.description:
            col_names = [col[0] for col in self._raw_cursor.description]
            return [DictRow(r, col_names) for r in rows]
        return rows


class DeferredRow(tuple):
    """Subscriptable tuple that behaves like an empty/default row during deferred import."""
    def __new__(cls, values=(0,)):
        return super().__new__(cls, values)

    def __getitem__(self, item):
        if isinstance(item, int) and item < len(self):
            return super().__getitem__(item)
        if isinstance(item, int):
            return 0
        return 0

    def __bool__(self):
        return False

    def get(self, key, default=0):
        return default


class DeferredCursor:
    """Cursor that records queries or returns empty results during deferred import mode."""
    def __init__(self, db_instance, sql="", params=()):
        self.db = db_instance
        self.sql = sql
        self.params = params

    def execute(self, sql: str, params: Any = ()):
        self.db._deferred_queries.append(('execute', sql, params))
        return self

    def executemany(self, sql: str, params_seq: Any = ()):
        self.db._deferred_queries.append(('executemany', sql, params_seq))
        return self

    def fetchone(self):
        return DeferredRow((0,))

    def fetchall(self):
        return []

    @property
    def rowcount(self):
        return 0

    @property
    def lastrowid(self):
        return 0

    def __iter__(self):
        return iter([])


class DeferredConnectionProxy:
    """Proxy connection returned during module import when live database is unreachable."""
    def __init__(self, db_instance):
        self.db = db_instance

    @property
    def row_factory(self):
        return getattr(self, "_row_factory", None)

    @row_factory.setter
    def row_factory(self, val):
        self._row_factory = val

    def cursor(self):
        return self

    def execute(self, sql: str, params: Any = ()):
        self.db._deferred_queries.append(('execute', sql, params))
        return DeferredCursor(self.db, sql, params)

    def executemany(self, sql: str, params_seq: Any = ()):
        self.db._deferred_queries.append(('executemany', sql, params_seq))
        return DeferredCursor(self.db, sql, params_seq)

    def executescript(self, sql_script: str):
        self.db._deferred_queries.append(('executescript', sql_script, ()))
        return DeferredCursor(self.db, sql_script)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


TABLE_PRIMARY_KEYS: Dict[str, Tuple[str, ...]] = {
    "missions": ("mission_id",),
    "tenant_concurrency_leases": ("lease_id",),
    "employees": ("agent_id",),
    "a2a_skills": ("skill_id",),
    "a2a_tasks": ("task_id",),
    "immutable_agent_packages": ("package_id",),
    "governed_agents": ("agent_id",),
    "installed_applications": ("app_id",),
    "auth_revoked_tokens": ("token_id",),
    "automation_connector_idempotency": ("idempotency_key",),
    "automation_sync_checkpoints": ("tenant_id", "stream_name", "connector_id"),
    "automation_revoked_leases": ("lease_id",),
    "enterprise_budget_allocations": ("budget_id",),
    "coworker_background_missions": ("mission_id",),
    "coworker_profiles": ("worker_id",),
    "coworker_execution_graphs": ("mission_id",),
    "coworker_execution_nodes": ("task_id",),
    "coworker_workflow_instances": ("workflow_id",),
    "workflow_resource_locks": ("lock_id",),
    "workflows": ("workflow_id",),
    "agent_blueprints": ("blueprint_id",),
    "enterprise_files": ("file_id",),
    "enterprise_records": ("record_id",),
    "enterprise_reports": ("report_id",),
    "host_capabilities": ("cap_id",),
    "enterprise_identities": ("identity_id",),
    "enterprise_killswitch_matrix": ("switch_id",),
    "employee_kpis": ("kpi_id",),
    "employee_kras": ("kra_id",),
    "mcp_tools": ("tool_id",),
    "mcp_resources": ("resource_id",),
    "mcp_published_capabilities": ("published_id",),
    "multimodal_capabilities": ("tenant_id", "capability_id"),
    "stateful_agent_identities": ("tenant_id", "agent_id"),
    "organization_nodes": ("node_id",),
    "organization_edges": ("edge_id",),
    "companies": ("company_id",),
    "departments": ("department_id",),
    "users": ("user_id",),
    "data_sources": ("source_id",),
    "tenants": ("tenant_id",),
    "enterprise_budgets": ("entity_id",),
    "enterprise_budget_reservations": ("reservation_id",),
    "action_approval_nonces": ("nonce",),
    "tenant_subscriptions": ("subscription_id",),
    "billing_webhook_events": ("event_id",),
    "tenant_invoices": ("invoice_id",),
    "supervisor_heartbeats": ("heartbeat_id",),
    "temporal_workers": ("worker_id",),
    "governed_tools": ("tool_id",),
    "terminal_checkpoints": ("checkpoint_id",),
    "employee_performance_records": ("record_id",),
    "company_processes": ("process_id",),
    "optimistic_lock_registry": ("table_name",),
    "schema_migrations": ("version",),
    "async_command_queue": ("command_id",),
    "crm_customers": ("customer_id",),
    "crm_deals": ("deal_id",),
    "organizations": ("org_id",),
    "corporate_departments": ("department_id",),
    "corporate_positions": ("position_id",),
    "corporate_employees": ("employee_id",),
    "employee_reporting_relationships": ("relationship_id",),
    "employee_authority_profiles": ("profile_id",),
    "employee_knowledge_profiles": ("profile_id",),
    "sop_definitions": ("sop_id",),
    "sop_versions": ("version_id",),
    "employee_sop_assignments": ("assignment_id",),
    "employee_kras": ("kra_id",),
    "kpi_definitions": ("kpi_id",),
    "kpi_measurements": ("measurement_id",),
    "employee_performance_reviews": ("review_id",),
    "workforce_requisitions": ("requisition_id",),
    "agent_capabilities": ("capability_id",),
    "agent_templates": ("template_id",),
    "agent_template_versions": ("version_id",),
    "agent_instances": ("instance_id",),
    "agent_leases": ("lease_id",),
    "agent_execution_sessions": ("session_id",),
    "corporate_missions": ("mission_id",),
    "employee_tasks": ("task_id",),
    "cross_department_collaborations": ("collab_id",),
    "corporate_knowledge_assets": ("asset_id",),
    "assistant_messages": ("message_id",),
    "assistant_generated_documents": ("doc_id",),
    "meeting_integrations": ("integration_id",),
}


def _tokenize_and_replace_placeholders(sql: str) -> str:
    """
    Safely converts SQLite '?' parameter placeholders to PostgreSQL '%s'
    while strictly preserving literal question marks inside:
    - Single-quoted string literals ('...')
    - Double-quoted identifiers ("...")
    - Single-line SQL comments (-- ...)
    - Multi-line block comments (/* ... */)
    - Dollar-quoted string constants ($$...$$ or $tag$...$tag$)
    """
    if "?" not in sql:
        return sql

    out = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    in_dollar_quote = False
    dollar_tag = ""

    i = 0
    n = len(sql)

    while i < n:
        c = sql[i]
        next_c = sql[i + 1] if i + 1 < n else ""

        # Handle comments when not in string literal
        if not in_single_quote and not in_double_quote and not in_dollar_quote:
            if in_line_comment:
                if c == "%":
                    if next_c == "%":
                        out.append("%%")
                        i += 2
                        continue
                    else:
                        out.append("%%")
                        i += 1
                        continue
                out.append(c)
                if c == "\n":
                    in_line_comment = False
                i += 1
                continue
            elif in_block_comment:
                if c == "%":
                    if next_c == "%":
                        out.append("%%")
                        i += 2
                        continue
                    else:
                        out.append("%%")
                        i += 1
                        continue
                out.append(c)
                if c == "*" and next_c == "/":
                    out.append(next_c)
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            elif c == "-" and next_c == "-":
                in_line_comment = True
                out.append("--")
                i += 2
                continue
            elif c == "/" and next_c == "*":
                in_block_comment = True
                out.append("/*")
                i += 2
                continue

        # Handle dollar quotes ($$...$$ or $tag$...$tag$)
        if not in_single_quote and not in_double_quote and not in_line_comment and not in_block_comment:
            if in_dollar_quote:
                out.append(c)
                if c == "$" and sql[i:i + len(dollar_tag)] == dollar_tag:
                    out.append(dollar_tag[1:])
                    i += len(dollar_tag)
                    in_dollar_quote = False
                    dollar_tag = ""
                    continue
                i += 1
                continue
            elif c == "$":
                end_dollar = sql.find("$", i + 1)
                if end_dollar != -1 and end_dollar - i <= 32:
                    tag_candidate = sql[i:end_dollar + 1]
                    inner = tag_candidate[1:-1]
                    if inner == "" or inner.isidentifier():
                        in_dollar_quote = True
                        dollar_tag = tag_candidate
                        out.append(tag_candidate)
                        i = end_dollar + 1
                        continue

        # Handle single and double quotes
        if not in_line_comment and not in_block_comment and not in_dollar_quote:
            if in_single_quote:
                if c == "%":
                    if next_c == "%":
                        out.append("%%")
                        i += 2
                        continue
                    else:
                        out.append("%%")
                        i += 1
                        continue
                out.append(c)
                if c == "'":
                    if next_c == "'":  # Escaped single quote: ''
                        out.append(next_c)
                        i += 2
                        continue
                    elif i > 0 and sql[i - 1] == "\\":  # Backslash escape \'
                        pass
                    else:
                        in_single_quote = False
                i += 1
                continue
            elif in_double_quote:
                if c == "%":
                    if next_c == "%":
                        out.append("%%")
                        i += 2
                        continue
                    else:
                        out.append("%%")
                        i += 1
                        continue
                out.append(c)
                if c == '"':
                    if next_c == '"':  # Escaped double quote: ""
                        out.append(next_c)
                        i += 2
                        continue
                    else:
                        in_double_quote = False
                i += 1
                continue
            else:
                if c == "'":
                    in_single_quote = True
                    out.append(c)
                    i += 1
                    continue
                elif c == '"':
                    in_double_quote = True
                    out.append(c)
                    i += 1
                    continue
                elif c == "?":
                    out.append("%s")
                    i += 1
                    continue
                elif c == "%":
                    if next_c == "%":
                        out.append("%%")
                        i += 2
                        continue
                    elif next_c == "s" or next_c == "(":
                        out.append("%")
                        i += 1
                        continue
                    else:
                        out.append("%%")
                        i += 1
                        continue

        out.append(c)
        i += 1

    return "".join(out)


def normalize_sql_for_postgres(sql: str) -> str:
    """
    Normalizes SQL statements for PostgreSQL compatibility:
    - Strips SQLite PRAGMA commands (returns empty string)
    - Safely replaces ? parameter placeholders with %s outside string literals/comments
    - Converts SQLite INSERT OR IGNORE INTO to ANSI ON CONFLICT DO NOTHING
    - Converts legacy INSERT OR REPLACE INTO to ANSI ON CONFLICT (<pk>) DO UPDATE SET ...
    """
    stripped = sql.strip()
    if stripped.upper().startswith("PRAGMA "):
        return ""
    if stripped.upper() in ("BEGIN IMMEDIATE", "BEGIN IMMEDIATE;"):
        return ""

    # Convert ? placeholders to %s safely outside literals and comments
    normalized = _tokenize_and_replace_placeholders(sql)

    import re

    # Convert BOOLEAN DEFAULT 0/1 to BOOLEAN DEFAULT FALSE/TRUE
    normalized = re.sub(r"\bBOOLEAN(\s+NOT\s+NULL)?\s+DEFAULT\s+0\b", r"BOOLEAN\1 DEFAULT FALSE", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bBOOLEAN(\s+NOT\s+NULL)?\s+DEFAULT\s+1\b", r"BOOLEAN\1 DEFAULT TRUE", normalized, flags=re.IGNORECASE)

    # Handle SQLite INSERT OR IGNORE -> PostgreSQL ON CONFLICT DO NOTHING
    if re.search(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", normalized, re.IGNORECASE):
        normalized = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", normalized, flags=re.IGNORECASE)
        if "ON CONFLICT" not in normalized.upper():
            normalized = normalized.rstrip("; ") + " ON CONFLICT DO NOTHING"

    # Handle SQLite INSERT OR REPLACE INTO -> PostgreSQL ANSI ON CONFLICT ... DO UPDATE SET ...
    replace_match = re.search(
        r"\bINSERT\s+OR\s+REPLACE\s+INTO\s+([a-zA-Z0-9_]+)\s*\(([^)]+)\)",
        normalized,
        re.IGNORECASE
    )
    if replace_match:
        table_name = replace_match.group(1).strip()
        columns_str = replace_match.group(2)
        columns = [c.strip().strip('"').strip('`') for c in columns_str.split(",") if c.strip()]

        pk_cols = TABLE_PRIMARY_KEYS.get(table_name)
        if pk_cols:
            update_cols = [c for c in columns if c not in pk_cols and c.lower() != "created_at"]
            pk_target = ", ".join(pk_cols)
            if update_cols:
                set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])
                conflict_clause = f" ON CONFLICT ({pk_target}) DO UPDATE SET {set_clause}"
            else:
                conflict_clause = f" ON CONFLICT ({pk_target}) DO NOTHING"
        else:
            conflict_clause = " ON CONFLICT DO NOTHING"

        # Substitute INSERT OR REPLACE INTO with INSERT INTO
        normalized = re.sub(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", "INSERT INTO", normalized, flags=re.IGNORECASE)
        if "ON CONFLICT" not in normalized.upper():
            normalized = normalized.rstrip("; ") + conflict_clause
    elif re.search(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", normalized, re.IGNORECASE):
        normalized = re.sub(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", "INSERT INTO", normalized, flags=re.IGNORECASE)
        if "ON CONFLICT" not in normalized.upper():
            normalized = normalized.rstrip("; ") + " ON CONFLICT DO NOTHING"

    return normalized


class PostgresConnectionWrapper:
    """Wraps raw PostgreSQL connection with sqlite3-compatible Row and transaction semantics."""
    def __init__(self, raw_conn, pool=None):
        self.raw_conn = raw_conn
        self._pool = pool
        self._is_closed = False
        self._apply_rls_context()

    def _apply_rls_context(self) -> None:
        """Applies the request tenant/company to this session for fail-closed RLS.

        Session-level settings are always overwritten (including to empty string)
        so a pooled connection cannot leak a previous request's scope.
        """
        tenant_id = _current_tenant_id.get() or ""
        company_id = _current_company_id.get() or ""
        try:
            cursor = self.raw_conn.cursor()
            cursor.execute(
                "SELECT set_config('zonata.tenant_id', %s, false), "
                "set_config('zonata.company_id', %s, false)",
                (tenant_id, company_id),
            )
            try:
                cursor.close()
            except Exception:
                pass
        except Exception:
            # RLS is fail-closed, so a missing context yields zero rows rather
            # than cross-tenant disclosure.
            pass

    @property
    def row_factory(self):
        return getattr(self, "_row_factory", None)

    @row_factory.setter
    def row_factory(self, val):
        self._row_factory = val

    def _normalize_sql(self, sql: str) -> str:
        return normalize_sql_for_postgres(sql)

    def execute(self, sql: str, params: Any = ()):
        if self._is_closed:
            raise RuntimeError("Cannot execute query on closed database connection.")
        normalized_sql = self._normalize_sql(sql)
        if not normalized_sql:
            class DummyCursor:
                def fetchone(self): return None
                def fetchall(self): return []
                @property
                def rowcount(self): return 0
                def __iter__(self): return iter([])
            return DummyCursor()
        try:
            import psycopg2.extras
            cursor = self.raw_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            if not params:
                cursor.execute(normalized_sql)
            else:
                cursor.execute(normalized_sql, params)
            return PostgresCursorWrapper(cursor, normalize_fn=self._normalize_sql)
        except Exception:
            cursor = self.raw_conn.cursor()
            if not params:
                cursor.execute(normalized_sql)
            else:
                cursor.execute(normalized_sql, params)
            return PostgresCursorWrapper(cursor, normalize_fn=self._normalize_sql)

    def executemany(self, sql: str, params_seq: Any = ()):
        if self._is_closed:
            raise RuntimeError("Cannot execute query on closed database connection.")
        normalized_sql = self._normalize_sql(sql)
        if not normalized_sql:
            class DummyCursor:
                def fetchone(self): return None
                def fetchall(self): return []
                @property
                def rowcount(self): return 0
                def __iter__(self): return iter([])
            return DummyCursor()
        try:
            import psycopg2.extras
            cursor = self.raw_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.executemany(normalized_sql, params_seq)
            return PostgresCursorWrapper(cursor, normalize_fn=self._normalize_sql)
        except Exception:
            cursor = self.raw_conn.cursor()
            cursor.executemany(normalized_sql, params_seq)
            return PostgresCursorWrapper(cursor, normalize_fn=self._normalize_sql)

    def executescript(self, sql_script: str):
        if self._is_closed:
            raise RuntimeError("Cannot execute script on closed database connection.")
        try:
            self.raw_conn.rollback()
        except Exception:
            pass
        prev_autocommit = getattr(self.raw_conn, "autocommit", False)
        try:
            self.raw_conn.autocommit = True
        except Exception:
            pass
        try:
            cursor = self.raw_conn.cursor()
            for statement in sql_script.split(";"):
                stmt = statement.strip()
                if stmt:
                    norm = self._normalize_sql(stmt)
                    if norm:
                        try:
                            cursor.execute(norm)
                        except Exception:
                            pass
            return cursor
        finally:
            try:
                self.raw_conn.autocommit = prev_autocommit
            except Exception:
                pass

    def cursor(self):
        if self._is_closed:
            raise RuntimeError("Cannot create cursor on closed database connection.")
        try:
            import psycopg2.extras
            raw_cur = self.raw_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except Exception:
            raw_cur = self.raw_conn.cursor()
        return PostgresCursorWrapper(raw_cur, normalize_fn=self._normalize_sql)

    def commit(self):
        if self._is_closed:
            raise RuntimeError("Cannot commit on closed database connection.")
        self.raw_conn.commit()

    def rollback(self):
        if self._is_closed:
            return
        self.raw_conn.rollback()

    def close(self):
        if self._is_closed:
            return
        self._is_closed = True
        if self._pool is not None:
            self._pool.return_connection(self.raw_conn)
        else:
            try:
                self.raw_conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.rollback()
            else:
                self.commit()
        finally:
            self.close()


class DatabasePoolExhaustedError(RuntimeError):
    """Raised when the PostgreSQL connection pool is exhausted and timeout expires."""
    pass


class PostgresConnectionPool:
    """
    Thread-safe connection pool for PostgreSQL clusters.
    Supports both psycopg2 and pg8000 drivers with configurable bounds,
    checkout timeout, health validation, auto-rollback on return,
    and stale/broken connection eviction.
    """
    def __init__(
        self,
        db_instance: 'Database',
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        idle_timeout: float = 300.0,
    ):
        self.db_instance = db_instance
        self.max_size = max(1, int(max_size))
        self.min_size = max(1, min(int(min_size), self.max_size))
        self.timeout = float(timeout)
        self.idle_timeout = float(idle_timeout)

        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._idle_connections: List[Tuple[Any, float]] = []  # List of (raw_conn, last_used_timestamp)
        self._checked_out: Set[Any] = set()
        self._total_count: int = 0
        self._is_closed: bool = False

    def _validate_raw_connection(self, raw_conn: Any) -> bool:
        """Probes a raw connection to ensure it is healthy and responsive."""
        try:
            if hasattr(raw_conn, "closed") and raw_conn.closed != 0:
                return False
            cursor = raw_conn.cursor()
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            cursor.close()
            return bool(row and row[0] == 1)
        except Exception:
            return False

    def get_connection(self, timeout: Optional[float] = None) -> PostgresConnectionWrapper:
        """
        Acquires a connection from the pool.
        Blocks up to timeout seconds if the pool has reached max_size.
        """
        wait_timeout = self.timeout if timeout is None else float(timeout)
        deadline = time.time() + wait_timeout

        with self._cond:
            if self._is_closed:
                raise RuntimeError("Database connection pool is closed.")

            while True:
                # 1. Check for available idle connections
                while self._idle_connections:
                    raw_conn, last_used = self._idle_connections.pop()
                    is_alive = True
                    if (time.time() - last_used) > self.idle_timeout:
                        is_alive = self._validate_raw_connection(raw_conn)

                    if is_alive:
                        self._checked_out.add(raw_conn)
                        return PostgresConnectionWrapper(raw_conn, pool=self)
                    else:
                        try:
                            raw_conn.close()
                        except Exception:
                            pass
                        self._total_count = max(0, self._total_count - 1)

                # 2. Spawn a new connection if total is under max_size
                if self._total_count < self.max_size:
                    raw_conn = self.db_instance._create_raw_connection()
                    self._total_count += 1
                    self._checked_out.add(raw_conn)
                    return PostgresConnectionWrapper(raw_conn, pool=self)

                # 3. Saturated pool: wait on condition variable
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise DatabasePoolExhaustedError(
                        f"Database connection pool exhausted: all {self.max_size} connections are in use "
                        f"(waited {wait_timeout:.1f}s)."
                    )

                self._cond.wait(timeout=remaining)
                if self._is_closed:
                    raise RuntimeError("Database connection pool was closed while waiting.")
                if time.time() >= deadline and not self._idle_connections and self._total_count >= self.max_size:
                    raise DatabasePoolExhaustedError(
                        f"Database connection pool exhausted: all {self.max_size} connections are in use "
                        f"(waited {wait_timeout:.1f}s)."
                    )

    def return_connection(self, raw_conn: Any, discard: bool = False):
        """
        Returns a connection to the idle pool.
        Executes a safety rollback to ensure transaction isolation.
        """
        with self._cond:
            if raw_conn in self._checked_out:
                self._checked_out.remove(raw_conn)

            if self._is_closed or discard:
                try:
                    raw_conn.close()
                except Exception:
                    pass
                self._total_count = max(0, self._total_count - 1)
                self._cond.notify()
                return

            # Safety rollback before returning connection to pool
            try:
                raw_conn.rollback()
                self._idle_connections.append((raw_conn, time.time()))
                self._cond.notify()
            except Exception:
                try:
                    raw_conn.close()
                except Exception:
                    pass
                self._total_count = max(0, self._total_count - 1)
                self._cond.notify()

    def close_all(self):
        """Closes all pooled connections immediately."""
        with self._cond:
            self._is_closed = True
            for raw_conn, _ in self._idle_connections:
                try:
                    raw_conn.close()
                except Exception:
                    pass
            self._idle_connections.clear()

            for raw_conn in list(self._checked_out):
                try:
                    raw_conn.close()
                except Exception:
                    pass
            self._checked_out.clear()
            self._total_count = 0
            self._cond.notify_all()

    def get_stats(self) -> Dict[str, Any]:
        """Returns snapshot metrics of connection pool utilization."""
        with self._lock:
            return {
                "dialect": "postgresql",
                "status": "CLOSED" if self._is_closed else "HEALTHY",
                "total_connections": self._total_count,
                "active_connections": len(self._checked_out),
                "idle_connections": len(self._idle_connections),
                "min_size": self.min_size,
                "max_size": self.max_size,
                "timeout_sec": self.timeout,
                "idle_timeout_sec": self.idle_timeout
            }



class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.database_url = os.environ.get("DATABASE_URL", "").strip()
        dialect_env = os.environ.get("ZONATA_DB_DIALECT", "").lower()
        app_env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").lower()
        is_prod = app_env in ("production", "prod")

        # In production mode, SQLite is prohibited under all circumstances.
        # Legacy ZONATA_ALLOW_SQLITE_IN_PRODUCTION is strictly rejected.
        if is_prod and not (os.environ.get("ZONATA_ALLOW_DEGRADED", "0") == "1"):
            if not self.database_url or self.database_url.startswith(("sqlite://", "sqlite:")) or not (
                self.database_url.startswith(("postgresql://", "postgres://")) or dialect_env == "postgresql"
            ):
                raise RuntimeError(
                    "Production Safety Invariant Violation: Direct SQLite fallback is prohibited in production mode. "
                    "A valid PostgreSQL DATABASE_URL must be configured. Set ZONATA_ALLOW_DEGRADED=1 to bypass for testing."
                )

        if not is_prod and (dialect_env == "sqlite" or bool(os.environ.get("ZONATA_DB_PATH"))):
            self.dialect = DatabaseDialect.SQLITE
        elif self.database_url.startswith(("postgresql://", "postgres://")) or dialect_env == "postgresql":
            self.dialect = DatabaseDialect.POSTGRESQL
        else:
            self.dialect = DatabaseDialect.SQLITE

        self._is_ready = (self.dialect == DatabaseDialect.SQLITE)
        self._deferred_import_mode = (self.dialect == DatabaseDialect.POSTGRESQL)
        self._deferred_queries = []
        self._pg_pool: Optional[PostgresConnectionPool] = None

        if db_path is None:
            self.db_path = get_default_db_path()
        elif db_path.startswith("/roboassistant/") and not os.path.exists("/roboassistant"):
            rel = os.path.relpath(db_path, "/roboassistant")
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.db_path = os.path.join(base_dir, rel)
        else:
            self.db_path = os.path.abspath(db_path)

        if self.dialect == DatabaseDialect.SQLITE:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            protected_db = os.path.abspath(os.path.join(base_dir, "storage", "roboassistant.db"))
            if os.path.abspath(self.db_path) == protected_db and os.path.exists(protected_db):
                # Protected baseline database — never mutate or execute schema scripts automatically
                pass
            else:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True, mode=0o750)
                self._init_db()

    def set_db_path(self, new_path: str):
        app_env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").lower()
        is_prod = app_env in ("production", "prod")
        if is_prod:
            raise RuntimeError(
                "Production Safety Invariant Violation: Direct SQLite path reconfiguration is prohibited in production mode."
            )
        if self._pg_pool is not None:
            self._pg_pool.close_all()
            self._pg_pool = None
        self.db_path = os.path.abspath(new_path)
        self.dialect = DatabaseDialect.SQLITE
        self._is_ready = True
        self._deferred_import_mode = False
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        protected_db = os.path.abspath(os.path.join(base_dir, "storage", "roboassistant.db"))
        if os.path.abspath(self.db_path) == protected_db and os.path.exists(protected_db):
            pass
        else:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True, mode=0o750)
            self._init_db()
        try:
            from core.database_engine import engine
            engine.dialect = DatabaseDialect.SQLITE
            engine.db_path = self.db_path
            engine._is_ready = True
            engine._deferred_import_mode = False
            if hasattr(engine, 'pools') and engine.pools:
                for p in engine.pools.values():
                    p.dialect = DatabaseDialect.SQLITE
                    p._deferred_import_mode = False
                    p.reset()
        except Exception:
            pass
        try:
            from core.evidence_service import evidence_service
            evidence_service._init_db()
        except Exception:
            pass
        try:
            from core.automation_fabric.fabric import universal_automation_fabric
            universal_automation_fabric._init_automation_tables()
            universal_automation_fabric._ensure_signing_keys_table()
        except Exception:
            pass
        try:
            from core.security_center import security_center
            security_center._init_db()
        except Exception:
            pass

    def initialize(self):
        if self.dialect == DatabaseDialect.POSTGRESQL:
            return self.verify_readiness()
        return self._init_db()

    def get_dialect(self) -> str:
        return self.dialect

    def is_postgresql(self) -> bool:
        return self.dialect == DatabaseDialect.POSTGRESQL

    def is_ready(self) -> bool:
        """Returns True if the database connection has been verified."""
        if self.dialect == DatabaseDialect.SQLITE:
            return True
        return bool(self._is_ready)

    def verify_readiness(self) -> bool:
        """Verifies genuine database connectivity. Fails closed with actionable sanitized errors."""
        if self.dialect == DatabaseDialect.SQLITE:
            self._is_ready = True
            self._deferred_import_mode = False
            return True

        if not self.database_url:
            raise RuntimeError(
                "Production Safety Invariant Violation: Direct SQLite fallback is prohibited in production mode. "
                "A valid PostgreSQL DATABASE_URL must be configured."
            )

        try:
            pool = self._ensure_pg_pool()
            conn = pool.get_connection()
            with conn:
                cur = conn.execute("SELECT 1")
                res = cur.fetchone()
                if not res or res[0] != 1:
                    raise RuntimeError("Database readiness probe returned invalid result.")
            self._is_ready = True
            self._deferred_import_mode = False
            return True
        except Exception as e:
            self._is_ready = False
            sanitized_url = sanitize_db_url(self.database_url)
            sanitized_err = sanitize_db_url(str(e))
            raise RuntimeError(
                f"Database Readiness Verification Failed for '{sanitized_url}': {sanitized_err}"
            )

    def get_connection(self):
        if self.dialect == DatabaseDialect.POSTGRESQL:
            if self._deferred_import_mode and not self._is_ready:
                return DeferredConnectionProxy(self)
            return self._get_pooled_postgresql_connection()
        if not self.db_path or not os.path.exists(os.path.dirname(os.path.abspath(self.db_path))):
            session_db = os.environ.get("ZONATA_SESSION_TEST_DB")
            if session_db and os.path.exists(os.path.dirname(os.path.abspath(session_db))):
                self.set_db_path(session_db)
            else:
                configure_isolated_test_db()
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _ensure_pg_pool(self) -> PostgresConnectionPool:
        if self._pg_pool is None:
            min_size = int(os.environ.get("DATABASE_MIN_POOL_SIZE", "5"))
            max_size = int(os.environ.get("DATABASE_MAX_POOL_SIZE", "20"))
            timeout_ms = float(os.environ.get("DATABASE_BUSY_TIMEOUT_MS", "60000"))
            pool_timeout = float(os.environ.get("DATABASE_POOL_TIMEOUT", str(timeout_ms / 1000.0)))
            idle_timeout = float(os.environ.get("DATABASE_IDLE_TIMEOUT_SEC", "300"))
            self._pg_pool = PostgresConnectionPool(
                db_instance=self,
                min_size=min_size,
                max_size=max_size,
                timeout=pool_timeout,
                idle_timeout=idle_timeout
            )
        return self._pg_pool

    def _get_pooled_postgresql_connection(self) -> PostgresConnectionWrapper:
        pool = self._ensure_pg_pool()
        return pool.get_connection()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Returns connection pool metrics for Prometheus / SRE telemetry."""
        if self.dialect == DatabaseDialect.POSTGRESQL and self._pg_pool is not None:
            return self._pg_pool.get_stats()
        return {
            "dialect": self.dialect,
            "status": "UNPOOLED" if self.dialect == DatabaseDialect.SQLITE else "UNINITIALIZED",
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "min_size": 1,
            "max_size": 1,
            "timeout_sec": 60.0,
            "idle_timeout_sec": 300.0
        }

    def close(self):
        """Closes all active and idle pooled connections."""
        if self._pg_pool is not None:
            self._pg_pool.close_all()
            self._pg_pool = None

    def _create_raw_connection(self):
        # 1. Try psycopg2 driver
        try:
            import psycopg2
            import psycopg2.extras
            raw_conn = psycopg2.connect(self.database_url, connect_timeout=10)
            raw_conn.autocommit = False
            return raw_conn
        except ImportError:
            pass
        except Exception as e:
            sanitized_url = sanitize_db_url(self.database_url)
            sanitized_err = sanitize_db_url(str(e))
            raise RuntimeError(
                f"Failed to connect to PostgreSQL database at '{sanitized_url}': {sanitized_err}"
            )

        # 2. Fallback to pg8000 pure-Python driver
        try:
            _prefix = os.environ.get("PREFIX")
            if _prefix:
                _termux_site = os.path.join(_prefix, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
                if os.path.exists(_termux_site) and _termux_site not in sys.path:
                    sys.path.insert(0, _termux_site)
            import pg8000
            import ssl
            parsed = urllib.parse.urlsplit(self.database_url)
            user = parsed.username or "postgres"
            password = parsed.password or ""
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            database = parsed.path.lstrip("/") or "postgres"
            ssl_ctx = None
            if "sslmode=require" in self.database_url or "neon.tech" in (parsed.hostname or ""):
                ssl_ctx = ssl.create_default_context()
            raw_conn = pg8000.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=database,
                ssl_context=ssl_ctx,
                timeout=int(os.environ.get("DATABASE_TIMEOUT", "60"))
            )
            raw_conn.autocommit = False
            return raw_conn
        except ImportError:
            raise RuntimeError(
                "PostgreSQL driver (psycopg2 or pg8000) is not installed in the runtime environment. "
                "Install psycopg2-binary or pg8000."
            )
        except Exception as e:
            sanitized_url = sanitize_db_url(self.database_url)
            sanitized_err = sanitize_db_url(str(e))
            raise RuntimeError(
                f"Failed to connect to PostgreSQL database at '{sanitized_url}': {sanitized_err}"
            )

    def _get_postgresql_connection(self):
        raw_conn = self._create_raw_connection()
        return PostgresConnectionWrapper(raw_conn)

    def _init_db(self):
        if self.dialect == DatabaseDialect.SQLITE:
            pass
        elif self.dialect == DatabaseDialect.POSTGRESQL and not self._is_ready:
            self.verify_readiness()
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            # Additive, idempotent column migrations for existing databases.
            for stmt in (
                "ALTER TABLE approvals ADD COLUMN decision_reason TEXT",
                "ALTER TABLE employee_kras ADD COLUMN responsibility TEXT",
                "ALTER TABLE employee_kras ADD COLUMN associated_workflows JSON",
                "ALTER TABLE employee_kras ADD COLUMN associated_kpi_ids JSON",
                "ALTER TABLE employee_kras ADD COLUMN allowed_tools JSON",
                "ALTER TABLE employee_kras ADD COLUMN authority_scope JSON",
                "ALTER TABLE employee_kras ADD COLUMN escalation_rules JSON",
                "ALTER TABLE employee_kras ADD COLUMN expected_outcomes JSON",
                "ALTER TABLE employee_kras ADD COLUMN position_id TEXT",
                "ALTER TABLE employee_kras ADD COLUMN strategic_objective_id TEXT",
                "ALTER TABLE employee_kras ADD COLUMN weight_percentage REAL DEFAULT 25.0",
                "ALTER TABLE employee_kras ADD COLUMN accountability_statement TEXT",
                "ALTER TABLE employee_kras ADD COLUMN updated_at REAL",
                "ALTER TABLE organizations ADD COLUMN company_id TEXT",
                """CREATE TABLE IF NOT EXISTS assistant_messages (
                    message_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    workspace_mode TEXT NOT NULL DEFAULT 'PERSONAL',
                    content TEXT NOT NULL,
                    intent_category TEXT,
                    deliverables JSON,
                    citations JSON,
                    timestamp REAL NOT NULL
                )""",
                """CREATE TABLE IF NOT EXISTS assistant_generated_documents (
                    doc_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    user_id TEXT NOT NULL,
                    storage_boundary TEXT NOT NULL DEFAULT 'PERSONAL',
                    title TEXT NOT NULL,
                    format TEXT NOT NULL,
                    category TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL,
                    metadata JSON,
                    created_at REAL NOT NULL
                )""",
                """CREATE TABLE IF NOT EXISTS meeting_integrations (
                    integration_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    schedule_id TEXT,
                    provider TEXT NOT NULL DEFAULT 'GOOGLE_MEET',
                    meet_url TEXT NOT NULL,
                    dial_in_info JSON,
                    calendar_event_id TEXT,
                    ai_representative_enabled INTEGER NOT NULL DEFAULT 1,
                    statutory_disclosure_signed INTEGER NOT NULL DEFAULT 1,
                    briefing_dossier_id TEXT,
                    created_at REAL NOT NULL
                )""",
            ):
                try:
                    conn.execute(stmt)
                    conn.commit()
                except Exception:
                    # Additive migration already applied (or unsupported):
                    # roll back so PostgreSQL does not stay in aborted state.
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            try:
                from core.documents.schema import ensure_document_backbone_tables
                ensure_document_backbone_tables(conn)
                from core.folios.schema import ensure_folio_tables
                ensure_folio_tables(conn)
                from core.ledger.schema import ensure_ledger_tables
                ensure_ledger_tables(conn)
                from core.industry_packs.loader import ensure_industry_pack_tables
                ensure_industry_pack_tables(conn)
                from core.baseline.outbox import ensure_outbox_tables
                ensure_outbox_tables(conn)
                from core.baseline.scheduler import ensure_scheduler_tables
                ensure_scheduler_tables(conn)
                from core.organization import ensure_organization_tables
                ensure_organization_tables(conn)
                from core.agents import ensure_agent_runtime_tables
                ensure_agent_runtime_tables(conn)
                from core.work import ensure_work_kernel_tables
                ensure_work_kernel_tables(conn)
                from core.sop import ensure_sop_tables
                ensure_sop_tables(conn)
            except Exception:
                pass
            conn.commit()

# Global Singleton Database Instance
db = Database()

def configure_isolated_test_db(custom_path: Optional[str] = None) -> str:
    """Configures an isolated SQLite database for unit tests or simulations."""
    if not custom_path:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        custom_path = tmp.name
        tmp.close()
    db.set_db_path(custom_path)
    os.environ["ZONATA_DB_PATH"] = custom_path
    try:
        from core.database_engine import engine, DatabaseDialect
        engine.dialect = DatabaseDialect.SQLITE
        engine.db_path = custom_path
        engine._is_ready = True
        engine._deferred_import_mode = False
        if hasattr(engine, 'pools') and engine.pools:
            for p in engine.pools.values():
                p.dialect = DatabaseDialect.SQLITE
                p._deferred_import_mode = False
                p.reset()
    except Exception:
        pass
    try:
        from core.evidence_service import evidence_service
        evidence_service._init_db()
    except Exception:
        pass
    try:
        from core.documents.schema import ensure_document_backbone_tables
        ensure_document_backbone_tables()
        from core.folios.schema import ensure_folio_tables
        ensure_folio_tables()
        from core.ledger.schema import ensure_ledger_tables
        ensure_ledger_tables()
        from core.industry_packs.loader import ensure_industry_pack_tables
        ensure_industry_pack_tables()
        from core.baseline.outbox import ensure_outbox_tables
        ensure_outbox_tables()
        from core.baseline.scheduler import ensure_scheduler_tables
        ensure_scheduler_tables()
        from core.organization import ensure_organization_tables
        ensure_organization_tables()
        from core.agents import ensure_agent_runtime_tables
        ensure_agent_runtime_tables()
        from core.work import ensure_work_kernel_tables
        ensure_work_kernel_tables()
        from core.sop import ensure_sop_tables
        ensure_sop_tables()
    except Exception:
        pass
    try:
        from core.automation_fabric.fabric import universal_automation_fabric
        universal_automation_fabric._init_automation_tables()
        universal_automation_fabric._ensure_signing_keys_table()
    except Exception:
        pass
    try:
        from core.security_center import security_center
        security_center._init_db()
    except Exception:
        pass
    try:
        from tests.schema_bootstrap import init_all_subsystem_schemas, seed_baseline_tenant_scope
        init_all_subsystem_schemas()
        seed_baseline_tenant_scope()
    except Exception:
        pass
    return custom_path


