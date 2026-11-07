-- Settings V2 append-only guard (PostgreSQL).
-- CREATE RULE ... DO INSTEAD NOTHING keeps this migration free of PL/pgSQL
-- bodies, so the portable SQL splitter and the migration runner can execute it
-- without dialect-specific parsing.  Dropping first makes the file idempotent.

DROP RULE IF EXISTS settings_audit_no_update ON settings_audit;
CREATE RULE settings_audit_no_update AS ON UPDATE TO settings_audit DO INSTEAD NOTHING;

DROP RULE IF EXISTS settings_audit_no_delete ON settings_audit;
CREATE RULE settings_audit_no_delete AS ON DELETE TO settings_audit DO INSTEAD NOTHING;
