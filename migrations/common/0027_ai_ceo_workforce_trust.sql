-- Common SQLite/PostgreSQL Migration 0027: AI CEO Executive Brain and Workforce Trust
-- OpenCode Step 2J: Directives, Decision Records, Risk Register, and Workforce Trust Levels

-- 1. CEO Directives Table (Interpreted Owner Commands)
CREATE TABLE IF NOT EXISTS ceo_directives (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    owner_command TEXT NOT NULL,
    objective TEXT NOT NULL,
    constraints JSON,
    deadline_ts REAL,
    budget_minor_units BIGINT NOT NULL DEFAULT 0,
    target_kpis JSON,
    scope JSON,
    is_ambiguous INTEGER NOT NULL DEFAULT 0,
    clarifying_question TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ceo_directives_tenant_comp ON ceo_directives(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_ceo_directives_status ON ceo_directives(status);

-- 2. CEO Decision Records Table (Evidence-Sealed Decisions)
CREATE TABLE IF NOT EXISTS ceo_decision_records (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    directive_id TEXT,
    title TEXT NOT NULL,
    options JSON NOT NULL,
    evidence_ids JSON NOT NULL,
    chosen_option TEXT NOT NULL,
    reason TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    outcome_review_date TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(directive_id) REFERENCES ceo_directives(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ceo_decisions_tenant_comp ON ceo_decision_records(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_ceo_decisions_directive ON ceo_decision_records(directive_id);

-- 3. Company Risk Register Table (Trigger-Driven Risk Events & Corrective Actions)
CREATE TABLE IF NOT EXISTS company_risk_register (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    details JSON NOT NULL,
    corrective_task_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    detected_at REAL NOT NULL,
    resolved_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(corrective_task_id) REFERENCES work_tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_register_tenant_comp ON company_risk_register(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_risk_register_status ON company_risk_register(status);

-- 4. Employee Trust Levels Table (Earned Autonomy via Measured Performance)
CREATE TABLE IF NOT EXISTS employee_trust_levels (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    current_level TEXT NOT NULL DEFAULT 'SHADOW',
    tasks_completed_count INTEGER NOT NULL DEFAULT 0,
    verified_pass_rate REAL NOT NULL DEFAULT 1.0,
    sop_compliance_score REAL NOT NULL DEFAULT 100.0,
    policy_violation_count INTEGER NOT NULL DEFAULT 0,
    last_promoted_at REAL,
    is_suspended INTEGER NOT NULL DEFAULT 0,
    is_killed INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    UNIQUE(tenant_id, company_id, employee_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_trust_tenant_comp ON employee_trust_levels(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_employee_trust_employee ON employee_trust_levels(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_trust_level ON employee_trust_levels(current_level);
