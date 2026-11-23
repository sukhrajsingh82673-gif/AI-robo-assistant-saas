-- Migration 0019: Common Schema for Model Gateway, Tiers, Hierarchical Budgets and Tracing

CREATE TABLE IF NOT EXISTS llm_budget_hierarchies (
    budget_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('TENANT', 'COMPANY', 'DEPARTMENT', 'POSITION', 'EMPLOYEE', 'MISSION', 'TASK')),
    entity_id TEXT NOT NULL,
    period_start REAL NOT NULL,
    period_end REAL NOT NULL,
    allocated_micro_usd INTEGER NOT NULL,
    reserved_micro_usd INTEGER NOT NULL DEFAULT 0,
    spent_micro_usd INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    CONSTRAINT uq_budget_entity_period UNIQUE(tenant_id, company_id, entity_type, entity_id, period_start)
);

CREATE INDEX IF NOT EXISTS idx_llm_budget_lookup 
ON llm_budget_hierarchies(tenant_id, company_id, entity_type, entity_id);

CREATE TABLE IF NOT EXISTS llm_budget_reservations (
    reservation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    mission_id TEXT,
    task_id TEXT,
    reserved_micro_usd INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'SETTLED', 'RELEASED')),
    created_at REAL NOT NULL,
    settled_at REAL
);

CREATE INDEX IF NOT EXISTS idx_llm_res_status 
ON llm_budget_reservations(tenant_id, company_id, status);

CREATE TABLE IF NOT EXISTS model_calls (
    call_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    correlation_id TEXT,
    tier TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_micro_usd INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    latency_ms REAL NOT NULL,
    outcome TEXT NOT NULL,
    evidence_id TEXT,
    prompt_stored TEXT,
    response_stored TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_model_calls_tenant 
ON model_calls(tenant_id, company_id);

CREATE INDEX IF NOT EXISTS idx_model_calls_trace 
ON model_calls(trace_id);

CREATE TABLE IF NOT EXISTS tenant_model_policies (
    policy_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    allowed_providers_json TEXT NOT NULL DEFAULT '[]',
    allowed_regions_json TEXT NOT NULL DEFAULT '[]',
    require_no_retention INTEGER NOT NULL DEFAULT 0,
    block_restricted_docs INTEGER NOT NULL DEFAULT 1,
    allow_degraded INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    CONSTRAINT uq_tenant_company_model_policy UNIQUE(tenant_id, company_id)
);

CREATE TABLE IF NOT EXISTS llm_price_catalog (
    price_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    effective_from REAL NOT NULL,
    effective_to REAL,
    input_micro_usd_per_1k INTEGER NOT NULL,
    output_micro_usd_per_1k INTEGER NOT NULL,
    CONSTRAINT uq_provider_model_effective UNIQUE(provider, model, effective_from)
);
