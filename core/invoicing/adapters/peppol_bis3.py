"""
Peppol BIS Billing 3.0 UBL 2.1 Export Adapter (Rule 70 & Rule 73)
Maps CanonicalInvoice (EN 16931) to Peppol UBL 2.1 Invoice XML.
Adheres to OpenPeppol BIS Billing 3.0 specification.
"""

from typing import Dict, Any
import xml.etree.ElementTree as ET
from core.invoicing.canonical import CanonicalInvoice


class PeppolBIS3Adapter:
    """Exports EN 16931 canonical invoice to Peppol BIS Billing 3.0 UBL XML."""

    ADAPTER_ID = "adapter_peppol_bis3_ubl"
    MODEL_TYPE = "PEPPOL_NETWORK"

    def __init__(self, is_configured: bool = False):
        self.is_configured = is_configured

    def generate_ubl_xml(self, invoice: CanonicalInvoice) -> str:
        """Constructs Peppol BIS 3.0 compliant UBL 2.1 XML."""
        totals = invoice.calculate_totals()

        # Root element with UBL namespaces
        root = ET.Element("Invoice", {
            "xmlns": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "xmlns:cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "xmlns:cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        })

        # Customization & Profile IDs
        customization = ET.SubElement(root, "cbc:CustomizationID")
        customization.text = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
        profile = ET.SubElement(root, "cbc:ProfileID")
        profile.text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

        # Invoice ID and Dates
        doc_id = ET.SubElement(root, "cbc:ID")
        doc_id.text = invoice.invoice_number
        issue_date = ET.SubElement(root, "cbc:IssueDate")
        issue_date.text = invoice.issue_date
        due_date = ET.SubElement(root, "cbc:DueDate")
        due_date.text = invoice.due_date
        type_code = ET.SubElement(root, "cbc:InvoiceTypeCode")
        type_code.text = "380"
        currency = ET.SubElement(root, "cbc:DocumentCurrencyCode")
        currency.text = invoice.currency

        # Supplier
        supplier_party = ET.SubElement(root, "cac:AccountingSupplierParty")
        party = ET.SubElement(supplier_party, "cac:Party")
        pname = ET.SubElement(party, "cac:PartyName")
        ET.SubElement(pname, "cbc:Name").text = invoice.supplier.legal_name
        legal_entity = ET.SubElement(party, "cac:PartyLegalEntity")
        ET.SubElement(legal_entity, "cbc:RegistrationName").text = invoice.supplier.legal_name
        tax_scheme = ET.SubElement(party, "cac:PartyTaxScheme")
        ET.SubElement(tax_scheme, "cbc:CompanyID").text = invoice.supplier.tax_identifier
        ET.SubElement(tax_scheme, "cac:TaxScheme").append(ET.Element("cbc:ID", text="VAT"))

        # Customer
        customer_party = ET.SubElement(root, "cac:AccountingCustomerParty")
        c_party = ET.SubElement(customer_party, "cac:Party")
        c_name = ET.SubElement(c_party, "cac:PartyName")
        ET.SubElement(c_name, "cbc:Name").text = invoice.customer.legal_name
        c_tax_scheme = ET.SubElement(c_party, "cac:PartyTaxScheme")
        ET.SubElement(c_tax_scheme, "cbc:CompanyID").text = invoice.customer.tax_identifier
        ET.SubElement(c_tax_scheme, "cac:TaxScheme").append(ET.Element("cbc:ID", text="VAT"))

        # Monetary Totals
        monetary_total = ET.SubElement(root, "cac:LegalMonetaryTotal")
        ET.SubElement(monetary_total, "cbc:LineExtensionAmount", {"currencyID": invoice.currency}).text = f"{totals['total_net_minor'] / 100.0:.2f}"
        ET.SubElement(monetary_total, "cbc:TaxExclusiveAmount", {"currencyID": invoice.currency}).text = f"{totals['total_net_minor'] / 100.0:.2f}"
        ET.SubElement(monetary_total, "cbc:TaxInclusiveAmount", {"currencyID": invoice.currency}).text = f"{totals['grand_total_minor'] / 100.0:.2f}"
        ET.SubElement(monetary_total, "cbc:PayableAmount", {"currencyID": invoice.currency}).text = f"{totals['grand_total_minor'] / 100.0:.2f}"

        # Invoice Lines
        for i, line in enumerate(invoice.lines, 1):
            inv_line = ET.SubElement(root, "cac:InvoiceLine")
            ET.SubElement(inv_line, "cbc:ID").text = str(i)
            ET.SubElement(inv_line, "cbc:InvoicedQuantity", {"unitCode": "C62"}).text = str(line.quantity)
            ET.SubElement(inv_line, "cbc:LineExtensionAmount", {"currencyID": invoice.currency}).text = f"{line.line_total_minor / 100.0:.2f}"

            item = ET.SubElement(inv_line, "cac:Item")
            ET.SubElement(item, "cbc:Name").text = line.item_name
            tax_cat = ET.SubElement(item, "cac:ClassifiedTaxCategory")
            ET.SubElement(tax_cat, "cbc:ID").text = line.tax_category
            ET.SubElement(tax_cat, "cbc:Percent").text = str(line.tax_rate_percent)
            ET.SubElement(tax_cat, "cac:TaxScheme").append(ET.Element("cbc:ID", text="VAT"))

            price = ET.SubElement(inv_line, "cac:Price")
            ET.SubElement(price, "cbc:PriceAmount", {"currencyID": invoice.currency}).text = f"{line.unit_price_minor / 100.0:.2f}"

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    generate_peppol_ubl = generate_ubl_xml
