-- Settings V2 append-only guard (SQLite).
-- The canonical audit table is created in migrations/common/0003.
-- Application code must never update or delete audit rows; these triggers make
-- that guarantee a property of the database rather than a convention.

CREATE TRIGGER IF NOT EXISTS settings_audit_no_update
BEFORE UPDATE ON settings_audit
BEGIN
    SELECT RAISE(ABORT, 'settings_audit is append-only: UPDATE is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS settings_audit_no_delete
BEFORE DELETE ON settings_audit
BEGIN
    SELECT RAISE(ABORT, 'settings_audit is append-only: DELETE is forbidden');
END;
