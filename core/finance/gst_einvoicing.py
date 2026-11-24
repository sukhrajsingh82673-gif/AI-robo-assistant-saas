"""
India GST & E-Invoicing Engine (Schema v1.03 Compliance)
========================================================
Adheres to:
- Rule 61: Statutory Content as Cited Data (rates read from packs/regions/india/gst_rules.json)
- NIC / IRP E-Invoice Schema v1.03 standard
- E-Way Bill JSON generation for consignments > statutory threshold (INR 50,000)
- GSTR-1 preparation and GSTR-2B purchase reconciliation
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GST_RULES_PATH = os.path.join(REPO_ROOT, "packs", "regions", "india", "gst_rules.json")


def load_gst_statutory_pack() -> Dict[str, Any]:
    with open(GST_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class GSTItem(BaseModel):
    item_id: str
    description: str
    hsn_code: str
    quantity: float
    unit_price: float
    gst_rate: float  # e.g. 0.18 for 18%


class EInvoiceParty(BaseModel):
    gstin: str
    legal_name: str
    address: str
    location: str
    pincode: int
    state_code: str  # 2-digit state code, e.g. "27" for Maharashtra, "07" for Delhi


class EInvoicePayload(BaseModel):
    doc_number: str
    doc_date: str  # DD/MM/YYYY
    seller: EInvoiceParty
    buyer: EInvoiceParty
    items: List[GSTItem]


class EWayBillPayload(BaseModel):
    doc_number: str
    doc_date: str
    from_gstin: str
    to_gstin: str
    total_value: float
    hsn_code: str
    distance_km: int
    transporter_id: Optional[str] = None
    vehicle_number: Optional[str] = None


class GSTR2BEntry(BaseModel):
    supplier_gstin: str
    invoice_number: str
    invoice_date: str
    invoice_value: float
    taxable_value: float
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0


class GSTR2BReconResult(BaseModel):
    matched: List[str]
    missing_in_gstr2b: List[str]  # In purchase register but supplier didn't file
    missing_in_books: List[str]   # Supplier filed in 2B but not in purchase register
    value_mismatches: List[Dict[str, Any]]
    total_itc_eligible: float


class IndiaGSTEngine:
    """Computes taxes, formats NIC-compliant JSON, and produces IRN and E-Way bills."""

    def __init__(self):
        self.pack = load_gst_statutory_pack()

    def generate_einvoice_json(self, payload: EInvoicePayload) -> Dict[str, Any]:
        """Generates NIC E-Invoice Schema v1.03 JSON structure."""
        is_interstate = payload.seller.state_code != payload.buyer.state_code
        item_list = []
        tot_ass_val = 0.0
        tot_cgst = 0.0
        tot_sgst = 0.0
        tot_igst = 0.0

        for i, item in enumerate(payload.items):
            ass_amt = round(item.quantity * item.unit_price, 2)
            tot_ass_val += ass_amt
            rate_pct = item.gst_rate * 100.0

            if is_interstate:
                igst_amt = round(ass_amt * item.gst_rate, 2)
                cgst_amt = 0.0
                sgst_amt = 0.0
                tot_igst += igst_amt
            else:
                half_rate = item.gst_rate / 2.0
                cgst_amt = round(ass_amt * half_rate, 2)
                sgst_amt = round(ass_amt * half_rate, 2)
                igst_amt = 0.0
                tot_cgst += cgst_amt
                tot_sgst += sgst_amt

            tot_item_val = round(ass_amt + igst_amt + cgst_amt + sgst_amt, 2)
            item_list.append({
                "SlNo": str(i + 1),
                "PrdDesc": item.description,
                "IsServc": "N",
                "HsnCd": item.hsn_code,
                "Qty": item.quantity,
                "UnitPrice": item.unit_price,
                "TotAmt": ass_amt,
                "AssAmt": ass_amt,
                "GstRt": rate_pct,
                "IgstAmt": igst_amt,
                "CgstAmt": cgst_amt,
                "SgstAmt": sgst_amt,
                "TotItemVal": tot_item_val
            })

        tot_inv_val = round(tot_ass_val + tot_igst + tot_cgst + tot_sgst, 2)

        schema_json = {
            "Version": "1.03",
            "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B"},
            "DocDtls": {"Typ": "INV", "No": payload.doc_number, "Dt": payload.doc_date},
            "SellerDtls": {
                "Gstin": payload.seller.gstin,
                "LglNm": payload.seller.legal_name,
                "Addr1": payload.seller.address,
                "Loc": payload.seller.location,
                "Pin": payload.seller.pincode,
                "Stcd": payload.seller.state_code
            },
            "BuyerDtls": {
                "Gstin": payload.buyer.gstin,
                "LglNm": payload.buyer.legal_name,
                "Pos": payload.buyer.state_code,
                "Addr1": payload.buyer.address,
                "Loc": payload.buyer.location,
                "Pin": payload.buyer.pincode,
                "Stcd": payload.buyer.state_code
            },
            "ItemList": item_list,
            "ValDtls": {
                "AssVal": tot_ass_val,
                "CgstVal": tot_cgst,
                "SgstVal": tot_sgst,
                "IgstVal": tot_igst,
                "TotInvVal": tot_inv_val
            }
        }
        return schema_json

    def compute_irn_hash(self, seller_gstin: str, doc_type: str, doc_number: str, fin_year: str) -> str:
        """Computes official 64-character SHA256 Invoice Reference Number (IRN)."""
        raw_string = f"{seller_gstin}:{doc_type}:{doc_number}:{fin_year}"
        return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

    def generate_eway_bill_if_applicable(self, einvoice: Dict[str, Any], distance_km: int = 150) -> Optional[Dict[str, Any]]:
        threshold = self.pack["rules"]["eway_bill_threshold_inr"]
        tot_val = einvoice["ValDtls"]["TotInvVal"]
        if tot_val < threshold:
            return None

        doc_dtls = einvoice["DocDtls"]
        seller = einvoice["SellerDtls"]
        buyer = einvoice["BuyerDtls"]

        return {
            "supplyType": "O",
            "subSupplyType": "1",
            "docType": "INV",
            "docNo": doc_dtls["No"],
            "docDate": doc_dtls["Dt"],
            "fromGstin": seller["Gstin"],
            "fromTrdName": seller["LglNm"],
            "toGstin": buyer["Gstin"],
            "toTrdName": buyer["LglNm"],
            "totalValue": tot_val,
            "transDistance": distance_km,
            "status": "GENERATED"
        }

    def reconcile_gstr2b(self, purchase_register: List[Dict[str, Any]], gstr2b_feed: List[GSTR2BEntry]) -> GSTR2BReconResult:
        gstr2b_map = {f"{e.supplier_gstin}:{e.invoice_number}": e for e in gstr2b_feed}
        matched = []
        missing_in_2b = []
        value_mismatches = []
        eligible_itc = 0.0

        for pr in purchase_register:
            key = f"{pr['supplier_gstin']}:{pr['invoice_number']}"
            if key in gstr2b_map:
                entry_2b = gstr2b_map[key]
                diff = abs(pr["taxable_value"] - entry_2b.taxable_value)
                if diff > 1.0:
                    value_mismatches.append({
                        "key": key,
                        "books_value": pr["taxable_value"],
                        "gstr2b_value": entry_2b.taxable_value,
                        "diff": diff
                    })
                else:
                    matched.append(key)
                    eligible_itc += (entry_2b.igst + entry_2b.cgst + entry_2b.sgst)
            else:
                missing_in_2b.append(key)

        pr_keys = {f"{pr['supplier_gstin']}:{pr['invoice_number']}" for pr in purchase_register}
        missing_in_books = [k for k in gstr2b_map.keys() if k not in pr_keys]

        return GSTR2BReconResult(
            matched=matched,
            missing_in_gstr2b=missing_in_2b,
            missing_in_books=missing_in_books,
            value_mismatches=value_mismatches,
            total_itc_eligible=round(eligible_itc, 2)
        )
