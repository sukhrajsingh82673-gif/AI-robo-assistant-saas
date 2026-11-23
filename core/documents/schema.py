"""ZONATA Sovereign Core — Document Backbone Data Model & Schema Bootstrap.

Implements OpenCode Step 1E:
- 10 governed tables:
    1. documents
    2. blobs (deduplicated per tenant via UNIQUE(tenant_id, sha256))
    3. document_versions (immutable version chain)
    4. document_events (append-only lifecycle audit trail)
    5. classifications
    6. extractions (trust: UNTRUSTED, DLP labels, provenance)
    7. retention_policies
    8. legal_holds
    9. access_grants
    10. share_links
- Cross-dialect compatibility (SQLite dev profile and PostgreSQL 16 production).
- RLS policy setup for PostgreSQL 16.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Any
from core.db import db, DatabaseDialect


class DocumentStatus(str, Enum):
    RECEIVED = "RECEIVED"
    QUARANTINED = "QUARANTINED"
    SCANNED = "SCANNED"
    STORED = "STORED"
    EXTRACTED = "EXTRACTED"
    CLASSIFIED = "CLASSIFIED"
    INDEXED = "INDEXED"
    AVAILABLE = "AVAILABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class SensitivityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class DocumentChannel(str, Enum):
    UPLOAD = "UPLOAD"
    API = "API"
    INBOUND_EMAIL = "INBOUND_EMAIL"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"
    RESERVED_BROWSER_SCAN = "RESERVED_BROWSER_SCAN"
    IMPORT_LANE = "IMPORT_LANE"


class ClassificationMethod(str, Enum):
    DETERMINISTIC_RULE = "deterministic_rule"
    MODEL_CLASSIFIER = "model_classifier"
    MANUAL_REVIEW = "manual_review"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VersionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


SQLITE_SCHEMA_DDL = """
-- 1. documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    folio_id TEXT,
    name TEXT NOT NULL,
    current_version_id TEXT,
    status TEXT NOT NULL DEFAULT 'RECEIVED',
    sensitivity_level TEXT NOT NULL DEFAULT 'INTERNAL',
    regime_tags TEXT NOT NULL DEFAULT '[]',
    legal_hold INTEGER NOT NULL DEFAULT 0,
    retention_policy_id TEXT,
    retention_until REAL,
    disposed_at REAL,
    tombstone INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_tenant_comp ON documents (tenant_id, company_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);

-- 2. blobs (deduplicated per tenant)
CREATE TABLE IF NOT EXISTS blobs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    storage_provider TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 1,
    dek_wrapped TEXT,
    encryption_iv TEXT,
    ref_count INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    CONSTRAINT uq_tenant_company_blob_sha UNIQUE (tenant_id, company_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_blobs_sha256 ON blobs (sha256);

-- 3. document_versions (immutable)
CREATE TABLE IF NOT EXISTS document_versions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    blob_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    change_reason TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    evidence_id TEXT,
    created_at REAL NOT NULL,
    CONSTRAINT uq_doc_version UNIQUE (document_id, version_number),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (blob_id) REFERENCES blobs(id)
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_doc ON document_versions (document_id);

-- 4. document_events (append-only)
CREATE TABLE IF NOT EXISTS document_events (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    actor_id TEXT NOT NULL,
    evidence_id TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_doc_events_doc ON document_events (document_id);

-- 5. classifications
CREATE TABLE IF NOT EXISTS classifications (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    method TEXT NOT NULL,
    confidence REAL NOT NULL,
    attributes TEXT NOT NULL DEFAULT '{}',
    classified_by TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'APPROVED',
    created_at REAL NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_classifications_doc ON classifications (document_id);

-- 6. extractions
CREATE TABLE IF NOT EXISTS extractions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    raw_text TEXT,
    trust TEXT NOT NULL DEFAULT 'UNTRUSTED',
    dlp_labels TEXT NOT NULL DEFAULT '[]',
    provenance TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_extractions_doc ON extractions (document_id);

-- 7. retention_policies
CREATE TABLE IF NOT EXISTS retention_policies (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    trigger_event TEXT NOT NULL DEFAULT 'CREATED',
    jurisdiction TEXT NOT NULL DEFAULT 'GLOBAL',
    worm_required INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

-- 8. legal_holds
CREATE TABLE IF NOT EXISTS legal_holds (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    matter_id TEXT,
    applied_by TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    applied_at REAL NOT NULL,
    released_at REAL,
    released_by TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_legal_holds_doc ON legal_holds (document_id);

-- 9. access_grants
CREATE TABLE IF NOT EXISTS access_grants (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    grantee_type TEXT NOT NULL,
    grantee_id TEXT NOT NULL,
    permission TEXT NOT NULL DEFAULT 'READ',
    granted_by TEXT NOT NULL,
    granted_at REAL NOT NULL,
    revoked_at REAL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_access_grants_doc ON access_grants (document_id);

-- 10. share_links
CREATE TABLE IF NOT EXISTS share_links (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL,
    created_by TEXT NOT NULL,
    revoked_at REAL,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_share_links_hash ON share_links (token_hash);
"""


def ensure_document_backbone_tables(conn=None) -> None:
    """Ensures all 10 document backbone tables and indexes are initialized."""
    if conn is not None:
        conn.executescript(SQLITE_SCHEMA_DDL)
        return

    with db.get_connection() as connection:
        if db.dialect == DatabaseDialect.SQLITE:
            connection.executescript(SQLITE_SCHEMA_DDL)
        else:
            # PostgreSQL migration execution
            import os
            mig_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "migrations", "pg", "0014_document_backbone.sql"
            )
            if os.path.exists(mig_path):
                with open(mig_path, "r", encoding="utf-8") as f:
                    connection.execute(f.read())
