"""
ZONATA Universal AI Company OS — Enterprise Files & Documents Center
Departmental document management with versioning, cryptographic checksums,
access classification, metadata, and linkages to records, transactions, and agents.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
import hashlib
import os
from .db import db

class EnterpriseFilesEngine:
    """Enterprise file & document repository with departmental taxonomy and evidence tracking."""

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._init_db()
        self._seed_default_files_if_empty()

    def _init_db(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_files (
                file_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                department TEXT NOT NULL, -- Corporate, Finance, HR, Legal, Sales, Marketing, Operations, Procurement, Compliance, AI
                name TEXT NOT NULL,
                category TEXT NOT NULL, -- CONTRACT, INVOICE, REPORT, POLICY, SOP, EVIDENCE, SPREADSHEET, SPECIFICATION
                document_type TEXT NOT NULL, -- PDF, DOCX, XLSX, CSV, JSON, PNG, TXT
                size_bytes INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL,
                classification TEXT NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
                version INTEGER NOT NULL DEFAULT 1,
                storage_path TEXT NOT NULL,
                linked_records JSON, -- linked record_ids
                tags JSON,
                uploaded_by TEXT NOT NULL,
                summary TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_tenant_comp ON enterprise_files(tenant_id, company_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_dept ON enterprise_files(department);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_cat ON enterprise_files(category);")
            conn.commit()

    def list_files(
        self,
        company_id: Optional[str] = None,
        department: Optional[str] = None,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        with db.get_connection() as conn:
            query = "SELECT * FROM enterprise_files WHERE tenant_id = ?"
            params: List[Any] = [self.tenant_id]

            if company_id and company_id != "all":
                query += " AND company_id = ?"
                params.append(company_id)

            if department and department != "ALL":
                query += " AND department = ?"
                params.append(department)

            if category and category != "ALL":
                query += " AND category = ?"
                params.append(category.upper())

            if search_query:
                query += " AND (name LIKE ? OR summary LIKE ?)"
                like_term = f"%{search_query.strip()}%"
                params.extend([like_term, like_term])

            count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
            total = conn.execute(count_query, params).fetchone()[0]

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            files = []
            for r in rows:
                files.append({
                    "file_id": r["file_id"],
                    "tenant_id": r["tenant_id"],
                    "company_id": r["company_id"],
                    "department": r["department"],
                    "name": r["name"],
                    "category": r["category"],
                    "document_type": r["document_type"],
                    "size_bytes": r["size_bytes"],
                    "sha256": r["sha256"],
                    "classification": r["classification"],
                    "version": r["version"],
                    "storage_path": r["storage_path"],
                    "linked_records": json.loads(r["linked_records"]) if r["linked_records"] else [],
                    "tags": json.loads(r["tags"]) if r["tags"] else [],
                    "uploaded_by": r["uploaded_by"],
                    "summary": r["summary"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                })

            return {
                "files": files,
                "total": total,
                "limit": limit,
                "offset": offset
            }

    def register_file(self, data: Dict[str, Any]) -> Dict[str, Any]:
        fid = data.get("file_id") or f"doc_{uuid.uuid4().hex[:10]}"
        now = time.time()
        name = data.get("name", "untitled_document.pdf")
        dept = data.get("department", "Corporate")
        cat = data.get("category", "REPORT").upper()
        dtype = data.get("document_type", name.split(".")[-1].upper() if "." in name else "DOC")
        size = int(data.get("size_bytes", 1024))
        content_str = data.get("content", name)
        sha = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
        storage_path = data.get("storage_path") or f"storage/files/{dept.lower()}/{fid}_{name}"

        with db.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO enterprise_files (
                file_id, tenant_id, company_id, department, name, category,
                document_type, size_bytes, sha256, classification, version,
                storage_path, linked_records, tags, uploaded_by, summary,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fid, self.tenant_id, data.get("company_id", "comp_primary"),
                dept, name, cat, dtype, size, sha,
                data.get("classification", "INTERNAL"),
                int(data.get("version", 1)),
                storage_path,
                json.dumps(data.get("linked_records", [])),
                json.dumps(data.get("tags", [])),
                data.get("uploaded_by", "Owner / AI Assistant"),
                data.get("summary", ""),
                now, now
            ))
            conn.commit()

        return self.get_file(fid)

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM enterprise_files WHERE file_id = ? AND tenant_id = ?",
                (file_id, self.tenant_id)
            ).fetchone()
            if not r:
                return None
            return {
                "file_id": r["file_id"],
                "tenant_id": r["tenant_id"],
                "company_id": r["company_id"],
                "department": r["department"],
                "name": r["name"],
                "category": r["category"],
                "document_type": r["document_type"],
                "size_bytes": r["size_bytes"],
                "sha256": r["sha256"],
                "classification": r["classification"],
                "version": r["version"],
                "storage_path": r["storage_path"],
                "linked_records": json.loads(r["linked_records"]) if r["linked_records"] else [],
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "uploaded_by": r["uploaded_by"],
                "summary": r["summary"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            }

    def _seed_default_files_if_empty(self):
        with db.get_connection() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM enterprise_files WHERE tenant_id = ?", (self.tenant_id,)).fetchone()[0]
            if cnt > 0:
                return

        app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
        clean_mode = (app_env in ("production", "prod")) or (os.environ.get("ZONATA_DISABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes")) or (os.environ.get("ZONATA_CLEAN_STARTUP", "0").lower() in ("1", "true", "yes"))
        if clean_mode:
            return

        now = time.time()
        initial_files = [
            {
                "file_id": "file_corp_incorp",
                "department": "Corporate",
                "name": "Certificate_of_Incorporation_ZONATA_Enterprises.pdf",
                "category": "CONTRACT",
                "document_type": "PDF",
                "size_bytes": 1048576,
                "classification": "CONFIDENTIAL",
                "version": 1,
                "tags": ["corporate", "legal", "incorporation", "statutory"],
                "uploaded_by": "Host / Sovereign Owner",
                "summary": "Statutory corporate registration and sovereign articles of association."
            },
            {
                "file_id": "file_fin_audited_pnl",
                "department": "Finance",
                "name": "Q3_Audited_Financial_Statement_and_CashFlow.xlsx",
                "category": "REPORT",
                "document_type": "XLSX",
                "size_bytes": 2457600,
                "classification": "RESTRICTED",
                "version": 2,
                "tags": ["finance", "pnl", "cashflow", "audited", "q3"],
                "uploaded_by": "Chief Financial Controller",
                "summary": "Reconciled ledger positions, EBITDA metrics, and multi-tenant cash distributions."
            },
            {
                "file_id": "file_legal_msa_taj",
                "department": "Legal",
                "name": "Master_Services_Agreement_Taj_Hospitality_2026.pdf",
                "category": "CONTRACT",
                "document_type": "PDF",
                "size_bytes": 3145728,
                "classification": "CONFIDENTIAL",
                "version": 1,
                "tags": ["legal", "contract", "taj", "hospitality", "msa"],
                "uploaded_by": "Legal Counsel Agent",
                "summary": "Governed contractual master framework with ₹10,00,000 monthly billing schedule."
            },
            {
                "file_id": "file_ops_sop_nightaudit",
                "department": "Operations",
                "name": "SOP-OPS-012_Automated_Night_Audit_and_Room_Reconciliation.pdf",
                "category": "SOP",
                "document_type": "PDF",
                "size_bytes": 524288,
                "classification": "INTERNAL",
                "version": 3,
                "tags": ["operations", "sop", "hospitality", "night_audit", "pms"],
                "uploaded_by": "Operations Excellence Agent",
                "summary": "Standard operating procedure executed autonomously by Hospitality Night Auditor Agent."
            },
            {
                "file_id": "file_hr_handbook_2026",
                "department": "HR",
                "name": "Global_Employee_Policy_Handbook_and_Ethics_Charter.pdf",
                "category": "POLICY",
                "document_type": "PDF",
                "size_bytes": 1835008,
                "classification": "INTERNAL",
                "version": 1,
                "tags": ["hr", "handbook", "ethics", "workforce", "policy"],
                "uploaded_by": "People & Culture Lead",
                "summary": "Comprehensive organizational policies, compensation tiers, and leaves charter."
            },
            {
                "file_id": "file_ai_evidence_sha",
                "department": "AI",
                "name": "Merkle_Audit_Ledger_Cryptographic_Proofs_October_2026.json",
                "category": "EVIDENCE",
                "document_type": "JSON",
                "size_bytes": 4194304,
                "classification": "RESTRICTED",
                "version": 1,
                "tags": ["ai", "merkle", "evidence", "ledger", "immutable"],
                "uploaded_by": "EvidenceLedger Subsystem",
                "summary": "Cryptographically sealed SHA-256 evidence tree for all automated transactions."
            }
        ]

        with db.get_connection() as conn:
            for f in initial_files:
                sha = hashlib.sha256(f["name"].encode("utf-8")).hexdigest()
                conn.execute("""
                INSERT OR IGNORE INTO enterprise_files (
                    file_id, tenant_id, company_id, department, name, category,
                    document_type, size_bytes, sha256, classification, version,
                    storage_path, linked_records, tags, uploaded_by, summary,
                    created_at, updated_at
                ) VALUES (?, ?, 'comp_primary', ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?, ?)
                """, (
                    f["file_id"], self.tenant_id, f["department"], f["name"],
                    f["category"], f["document_type"], f["size_bytes"], sha,
                    f["classification"], f["version"], f"storage/files/{f['name']}",
                    json.dumps(f["tags"]), f["uploaded_by"], f["summary"],
                    now, now
                ))
            conn.commit()

files_engine = EnterpriseFilesEngine()
