-- Reverse of 0012_user_two_step.sql. Destroys enrolled two-step secrets.
-- Never applied automatically; an operator must decide to do this.

DROP INDEX IF EXISTS idx_user_two_step_tenant;
DROP TABLE IF EXISTS user_two_step;
