"""
Accounts Payable (AP) 3-Way Matching Engine
===========================================
Matches Purchase Order (PO), Goods Receipt Note (GRN), and Vendor Invoice.
Adheres to:
- Rule 59: Systems of Record as Ports
- Rule 62: Reserved Human Financial Decisions (gateway approval on matched invoices)
"""

from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class DiscrepancyCode(str, Enum):
    VENDOR_MISMATCH = "VENDOR_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    LINE_COUNT_MISMATCH = "LINE_COUNT_MISMATCH"
    QUANTITY_OVER_RECEIPT = "QUANTITY_OVER_RECEIPT"
    PRICE_VARIANCE_EXCEEDS_TOLERANCE = "PRICE_VARIANCE_EXCEEDS_TOLERANCE"
    MISSING_GRN = "MISSING_GRN"


class POLineItem(BaseModel):
    item_id: str
    description: str
    quantity: float
    unit_price: float


class GRNLineItem(BaseModel):
    item_id: str
    quantity_received: float
    quantity_accepted: float


class InvoiceLineItem(BaseModel):
    item_id: str
    quantity_invoiced: float
    unit_price: float


class PurchaseOrder(BaseModel):
    po_id: str
    tenant_id: str
    company_id: str
    vendor_id: str
    currency: str
    lines: List[POLineItem]


class GoodsReceiptNote(BaseModel):
    grn_id: str
    tenant_id: str
    company_id: str
    po_id: str
    lines: List[GRNLineItem]


class VendorInvoice(BaseModel):
    invoice_id: str
    tenant_id: str
    company_id: str
    vendor_id: str
    po_id: str
    currency: str
    lines: List[InvoiceLineItem]


class APMatchDiscrepancy(BaseModel):
    code: DiscrepancyCode
    item_id: Optional[str] = None
    expected_value: Any
    actual_value: Any
    message: str


class APMatchResult(BaseModel):
    status: str  # 'MATCHED' or 'DISCREPANCY'
    invoice_id: str
    po_id: str
    grn_id: Optional[str] = None
    discrepancies: List[APMatchDiscrepancy] = Field(default_factory=list)
    total_invoiced_amount: float
    ready_for_payment_approval: bool = False


class AP3WayMatcher:
    """3-Way Matching Evaluator with configurable quantity and price tolerances."""

    def __init__(self, quantity_tolerance_pct: float = 0.0, price_tolerance_pct: float = 0.01, max_price_variance_abs: float = 50.0):
        self.quantity_tolerance_pct = quantity_tolerance_pct
        self.price_tolerance_pct = price_tolerance_pct
        self.max_price_variance_abs = max_price_variance_abs

    def match(self, po: PurchaseOrder, grn: Optional[GoodsReceiptNote], invoice: VendorInvoice) -> APMatchResult:
        discrepancies: List[APMatchDiscrepancy] = []

        # 1. Vendor & Currency Checks
        if po.vendor_id != invoice.vendor_id:
            discrepancies.append(APMatchDiscrepancy(
                code=DiscrepancyCode.VENDOR_MISMATCH,
                expected_value=po.vendor_id,
                actual_value=invoice.vendor_id,
                message=f"Vendor mismatch: PO vendor {po.vendor_id} != Invoice vendor {invoice.vendor_id}"
            ))

        if po.currency != invoice.currency:
            discrepancies.append(APMatchDiscrepancy(
                code=DiscrepancyCode.CURRENCY_MISMATCH,
                expected_value=po.currency,
                actual_value=invoice.currency,
                message=f"Currency mismatch: PO currency {po.currency} != Invoice currency {invoice.currency}"
            ))

        # 2. GRN Existence
        if not grn:
            discrepancies.append(APMatchDiscrepancy(
                code=DiscrepancyCode.MISSING_GRN,
                expected_value=po.po_id,
                actual_value=None,
                message="Goods Receipt Note (GRN) not found for Purchase Order"
            ))
            return APMatchResult(
                status="DISCREPANCY",
                invoice_id=invoice.invoice_id,
                po_id=po.po_id,
                discrepancies=discrepancies,
                total_invoiced_amount=sum(l.quantity_invoiced * l.unit_price for l in invoice.lines),
                ready_for_payment_approval=False
            )

        # 3. Line Matching
        po_lines = {l.item_id: l for l in po.lines}
        grn_lines = {l.item_id: l for l in grn.lines}

        total_amount = 0.0
        for inv_line in invoice.lines:
            line_total = inv_line.quantity_invoiced * inv_line.unit_price
            total_amount += line_total

            po_line = po_lines.get(inv_line.item_id)
            grn_line = grn_lines.get(inv_line.item_id)

            if not po_line or not grn_line:
                discrepancies.append(APMatchDiscrepancy(
                    code=DiscrepancyCode.LINE_COUNT_MISMATCH,
                    item_id=inv_line.item_id,
                    expected_value="Present in PO and GRN",
                    actual_value="Missing",
                    message=f"Item {inv_line.item_id} missing in PO or GRN"
                ))
                continue

            # Quantity Check: Invoiced quantity vs GRN accepted quantity (0% default tolerance)
            max_allowed_qty = grn_line.quantity_accepted * (1.0 + self.quantity_tolerance_pct)
            if inv_line.quantity_invoiced > max_allowed_qty:
                discrepancies.append(APMatchDiscrepancy(
                    code=DiscrepancyCode.QUANTITY_OVER_RECEIPT,
                    item_id=inv_line.item_id,
                    expected_value=grn_line.quantity_accepted,
                    actual_value=inv_line.quantity_invoiced,
                    message=f"Invoiced qty {inv_line.quantity_invoiced} exceeds GRN accepted qty {grn_line.quantity_accepted}"
                ))

            # Price Check: Invoiced unit price vs PO unit price
            price_variance = inv_line.unit_price - po_line.unit_price
            if price_variance > 0:
                pct_variance = price_variance / po_line.unit_price
                abs_variance = price_variance * inv_line.quantity_invoiced
                if pct_variance > self.price_tolerance_pct and abs_variance > self.max_price_variance_abs:
                    discrepancies.append(APMatchDiscrepancy(
                        code=DiscrepancyCode.PRICE_VARIANCE_EXCEEDS_TOLERANCE,
                        item_id=inv_line.item_id,
                        expected_value=po_line.unit_price,
                        actual_value=inv_line.unit_price,
                        message=f"Unit price {inv_line.unit_price} exceeds PO price {po_line.unit_price} beyond tolerance"
                    ))

        is_matched = len(discrepancies) == 0
        return APMatchResult(
            status="MATCHED" if is_matched else "DISCREPANCY",
            invoice_id=invoice.invoice_id,
            po_id=po.po_id,
            grn_id=grn.grn_id,
            discrepancies=discrepancies,
            total_invoiced_amount=total_amount,
            ready_for_payment_approval=is_matched
        )
