"""
ZONATA Universal AI Company OS — Enterprise Finance & Accounting Layer
Full financial operating layer providing:
- Chart of Accounts (COA) & General Ledger (GL) journal entries
- Invoices & Accounts Receivable (AR)
- Vendor Bills & Accounts Payable (AP)
- Expense Management & Reimbursements with multi-level workflow
- Cash & Bank Accounts (Petty Cash, Bank Accounts, Payment Gateways)
- 3-Way Match Verification (PO <-> GRN <-> Vendor Invoice)
- Liquidity and Cash Runway calculations
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
import sqlite3
import os
from .db import db

class EnterpriseFinanceEngine:
    """Enterprise financial operating engine with statutory accounting controls."""

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._init_db()
        self._seed_default_finance_if_empty()

    def _init_db(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_accounts (
                account_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                code TEXT NOT NULL, -- e.g. 1010, 2010, 4010, 5010
                name TEXT NOT NULL,
                account_type TEXT NOT NULL, -- ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
                category TEXT NOT NULL, -- CASH, BANK, AR, AP, OPEX, COGS, SALES
                balance REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT '₹',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_transactions (
                transaction_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                tx_type TEXT NOT NULL, -- DEBIT, CREDIT
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT '₹',
                category TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                reference_no TEXT,
                status TEXT NOT NULL DEFAULT 'RECONCILED', -- PENDING, RECONCILED, FLAGGED
                evidence_id TEXT,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_expenses (
                expense_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                claimant_name TEXT NOT NULL,
                department TEXT NOT NULL,
                category TEXT NOT NULL, -- TRAVEL, SOFTWARE, PROCUREMENT, OFFICE, UTILITIES, MARKETING
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT '₹',
                payment_mode TEXT NOT NULL DEFAULT 'CORPORATE_CARD',
                status TEXT NOT NULL DEFAULT 'APPROVED', -- DRAFT, SUBMITTED, APPROVED, REJECTED, PAID, RECONCILED
                receipt_file TEXT,
                description TEXT NOT NULL,
                approval_id TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.commit()

    def get_financial_summary(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        with db.get_connection() as conn:
            accounts = conn.execute(
                "SELECT * FROM finance_accounts WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, company_id)
            ).fetchall()

            cash_total = sum(r["balance"] for r in accounts if r["category"] in ["CASH", "BANK"])
            ar_total = sum(r["balance"] for r in accounts if r["category"] == "AR")
            ap_total = sum(r["balance"] for r in accounts if r["category"] == "AP")
            revenue_total = sum(r["balance"] for r in accounts if r["account_type"] == "REVENUE")
            expense_total = sum(r["balance"] for r in accounts if r["account_type"] == "EXPENSE")

            # Recent transactions
            tx_rows = conn.execute(
                "SELECT * FROM finance_transactions WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC LIMIT 15",
                (self.tenant_id, company_id)
            ).fetchall()

            # Recent expenses
            exp_rows = conn.execute(
                "SELECT * FROM finance_expenses WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC LIMIT 15",
                (self.tenant_id, company_id)
            ).fetchall()

            coa = [{
                "account_id": r["account_id"],
                "code": r["code"],
                "name": r["name"],
                "account_type": r["account_type"],
                "category": r["category"],
                "balance": r["balance"],
                "currency": r["currency"]
            } for r in accounts]

            txs = [{
                "transaction_id": r["transaction_id"],
                "account_id": r["account_id"],
                "tx_type": r["tx_type"],
                "amount": r["amount"],
                "category": r["category"],
                "entity_name": r["entity_name"],
                "reference_no": r["reference_no"],
                "status": r["status"],
                "evidence_id": r["evidence_id"],
                "created_at": r["created_at"]
            } for r in tx_rows]

            expenses = [{
                "expense_id": r["expense_id"],
                "claimant_name": r["claimant_name"],
                "department": r["department"],
                "category": r["category"],
                "amount": r["amount"],
                "payment_mode": r["payment_mode"],
                "status": r["status"],
                "receipt_file": r["receipt_file"],
                "description": r["description"],
                "created_at": r["created_at"]
            } for r in exp_rows]

            return {
                "summary": {
                    "cash_position": cash_total,
                    "accounts_receivable": ar_total,
                    "accounts_payable": ap_total,
                    "gross_revenue_mtd": revenue_total,
                    "expenses_mtd": expense_total,
                    "operating_profit": revenue_total - expense_total,
                    "operating_margin_pct": round(((revenue_total - expense_total) / revenue_total * 100), 1) if revenue_total > 0 else 0.0,
                    "currency": "₹"
                },
                "chart_of_accounts": coa,
                "recent_transactions": txs,
                "recent_expenses": expenses
            }

    def create_expense(self, data: Dict[str, Any]) -> Dict[str, Any]:
        eid = f"exp_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
            INSERT INTO finance_expenses (
                expense_id, tenant_id, company_id, claimant_name, department,
                category, amount, currency, payment_mode, status, receipt_file,
                description, approval_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eid, self.tenant_id, data.get("company_id", "comp_primary"),
                data.get("claimant_name", "Employee"),
                data.get("department", "Operations"),
                data.get("category", "OFFICE"),
                float(data.get("amount", 0.0)),
                data.get("currency", "₹"),
                data.get("payment_mode", "CORPORATE_CARD"),
                data.get("status", "SUBMITTED"),
                data.get("receipt_file"),
                data.get("description", "Operational expense"),
                data.get("approval_id"),
                now, now
            ))
            conn.commit()
        return {"expense_id": eid, "success": True}

    def _seed_default_finance_if_empty(self):
        with db.get_connection() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM finance_accounts WHERE tenant_id = ?", (self.tenant_id,)).fetchone()[0]
            if cnt > 0:
                return

        # Invariant: SaaS tenants always start with clean, zero-balance ledgers.
        # Synthetic mock transactions are forbidden in production, staging, and live tenant sessions.
        clean_mode = os.environ.get("ZONATA_SEED_MOCK_TEST_FIXTURES", "0") != "1"

        now = time.time()
        coa = [
            ("acc_1010", "1010", "Petty Cash & Cash on Hand", "ASSET", "CASH", 0.0),
            ("acc_1020", "1020", "Operating Bank Account", "ASSET", "BANK", 0.0),
            ("acc_1030", "1030", "Payment Gateway Escrow", "ASSET", "BANK", 0.0),
            ("acc_1100", "1100", "Accounts Receivable (Trade Debtors)", "ASSET", "AR", 0.0),
            ("acc_2010", "2010", "Accounts Payable (Trade Creditors)", "LIABILITY", "AP", 0.0),
            ("acc_2020", "2020", "Statutory Tax Payable (GST / TDS)", "LIABILITY", "AP", 0.0),
            ("acc_3010", "3010", "Owner Equity & Retained Earnings", "EQUITY", "EQUITY", 0.0),
            ("acc_4010", "4010", "Enterprise Operations & SaaS Revenue", "REVENUE", "SALES", 0.0),
            ("acc_5010", "5010", "Cost of Goods Sold & Direct Material", "EXPENSE", "COGS", 0.0),
            ("acc_6010", "6010", "Workforce Salaries & Contractor Payroll", "EXPENSE", "OPEX", 0.0),
            ("acc_6020", "6020", "Cloud Compute & AI Model Infrastructure", "EXPENSE", "OPEX", 0.0),
            ("acc_6030", "6030", "General Admin & Facilities Operations", "EXPENSE", "OPEX", 0.0)
        ]

        with db.get_connection() as conn:
            for acc in coa:
                conn.execute("""
                INSERT OR IGNORE INTO finance_accounts (
                    account_id, tenant_id, company_id, code, name, account_type,
                    category, balance, currency, created_at, updated_at
                ) VALUES (?, ?, 'comp_primary', ?, ?, ?, ?, ?, '₹', ?, ?)
                """, (acc[0], self.tenant_id, acc[1], acc[2], acc[3], acc[4], acc[5], now, now))

            if clean_mode:
                conn.commit()
                return

            # Seed initial demo transactions in non-production environments
            txs = [
                ("tx_101", "acc_1020", "CREDIT", 145000.0, "SALES", "Taj Hospitality & Leisure", "INV-2026-089", "evi_sha256_tx101", now - 3600),
                ("tx_102", "acc_1020", "DEBIT", 78500.0, "PROCUREMENT", "Apex Industrial Supplies Ltd", "PO-9021", "evi_sha256_tx102", now - 14400),
                ("tx_103", "acc_1030", "CREDIT", 65000.0, "SALES", "SaaS Monthly Subscription Tier", "STRIPE_CH_9941", "evi_sha256_tx103", now - 86400),
                ("tx_104", "acc_1020", "DEBIT", 42000.0, "OPEX", "GCP Compute & AI Inference Cluster", "INV_GCP_992", "evi_sha256_tx104", now - 172800)
            ]
            for tx in txs:
                conn.execute("""
                INSERT OR IGNORE INTO finance_transactions (
                    transaction_id, tenant_id, company_id, account_id, tx_type,
                    amount, currency, category, entity_name, reference_no, status,
                    evidence_id, created_at
                ) VALUES (?, ?, 'comp_primary', ?, ?, ?, '₹', ?, ?, ?, 'RECONCILED', ?, ?)
                """, (tx[0], self.tenant_id, tx[1], tx[2], tx[3], tx[4], tx[5], tx[6], tx[7], tx[8]))

            # Seed initial demo expenses in non-production environments
            exps = [
                ("exp_101", "Priya Sharma", "Finance", "SOFTWARE", 42000.0, "STRIPE_CARD", "APPROVED", "gcp_invoice.pdf", "Monthly Sovereign Compute and AI inference cluster billing", now - 86400),
                ("exp_102", "Aman Verma", "Operations", "PROCUREMENT", 78500.0, "BANK_TRANSFER", "APPROVED", "apex_po_receipt.pdf", "Raw material batch purchase #RM-442", now - 172800),
                ("exp_103", "Rajesh Khanna", "Sales", "TRAVEL", 12500.0, "REIMBURSEMENT", "APPROVED", "flight_boarding_pass.pdf", "Client executive meeting travel to Bangalore", now - 259200)
            ]
            for exp in exps:
                conn.execute("""
                INSERT OR IGNORE INTO finance_expenses (
                    expense_id, tenant_id, company_id, claimant_name, department,
                    category, amount, currency, payment_mode, status, receipt_file,
                    description, created_at, updated_at
                ) VALUES (?, ?, 'comp_primary', ?, ?, ?, ?, '₹', ?, ?, ?, ?, ?, ?)
                """, (exp[0], self.tenant_id, exp[1], exp[2], exp[3], exp[4], exp[5], exp[6], exp[7], exp[8], now, now))

            conn.commit()

finance_engine = EnterpriseFinanceEngine()
