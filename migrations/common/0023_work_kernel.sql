-- Common SQLite/PostgreSQL Migration 0023: Work Kernel
-- OpenCode Step 2F: Missions, Projects, Work Tasks, Dependencies, Events, and Human Inbox

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
    target_deadline_ts REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_work_missions_tenant_company ON work_missions(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_work_missions_status ON work_missions(status);

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
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(mission_id) REFERENCES work_missions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_work_projects_tenant_company ON work_projects(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_work_projects_mission ON work_projects(mission_id);

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
    acceptance_criteria JSON,
    required_capabilities JSON,
    required_autonomy_level TEXT NOT NULL DEFAULT 'SHADOW',
    sla_seconds INTEGER,
    deadline_ts REAL,
    sla_expires_at REAL,
    sla_escalation_level INTEGER NOT NULL DEFAULT 0,
    linked_folio_id TEXT,
    linked_document_ids JSON,
    assignment_reasons JSON,
    submitted_deliverable JSON,
    verification_report_id TEXT,
    completed_by TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    submitted_at REAL,
    completed_at REAL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(mission_id) REFERENCES work_missions(id) ON DELETE SET NULL,
    FOREIGN KEY(project_id) REFERENCES work_projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_work_tasks_tenant_company ON work_tasks(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_work_tasks_status ON work_tasks(status);
CREATE INDEX IF NOT EXISTS idx_work_tasks_assignee ON work_tasks(assignee_type, assignee_id);
CREATE INDEX IF NOT EXISTS idx_work_tasks_sla ON work_tasks(sla_expires_at, status);

-- 4. Task Dependencies Table (DAG relations)
CREATE TABLE IF NOT EXISTS task_dependencies (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(task_id) REFERENCES work_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(depends_on_task_id) REFERENCES work_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_task_deps_pair ON task_dependencies(tenant_id, company_id, task_id, depends_on_task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_depends ON task_dependencies(depends_on_task_id);

-- 5. Task Events Table (Append-only state audit)
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
    details JSON,
    evidence_event_id TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY(task_id) REFERENCES work_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, timestamp);

-- 6. Human Inbox Table
CREATE TABLE IF NOT EXISTS human_inbox (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    task_id TEXT,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    context_data JSON,
    target_principal_type TEXT NOT NULL,
    target_principal_id TEXT NOT NULL,
    decision_needed TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    due_date_ts REAL,
    acknowledged_at REAL,
    acknowledged_by TEXT,
    resolved_at REAL,
    resolved_by TEXT,
    resolution_data JSON,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES work_tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_human_inbox_tenant_company ON human_inbox(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_human_inbox_target ON human_inbox(target_principal_type, target_principal_id, status);
