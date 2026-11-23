-- PostgreSQL 16 Schema for LangGraph Encrypted Checkpointer (OpenCode Step 4C)

CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint_type TEXT NOT NULL DEFAULT 'checkpoint',
    checkpoint_blob TEXT NOT NULL,
    metadata_blob TEXT NOT NULL,
    step_count INTEGER NOT NULL DEFAULT 0,
    idempotency_key TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (tenant_id, company_id, thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_lg_cp_thread ON langgraph_checkpoints(tenant_id, company_id, thread_id);
CREATE INDEX IF NOT EXISTS idx_lg_cp_idem ON langgraph_checkpoints(tenant_id, company_id, idempotency_key);

ALTER TABLE langgraph_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE langgraph_checkpoints FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lg_cp_tenant_isolation ON langgraph_checkpoints;
CREATE POLICY lg_cp_tenant_isolation ON langgraph_checkpoints
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    )
    WITH CHECK (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    );

CREATE TABLE IF NOT EXISTS langgraph_checkpoint_writes (
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    write_type TEXT,
    value_blob TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (tenant_id, company_id, thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE INDEX IF NOT EXISTS idx_lg_cp_writes ON langgraph_checkpoint_writes(tenant_id, company_id, thread_id, checkpoint_id);

ALTER TABLE langgraph_checkpoint_writes ENABLE ROW LEVEL SECURITY;
ALTER TABLE langgraph_checkpoint_writes FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lg_cp_writes_tenant_isolation ON langgraph_checkpoint_writes;
CREATE POLICY lg_cp_writes_tenant_isolation ON langgraph_checkpoint_writes
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    )
    WITH CHECK (
        tenant_id = current_setting('app.current_tenant_id', true)
        AND (company_id = current_setting('app.current_company_id', true) OR current_setting('app.current_company_id', true) = '')
    );
