"""
Unit & Contract Tests for Step 7C: Finance & Accounting Depth.
==============================================================
Validates:
- AP 3-Way Matching with tolerances and discrepancy holds.
- Multi-format Bank Statement Parsing (CSV, MT940, CAMT.053).
- Exact & Fuzzy Bank Reconciliation.
- Vendor Fraud 72-Hour Hold on Bank Detail Updates (Rule 62).
- Deterministic Month-End Close Workflow with Trial Balance Check.
- India GST E-Invoicing Schema v1.03, IRN Hashing & GSTR-2B Recon (Rule 61).
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.finance.ap_matching import (
    AP3WayMatcher, PurchaseOrder, GoodsReceiptNote, VendorInvoice,
    POLineItem, GRNLineItem, InvoiceLineItem, DiscrepancyCode
)
from core.finance.bank_rec import (
    BankStatementParser, BankReconciliationMatcher, LedgerTransaction
)
from core.finance.vendor_fraud import (
    VendorFraudDefenseManager, VendorBankAccount
)
from core.finance.month_end_close import (
    MonthEndCloseEngine, TrialBalanceAccount
)
from core.finance.gst_einvoicing import (
    IndiaGSTEngine, EInvoicePayload, EInvoiceParty, GSTItem, GSTR2BEntry
)


# --- 1. AP 3-WAY MATCHING TESTS ---

def test_01_ap_matching_success():
    matcher = AP3WayMatcher()
    po = PurchaseOrder(
        po_id="PO-1001",
        tenant_id="t1",
        company_id="c1",
        vendor_id="VEND-01",
        currency="INR",
        lines=[POLineItem(item_id="ITEM-A", description="Server Rack", quantity=2.0, unit_price=50000.0)]
    )
    grn = GoodsReceiptNote(
        grn_id="GRN-1001",
        tenant_id="t1",
        company_id="c1",
        po_id="PO-1001",
        lines=[GRNLineItem(item_id="ITEM-A", quantity_received=2.0, quantity_accepted=2.0)]
    )
    inv = VendorInvoice(
        invoice_id="INV-9901",
        tenant_id="t1",
        company_id="c1",
        vendor_id="VEND-01",
        po_id="PO-1001",
        currency="INR",
        lines=[InvoiceLineItem(item_id="ITEM-A", quantity_invoiced=2.0, unit_price=50000.0)]
    )

    res = matcher.match(po, grn, inv)
    assert res.status == "MATCHED"
    assert res.ready_for_payment_approval is True
    assert len(res.discrepancies) == 0


def test_02_ap_matching_discrepancy_holds():
    matcher = AP3WayMatcher(quantity_tolerance_pct=0.0, price_tolerance_pct=0.01, max_price_variance_abs=50.0)
    po = PurchaseOrder(
        po_id="PO-1002",
        tenant_id="t1",
        company_id="c1",
        vendor_id="VEND-01",
        currency="INR",
        lines=[POLineItem(item_id="ITEM-B", description="Memory Module", quantity=10.0, unit_price=2000.0)]
    )
    grn = GoodsReceiptNote(
        grn_id="GRN-1002",
        tenant_id="t1",
        company_id="c1",
        po_id="PO-1002",
        lines=[GRNLineItem(item_id="ITEM-B", quantity_received=10.0, quantity_accepted=8.0)]  # 2 rejected
    )
    # Invoicing for 10 units @ 2500 INR (over quantity and over unit price)
    inv = VendorInvoice(
        invoice_id="INV-9902",
        tenant_id="t1",
        company_id="c1",
        vendor_id="VEND-01",
        po_id="PO-1002",
        currency="INR",
        lines=[InvoiceLineItem(item_id="ITEM-B", quantity_invoiced=10.0, unit_price=2500.0)]
    )

    res = matcher.match(po, grn, inv)
    assert res.status == "DISCREPANCY"
    assert res.ready_for_payment_approval is False
    codes = {d.code for d in res.discrepancies}
    assert DiscrepancyCode.QUANTITY_OVER_RECEIPT in codes
    assert DiscrepancyCode.PRICE_VARIANCE_EXCEEDS_TOLERANCE in codes


# --- 2. BANK STATEMENT PARSING & RECONCILIATION TESTS ---

def test_03_bank_statement_parsers():
    # CSV Parse
    csv_data = "Date,Amount,Narrative,Reference\n2026-10-15,15000.00,Client Payment Alpha,REF-001\n2026-10-16,-4500.00,AWS Cloud Hosting,REF-002"
    csv_txs = BankStatementParser.parse_csv(csv_data)
    assert len(csv_txs) == 2
    assert csv_txs[0].amount == 15000.00
    assert csv_txs[1].amount == -4500.00

    # MT940 Parse
    mt940_data = ":61:261015C15000,00NTRF\n:86:Client Payment Alpha\n:61:261016D4500,00NTRF\n:86:AWS Cloud Hosting"
    mt_txs = BankStatementParser.parse_mt940(mt940_data)
    assert len(mt_txs) == 2
    assert mt_txs[0].date == "2026-10-15"
    assert mt_txs[0].amount == 15000.00
    assert mt_txs[1].amount == -4500.00

    # CAMT.053 Parse
    camt_data = """<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
        <BkToCstmrStmt>
            <Stmt>
                <Ntry>
                    <Amt Ccy="INR">15000.00</Amt>
                    <CdtDbtInd>CRDT</CdtDbtInd>
                    <BookgDt><Dt>2026-10-15</Dt></BookgDt>
                    <AddtlNtryInf>Client Payment Alpha</AddtlNtryInf>
                </Ntry>
            </Stmt>
        </BkToCstmrStmt>
    </Document>"""
    camt_txs = BankStatementParser.parse_camt053(camt_data)
    assert len(camt_txs) == 1
    assert camt_txs[0].amount == 15000.00
    assert camt_txs[0].date == "2026-10-15"


def test_04_exact_and_fuzzy_bank_reconciliation():
    csv_data = (
        "Date,Amount,Narrative,Reference\n"
        "2026-10-15,15000.00,Client Alpha Pvt Ltd,INV-101\n"
        "2026-10-17,-3500.00,Zonata Tech Office Rent,None\n"
        "2026-10-20,999.00,Unidentified Inflow,None"
    )
    bank_txs = BankStatementParser.parse_csv(csv_data)

    ledger_entries = [
        # Exact match
        LedgerTransaction(entry_id="LED-1", date="2026-10-15", amount=15000.00, currency="INR", payee="Client Alpha Pvt Ltd", reference="INV-101"),
        # Fuzzy match: date is 2026-10-18 (within 3 days) and payee similarity is high
        LedgerTransaction(entry_id="LED-2", date="2026-10-18", amount=-3500.00, currency="INR", payee="Zonata Tech Office Rent", reference=None)
    ]

    matcher = BankReconciliationMatcher(date_window_days=3, min_similarity=0.85)
    res = matcher.reconcile(bank_txs, ledger_entries)

    assert res.matched_count == 2
    assert len(res.unmatched_bank_txs) == 1
    assert res.unmatched_bank_txs[0].amount == 999.00
    match_types = {m.match_type for m in res.matches}
    assert "EXACT" in match_types
    assert "FUZZY" in match_types


# --- 3. VENDOR FRAUD DEFENSE TESTS ---

def test_05_vendor_fraud_hold_and_release():
    mgr = VendorFraudDefenseManager(hold_duration_hours=72)
    acc1 = VendorBankAccount(
        vendor_id="VEND-09",
        tenant_id="t1",
        company_id="c1",
        bank_name="HDFC Bank",
        account_number="111122223333",
        routing_or_ifsc="HDFC0001234",
        beneficiary_name="Acme Solutions"
    )
    # Initial registration: no hold
    hold = mgr.register_or_update_bank_account(acc1)
    assert hold is None

    # Modified bank details: triggers 72h hold
    acc2 = VendorBankAccount(
        vendor_id="VEND-09",
        tenant_id="t1",
        company_id="c1",
        bank_name="ICICI Bank",
        account_number="999988887777",
        routing_or_ifsc="ICIC0005678",
        beneficiary_name="Acme Offshore LLC"
    )
    hold = mgr.register_or_update_bank_account(acc2, previous_account=acc1)
    assert hold is not None
    assert hold.is_active is True

    # Payout is blocked
    can_disburse, reason = mgr.can_disburse_payout("t1", "c1", "VEND-09")
    assert can_disburse is False
    assert "Payout blocked" in reason

    # Out-of-band human verification release (Rule 62)
    assert mgr.release_hold_with_human_verification("t1", "c1", "VEND-09", "SEC-TOKEN-7788", "cfo_principal") is True

    # Now payout is allowed
    future_time = datetime.now(timezone.utc) + timedelta(hours=73)
    can_disburse_now, _ = mgr.can_disburse_payout("t1", "c1", "VEND-09", current_time=future_time)
    assert can_disburse_now is True


# --- 4. MONTH-END CLOSE WORKFLOW TESTS ---

def test_06_month_end_close_workflow_and_balancing():
    engine = MonthEndCloseEngine(tenant_id="t1", company_id="c1", period="2026-10")

    # Sequential steps
    assert engine.execute_ap_cutoff(unposted_invoices_count=0) is True
    assert engine.execute_ar_cutoff(pending_billing_runs=0) is True
    assert engine.execute_depreciation(assets_count=12, total_depreciation=45000.0) == 45000.0
    assert engine.signoff_bank_rec(unreviewed_exceptions=0) is True
    assert engine.execute_intercompany_eliminations({"co_us": 12000.0}) == 12000.0

    # Trial Balance Check: debits must equal credits
    accounts = [
        TrialBalanceAccount(account_code="1000", account_name="Cash", debit_total=100000.0, credit_total=0.0),
        TrialBalanceAccount(account_code="2000", account_name="Accounts Payable", debit_total=0.0, credit_total=40000.0),
        TrialBalanceAccount(account_code="3000", account_name="Retained Earnings", debit_total=0.0, credit_total=60000.0),
    ]
    tb_res = engine.verify_trial_balance(accounts)
    assert tb_res.is_balanced is True
    assert tb_res.imbalance_amount == 0.0

    # Imbalanced accounts raise ValueError
    bad_accounts = [
        TrialBalanceAccount(account_code="1000", account_name="Cash", debit_total=100000.0, credit_total=0.0),
        TrialBalanceAccount(account_code="2000", account_name="AP", debit_total=0.0, credit_total=90000.0),
    ]
    with pytest.raises(ValueError):
        engine.verify_trial_balance(bad_accounts)

    # Lock period
    state = engine.lock_period(principal_id="cfo_user")
    assert state.period_locked is True
    assert state.locked_by_principal == "cfo_user"


# --- 5. INDIA GST E-INVOICING & GSTR-2B RECON TESTS ---

def test_07_india_gst_einvoice_and_recon():
    gst_engine = IndiaGSTEngine()
    seller = EInvoiceParty(
        gstin="27AABCU9603R1ZM",
        legal_name="Zonata Tech India Pvt Ltd",
        address="100 Tech Park",
        location="Mumbai",
        pincode=400001,
        state_code="27"
    )
    # Interstate buyer (Delhi: Stcd 07)
    buyer = EInvoiceParty(
        gstin="07BBBCU9603R1ZN",
        legal_name="Delhi Enterprises",
        address="200 Ring Road",
        location="New Delhi",
        pincode=110001,
        state_code="07"
    )
    items = [
        GSTItem(item_id="SRV-01", description="SaaS Subscription", hsn_code="998313", quantity=1.0, unit_price=100000.0, gst_rate=0.18)
    ]

    payload = EInvoicePayload(
        doc_number="INV/2026/001",
        doc_date="15/10/2026",
        seller=seller,
        buyer=buyer,
        items=items
    )

    einvoice = gst_engine.generate_einvoice_json(payload)
    assert einvoice["Version"] == "1.03"
    assert einvoice["ValDtls"]["AssVal"] == 100000.0
    assert einvoice["ValDtls"]["IgstVal"] == 18000.0
    assert einvoice["ValDtls"]["CgstVal"] == 0.0
    assert einvoice["ValDtls"]["TotInvVal"] == 118000.0

    # Compute official IRN hash (64 hex characters)
    irn = gst_engine.compute_irn_hash(seller.gstin, "INV", "INV/2026/001", "2026-27")
    assert len(irn) == 64

    # E-Way bill generation (Total value 118,000 INR >= statutory threshold 50,000 INR)
    eway = gst_engine.generate_eway_bill_if_applicable(einvoice, distance_km=1200)
    assert eway is not None
    assert eway["totalValue"] == 118000.0

    # GSTR-2B Reconciliation
    purchase_register = [
        {"supplier_gstin": "27SUPPLIER1", "invoice_number": "IN-01", "taxable_value": 50000.0},
        {"supplier_gstin": "27SUPPLIER2", "invoice_number": "IN-02", "taxable_value": 20000.0},
    ]
    gstr2b_feed = [
        GSTR2BEntry(supplier_gstin="27SUPPLIER1", invoice_number="IN-01", invoice_date="2026-10-10", invoice_value=59000.0, taxable_value=50000.0, igst=9000.0),
        # Supplier 2 didn't file, but Supplier 3 filed unexpected invoice
        GSTR2BEntry(supplier_gstin="27SUPPLIER3", invoice_number="IN-03", invoice_date="2026-10-12", invoice_value=11800.0, taxable_value=10000.0, igst=1800.0),
    ]

    recon_res = gst_engine.reconcile_gstr2b(purchase_register, gstr2b_feed)
    assert len(recon_res.matched) == 1
    assert "27SUPPLIER1:IN-01" in recon_res.matched
    assert "27SUPPLIER2:IN-02" in recon_res.missing_in_gstr2b
    assert "27SUPPLIER3:IN-03" in recon_res.missing_in_books
    assert recon_res.total_itc_eligible == 9000.0
