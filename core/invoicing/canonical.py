"""
Canonical E-Invoice Model Aligned to European Standard EN 16931-1:2017 (Rule 70 & Rule 73)
==========================================================================================
All monetary amounts are integer minor units in ISO 4217 currencies.
Tax categories map to UN/CEFACT EDIFACT 5305 duty/tax/fee codes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import datetime
import hashlib
import json


@dataclass
class InvoiceParty:
    party_id: str
    legal_name: str
    tax_identifier: str  # e.g., VAT ID, GSTIN, EIN
    country_code: str    # ISO 3166-1 alpha-2
    street_address: str
    city: str
    postal_code: str


@dataclass
class InvoiceLineItem:
    line_id: str
    item_name: str
    quantity: float
    unit_price_minor: int           # integer minor units (e.g. cents/paise)
    tax_category: str = "S"         # UN/CEFACT 5305: 'S' (Standard), 'Z' (Zero), 'E' (Exempt), 'AE' (Reverse Charge)
    tax_rate_percent: float = 19.0
    line_total_minor: int = 0       # quantity * unit_price_minor

    def __post_init__(self):
        if self.line_total_minor == 0:
            self.line_total_minor = int(round(self.quantity * self.unit_price_minor))


@dataclass
class CanonicalInvoice:
    invoice_number: str
    issue_date: str                 # YYYY-MM-DD
    due_date: str                   # YYYY-MM-DD
    currency: str                   # ISO 4217 (e.g., 'EUR', 'USD', 'INR')
    supplier: InvoiceParty
    customer: InvoiceParty
    lines: List[InvoiceLineItem]
    payment_terms: str = "Net 30 Days"
    notes: Optional[str] = None

    def calculate_totals(self) -> Dict[str, int]:
        """Calculates total net amount, total tax amount, and grand total in minor units."""
        total_net_minor = sum(line.line_total_minor for line in self.lines)
        total_tax_minor = sum(
            int(round(line.line_total_minor * (line.tax_rate_percent / 100.0)))
            for line in self.lines
        )
        grand_total_minor = total_net_minor + total_tax_minor
        return {
            "total_net_minor": total_net_minor,
            "total_tax_minor": total_tax_minor,
            "grand_total_minor": grand_total_minor,
        }

    def compute_canonical_hash(self) -> str:
        """Computes deterministic SHA-256 hash over canonical invoice contents."""
        totals = self.calculate_totals()
        payload = {
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date,
            "currency": self.currency,
            "supplier": self.supplier.tax_identifier,
            "customer": self.customer.tax_identifier,
            "grand_total_minor": totals["grand_total_minor"],
            "line_count": len(self.lines),
        }
        canonical_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
