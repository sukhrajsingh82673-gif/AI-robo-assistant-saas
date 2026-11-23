-- PostgreSQL 16 Dialect: Remote View Sessions and Human Takeover Events with RLS (Step 3G)
CREATE TABLE IF NOT EXISTS remote_view_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
    company_id VARCHAR(64) NOT NULL REFERENCES companies(company_id),
    target_type VARCHAR(32) NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    stream_protocol VARCHAR(32) NOT NULL DEFAULT 'WEBSOCKET_MJPEG',
    viewport_bounds JSONB NOT NULL,
    mask_regions JSONB DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS human_takeover_events (
    event_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES remote_view_sessions(session_id),
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
    company_id VARCHAR(64) NOT NULL REFERENCES companies(company_id),
    human_principal_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    handback_state_assertion JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_remote_sessions_active ON remote_view_sessions(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_takeover_events_session ON human_takeover_events(session_id, recorded_at);

ALTER TABLE remote_view_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_takeover_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS remote_view_sessions_tenant_isolation ON remote_view_sessions;
CREATE POLICY remote_view_sessions_tenant_isolation ON remote_view_sessions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

DROP POLICY IF EXISTS human_takeover_events_tenant_isolation ON human_takeover_events;
CREATE POLICY human_takeover_events_tenant_isolation ON human_takeover_events
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
