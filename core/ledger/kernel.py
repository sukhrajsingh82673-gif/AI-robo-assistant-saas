"""
ZONATA Sovereign Financial Ledger — Double-Entry Financial Ledger Kernel
Strict adherence to:
- Rule 1: Truth rule (never fabricate balances or posting receipts)
- Rule 12: Integer minor units only, zero float arithmetic, UTC timestamps
- Sub-step 1G: Multi-tenant, zero-balance invariant, database-enforced immutability,
               reversing entries, trial balance generation, folio integration.
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

from core.db import db
from core.ledger.currency import format_minor_units, validate_currency
from core.ledger.schema import (
    AccountType,
    JournalEntryStatus,
    ensure_ledger_tables,
)


class LedgerError(Exception):
    """Base exception for ledger kernel operations."""
    pass


class UnbalancedJournalEntryError(LedgerError):
    """Raised when sum(debits) != sum(credits) per currency in a journal entry."""
    pass


class ImmutableJournalEntryError(LedgerError):
    """Raised when an attempt is made to update or delete a POSTED or REVERSED journal entry."""
    pass


class InactiveAccountError(LedgerError):
    """Raised when attempting to post transactions to an inactive account."""
    pass


class CurrencyMismatchError(LedgerError):
    """Raised when line currency does not match account currency."""
    pass


class InvalidMinorUnitError(LedgerError):
    """Raised when debit or credit amount is negative, fractional, or non-integer."""
    pass


class UnpostedFolioJournalEntriesError(LedgerError):
    """Raised when sealing a folio that contains draft or unposted journal entries."""
    pass


class LedgerKernel:
    """Double-entry financial ledger kernel enforcing strict statutory invariants."""

    def __init__(self):
        ensure_ledger_tables()

    # =========================================================================
    # 1. CHART OF ACCOUNTS (COA)
    # =========================================================================

    def create_account(
        self,
        tenant_id: str,
        company_id: str,
        code: str,
        name: str,
        account_type: AccountType,
        currency: str,
        is_active: bool = True,
    ) -> str:
        """Creates a governed ledger account within a company's Chart of Accounts."""
        curr = validate_currency(currency)
        if not isinstance(account_type, AccountType):
            account_type = AccountType(account_type)

        account_id = f"acct_{uuid.uuid4().hex[:16]}"
        now = time.time()

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO accounts (
                    account_id, tenant_id, company_id, code, name, type, currency, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    tenant_id,
                    company_id,
                    code.strip(),
                    name.strip(),
                    account_type.value,
                    curr,
                    1 if is_active else 0,
                    now,
                ),
            )
            conn.commit()

        return account_id

    def get_account(self, tenant_id: str, company_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an account by its ID, enforcing tenant and company scoping."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT account_id, tenant_id, company_id, code, name, type, currency, is_active, created_at
                FROM accounts
                WHERE tenant_id = ? AND company_id = ? AND account_id = ?
                """,
                (tenant_id, company_id, account_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "account_id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "code": row[3],
                "name": row[4],
                "type": AccountType(row[5]),
                "currency": row[6],
                "is_active": bool(row[7]),
                "created_at": row[8],
            }

    def get_account_by_code(self, tenant_id: str, company_id: str, code: str) -> Optional[Dict[str, Any]]:
        """Retrieves an account by its code within a tenant and company."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT account_id, tenant_id, company_id, code, name, type, currency, is_active, created_at
                FROM accounts
                WHERE tenant_id = ? AND company_id = ? AND code = ?
                """,
                (tenant_id, company_id, code.strip()),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "account_id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "code": row[3],
                "name": row[4],
                "type": AccountType(row[5]),
                "currency": row[6],
                "is_active": bool(row[7]),
                "created_at": row[8],
            }

    def list_accounts(self, tenant_id: str, company_id: str, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Lists accounts for a company with optional active filter."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            sql = "SELECT account_id, tenant_id, company_id, code, name, type, currency, is_active, created_at FROM accounts WHERE tenant_id = ? AND company_id = ?"
            params: List[Any] = [tenant_id, company_id]
            if is_active is not None:
                sql += " AND is_active = ?"
                params.append(1 if is_active else 0)
            sql += " ORDER BY code ASC"
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [
                {
                    "account_id": r[0],
                    "tenant_id": r[1],
                    "company_id": r[2],
                    "code": r[3],
                    "name": r[4],
                    "type": AccountType(r[5]),
                    "currency": r[6],
                    "is_active": bool(r[7]),
                    "created_at": r[8],
                }
                for r in rows
            ]

    # =========================================================================
    # 2. JOURNAL ENTRIES & LINES
    # =========================================================================

    def create_journal_entry(
        self,
        tenant_id: str,
        company_id: str,
        entry_number: str,
        date: str,
        description: str,
        created_by: str,
        folio_id: Optional[str] = None,
        reversal_of_entry_id: Optional[str] = None,
    ) -> str:
        """Initializes a new journal entry in DRAFT status."""
        entry_id = f"je_{uuid.uuid4().hex[:16]}"
        now = time.time()

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO journal_entries (
                    entry_id, tenant_id, company_id, folio_id, entry_number, date, description,
                    status, reversal_of_entry_id, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?)
                """,
                (
                    entry_id,
                    tenant_id,
                    company_id,
                    folio_id,
                    entry_number.strip(),
                    date.strip(),
                    description.strip(),
                    reversal_of_entry_id,
                    created_by,
                    now,
                ),
            )
            conn.commit()

        return entry_id

    def add_journal_line(
        self,
        tenant_id: str,
        company_id: str,
        entry_id: str,
        account_id: str,
        debit_amount: int,
        credit_amount: int,
        currency: str,
        memo: Optional[str] = None,
    ) -> str:
        """Adds a debit or credit line to a DRAFT journal entry.
        
        Strict minor unit integer verification (no floats, non-negative).
        """
        curr = validate_currency(currency)

        # Rule 12 / Invariant checks: Integer minor units only
        if not isinstance(debit_amount, int) or isinstance(debit_amount, bool):
            raise InvalidMinorUnitError(f"Debit amount must be integer minor units, got {type(debit_amount).__name__}")
        if not isinstance(credit_amount, int) or isinstance(credit_amount, bool):
            raise InvalidMinorUnitError(f"Credit amount must be integer minor units, got {type(credit_amount).__name__}")
        if debit_amount < 0 or credit_amount < 0:
            raise InvalidMinorUnitError("Debit and credit amounts cannot be negative")
        if (debit_amount > 0 and credit_amount > 0) or (debit_amount == 0 and credit_amount == 0):
            raise InvalidMinorUnitError("A journal line must specify either a positive debit OR a positive credit, never both or neither")

        with db.get_connection() as conn:
            cur = conn.cursor()

            # Verify entry exists and is DRAFT
            cur.execute(
                "SELECT status, tenant_id, company_id FROM journal_entries WHERE entry_id = ?",
                (entry_id,),
            )
            entry_row = cur.fetchone()
            if not entry_row:
                raise LedgerError(f"Journal entry {entry_id} not found")
            if entry_row[1] != tenant_id or entry_row[2] != company_id:
                raise LedgerError(f"Journal entry {entry_id} belongs to a different tenant/company")
            if entry_row[0] != JournalEntryStatus.DRAFT.value:
                raise ImmutableJournalEntryError(f"Cannot add lines to entry {entry_id} with status {entry_row[0]}")

            # Verify account exists, belongs to same tenant/company, is active, and currency matches
            cur.execute(
                "SELECT currency, is_active FROM accounts WHERE tenant_id = ? AND company_id = ? AND account_id = ?",
                (tenant_id, company_id, account_id),
            )
            acct_row = cur.fetchone()
            if not acct_row:
                raise LedgerError(f"Account {account_id} not found in tenant {tenant_id} / company {company_id}")
            if not acct_row[1]:
                raise InactiveAccountError(f"Account {account_id} is inactive")
            if acct_row[0] != curr:
                raise CurrencyMismatchError(
                    f"Line currency '{curr}' does not match account currency '{acct_row[0]}'"
                )

            line_id = f"jl_{uuid.uuid4().hex[:16]}"
            cur.execute(
                """
                INSERT INTO journal_lines (
                    line_id, tenant_id, company_id, entry_id, account_id, debit_amount, credit_amount, currency, memo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    line_id,
                    tenant_id,
                    company_id,
                    entry_id,
                    account_id,
                    debit_amount,
                    credit_amount,
                    curr,
                    memo,
                ),
            )
            conn.commit()

        return line_id

    def get_journal_entry(self, tenant_id: str, company_id: str, entry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a journal entry with all its lines."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT entry_id, tenant_id, company_id, folio_id, entry_number, date, description,
                       status, reversal_of_entry_id, created_by, posted_at, created_at
                FROM journal_entries
                WHERE tenant_id = ? AND company_id = ? AND entry_id = ?
                """,
                (tenant_id, company_id, entry_id),
            )
            row = cur.fetchone()
            if not row:
                return None

            cur.execute(
                """
                SELECT line_id, account_id, debit_amount, credit_amount, currency, memo
                FROM journal_lines
                WHERE entry_id = ?
                ORDER BY line_id ASC
                """,
                (entry_id,),
            )
            line_rows = cur.fetchall()

            return {
                "entry_id": row[0],
                "tenant_id": row[1],
                "company_id": row[2],
                "folio_id": row[3],
                "entry_number": row[4],
                "date": row[5],
                "description": row[6],
                "status": JournalEntryStatus(row[7]),
                "reversal_of_entry_id": row[8],
                "created_by": row[9],
                "posted_at": row[10],
                "created_at": row[11],
                "lines": [
                    {
                        "line_id": lr[0],
                        "account_id": lr[1],
                        "debit_amount": lr[2],
                        "credit_amount": lr[3],
                        "currency": lr[4],
                        "memo": lr[5],
                    }
                    for lr in line_rows
                ],
            }

    # =========================================================================
    # 3. POSTING & ZERO-BALANCE ENFORCEMENT
    # =========================================================================

    def post_journal_entry(self, tenant_id: str, company_id: str, entry_id: str) -> Dict[str, Any]:
        """Posts a DRAFT journal entry after validating the zero-balance invariant per currency.
        
        Once posted, database triggers make the entry and lines strictly immutable.
        """
        entry = self.get_journal_entry(tenant_id, company_id, entry_id)
        if not entry:
            raise LedgerError(f"Journal entry {entry_id} not found")
        if entry["status"] != JournalEntryStatus.DRAFT:
            raise LedgerError(f"Cannot post journal entry with status {entry['status'].value}")

        lines = entry["lines"]
        if len(lines) < 2:
            raise UnbalancedJournalEntryError(
                f"Journal entry {entry_id} must have at least 2 lines, found {len(lines)}"
            )

        # Invariant 3: Zero-balance strictly per currency
        currency_totals: Dict[str, Dict[str, int]] = {}
        for line in lines:
            curr = line["currency"]
            if curr not in currency_totals:
                currency_totals[curr] = {"debits": 0, "credits": 0}
            currency_totals[curr]["debits"] += line["debit_amount"]
            currency_totals[curr]["credits"] += line["credit_amount"]

        for curr, totals in currency_totals.items():
            debits = totals["debits"]
            credits = totals["credits"]
            if debits != credits:
                raise UnbalancedJournalEntryError(
                    f"Journal entry {entry_id} is unbalanced for currency '{curr}': "
                    f"total debits {format_minor_units(debits, curr)} != total credits {format_minor_units(credits, curr)}"
                )
            if debits <= 0:
                raise UnbalancedJournalEntryError(
                    f"Journal entry {entry_id} currency leg '{curr}' has zero total amount"
                )

        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE journal_entries
                SET status = 'POSTED', posted_at = ?
                WHERE entry_id = ? AND status = 'DRAFT'
                """,
                (now, entry_id),
            )
            conn.commit()

        entry["status"] = JournalEntryStatus.POSTED
        entry["posted_at"] = now

        # Folio integration: if linked to a folio, log timeline entry
        if entry.get("folio_id"):
            try:
                from core.folios.manager import FolioManager
                from core.folios.schema import FolioEntryType
                f_mgr = FolioManager()
                f_mgr.add_entry(
                    folio_id=entry["folio_id"],
                    entry_type=FolioEntryType.RECEIPT,
                    reference_id=entry_id,
                    title=f"Journal Entry Posted: {entry['entry_number']}",
                    payload={
                        "entry_id": entry_id,
                        "entry_number": entry["entry_number"],
                        "date": entry["date"],
                        "currencies": list(currency_totals.keys()),
                        "totals": {c: t["debits"] for c, t in currency_totals.items()},
                    },
                    author_id=entry["created_by"],
                )
            except Exception:
                pass

        return entry

    # =========================================================================
    # 4. REVERSING ENTRIES (CORRECTIONS)
    # =========================================================================

    def reverse_journal_entry(
        self,
        tenant_id: str,
        company_id: str,
        original_entry_id: str,
        reversal_entry_number: str,
        reversed_by: str,
        reason: Optional[str] = None,
    ) -> str:
        """Creates a reversing journal entry (mirror debits & credits) and marks the original as REVERSED.
        
        Strict adherence to Invariant 4: Posted entries are immutable.
        Corrections are done exclusively via reversing entries.
        """
        orig = self.get_journal_entry(tenant_id, company_id, original_entry_id)
        if not orig:
            raise LedgerError(f"Original journal entry {original_entry_id} not found")
        if orig["status"] != JournalEntryStatus.POSTED:
            raise LedgerError(
                f"Cannot reverse journal entry {original_entry_id}: "
                f"expected status POSTED, got {orig['status'].value}"
            )

        # 1. Create reversal journal entry
        rev_desc = f"Reversal of {orig['entry_number']}"
        if reason:
            rev_desc += f": {reason}"

        reversal_entry_id = self.create_journal_entry(
            tenant_id=tenant_id,
            company_id=company_id,
            entry_number=reversal_entry_number,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            description=rev_desc,
            created_by=reversed_by,
            folio_id=orig.get("folio_id"),
            reversal_of_entry_id=original_entry_id,
        )

        # 2. Add mirror swapped lines (swap debit and credit)
        for line in orig["lines"]:
            self.add_journal_line(
                tenant_id=tenant_id,
                company_id=company_id,
                entry_id=reversal_entry_id,
                account_id=line["account_id"],
                debit_amount=line["credit_amount"],   # Swapped!
                credit_amount=line["debit_amount"],   # Swapped!
                currency=line["currency"],
                memo=f"Reversal of line {line['line_id']}: {line.get('memo') or ''}".strip(),
            )

        # 3. Post the reversal entry
        self.post_journal_entry(tenant_id, company_id, reversal_entry_id)

        # 4. Mark original entry as REVERSED
        # (Our database triggers explicitly allow setting status='REVERSED' on POSTED entries)
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE journal_entries SET status = 'REVERSED' WHERE entry_id = ? AND status = 'POSTED'",
                (original_entry_id,),
            )
            conn.commit()

        return reversal_entry_id

    # =========================================================================
    # 5. TRIAL BALANCE GENERATION
    # =========================================================================

    def generate_trial_balance(
        self,
        tenant_id: str,
        company_id: str,
        currency: str,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates a company-scoped trial balance as of a given date.
        
        Calculates total debits and credits per account and mathematically verifies:
        sum(total_debit) == sum(total_credit) across all accounts.
        """
        curr = validate_currency(currency)

        with db.get_connection() as conn:
            cur = conn.cursor()

            # Query all accounts for company with given currency
            cur.execute(
                """
                SELECT account_id, code, name, type
                FROM accounts
                WHERE tenant_id = ? AND company_id = ? AND currency = ?
                ORDER BY code ASC
                """,
                (tenant_id, company_id, curr),
            )
            accounts = cur.fetchall()

            # Query posted lines up to as_of_date
            sql = """
                SELECT jl.account_id,
                       COALESCE(SUM(jl.debit_amount), 0) AS total_debit,
                       COALESCE(SUM(jl.credit_amount), 0) AS total_credit
                FROM journal_lines jl
                JOIN journal_entries je ON jl.entry_id = je.entry_id
                WHERE je.tenant_id = ? AND je.company_id = ? AND jl.currency = ?
                  AND je.status IN ('POSTED', 'REVERSED')
            """
            params: List[Any] = [tenant_id, company_id, curr]
            if as_of_date:
                sql += " AND je.date <= ?"
                params.append(as_of_date)

            sql += " GROUP BY jl.account_id"
            cur.execute(sql, tuple(params))
            totals_by_account = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

            grand_total_debits = 0
            grand_total_credits = 0
            account_balances: List[Dict[str, Any]] = []

            for acct_id, code, name, acct_type_str in accounts:
                acct_type = AccountType(acct_type_str)
                deb, cred = totals_by_account.get(acct_id, (0, 0))
                grand_total_debits += deb
                grand_total_credits += cred

                # Net balance based on normal balance convention
                if acct_type.is_debit_normal:
                    net = deb - cred
                else:
                    net = cred - deb

                account_balances.append({
                    "account_id": acct_id,
                    "code": code,
                    "name": name,
                    "type": acct_type.value,
                    "currency": curr,
                    "total_debit": deb,
                    "total_credit": cred,
                    "net_balance": net,
                })

            # Check zero-balance invariant
            is_balanced = (grand_total_debits == grand_total_credits)

            return {
                "tenant_id": tenant_id,
                "company_id": company_id,
                "currency": curr,
                "as_of_date": as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "accounts": account_balances,
                "total_debits": grand_total_debits,
                "total_credits": grand_total_credits,
                "is_balanced": is_balanced,
                "formatted": {
                    "total_debits": format_minor_units(grand_total_debits, curr),
                    "total_credits": format_minor_units(grand_total_credits, curr),
                },
            }

    # =========================================================================
    # 6. FOLIO INTEGRATION VERIFICATION
    # =========================================================================

    def verify_folio_journal_entries_posted(self, tenant_id: str, company_id: str, folio_id: str) -> bool:
        """Verifies that all journal entries associated with a folio are in POSTED status."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM journal_entries
                WHERE tenant_id = ? AND company_id = ? AND folio_id = ? AND status != 'POSTED'
                """,
                (tenant_id, company_id, folio_id),
            )
            unposted_count = cur.fetchone()[0]
            if unposted_count > 0:
                raise UnpostedFolioJournalEntriesError(
                    f"Folio {folio_id} cannot be sealed: {unposted_count} linked journal entries are unposted"
                )
            return True
