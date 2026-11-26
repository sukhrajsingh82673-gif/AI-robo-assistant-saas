"""
ZONATA Universal AI Company OS — Enterprise Records Engine
Comprehensive structured business events & historical state management:
Customer, Vendor, Employee, Expense, Revenue, Payment, Invoice, Purchase Order,
Sales Order, Inventory Movement, Journal Entry, Incident, Audit Record, AI Decisions.

Supports timeline, table, relations graph, date filters, and cryptographic evidence links.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
import sqlite3
import os
from .db import db
from .evidence_ledger import EvidenceLedger

class EnterpriseRecordsEngine:
    """Manages structured business events and historical state with immutable IDs and audit trails."""

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._init_db()
        self._seed_default_records_if_empty()

    def _init_db(self):
        with db.get_connection() as conn:
            if db.pg_tables_ready(conn, "enterprise_records"):
                return
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_records (
                record_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                department TEXT NOT NULL,
                record_type TEXT NOT NULL, -- CUSTOMER, VENDOR, EMPLOYEE, EXPENSE, REVENUE, PAYMENT, INVOICE, PURCHASE_ORDER, SALES_ORDER, INVENTORY, JOURNAL, AUDIT, DECISION
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'COMPLETED', -- DRAFT, PENDING, APPROVED, COMPLETED, CANCELLED, FLAGGED
                actor_type TEXT NOT NULL DEFAULT 'AI_AGENT', -- HUMAN_OWNER, AI_AGENT, SYSTEM, EXTERNAL_INTEGRATION
                actor_name TEXT NOT NULL,
                amount REAL DEFAULT 0.0,
                currency TEXT DEFAULT '₹',
                attributes JSON,
                relations JSON, -- linked record_ids, file_ids, transaction_ids
                evidence_id TEXT,
                notes TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_tenant_comp ON enterprise_records(tenant_id, company_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_type ON enterprise_records(record_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_dept ON enterprise_records(department);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_created ON enterprise_records(created_at);")
            conn.commit()

    def list_records(
        self,
        company_id: Optional[str] = None,
        record_type: Optional[str] = None,
        department: Optional[str] = None,
        date_range: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lists records with rich multi-dimensional enterprise filtering."""
        with db.get_connection() as conn:
            query = "SELECT * FROM enterprise_records WHERE tenant_id = ?"
            params: List[Any] = [self.tenant_id]

            if company_id and company_id != "all":
                query += " AND company_id = ?"
                params.append(company_id)

            if record_type and record_type != "ALL":
                query += " AND record_type = ?"
                params.append(record_type.upper())

            if department and department != "ALL":
                query += " AND department = ?"
                params.append(department)

            now = time.time()
            if date_range == "TODAY":
                query += " AND created_at >= ?"
                params.append(now - 86400)
            elif date_range == "YESTERDAY":
                query += " AND created_at >= ? AND created_at < ?"
                params.extend([now - 172800, now - 86400])
            elif date_range == "THIS_WEEK":
                query += " AND created_at >= ?"
                params.append(now - (7 * 86400))
            elif date_range == "THIS_MONTH":
                query += " AND created_at >= ?"
                params.append(now - (30 * 86400))
            elif date_range == "THIS_QUARTER":
                query += " AND created_at >= ?"
                params.append(now - (90 * 86400))
            elif date_range == "THIS_YEAR":
                query += " AND created_at >= ?"
                params.append(now - (365 * 86400))

            if search_query:
                query += " AND (title LIKE ? OR actor_name LIKE ? OR notes LIKE ?)"
                like_term = f"%{search_query.strip()}%"
                params.extend([like_term, like_term, like_term])

            # Get total count
            count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
            total = conn.execute(count_query, params).fetchone()[0]

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            records = []
            for r in rows:
                attrs = json.loads(r["attributes"]) if r["attributes"] else {}
                rels = json.loads(r["relations"]) if r["relations"] else {}
                records.append({
                    "record_id": r["record_id"],
                    "tenant_id": r["tenant_id"],
                    "company_id": r["company_id"],
                    "department": r["department"],
                    "record_type": r["record_type"],
                    "title": r["title"],
                    "status": r["status"],
                    "actor_type": r["actor_type"],
                    "actor_name": r["actor_name"],
                    "amount": r["amount"],
                    "currency": r["currency"],
                    "attributes": attrs,
                    "relations": rels,
                    "evidence_id": r["evidence_id"],
                    "notes": r["notes"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                })

            return {
                "records": records,
                "total": total,
                "limit": limit,
                "offset": offset
            }

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM enterprise_records WHERE record_id = ? AND tenant_id = ?",
                (record_id, self.tenant_id)
            ).fetchone()
            if not r:
                return None
            return {
                "record_id": r["record_id"],
                "tenant_id": r["tenant_id"],
                "company_id": r["company_id"],
                "department": r["department"],
                "record_type": r["record_type"],
                "title": r["title"],
                "status": r["status"],
                "actor_type": r["actor_type"],
                "actor_name": r["actor_name"],
                "amount": r["amount"],
                "currency": r["currency"],
                "attributes": json.loads(r["attributes"]) if r["attributes"] else {},
                "relations": json.loads(r["relations"]) if r["relations"] else {},
                "evidence_id": r["evidence_id"],
                "notes": r["notes"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            }

    def create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        rec_id = data.get("record_id") or f"rec_{uuid.uuid4().hex[:10]}"
        now = time.time()
        company_id = data.get("company_id", "comp_primary")
        dept = data.get("department", "Operations")
        rtype = (data.get("record_type") or "AUDIT").upper()
        title = data.get("title", "Untitled Record").strip()
        status = data.get("status", "COMPLETED").upper()
        actor_type = data.get("actor_type", "AI_AGENT")
        actor_name = data.get("actor_name", "ZONATA AI Operations Agent")
        amount = float(data.get("amount", 0.0))
        currency = data.get("currency", "₹")
        attrs = data.get("attributes", {})
        rels = data.get("relations", {})
        evidence_id = data.get("evidence_id") or f"evi_{uuid.uuid4().hex[:8]}"
        notes = data.get("notes", "")

        with db.get_connection() as conn:
            conn.execute("""
            INSERT INTO enterprise_records (
                record_id, tenant_id, company_id, department, record_type,
                title, status, actor_type, actor_name, amount, currency,
                attributes, relations, evidence_id, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (record_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                company_id = EXCLUDED.company_id,
                department = EXCLUDED.department,
                record_type = EXCLUDED.record_type,
                title = EXCLUDED.title,
                status = EXCLUDED.status,
                actor_type = EXCLUDED.actor_type,
                actor_name = EXCLUDED.actor_name,
                amount = EXCLUDED.amount,
                currency = EXCLUDED.currency,
                attributes = EXCLUDED.attributes,
                relations = EXCLUDED.relations,
                evidence_id = EXCLUDED.evidence_id,
                notes = EXCLUDED.notes,
                updated_at = EXCLUDED.updated_at
            """, (
                rec_id, self.tenant_id, company_id, dept, rtype,
                title, status, actor_type, actor_name, amount, currency,
                json.dumps(attrs), json.dumps(rels), evidence_id, notes, now, now
            ))
            conn.commit()

        return self.get_record(rec_id)

    def _seed_default_records_if_empty(self):
        with db.get_connection() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM enterprise_records WHERE tenant_id = ?", (self.tenant_id,)).fetchone()[0]
            if cnt > 0:
                return

        app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
        is_prod = (app_env in ("production", "prod", "staging")) or (os.environ.get("ZONATA_PRODUCTION", "0") == "1") or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")
        enable_demo = (os.environ.get("ZONATA_ENABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes")) and not is_prod
        clean_mode = is_prod or not enable_demo or (os.environ.get("ZONATA_DISABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes"))
        if clean_mode:
            return

        now = time.time()
        initial_records = [
            {
                "record_id": "rec_inv_1001",
                "department": "Finance",
                "record_type": "INVOICE",
                "title": "Corporate Folio Invoice #INV-2026-089 — Taj Hospitality & Events",
                "status": "APPROVED",
                "actor_type": "AI_AGENT",
                "actor_name": "Finance & Billing Agent",
                "amount": 145000.0,
                "attributes": {"invoice_no": "INV-2026-089", "tax_amount": 26100.0, "net_total": 171100.0, "payment_terms": "NET_30"},
                "relations": {"customer_id": "rec_cust_taj", "linked_files": ["doc_invoice_89.pdf"], "ledger_ref": "GL_4010_REV"},
                "evidence_id": "evi_sha256_inv_89",
                "notes": "Verified against PMS guest night audit log and signed purchase voucher.",
                "created_at": now - 3600
            },
            {
                "record_id": "rec_exp_2004",
                "department": "Procurement",
                "record_type": "EXPENSE",
                "title": "Industrial Raw Material Batch #RM-442 Procurement Order",
                "status": "COMPLETED",
                "actor_type": "AI_AGENT",
                "actor_name": "Procurement Agent",
                "amount": 78500.0,
                "attributes": {"po_number": "PO-9021", "vendor": "Apex Industrial Supplies Ltd", "category": "Raw Materials", "payment_mode": "BANK_NEFT"},
                "relations": {"vendor_id": "rec_vend_apex", "linked_files": ["po_9021_apex.pdf", "grn_receipt_442.pdf"]},
                "evidence_id": "evi_sha256_po_9021",
                "notes": "Three-way match confirmed: PO amount equals GRN items and verified tax invoice.",
                "created_at": now - 14400
            },
            {
                "record_id": "rec_cust_taj",
                "department": "Sales",
                "record_type": "CUSTOMER",
                "title": "Client Record: Taj Hospitality & Leisure Corporate Account",
                "status": "ACTIVE",
                "actor_type": "HUMAN_OWNER",
                "actor_name": "Sukhraj Singh",
                "amount": 540000.0,
                "attributes": {"industry": "Hospitality", "credit_limit": 1000000.0, "tier": "ENTERPRISE", "contacts": [{"name": "Aman Verma", "role": "VP Operations"}]},
                "relations": {"linked_invoices": ["rec_inv_1001"], "contracts": ["contract_taj_2026.pdf"]},
                "evidence_id": "evi_sha256_cust_taj",
                "notes": "SLA active with 99.8% customer satisfaction score.",
                "created_at": now - 86400
            },
            {
                "record_id": "rec_vend_apex",
                "department": "Procurement",
                "record_type": "VENDOR",
                "title": "Vendor Profile: Apex Industrial Supplies Ltd",
                "status": "ACTIVE",
                "actor_type": "AI_AGENT",
                "actor_name": "Supply Chain Agent",
                "amount": 320000.0,
                "attributes": {"category": "Industrial Spares & Raw Materials", "reliability_score": 98.4, "payment_terms": "NET_15"},
                "relations": {"linked_pos": ["rec_exp_2004"], "compliance_cert": ["iso_9001_apex.pdf"]},
                "evidence_id": "evi_sha256_vend_apex",
                "notes": "Vendor passed Q3 compliance verification with zero defect notices.",
                "created_at": now - 172800
            },
            {
                "record_id": "rec_emp_3001",
                "department": "HR",
                "record_type": "EMPLOYEE",
                "title": "Employee Dossier: Priya Sharma — Chief Financial Controller",
                "status": "ACTIVE",
                "actor_type": "HUMAN_OWNER",
                "actor_name": "Sukhraj Singh",
                "amount": 250000.0,
                "attributes": {"designation": "CFO", "grade": "EXECUTIVE_E1", "attendance_rate": 99.2, "leave_balance": 18},
                "relations": {"reports_to": "CEO", "payroll_reference": "PAY-2026-PRIYA"},
                "evidence_id": "evi_sha256_emp_priya",
                "notes": "Authorized signatory for financial disbursements up to ₹5,00,000.",
                "created_at": now - 259200
            },
            {
                "record_id": "rec_pay_4002",
                "department": "Finance",
                "record_type": "PAYMENT",
                "title": "Disbursement: Cloud Infrastructure & AI Compute Settlement",
                "status": "COMPLETED",
                "actor_type": "AI_AGENT",
                "actor_name": "Treasury & Finance Agent",
                "amount": 42000.0,
                "attributes": {"method": "STRIPE_CORPORATE_CARD", "reference": "ch_3M4K8912", "vendor": "GCP / Sovereign Compute Cluster"},
                "relations": {"budget_code": "BG_IT_INFRA", "evidence": "evi_sha256_stripe_42k"},
                "evidence_id": "evi_sha256_stripe_42k",
                "notes": "Automated reconciliation verified against infrastructure budget threshold.",
                "created_at": now - 345600
            },
            {
                "record_id": "rec_invt_5001",
                "department": "Operations",
                "record_type": "INVENTORY",
                "title": "Inventory Audit: Finished Goods Batch #FG-990 Quality Release",
                "status": "COMPLETED",
                "actor_type": "AI_AGENT",
                "actor_name": "Quality Assurance Agent",
                "amount": 89000.0,
                "attributes": {"sku": "SKU-HOSP-LUX-01", "units_cleared": 450, "inspection_pass_rate": 100.0},
                "relations": {"warehouse": "WH_PRIMARY_GOA", "batch_certificate": "batch_990_qc.pdf"},
                "evidence_id": "evi_sha256_invt_990",
                "notes": "Zero defect clearance signed by QA Automation Agent.",
                "created_at": now - 432000
            },
            {
                "record_id": "rec_dec_6001",
                "department": "Executive",
                "record_type": "DECISION",
                "title": "Executive AI CEO Decision: Capital Allocation for Q4 Expansion",
                "status": "APPROVED",
                "actor_type": "AI_AGENT",
                "actor_name": "AI CEO Executive Engine",
                "amount": 1250000.0,
                "attributes": {"allocation_target": "Operational Expansion & Autonomous Sales Workforce", "risk_index": "LOW", "projected_roi": "34.5%"},
                "relations": {"approval_id": "app_cap_alloc_q4", "council_debate_id": "deb_q4_cap"},
                "evidence_id": "evi_sha256_ceo_dec_q4",
                "notes": "Owner sovereign authorization verified via cryptographic token signature.",
                "created_at": now - 500000
            }
        ]

        with db.get_connection() as conn:
            for r in initial_records:
                conn.execute("""
                INSERT OR IGNORE INTO enterprise_records (
                    record_id, tenant_id, company_id, department, record_type,
                    title, status, actor_type, actor_name, amount, currency,
                    attributes, relations, evidence_id, notes, created_at, updated_at
                ) VALUES (?, ?, 'comp_primary', ?, ?, ?, ?, ?, ?, ?, '₹', ?, ?, ?, ?, ?, ?)
                """, (
                    r["record_id"], self.tenant_id, r["department"], r["record_type"],
                    r["title"], r["status"], r["actor_type"], r["actor_name"], r["amount"],
                    json.dumps(r["attributes"]), json.dumps(r["relations"]),
                    r["evidence_id"], r["notes"], r["created_at"], r["created_at"]
                ))
            conn.commit()

# Singleton instance
records_engine = EnterpriseRecordsEngine()
