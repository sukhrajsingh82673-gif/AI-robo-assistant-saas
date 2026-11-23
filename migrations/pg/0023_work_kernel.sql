-- PostgreSQL 16 Migration 0023: Work Kernel
-- Multi-Tenant Row Level Security & Rule 15 Principal Separation

-- 1. Work Missions Table
CREATE TABLE IF NOT EXISTS work_missions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    lead_position_id TEXT,
    sponsor_position_id TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNING',
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    budget_micro_units BIGINT NOT NULL DEFAULT 0,
    spent_micro_units BIGINT NOT NULL DEFAULT 0,
    target_deadline_ts DOUBLE PRECISION,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    completed_at DOUBLE PRECISION,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_work_missions_tenant_company ON work_missions(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_work_missions_status ON work_missions(status);

ALTER TABLE work_missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_missions FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'work_missions' AND policyname = 'tenant_isolation_work_missions'
    ) THEN
        CREATE POLICY tenant_isolation_work_missions ON work_missions
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 2. Work Projects Table
CREATE TABLE IF NOT EXISTS work_projects (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    lead_position_id TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNING',
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(mission_id) REFERENCES work_missions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_work_projects_tenant_company ON work_projects(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_work_projects_mission ON work_projects(mission_id);

ALTER TABLE work_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_projects FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'work_projects' AND policyname = 'tenant_isolation_work_projects'
    ) THEN
        CREATE POLICY tenant_isolation_work_projects ON work_projects
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 3. Work Tasks Table
CREATE TABLE IF NOT EXISTS work_tasks (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    mission_id TEXT,
    project_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    owner_id TEXT NOT NULL,
    assignee_type TEXT NOT NULL DEFAULT 'POSITION',
    assignee_id TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    blocked_reason_code TEXT,
    blocked_reason_detail TEXT,
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    estimate_seconds INTEGER NOT NULL DEFAULT 0,
    estimate_minor_units BIGINT NOT NULL DEFAULT 0,
    acceptance_criteria JSONB,
    required_capabilities JSONB,
    required_autonomy_level TEXT NOT NULL DEFAULT 'SHADOW',
    sla_seconds INTEGER,
    deadline_ts DOUBLE PRECISION,
    sla_expires_at DOUBLE PRECISION,
    sla_escalation_level INTEGER NOT NULL DEFAULT 0,
    linked_folio_id TEXT,
    linked_document_ids JSONB,
    assignment_reasons JSONB,
    submitted_deliverable JSONB,
    verification_report_id TEXT,
    completed_by TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    submitted_at DOUBLE PRECISION,
    completed_at DOUBLE PRECISION,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(mission_id) REFERENCES work_missions(id) ON DELETE SET NULL,
    FOREIGN KEY(project_id) REFERENCES work_projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_work_tasks_tenant_company ON work_tasks(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_work_tasks_status ON work_tasks(status);
CREATE INDEX IF NOT EXISTS idx_work_tasks_assignee ON work_tasks(assignee_type, assignee_id);
CREATE INDEX IF NOT EXISTS idx_work_tasks_sla ON work_tasks(sla_expires_at, status);

ALTER TABLE work_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_tasks FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'work_tasks' AND policyname = 'tenant_isolation_work_tasks'
    ) THEN
        CREATE POLICY tenant_isolation_work_tasks ON work_tasks
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 4. Task Dependencies Table
CREATE TABLE IF NOT EXISTS task_dependencies (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(task_id) REFERENCES work_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(depends_on_task_id) REFERENCES work_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_task_deps_pair ON task_dependencies(tenant_id, company_id, task_id, depends_on_task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_depends ON task_dependencies(depends_on_task_id);

ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_dependencies FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'task_dependencies' AND policyname = 'tenant_isolation_task_dependencies'
    ) THEN
        CREATE POLICY tenant_isolation_task_dependencies ON task_dependencies
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 5. Task Events Table
CREATE TABLE IF NOT EXISTS task_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    details JSONB,
    evidence_event_id TEXT,
    timestamp DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(task_id) REFERENCES work_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, timestamp);

ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_events FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'task_events' AND policyname = 'tenant_isolation_task_events'
    ) THEN
        CREATE POLICY tenant_isolation_task_events ON task_events
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- 6. Human Inbox Table
CREATE TABLE IF NOT EXISTS human_inbox (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    context_data JSONB,
    target_principal_type TEXT NOT NULL,
    target_principal_id TEXT NOT NULL,
    decision_needed TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    due_date_ts DOUBLE PRECISION,
    acknowledged_at DOUBLE PRECISION,
    acknowledged_by TEXT,
    resolved_at DOUBLE PRECISION,
    resolved_by TEXT,
    resolution_data JSONB,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES work_tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_human_inbox_tenant_company ON human_inbox(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_human_inbox_target ON human_inbox(target_principal_type, target_principal_id, status);

ALTER TABLE human_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_inbox FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'human_inbox' AND policyname = 'tenant_isolation_human_inbox'
    ) THEN
        CREATE POLICY tenant_isolation_human_inbox ON human_inbox
            FOR ALL
            USING (tenant_id = current_setting('zonata.tenant_id', true));
    END IF;
END $$;

-- Rule 15: Agent Role Protections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonata_agent_role') THEN
        REVOKE UPDATE (status, resolved_at, resolved_by, resolution_data) ON human_inbox FROM zonata_agent_role;
    END IF;
END $$;
