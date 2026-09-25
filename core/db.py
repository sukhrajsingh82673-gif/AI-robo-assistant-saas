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
