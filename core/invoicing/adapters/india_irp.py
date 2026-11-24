"""
India IRP E-Invoice Export Adapter (NIC JSON Schema v1.03)
Maps CanonicalInvoice (EN 16931) to India GST e-Invoice Schema.
Generates canonical SHA-256 Invoice Reference Number (IRN) preimage.
"""

from typing import Dict, Any
import hashlib
import json
from core.invoicing.canonical import CanonicalInvoice


class IndiaIRPAdapter:
    """Exports EN 16931 canonical invoices to India GST e-Invoice JSON payload."""

    ADAPTER_ID = "adapter_in_irp_v103"
    MODEL_TYPE = "CLEARANCE_CTC"

    def __init__(self, is_configured: bool = False):
        self.is_configured = is_configured

    def generate_irp_payload(self, invoice: CanonicalInvoice) -> Dict[str, Any]:
        """Maps canonical invoice to India GST IRP format."""
        totals = invoice.calculate_totals()

        # Convert minor units to major rupees
        tot_val = totals["grand_total_minor"] / 100.0
        ass_val = totals["total_net_minor"] / 100.0
        tax_val = totals["total_tax_minor"] / 100.0

        # Split tax between CGST & SGST (intra-state default)
        cgst_val = round(tax_val / 2.0, 2)
        sgst_val = round(tax_val / 2.0, 2)

        item_list = []
        for i, line in enumerate(invoice.lines, 1):
            unit_price = line.unit_price_minor / 100.0
            tot_amt = line.line_total_minor / 100.0
            item_list.append({
                "SlNo": str(i),
                "PrdDesc": line.item_name,
                "IsServc": "Y",
                "HsnCd": "998313",  # Information technology consulting
                "Qty": line.quantity,
                "UnitPrice": unit_price,
                "TotAmt": tot_amt,
                "AssAmt": tot_amt,
                "GstRt": line.tax_rate_percent,
                "IgstAmt": 0.0,
                "CgstAmt": round((tot_amt * (line.tax_rate_percent / 200.0)), 2),
                "SgstAmt": round((tot_amt * (line.tax_rate_percent / 200.0)), 2),
                "TotItemVal": round(tot_amt * (1.0 + (line.tax_rate_percent / 100.0)), 2),
            })

        payload = {
            "Version": "1.03",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": "B2B",
                "RegRev": "N",
            },
            "DocDtls": {
                "Typ": "INV",
                "No": invoice.invoice_number,
                "Dt": datetime_to_in_format(invoice.issue_date),
            },
            "SellerDtls": {
                "Gstin": invoice.supplier.tax_identifier,
                "LglNm": invoice.supplier.legal_name,
                "Addr1": invoice.supplier.street_address,
                "Loc": invoice.supplier.city,
                "Pin": int(invoice.supplier.postal_code) if invoice.supplier.postal_code.isdigit() else 110001,
                "Stcd": "07",  # Delhi state code default
            },
            "BuyerDtls": {
                "Gstin": invoice.customer.tax_identifier,
                "LglNm": invoice.customer.legal_name,
                "Pos": "07",
                "Addr1": invoice.customer.street_address,
                "Loc": invoice.customer.city,
                "Pin": int(invoice.customer.postal_code) if invoice.customer.postal_code.isdigit() else 110001,
                "Stcd": "07",
            },
            "ItemList": item_list,
            "ValDtls": {
                "AssVal": ass_val,
                "CgstVal": cgst_val,
                "SgstVal": sgst_val,
                "IgstVal": 0.0,
                "CesVal": 0.0,
                "StCesVal": 0.0,
                "Discount": 0.0,
                "OthChrg": 0.0,
                "RndOffAmt": 0.0,
                "TotInvVal": tot_val,
            },
        }

        # Generate canonical IRN hash
        irn_preimage = f"{invoice.supplier.tax_identifier}:{invoice.issue_date[:4]}:{invoice.invoice_number}"
        payload["Irn"] = hashlib.sha256(irn_preimage.encode("utf-8")).hexdigest()
        payload["TransmissionStatus"] = "CONFIGURED_READY" if self.is_configured else "NOT_CONFIGURED"

        return payload


def datetime_to_in_format(dt_str: str) -> str:
    """Converts YYYY-MM-DD to DD/MM/YYYY."""
    parts = dt_str.split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return dt_str
