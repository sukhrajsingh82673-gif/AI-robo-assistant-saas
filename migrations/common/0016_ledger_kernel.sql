-- SQLite Common Migration 0016: Ledger Kernel

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')),
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    UNIQUE (tenant_id, company_id, code)
);

CREATE INDEX IF NOT EXISTS idx_accounts_tenant_company ON accounts(tenant_id, company_id);

CREATE TABLE IF NOT EXISTS journal_entries (
    entry_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    folio_id TEXT REFERENCES folios(id),
    entry_number TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'POSTED', 'REVERSED')),
    reversal_of_entry_id TEXT REFERENCES journal_entries(entry_id),
    created_by TEXT NOT NULL,
    posted_at REAL,
    created_at REAL NOT NULL,
    UNIQUE (tenant_id, company_id, entry_number)
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_tenant_company ON journal_entries(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_folio ON journal_entries(folio_id);

CREATE TABLE IF NOT EXISTS journal_lines (
    line_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entry_id TEXT NOT NULL REFERENCES journal_entries(entry_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    debit_amount INTEGER NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount INTEGER NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    memo TEXT,
    CHECK (debit_amount > 0 OR credit_amount > 0),
    CHECK (NOT (debit_amount > 0 AND credit_amount > 0))
);

CREATE INDEX IF NOT EXISTS idx_journal_lines_entry ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_tenant_company ON journal_lines(tenant_id, company_id);

-- Immutability Triggers for SQLite
CREATE TRIGGER IF NOT EXISTS trg_prevent_delete_posted_entry
BEFORE DELETE ON journal_entries
FOR EACH ROW
WHEN OLD.status IN ('POSTED', 'REVERSED')
BEGIN
    SELECT RAISE(ABORT, 'Posted or reversed journal entries are immutable and cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_update_posted_entry
BEFORE UPDATE ON journal_entries
FOR EACH ROW
WHEN OLD.status = 'POSTED' AND NOT (
    NEW.status = 'REVERSED' AND
    NEW.entry_id = OLD.entry_id AND
    NEW.tenant_id = OLD.tenant_id AND
    NEW.company_id = OLD.company_id AND
    NEW.entry_number = OLD.entry_number AND
    NEW.date = OLD.date
)
BEGIN
    SELECT RAISE(ABORT, 'Posted journal entries are immutable and cannot be modified');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_update_reversed_entry
BEFORE UPDATE ON journal_entries
FOR EACH ROW
WHEN OLD.status = 'REVERSED'
BEGIN
    SELECT RAISE(ABORT, 'Reversed journal entries are immutable and cannot be modified');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_delete_posted_line
BEFORE DELETE ON journal_lines
FOR EACH ROW
WHEN (SELECT status FROM journal_entries WHERE entry_id = OLD.entry_id) IN ('POSTED', 'REVERSED')
BEGIN
    SELECT RAISE(ABORT, 'Lines of a posted or reversed journal entry cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_update_posted_line
BEFORE UPDATE ON journal_lines
FOR EACH ROW
WHEN (SELECT status FROM journal_entries WHERE entry_id = OLD.entry_id) IN ('POSTED', 'REVERSED')
BEGIN
    SELECT RAISE(ABORT, 'Lines of a posted or reversed journal entry cannot be updated');
END;
