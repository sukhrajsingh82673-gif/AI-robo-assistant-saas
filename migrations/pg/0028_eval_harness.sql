-- PostgreSQL 16 Migration 0028: Eval Harness and Qualification Results
-- OpenCode Step 2K: Multi-Tenant RLS and Eval Storage

CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tenant_id TEXT,
    company_id TEXT,
    department TEXT NOT NULL,
    tier TEXT NOT NULL,
    model TEXT NOT NULL,
    total_tasks INTEGER NOT NULL,
    passed_tasks INTEGER NOT NULL,
    pass_rate DOUBLE PRECISION NOT NULL,
    total_cost_micro_units BIGINT NOT NULL DEFAULT 0,
    avg_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_dept ON eval_runs(department, created_at);
CREATE INDEX IF NOT EXISTS idx_eval_runs_run_id ON eval_runs(run_id);

ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_runs FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'eval_runs' AND policyname = 'tenant_isolation_eval_runs') THEN
        CREATE POLICY tenant_isolation_eval_runs ON eval_runs
            FOR ALL USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('zonata.tenant_id', true), ''));
    END IF;
END $$;
