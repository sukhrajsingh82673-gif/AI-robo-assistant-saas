-- PostgreSQL 16 Double-Entry Financial Ledger Kernel Migration 0016

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')),
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_accounts_tenant_company_code UNIQUE (tenant_id, company_id, code)
);

CREATE INDEX IF NOT EXISTS idx_accounts_tenant_company ON accounts(tenant_id, company_id);

CREATE TABLE IF NOT EXISTS journal_entries (
    entry_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    folio_id TEXT REFERENCES folios(id) ON DELETE RESTRICT,
    entry_number TEXT NOT NULL,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'POSTED', 'REVERSED')),
    reversal_of_entry_id TEXT REFERENCES journal_entries(entry_id),
    created_by TEXT NOT NULL,
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_journal_entries_num UNIQUE (tenant_id, company_id, entry_number)
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_tenant_company ON journal_entries(tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_folio ON journal_entries(folio_id);

CREATE TABLE IF NOT EXISTS journal_lines (
    line_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entry_id TEXT NOT NULL REFERENCES journal_entries(entry_id) ON DELETE RESTRICT,
    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE RESTRICT,
    debit_amount BIGINT NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount BIGINT NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    memo TEXT,
    CONSTRAINT chk_journal_lines_positive CHECK (debit_amount > 0 OR credit_amount > 0),
    CONSTRAINT chk_journal_lines_not_both CHECK (NOT (debit_amount > 0 AND credit_amount > 0))
);

CREATE INDEX IF NOT EXISTS idx_journal_lines_entry ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_tenant_company ON journal_lines(tenant_id, company_id);

-- Immutability Triggers for PostgreSQL 16
CREATE OR REPLACE FUNCTION fn_prevent_posted_journal_entry_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status IN ('POSTED', 'REVERSED') THEN
            RAISE EXCEPTION 'Posted or reversed journal entries are immutable and cannot be deleted (entry_id: %)', OLD.entry_id;
        END IF;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status = 'POSTED' THEN
            -- Allow ONLY transitioning from POSTED to REVERSED with identical payload
            IF NEW.status = 'REVERSED' AND
               NEW.entry_id = OLD.entry_id AND
               NEW.tenant_id = OLD.tenant_id AND
               NEW.company_id = OLD.company_id AND
               NEW.entry_number = OLD.entry_number AND
               NEW.date = OLD.date THEN
                RETURN NEW;
            ELSE
                RAISE EXCEPTION 'Posted journal entries are immutable and cannot be modified (entry_id: %)', OLD.entry_id;
            END IF;
        ELSIF OLD.status = 'REVERSED' THEN
            RAISE EXCEPTION 'Reversed journal entries are immutable and cannot be modified (entry_id: %)', OLD.entry_id;
        END IF;
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_journal_entries_immutability ON journal_entries;
CREATE TRIGGER trg_journal_entries_immutability
BEFORE UPDATE OR DELETE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_journal_entry_modification();

CREATE OR REPLACE FUNCTION fn_prevent_posted_journal_line_modification()
RETURNS TRIGGER AS $$
DECLARE
    parent_status TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        SELECT status INTO parent_status FROM journal_entries WHERE entry_id = OLD.entry_id;
        IF parent_status IN ('POSTED', 'REVERSED') THEN
            RAISE EXCEPTION 'Lines of a posted or reversed journal entry cannot be deleted (entry_id: %)', OLD.entry_id;
        END IF;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        SELECT status INTO parent_status FROM journal_entries WHERE entry_id = OLD.entry_id;
        IF parent_status IN ('POSTED', 'REVERSED') THEN
            RAISE EXCEPTION 'Lines of a posted or reversed journal entry cannot be updated (entry_id: %)', OLD.entry_id;
        END IF;
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_journal_lines_immutability ON journal_lines;
CREATE TRIGGER trg_journal_lines_immutability
BEFORE UPDATE OR DELETE ON journal_lines
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_journal_line_modification();

-- PostgreSQL 16 Multi-Tenant Row Level Security (RLS)
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['accounts', 'journal_entries', 'journal_lines'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t||'_tenant_isolation', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (' ||
      '  (tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), '''') OR current_setting(''zonata.tenant_id'', true) IS NULL)' ||
      '  AND (company_id = NULLIF(current_setting(''zonata.company_id'', true), '''') OR current_setting(''zonata.company_id'', true) IS NULL)' ||
      ') WITH CHECK (' ||
      '  (tenant_id = NULLIF(current_setting(''zonata.tenant_id'', true), '''') OR current_setting(''zonata.tenant_id'', true) IS NULL)' ||
      '  AND (company_id = NULLIF(current_setting(''zonata.company_id'', true), '''') OR current_setting(''zonata.company_id'', true) IS NULL)' ||
      ')', t||'_tenant_isolation', t
    );
  END LOOP;
END $$;
