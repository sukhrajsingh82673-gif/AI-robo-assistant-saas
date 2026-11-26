-- PostgreSQL 16 Migration 0020: Action Gateway, Authority, Approvals, Delegations, and Constitution
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

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

ALTER TABLE policy_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_decisions FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'policy_decisions' AND policyname = 'tenant_isolation_policy_decisions'
    ) THEN
        CREATE POLICY tenant_isolation_policy_decisions ON policy_decisions
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

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

ALTER TABLE authority_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE authority_profiles FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'authority_profiles' AND policyname = 'tenant_isolation_authority_profiles'
    ) THEN
        CREATE POLICY tenant_isolation_authority_profiles ON authority_profiles
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

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

ALTER TABLE authority_delegations ENABLE ROW LEVEL SECURITY;
ALTER TABLE authority_delegations FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'authority_delegations' AND policyname = 'tenant_isolation_authority_delegations'
    ) THEN
        CREATE POLICY tenant_isolation_authority_delegations ON authority_delegations
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

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

ALTER TABLE action_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_approvals FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'action_approvals' AND policyname = 'tenant_isolation_action_approvals'
    ) THEN
        CREATE POLICY tenant_isolation_action_approvals ON action_approvals
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

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

ALTER TABLE company_constitutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_constitutions FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'company_constitutions' AND policyname = 'tenant_isolation_company_constitutions'
    ) THEN
        CREATE POLICY tenant_isolation_company_constitutions ON company_constitutions
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- Rule 15: Revoke mutating access to governance tables from agent principal database roles
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent') THEN
        REVOKE INSERT, UPDATE, DELETE ON authority_profiles, policy_decisions, authority_delegations, action_approvals, company_constitutions FROM zonata_agent;
    END IF;
END $$;
