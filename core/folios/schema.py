"""ZONATA Sovereign Core — Folio Backbone Schema and State Machine.

Implements OpenCode Step 1F:
- Folio aggregate data model (folios, folio_entries).
- State machine: OPEN → ACTIVE → SUSPENDED → PENDING_CLOSE → CLOSED → ARCHIVED → EXPUNGED.
- Entry types: DOCUMENT, LEDGER_TRANSACTION, TASK, EVENT, COMMUNICATION.
- Cross-dialect compatibility (SQLite dev profile and PostgreSQL 16 production).
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Set, Any
from core.db import db, DatabaseDialect


class FolioStatus(str, Enum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_CLOSE = "PENDING_CLOSE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
    EXPUNGED = "EXPUNGED"


class FolioEntryType(str, Enum):
    DOCUMENT = "DOCUMENT"
    LEDGER_TRANSACTION = "LEDGER_TRANSACTION"
    TASK = "TASK"
    EVENT = "EVENT"
    COMMUNICATION = "COMMUNICATION"


# Strict state transition matrix
ALLOWED_TRANSITIONS: Dict[FolioStatus, Set[FolioStatus]] = {
    FolioStatus.OPEN: {FolioStatus.ACTIVE, FolioStatus.SUSPENDED, FolioStatus.CLOSED},
    FolioStatus.ACTIVE: {FolioStatus.SUSPENDED, FolioStatus.PENDING_CLOSE, FolioStatus.CLOSED},
    FolioStatus.SUSPENDED: {FolioStatus.ACTIVE, FolioStatus.PENDING_CLOSE, FolioStatus.CLOSED},
    FolioStatus.PENDING_CLOSE: {FolioStatus.CLOSED, FolioStatus.ACTIVE},
    FolioStatus.CLOSED: {FolioStatus.ARCHIVED, FolioStatus.EXPUNGED},
    FolioStatus.ARCHIVED: {FolioStatus.EXPUNGED},
    FolioStatus.EXPUNGED: set(),  # Terminal state
}


SQLITE_FOLIO_SCHEMA_DDL = """
-- 1. folios
CREATE TABLE IF NOT EXISTS folios (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    folio_type TEXT NOT NULL,
    title TEXT NOT NULL,
    subject_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    retention_policy_id TEXT,
    retention_until REAL,
    merkle_root TEXT NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
    created_by TEXT NOT NULL,
    closed_at REAL,
    archived_at REAL,
    expunged_at REAL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_folios_tenant_comp ON folios (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_folios_status ON folios (status);
CREATE INDEX IF NOT EXISTS idx_folios_type ON folios (folio_type);

-- 2. folio_entries
CREATE TABLE IF NOT EXISTS folio_entries (
    id TEXT PRIMARY KEY,
    folio_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    title TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    author_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    entry_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    CONSTRAINT uq_folio_seq UNIQUE (folio_id, sequence_number),
    FOREIGN KEY (folio_id) REFERENCES folios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_folio_entries_folio ON folio_entries (folio_id);
CREATE INDEX IF NOT EXISTS idx_folio_entries_ref ON folio_entries (reference_id);
"""


def ensure_folio_tables(conn=None) -> None:
    """Ensures folios and folio_entries tables and indexes are initialized."""
    if conn is not None:
        conn.executescript(SQLITE_FOLIO_SCHEMA_DDL)
        return

    with db.get_connection() as connection:
        if db.dialect == DatabaseDialect.SQLITE:
            connection.executescript(SQLITE_FOLIO_SCHEMA_DDL)
        else:
            import os
            mig_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "migrations", "pg", "0015_folio_evidence_backbone.sql"
            )
            if os.path.exists(mig_path):
                with open(mig_path, "r", encoding="utf-8") as f:
                    connection.execute(f.read())
