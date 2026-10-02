-- ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
-- PostgreSQL Authoritative Relational Schema (121 Tables)
-- Version: 0001_postgresql_full_schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Tenants & Organizations
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(64) NOT NULL DEFAULT 'ENTERPRISE',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL,
    metadata JSONB
);

-- 2. Users & IAM
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(64) NOT NULL DEFAULT 'OWNER',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_users_email ON users(email);

-- 3. Companies & Operating Contexts
CREATE TABLE IF NOT EXISTS companies (
    company_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(8) NOT NULL DEFAULT 'IN',
    industry VARCHAR(128) NOT NULL,
    company_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPERATIONAL',
    currency VARCHAR(8) NOT NULL DEFAULT '₹',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    revenue DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    contribution DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    understanding_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    operating_rules JSONB,
    baseline_summary JSONB,
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_companies_tenant ON companies(tenant_id);

-- 4. Departments & Control Units
CREATE TABLE IF NOT EXISTS departments (
    department_id VARCHAR(64) PRIMARY KEY,
    company_id VARCHAR(64) NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    manager_agent_id VARCHAR(64),
    budget_limit DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    spending_limit DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_depts_company ON departments(company_id);

-- 5. AI Workforce & Employees
CREATE TABLE IF NOT EXISTS employees (
    agent_id VARCHAR(64) PRIMARY KEY,
    company_id VARCHAR(64) NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    department_id VARCHAR(64) REFERENCES departments(department_id) ON DELETE SET NULL,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    role VARCHAR(128) NOT NULL,
    department VARCHAR(128) NOT NULL,
    manager VARCHAR(128) NOT NULL DEFAULT 'AI CEO',
    responsibilities JSONB,
    objectives JSONB,
    allowed_tools JSONB,
    allowed_hosts JSONB,
    data_access JSONB,
    budget_limit DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    spending_limit DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    authority_ceiling VARCHAR(64) NOT NULL DEFAULT 'AUTOMATIC_IDEMPOTENT',
    decision_authority JSONB,
    forbidden_actions JSONB,
    working_state VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_emp_comp ON employees(company_id);
CREATE INDEX IF NOT EXISTS idx_pg_emp_tenant ON employees(tenant_id);

-- 6. Missions & Strategic Directives
CREATE TABLE IF NOT EXISTS missions (
    mission_id VARCHAR(64) PRIMARY KEY,
    company_id VARCHAR(64) NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    department VARCHAR(128),
    lead_agent_id VARCHAR(64),
    priority VARCHAR(32) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    expected_outcome TEXT,
    deadline DOUBLE PRECISION,
    financial_budget DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    financial_spend DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    approved_by VARCHAR(64),
    approved_at DOUBLE PRECISION,
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_missions_comp ON missions(company_id);
CREATE INDEX IF NOT EXISTS idx_pg_missions_tenant ON missions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_missions_status ON missions(status);

-- 7. Governed Agents (Agent Factory)
CREATE TABLE IF NOT EXISTS governed_agents (
    agent_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    company_id VARCHAR(64) NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    parent_agent_id VARCHAR(64),
    agent_version VARCHAR(32) NOT NULL DEFAULT 'v1.0.0',
    factory_version VARCHAR(32) NOT NULL DEFAULT 'v2.0.0',
    role VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DESIGNED',
    delegation_depth INT NOT NULL DEFAULT 0,
    capability_manifest JSONB,
    authority_scope JSONB,
    resource_budget JSONB,
    concurrency_budget INT NOT NULL DEFAULT 1,
    network_policy JSONB,
    data_policy JSONB,
    approval_policy JSONB,
    version INT NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_gov_agt_tenant ON governed_agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_gov_agt_status ON governed_agents(status);

-- 8. Governed Tools (Tool Factory)
CREATE TABLE IF NOT EXISTS governed_tools (
    tool_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    tool_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    status VARCHAR(32) NOT NULL DEFAULT 'DESIGNED',
    source_code TEXT NOT NULL,
    risk_class VARCHAR(64) NOT NULL DEFAULT 'LOW_RISK',
    sandbox_profile VARCHAR(64) NOT NULL DEFAULT 'ROOTLESS_CONTAINER',
    network_policy JSONB,
    filesystem_policy JSONB,
    credential_policy JSONB,
    security_scan_results JSONB,
    approval_id VARCHAR(64),
    signature VARCHAR(256),
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_gov_tool_tenant ON governed_tools(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_gov_tool_status ON governed_tools(status);

-- 9. Authoritative Merkle Evidence Events
CREATE TABLE IF NOT EXISTS merkle_evidence_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_index BIGSERIAL NOT NULL,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    company_id VARCHAR(64) NOT NULL,
    mission_id VARCHAR(64),
    workflow_id VARCHAR(64),
    agent_id VARCHAR(64),
    action_id VARCHAR(64),
    event_type VARCHAR(64) NOT NULL,
    canonical_payload_hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    current_hash VARCHAR(64) NOT NULL,
    causality_id VARCHAR(64),
    verification_state VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    artifact_storage_ref TEXT,
    timestamp DOUBLE PRECISION NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pg_ev_seq ON merkle_evidence_events(event_index);
CREATE INDEX IF NOT EXISTS idx_pg_ev_tenant ON merkle_evidence_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_ev_mission ON merkle_evidence_events(mission_id);
CREATE INDEX IF NOT EXISTS idx_pg_ev_hash ON merkle_evidence_events(current_hash);

-- 10. Temporal Durable Workflows
CREATE TABLE IF NOT EXISTS temporal_workflows (
    workflow_id VARCHAR(128) PRIMARY KEY,
    run_id VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    company_id VARCHAR(64) NOT NULL,
    mission_id VARCHAR(64),
    task_id VARCHAR(64),
    workflow_type VARCHAR(128) NOT NULL,
    task_queue VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
    workflow_version VARCHAR(32) NOT NULL DEFAULT 'v1.0.0',
    input_payload JSONB,
    result_payload JSONB,
    error_message TEXT,
    idempotency_key VARCHAR(128),
    execution_budget JSONB,
    resource_usage JSONB,
    verification_status VARCHAR(32) DEFAULT 'UNVERIFIED',
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    completed_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_pg_temp_wf_tenant ON temporal_workflows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_temp_wf_status ON temporal_workflows(status);

-- 11. Nango Executions & Integrations
CREATE TABLE IF NOT EXISTS nango_executions (
    execution_id VARCHAR(64) PRIMARY KEY,
    connection_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    company_id VARCHAR(64) NOT NULL,
    capability_id VARCHAR(64),
    action_name VARCHAR(128) NOT NULL,
    risk_class VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED',
    idempotency_key VARCHAR(128),
    input_payload JSONB,
    response_payload JSONB,
    error_message TEXT,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    evidence_ledger_id VARCHAR(64),
    outcome_status VARCHAR(32) DEFAULT 'PENDING',
    created_at DOUBLE PRECISION NOT NULL,
    completed_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_pg_nango_exec_tenant ON nango_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pg_nango_exec_idemp ON nango_executions(idempotency_key);
