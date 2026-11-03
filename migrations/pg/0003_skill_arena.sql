-- Enterprise Skill Arena: persistent decisions and executable skill-contract runs.

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
    risk_level TEXT NOT NULL,
    required_authority TEXT NOT NULL,
    requester_authority TEXT NOT NULL,
    authority_granted BOOLEAN NOT NULL DEFAULT FALSE,
    policy_decision TEXT NOT NULL,
    approval_id TEXT,
    evidence_id TEXT,
    evidence_status TEXT,
    notes TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_arena_decisions_scope
    ON arena_decisions(tenant_id, company_id, created_at);

CREATE TABLE IF NOT EXISTS skill_runs (
    run_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    requester_role TEXT NOT NULL,
    status TEXT NOT NULL,
    required_authority TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    result_json TEXT,
    evidence_id TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_skill_runs_scope
    ON skill_runs(tenant_id, company_id, created_at);
