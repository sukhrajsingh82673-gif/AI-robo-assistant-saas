-- ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
-- Migration: 0002_add_version_optimistic_locks.sql
-- Adds version column and concurrency tracking to high-contention tables

CREATE TABLE IF NOT EXISTS optimistic_lock_registry (
    table_name TEXT PRIMARY KEY,
    version_column TEXT NOT NULL DEFAULT 'version',
    created_at REAL NOT NULL
);

INSERT OR IGNORE INTO optimistic_lock_registry (table_name, version_column, created_at) VALUES
('tenants', 'version', 1790939000.0),
('companies', 'version', 1790939000.0),
('departments', 'version', 1790939000.0),
('employees', 'version', 1790939000.0),
('missions', 'version', 1790939000.0),
('governed_agents', 'version', 1790939000.0),
('temporal_workflows', 'version', 1790939000.0),
('nango_executions', 'version', 1790939000.0);
