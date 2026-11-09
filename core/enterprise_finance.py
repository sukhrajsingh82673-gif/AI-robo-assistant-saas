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
                status TEXT NOT NULL DEFAULT 'SUBMITTED', -- DRAFT, SUBMITTED, APPROVED, REJECTED, PAID, RECONCILED
                receipt_file TEXT,
                description TEXT NOT NULL,
                approval_id TEXT,
                claimant_user_id TEXT,
                approved_by TEXT,
                approved_at REAL,
                decision_reason TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            # Additive migrations for databases created by earlier versions.
            for stmt in (
                "ALTER TABLE finance_expenses ADD COLUMN claimant_user_id TEXT",
                "ALTER TABLE finance_expenses ADD COLUMN approved_by TEXT",
                "ALTER TABLE finance_expenses ADD COLUMN approved_at REAL",
                "ALTER TABLE finance_expenses ADD COLUMN decision_reason TEXT",
            ):
                try:
                    conn.execute(stmt)
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            conn.commit()

    def _ensure_company_coa(self, company_id: str, conn=None) -> None:
        """Provision the statutory chart of accounts for a specific company.

        Account ids are namespaced per company so multiple companies inside one
        tenant each get an independent, reconcilable ledger.
        """
        if not company_id:
            return
        now = time.time()
        coa = [
            ("1010", "Petty Cash & Cash on Hand", "ASSET", "CASH"),
            ("1020", "Operating Bank Account", "ASSET", "BANK"),
            ("1030", "Payment Gateway Escrow", "ASSET", "BANK"),
            ("1100", "Accounts Receivable (Trade Debtors)", "ASSET", "AR"),
            ("2010", "Accounts Payable (Trade Creditors)", "LIABILITY", "AP"),
            ("2020", "Statutory Tax Payable (GST / TDS)", "LIABILITY", "AP"),
            ("3010", "Owner Equity & Retained Earnings", "EQUITY", "EQUITY"),
            ("4010", "Enterprise Operations & SaaS Revenue", "REVENUE", "SALES"),
            ("5010", "Cost of Goods Sold & Direct Material", "EXPENSE", "COGS"),
            ("6010", "Workforce Salaries & Contractor Payroll", "EXPENSE", "OPEX"),
            ("6020", "Cloud Compute & AI Model Infrastructure", "EXPENSE", "OPEX"),
            ("6030", "General Admin & Facilities Operations", "EXPENSE", "OPEX"),
        ]
        if conn is not None:
            self._insert_coa_rows(conn, company_id, coa, now)
            return
        with db.get_connection() as own_conn:
            self._insert_coa_rows(own_conn, company_id, coa, now)
            own_conn.commit()

    def _insert_coa_rows(self, conn, company_id: str, coa, now: float) -> None:
        for code, name, acc_type, cat in coa:
            acc_id = f"acc_{code}" if company_id == "comp_primary" else f"{company_id}_acc_{code}"
            conn.execute(
                """
                INSERT OR IGNORE INTO finance_accounts (
                    account_id, tenant_id, company_id, code, name, account_type,
                    category, balance, currency, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, '₹', ?, ?)
                """,
                (acc_id, self.tenant_id, company_id, code, name, acc_type, cat, now, now),
            )

    def get_financial_summary(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        self._ensure_company_coa(company_id)
        with db.get_connection() as conn:
            accounts = conn.execute(
                "SELECT * FROM finance_accounts WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, company_id)
            ).fetchall()

            cash_total = sum(r["balance"] for r in accounts if r["category"] in ["CASH", "BANK"])
            ar_total = sum(r["balance"] for r in accounts if r["category"] == "AR")
            ap_total = sum(r["balance"] for r in accounts if r["category"] == "AP")
            revenue_total = sum(r["balance"] for r in accounts if r["account_type"] == "REVENUE")
            account_expense_total = sum(r["balance"] for r in accounts if r["account_type"] == "EXPENSE")

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

            # Statutory reconciliation: Posted GL accounts + approved reimbursement claims
            approved_claims = sum(r["amount"] for r in exp_rows if r["status"] in ("APPROVED", "PAID", "RECONCILED"))
            pending_claims = sum(r["amount"] for r in exp_rows if r["status"] in ("SUBMITTED", "PENDING", "DRAFT"))
            expense_total = max(account_expense_total, approved_claims)

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
                    "expenses_pending_approval": pending_claims,
                    "operating_profit": revenue_total - expense_total,
                    "operating_margin_pct": round(((revenue_total - expense_total) / revenue_total * 100), 1) if revenue_total > 0 else 0.0,
                    "currency": "₹"
                },
                "chart_of_accounts": coa,
                "recent_transactions": txs,
                "recent_expenses": expenses
            }

    # ------------------------------------------------------------------
    # Expense policy (P0-3 / P1-10)
    # ------------------------------------------------------------------
    # A client may never assert an approval. Only these intake states exist.
    INTAKE_STATUSES = ("DRAFT", "SUBMITTED")
    APPROVER_ROLES = ("OWNER", "EXECUTIVE", "GLOBAL_ADMIN")

    @staticmethod
    def _setting(tenant_id: str, company_id: str, key: str, default: Any) -> Any:
        try:
            from core.settings_service import settings_service
            return settings_service.get_effective_setting(tenant_id, company_id, key, default)
        except Exception:
            return default

    def _month_bounds(self, now: float):
        import datetime as _dt
        dt = _dt.datetime.utcfromtimestamp(now)
        start = _dt.datetime(dt.year, dt.month, 1, tzinfo=_dt.timezone.utc).timestamp()
        if dt.month == 12:
            end = _dt.datetime(dt.year + 1, 1, 1, tzinfo=_dt.timezone.utc).timestamp()
        else:
            end = _dt.datetime(dt.year, dt.month + 1, 1, tzinfo=_dt.timezone.utc).timestamp()
        return start, end

    def _monthly_committed(self, conn, company_id: str, now: float, department: Optional[str] = None) -> float:
        start, end = self._month_bounds(now)
        sql = (
            "SELECT COALESCE(SUM(amount), 0) FROM finance_expenses "
            "WHERE tenant_id = ? AND company_id = ? AND created_at >= ? AND created_at < ? "
            "AND status IN ('SUBMITTED','APPROVED','PAID','RECONCILED')"
        )
        params: List[Any] = [self.tenant_id, company_id, start, end]
        if department:
            sql += " AND department = ?"
            params.append(department)
        return float(conn.execute(sql, tuple(params)).fetchone()[0] or 0.0)

    def _department_budget(self, conn, company_id: str, department: str) -> float:
        row = conn.execute(
            "SELECT budget_limit FROM departments WHERE tenant_id = ? AND company_id = ? AND name = ?",
            (self.tenant_id, company_id, department),
        ).fetchone()
        return float(row["budget_limit"] or 0.0) if row else 0.0

    def create_expense(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Intake an expense claim. Approval state is never trusted from the caller."""
        eid = f"exp_{uuid.uuid4().hex[:8]}"
        now = time.time()
        company_id = data.get("company_id", "comp_primary")
        category = str(data.get("category", "OFFICE")).upper()
        department = data.get("department", "Operations")
        claimant_name = data.get("claimant_name", "Employee")
        claimant_user_id = data.get("claimant_user_id") or None
        description = data.get("description", "Operational expense")

        # 1. Status is server-controlled. Anything else collapses to SUBMITTED.
        requested_status = str(data.get("status", "SUBMITTED")).upper()
        status = requested_status if requested_status in self.INTAKE_STATUSES else "SUBMITTED"
        if requested_status not in self.INTAKE_STATUSES:
            policy_note = (
                f"Caller-asserted status '{requested_status}' ignored; claims enter as SUBMITTED "
                "and require an authorised approval decision."
            )
        else:
            policy_note = None

        # 2. Amount validation and hard cap.
        try:
            amount = float(data.get("amount", 0.0))
        except (TypeError, ValueError):
            return {"success": False, "error": "INVALID_AMOUNT", "detail": "amount must be numeric"}
        if not (amount > 0.0) or amount != amount or amount in (float("inf"), float("-inf")):
            return {"success": False, "error": "INVALID_AMOUNT", "detail": "amount must be a positive finite number"}

        hard_limit = float(self._setting(
            self.tenant_id, company_id, "fin_expense_hard_limit", 1000000.0
        ) or 0.0)
        if hard_limit > 0 and amount > hard_limit:
            return {
                "success": False,
                "error": "EXPENSE_EXCEEDS_HARD_LIMIT",
                "detail": f"Claim amount {amount} exceeds the hard per-claim limit {hard_limit}.",
                "hard_limit": hard_limit,
            }

        self._ensure_company_coa(company_id)

        with db.get_connection() as conn:
            # 3. Monthly budget enforcement (department budget, else company budget).
            dept_budget = self._department_budget(conn, company_id, department)
            company_budget = float(self._setting(
                self.tenant_id, company_id, "fin_company_monthly_expense_budget", 0.0
            ) or 0.0)
            budget = dept_budget if dept_budget > 0 else company_budget
            if budget > 0:
                committed = self._monthly_committed(
                    conn, company_id, now,
                    department=department if dept_budget > 0 else None,
                )
                if committed + amount > budget:
                    return {
                        "success": False,
                        "error": "BUDGET_EXCEEDED",
                        "detail": (
                            f"Claim would push monthly committed spend to {committed + amount:.2f}, "
                            f"above the budget of {budget:.2f}."
                        ),
                        "budget": budget,
                        "committed": committed,
                    }

            conn.execute("""
            INSERT INTO finance_expenses (
                expense_id, tenant_id, company_id, claimant_name, claimant_user_id, department,
                category, amount, currency, payment_mode, status, receipt_file,
                description, approval_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eid, self.tenant_id, company_id,
                claimant_name, claimant_user_id, department,
                category, amount,
                data.get("currency", "₹"),
                data.get("payment_mode", "CORPORATE_CARD"),
                status,
                data.get("receipt_file"),
                description,
                data.get("approval_id"),
                now, now
            ))
            conn.commit()

        res = {"expense_id": eid, "success": True, "status": status,
               "amount": amount, "company_id": company_id}
        if policy_note:
            res["policy_note"] = policy_note
        if amount >= float(self._setting(
                self.tenant_id, company_id, "fin_high_expense_approval", 15000.0) or 0.0):
            res["requires_executive_approval"] = True
        return res

    def approve_expense(
        self,
        expense_id: str,
        approver: str = "Executive Approver",
        approver_role: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a SUBMITTED expense, enforcing SoD/budget, then post to GL."""
        now = time.time()

        if approver_role is not None and str(approver_role).upper() not in self.APPROVER_ROLES:
            return {
                "success": False,
                "error": "INSUFFICIENT_PERMISSIONS",
                "detail": "Only Owner, Executive, or Global Admin roles may approve expenses.",
                "role": approver_role,
            }

        with db.get_connection() as conn:
            exp = conn.execute(
                "SELECT * FROM finance_expenses WHERE expense_id = ? AND tenant_id = ?",
                (expense_id, self.tenant_id)
            ).fetchone()
            if not exp:
                return {"success": False, "error": "EXPENSE_NOT_FOUND"}
            if company_id and exp["company_id"] != company_id:
                # Cross-company probing must look identical to a missing record.
                return {"success": False, "error": "EXPENSE_NOT_FOUND"}

            if exp["status"] == "APPROVED":
                return {"success": False, "error": "ALREADY_APPROVED", "expense_id": expense_id}
            if exp["status"] not in ("SUBMITTED",):
                return {"success": False, "error": f"INVALID_STATE: expense is {exp['status']}"}

            # Segregation of duties: claimant cannot approve their own claim.
            claimant_user_id = exp["claimant_user_id"] if "claimant_user_id" in exp.keys() else None
            if claimant_user_id and str(claimant_user_id) == str(approver):
                return {
                    "success": False,
                    "error": "SEGREGATION_OF_DUTIES",
                    "detail": "The claimant cannot approve their own expense claim.",
                }
            if exp["claimant_name"] and str(approver) == str(exp["claimant_name"]):
                return {
                    "success": False,
                    "error": "SEGREGATION_OF_DUTIES",
                    "detail": "The claimant cannot approve their own expense claim.",
                }

            # Budget gate at execution time (re-checked, not just at intake).
            dept_budget = self._department_budget(conn, exp["company_id"], exp["department"])
            company_budget = float(self._setting(
                self.tenant_id, exp["company_id"], "fin_company_monthly_expense_budget", 0.0
            ) or 0.0)
            budget = dept_budget if dept_budget > 0 else company_budget
            if budget > 0:
                committed = self._monthly_committed(
                    conn, exp["company_id"], now,
                    department=exp["department"] if dept_budget > 0 else None,
                )
                if committed > budget:
                    return {
                        "success": False,
                        "error": "BUDGET_EXCEEDED",
                        "detail": f"Approved spend {committed:.2f} already exceeds budget {budget:.2f}.",
                    }

            cur = conn.execute(
                "UPDATE finance_expenses SET status = 'APPROVED', approved_by = ?, approved_at = ?, "
                "updated_at = ? WHERE expense_id = ? AND tenant_id = ? AND company_id = ? AND status = 'SUBMITTED'",
                (approver, now, now, expense_id, self.tenant_id, exp["company_id"])
            )
            if getattr(cur, "rowcount", 1) == 0:
                return {"success": False, "error": "INVALID_STATE: expense changed concurrently"}
            self._post_expense_to_gl(conn, expense_id, exp["company_id"], exp["category"], exp["amount"], now)
            conn.commit()

        return {
            "success": True,
            "expense_id": expense_id,
            "status": "APPROVED",
            "approved_by": approver,
            "amount": float(exp["amount"]),
            "company_id": exp["company_id"],
        }

    def _post_expense_to_gl(self, conn, expense_id: str, company_id: str, category: str, amount: float, timestamp: float):
        """Map expense category to GL Account code and post ledger entry."""
        cat_map = {
            "SOFTWARE": "6020",
            "CLOUD": "6020",
            "PROCUREMENT": "5010",
            "SALARIES": "6010",
            "PAYROLL": "6010",
            "OFFICE": "6030",
            "TRAVEL": "6030",
            "MARKETING": "6030",
            "UTILITIES": "6030"
        }
        code = cat_map.get(category.upper(), "6030")
        self._ensure_company_coa(company_id, conn=conn)
        row = conn.execute(
            "SELECT account_id FROM finance_accounts WHERE tenant_id = ? AND company_id = ? AND code = ?",
            (self.tenant_id, company_id, code),
        ).fetchone()
        acc_id = row["account_id"] if row else f"acc_{code}"
        conn.execute(
            "UPDATE finance_accounts SET balance = balance + ?, updated_at = ? WHERE account_id = ? AND tenant_id = ? AND company_id = ?",
            (amount, timestamp, acc_id, self.tenant_id, company_id)
        )
        tx_id = f"tx_{uuid.uuid4().hex[:8]}"
        conn.execute("""
        INSERT INTO finance_transactions (
            transaction_id, tenant_id, company_id, account_id, tx_type,
            amount, currency, category, entity_name, reference_no, status,
            evidence_id, created_at
        ) VALUES (?, ?, ?, ?, 'DEBIT', ?, '₹', ?, ?, ?, 'RECONCILED', ?, ?)
        """, (
            tx_id, self.tenant_id, company_id, acc_id,
            amount, category, "Expense Claim Posting", expense_id,
            f"evi_gl_{expense_id}", timestamp
        ))

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
