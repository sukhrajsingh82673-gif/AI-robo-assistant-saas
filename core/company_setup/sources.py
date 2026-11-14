"""The eight sources an existing company can connect.

Each entry explains, in plain words:

* what ZONATA would read (``reads``),
* why it helps (``why``),
* what is never copied or stored (``never``).

The catalogue is deliberately static and small. It is the contract the UI and
the onboarding workflow share, so the promise shown to the user and the scope
requested by the server can never drift apart.

All sources are optional. A user may skip one, but the skip reason is recorded
and shown again in the readiness score and the onboarding progress.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

#: Data classification used by readiness, audit and the UI badge.
CLASSIFICATIONS = {"FINANCIAL", "CUSTOMER", "OPERATIONAL", "DOCUMENT"}

SOURCE_CATALOGUE: List[Dict[str, Any]] = [
    {
        "id": "accounting",
        "name": "Accounting and books",
        "category": "FINANCIAL",
        "examples": ["Tally", "Zoho Books", "QuickBooks", "Xero"],
        "methods": ["OAUTH", "READ_ONLY_API", "CSV_UPLOAD"],
        "reads": "Ledger summary, invoices, expense categories, receivables and payables.",
        "why": "Shows margin, burn and cash risk from books you already keep.",
        "never": "Full journal exports, employee salaries or personal bank details.",
        "scope": ["read:ledger", "read:invoices", "read:expenses"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "banking",
        "name": "Bank accounts",
        "category": "FINANCIAL",
        "examples": ["Read-only bank statement feed", "Account Aggregator"],
        "methods": ["OAUTH", "READ_ONLY_API"],
        "reads": "Balances, incoming and outgoing transactions, bank fees.",
        "why": "Shows the real cash position and recurring leaks.",
        "never": "Card numbers, net-banking credentials or personal spending unrelated to the business.",
        "scope": ["read:balance", "read:transactions"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "payments",
        "name": "Payments and settlements",
        "category": "FINANCIAL",
        "examples": ["Razorpay", "Stripe", "PayU", "Cashfree"],
        "methods": ["OAUTH", "READ_ONLY_API"],
        "reads": "Settlements, refunds, chargebacks and platform fees.",
        "why": "Shows revenue quality and hidden payment costs.",
        "never": "Full card numbers, CVV values or customer payment credentials.",
        "scope": ["read:settlements", "read:refunds", "read:fees"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "commerce",
        "name": "Store, POS and orders",
        "category": "OPERATIONAL",
        "examples": ["Shopify", "WooCommerce", "Petpooja", "Loyverse"],
        "methods": ["OAUTH", "READ_ONLY_API", "CSV_UPLOAD"],
        "reads": "Orders, products, stock levels and returns.",
        "why": "Shows what sells, what sits and where stock leaks.",
        "never": "Customer addresses, phone numbers or order histories beyond aggregates.",
        "scope": ["read:orders", "read:products", "read:stock"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "crm",
        "name": "CRM and pipeline",
        "category": "CUSTOMER",
        "examples": ["HubSpot", "Salesforce", "Zoho CRM"],
        "methods": ["OAUTH", "READ_ONLY_API"],
        "reads": "Pipeline stages, win and loss counts, deal ages.",
        "why": "Shows where revenue stalls before it is lost.",
        "never": "Contact notes, personal data or email bodies.",
        "scope": ["read:pipeline", "read:deals"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "workspace",
        "name": "Files and spreadsheets",
        "category": "DOCUMENT",
        "examples": ["Google Workspace", "Microsoft 365"],
        "methods": ["OAUTH", "FILE_PICKER"],
        "reads": "Only the files you select: sheets, docs and reports.",
        "why": "Reuses the reports you already trust.",
        "never": "The rest of the drive, shared personal folders or deleted files.",
        "scope": ["read:selected_files"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "communications",
        "name": "Email and business messaging",
        "category": "CUSTOMER",
        "examples": ["Gmail read-only label", "Outlook", "WhatsApp Business"],
        "methods": ["OAUTH", "READ_ONLY_API"],
        "reads": "Volume, response times and unresolved threads, as counts only.",
        "why": "Shows customer service load and missed follow-ups.",
        "never": "Message bodies, attachments or personal conversations.",
        "scope": ["read:thread_metadata"],
        "requires_secret": True,
        "requires_verification": True,
    },
    {
        "id": "uploads",
        "name": "Upload files directly",
        "category": "DOCUMENT",
        "examples": ["CSV", "XLSX", "PDF"],
        "methods": ["FILE_UPLOAD"],
        "reads": "Only the files you upload, checked before use.",
        "why": "The fastest way to start with no integration.",
        "never": "Anything outside the uploaded file. Files are never shared with another company.",
        "scope": ["read:uploaded_files"],
        "requires_secret": False,
        "requires_verification": False,
    },
]

SOURCE_IDS = [source["id"] for source in SOURCE_CATALOGUE]


def catalogue() -> List[Dict[str, Any]]:
    """A deep copy so callers can annotate entries without mutating the source."""
    return copy.deepcopy(SOURCE_CATALOGUE)


def find_source(source_id: str) -> Optional[Dict[str, Any]]:
    key = str(source_id or "").strip().lower()
    if not key:
        return None
    for source in SOURCE_CATALOGUE:
        if source["id"] == key:
            return copy.deepcopy(source)
    return None


def is_known_source(source_id: str) -> bool:
    return find_source(source_id) is not None


#: Human-readable period labels for revenue. The server only stores the key.
REVENUE_PERIODS = ["DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "ANNUAL", "ONE_TIME"]
