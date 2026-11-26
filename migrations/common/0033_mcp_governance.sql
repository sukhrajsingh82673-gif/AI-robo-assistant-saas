-- Migration 0033: Governed MCP Server Registrations & Schema Pinning
-- Implements Standing Rule 39 (Untrusted External Metadata) & Multi-Tenant RLS

CREATE TABLE IF NOT EXISTS mcp_server_registrations (
    server_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    transport_type VARCHAR(32) NOT NULL DEFAULT 'stdio',
    endpoint_url TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_tenant_company 
ON mcp_server_registrations(tenant_id, company_id);

CREATE TABLE IF NOT EXISTS mcp_pinned_tools (
    tool_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    server_id VARCHAR(64) NOT NULL,
    tool_name VARCHAR(128) NOT NULL,
    schema_hash VARCHAR(64) NOT NULL,
    raw_schema_json TEXT NOT NULL,
    verified_description TEXT NOT NULL,
    required_action_class VARCHAR(64) NOT NULL DEFAULT 'READ_INTERNAL',
    is_approved INTEGER NOT NULL DEFAULT 0,
    pinned_at REAL NOT NULL,
    FOREIGN KEY (server_id) REFERENCES mcp_server_registrations(server_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mcp_pinned_tools_lookup 
ON mcp_pinned_tools(tenant_id, company_id, server_id, tool_name);
