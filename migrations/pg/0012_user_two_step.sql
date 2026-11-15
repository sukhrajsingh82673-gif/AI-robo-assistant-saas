-- ============================================================================
-- ZONATA — Real TOTP two-step verification (additive)
--
-- One row per account. The shared secret is encrypted with AES-GCM using a
-- key derived from ZONATA_AUTH_SECRET; this table never stores the plaintext
-- secret. pending=1 means the user has not proven a code yet.
--
-- The reverse migration is migrations/rollback/pg/0012_user_two_step_rollback.sql
-- and is never applied automatically.
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_two_step (
    user_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'TOTP',
    secret_ciphertext TEXT NOT NULL,
    secret_nonce TEXT NOT NULL,
    key_id TEXT NOT NULL,
    pending INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_used_step INTEGER NOT NULL DEFAULT 0,
    created_at DOUBLE PRECISION NOT NULL,
    confirmed_at DOUBLE PRECISION,
    updated_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_two_step_tenant ON user_two_step(tenant_id);
