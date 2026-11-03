-- Additive migration: rejection/decision reason on approval requests.
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS decision_reason TEXT;
