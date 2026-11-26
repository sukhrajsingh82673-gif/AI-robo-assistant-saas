"""
ZONATA Sovereign Financial Ledger — Schema, Enums, and Table Initialization
"""

from enum import Enum
import os
import pathlib
from typing import Any, Optional


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

    @property
    def is_debit_normal(self) -> bool:
        """Assets and Expenses carry a normal DEBIT balance."""
        return self in (AccountType.ASSET, AccountType.EXPENSE)

    @property
    def is_credit_normal(self) -> bool:
        """Liabilities, Equity, and Revenue carry a normal CREDIT balance."""
        return self in (AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE)


class JournalEntryStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


def ensure_ledger_tables(conn: Optional[Any] = None) -> None:
    """Ensures accounts, journal_entries, and journal_lines tables and immutability triggers exist."""
    from core.db import db, DatabaseDialect

    migration_file = "0016_ledger_kernel.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    if conn is not None:
        if db.pg_tables_ready(conn, "accounts", "journal_entries", "journal_lines"):
            return
        if hasattr(conn, "executescript") and db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                conn.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                conn.execute(sql_path.read_text(encoding="utf-8"))
        return

    with db.get_connection() as connection:
        if db.pg_tables_ready(connection, "accounts", "journal_entries", "journal_lines"):
            return
        if db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                connection.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                connection.execute(sql_path.read_text(encoding="utf-8"))
