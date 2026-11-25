-- Rollback Migration 0035: Step 9 Schemas Downgrade
-- Safely drops added Step 9 tables and schemas in reverse order per Rule 77.

DROP TABLE IF EXISTS marketplace.installations CASCADE;
DROP TABLE IF EXISTS marketplace.packages CASCADE;
DROP SCHEMA IF EXISTS marketplace CASCADE;

DROP TABLE IF EXISTS product.webhooks CASCADE;
DROP TABLE IF EXISTS product.api_keys CASCADE;
DROP TABLE IF EXISTS product.feature_flags CASCADE;
DROP TABLE IF EXISTS product.tenants_extended CASCADE;
DROP SCHEMA IF EXISTS product CASCADE;

DROP TABLE IF EXISTS billing.cost_caps CASCADE;
DROP TABLE IF EXISTS billing.invoices CASCADE;
DROP TABLE IF EXISTS billing.usage_ledger CASCADE;
DROP TABLE IF EXISTS billing.subscriptions CASCADE;
DROP TABLE IF EXISTS billing.plans CASCADE;
DROP SCHEMA IF EXISTS billing CASCADE;
