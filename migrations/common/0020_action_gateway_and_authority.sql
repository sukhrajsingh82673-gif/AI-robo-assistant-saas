-- Common SQLite/PostgreSQL Migration 0020: Action Gateway, Authority, Approvals, Delegations, and Constitution

CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    action_class TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    principal_type TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    rule_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    decision_path TEXT NOT NULL,
    evidence_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_policy_decisions_tenant_company ON policy_decisions(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_policy_decisions_action ON policy_decisions(action_id);
CREATE INDEX IF NOT EXISTS idx_policy_decisions_created ON policy_decisions(created_at);

CREATE TABLE IF NOT EXISTS authority_profiles (
    profile_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    principal_id TEXT,
    grade TEXT NOT NULL,
    tier TEXT NOT NULL,
    single_spend_limit_usd INTEGER NOT NULL,
    monthly_spend_limit_usd INTEGER NOT NULL,
    can_hire INTEGER NOT NULL DEFAULT 0,
    can_delegate INTEGER NOT NULL DEFAULT 0,
    can_modify_sops INTEGER NOT NULL DEFAULT 0,
    allowed_action_classes TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_authority_profiles_tenant_company ON authority_profiles(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_authority_profiles_principal ON authority_profiles(principal_id);
CREATE INDEX IF NOT EXISTS idx_authority_profiles_grade ON authority_profiles(grade);

CREATE TABLE IF NOT EXISTS authority_delegations (
    delegation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    delegator_id TEXT NOT NULL,
    delegate_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    starts_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    revoked_at REAL,
    revoked_by TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_delegations_lookup ON authority_delegations(tenant_id, company_id, delegate_id, is_active);

CREATE TABLE IF NOT EXISTS action_approvals (
    approval_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    action_class TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    maker_id TEXT NOT NULL,
    approver_id TEXT,
    approver_type TEXT,
    approver_role TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    quorum_required INTEGER NOT NULL DEFAULT 1,
    approvals_received TEXT NOT NULL DEFAULT '[]',
    expires_at REAL NOT NULL,
    decision_reason TEXT,
    created_at REAL NOT NULL,
    decided_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_action_approvals_lookup ON action_approvals(tenant_id, company_id, action_id);
CREATE INDEX IF NOT EXISTS idx_action_approvals_status ON action_approvals(status);

CREATE TABLE IF NOT EXISTS company_constitutions (
    constitution_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    mission TEXT,
    objectives TEXT,
    reserved_decisions TEXT,
    prohibited_actions TEXT,
    spend_ceilings TEXT,
    autonomy_ceiling TEXT NOT NULL DEFAULT 'SUPERVISED',
    is_active INTEGER NOT NULL DEFAULT 1,
    approved_by TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    UNIQUE(tenant_id, company_id, version)
);

CREATE INDEX IF NOT EXISTS idx_constitutions_company ON company_constitutions(tenant_id, company_id, is_active);
