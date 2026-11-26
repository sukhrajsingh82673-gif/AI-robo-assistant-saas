-- Rollback Migration 0034: Step 8 Schemas Downgrade
-- Safely drops added Step 8 tables and schemas in reverse order.

DROP TABLE IF EXISTS benchmarks.benchmark_claims CASCADE;
DROP TABLE IF EXISTS benchmarks.benchmark_vault CASCADE;
DROP SCHEMA IF EXISTS benchmarks CASCADE;

DROP TABLE IF EXISTS jurisdictions.jurisdiction_packs CASCADE;
DROP SCHEMA IF EXISTS jurisdictions CASCADE;

DROP TABLE IF EXISTS industries.overlay_expert_reviews CASCADE;
DROP TABLE IF EXISTS industries.industry_overlays CASCADE;
DROP SCHEMA IF EXISTS industries CASCADE;
