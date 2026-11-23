-- Common SQLite/PostgreSQL Migration 0028: Eval Harness and Qualification Results
-- OpenCode Step 2K: Golden eval tasks per department, pass rates, costs, and qualification runs

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
    pass_rate REAL NOT NULL,
    total_cost_micro_units BIGINT NOT NULL DEFAULT 0,
    avg_latency_ms REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_dept ON eval_runs(department, created_at);
CREATE INDEX IF NOT EXISTS idx_eval_runs_run_id ON eval_runs(run_id);
