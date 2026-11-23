-- SQLite Dialect: Remote View Sessions and Human Takeover Events (Step 3G)
CREATE TABLE IF NOT EXISTS remote_view_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    stream_protocol TEXT NOT NULL DEFAULT 'WEBSOCKET_MJPEG',
    viewport_bounds TEXT NOT NULL,
    mask_regions TEXT DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS human_takeover_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    human_principal_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    handback_state_assertion TEXT,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES remote_view_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_remote_sessions_active ON remote_view_sessions(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_takeover_events_session ON human_takeover_events(session_id, recorded_at);
