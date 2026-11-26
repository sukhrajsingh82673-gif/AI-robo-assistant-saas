"""
Germany ZUGFeRD 2.2 / Factur-X & XRechnung Export Adapter (Rule 70 & Rule 73)
Maps CanonicalInvoice (EN 16931) to Cross Industry Invoice (CII) XML.
Adheres to UN/CEFACT D16B CII standard used across Germany and France.
"""

from typing import Dict, Any
import xml.etree.ElementTree as ET
from core.invoicing.canonical import CanonicalInvoice


class GermanyZUGFeRDAdapter:
    """Exports EN 16931 canonical invoice to ZUGFeRD 2.2 / XRechnung CII XML."""

    ADAPTER_ID = "adapter_de_zugferd_v22"
    MODEL_TYPE = "POST_AUDIT_EXCHANGE"

    def __init__(self, is_configured: bool = False):
        self.is_configured = is_configured

    def generate_cii_xml(self, invoice: CanonicalInvoice) -> str:
        """Constructs canonical Cross Industry Invoice XML."""
        totals = invoice.calculate_totals()

        # Root element with UN/CEFACT namespaces
        root = ET.Element("rsm:CrossIndustryInvoice", {
            "xmlns:rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "xmlns:qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
            "xmlns:ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            "xmlns:udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
        })

        # ExchangedDocumentContext
        ctx = ET.SubElement(root, "rsm:ExchangedDocumentContext")
        guideline = ET.SubElement(ctx, "ram:GuidelineSpecifiedDocumentContextParameter")
        gid = ET.SubElement(guideline, "ram:ID")
        gid.text = "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.2"

        # ExchangedDocument
        doc = ET.SubElement(root, "rsm:ExchangedDocument")
        doc_id = ET.SubElement(doc, "ram:ID")
        doc_id.text = invoice.invoice_number
        type_code = ET.SubElement(doc, "ram:TypeCode")
        type_code.text = "380"  # Commercial Invoice
        issue_date = ET.SubElement(doc, "ram:IssueDateTime")
        date_str = ET.SubElement(issue_date, "udt:DateTimeString", {"format": "102"})
        date_str.text = invoice.issue_date.replace("-", "")

        # SupplyChainTradeTransaction
        tx = ET.SubElement(root, "rsm:SupplyChainTradeTransaction")

        # Line Items
        for i, line in enumerate(invoice.lines, 1):
            line_item = ET.SubElement(tx, "ram:IncludedSupplyChainTradeLineItem")
            line_doc = ET.SubElement(line_item, "ram:AssociatedDocumentLineDocument")
            lid = ET.SubElement(line_doc, "ram:LineID")
            lid.text = str(i)

            product = ET.SubElement(line_item, "ram:SpecifiedTradeProduct")
            pname = ET.SubElement(product, "ram:Name")
            pname.text = line.item_name

            price = ET.SubElement(line_item, "ram:SpecifiedLineTradeAgreement")
            net_price = ET.SubElement(price, "ram:NetPriceProductTradePrice")
            charge_amt = ET.SubElement(net_price, "ram:ChargeAmount")
            charge_amt.text = f"{line.unit_price_minor / 100.0:.2f}"

            delivery = ET.SubElement(line_item, "ram:SpecifiedLineTradeDelivery")
            qty = ET.SubElement(delivery, "ram:BilledQuantity", {"unitCode": "C62"})
            qty.text = str(line.quantity)

            settlement = ET.SubElement(line_item, "ram:SpecifiedLineTradeSettlement")
            monetary = ET.SubElement(settlement, "ram:SpecifiedTradeSettlementLineMonetarySummation")
            line_tot = ET.SubElement(monetary, "ram:LineTotalAmount")
            line_tot.text = f"{line.line_total_minor / 100.0:.2f}"

        # Trade Header Parties
        agreement = ET.SubElement(tx, "ram:ApplicableHeaderTradeAgreement")
        seller = ET.SubElement(agreement, "ram:SellerTradeParty")
        sname = ET.SubElement(seller, "ram:Name")
        sname.text = invoice.supplier.legal_name
        stax = ET.SubElement(seller, "ram:SpecifiedTaxRegistration")
        stax_id = ET.SubElement(stax, "ram:ID", {"schemeID": "VA"})
        stax_id.text = invoice.supplier.tax_identifier

        buyer = ET.SubElement(agreement, "ram:BuyerTradeParty")
        bname = ET.SubElement(buyer, "ram:Name")
        bname.text = invoice.customer.legal_name
        btax = ET.SubElement(buyer, "ram:SpecifiedTaxRegistration")
        btax_id = ET.SubElement(btax, "ram:ID", {"schemeID": "VA"})
        btax_id.text = invoice.customer.tax_identifier

        # Settlement Summary
        header_settlement = ET.SubElement(tx, "ram:ApplicableHeaderTradeSettlement")
        curr = ET.SubElement(header_settlement, "ram:InvoiceCurrencyCode")
        curr.text = invoice.currency

        summation = ET.SubElement(header_settlement, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
        line_total = ET.SubElement(summation, "ram:LineTotalAmount")
        line_total.text = f"{totals['total_net_minor'] / 100.0:.2f}"
        tax_total = ET.SubElement(summation, "ram:TaxTotalAmount", {"currencyID": invoice.currency})
        tax_total.text = f"{totals['total_tax_minor'] / 100.0:.2f}"
        grand_total = ET.SubElement(summation, "ram:GrandTotalAmount")
        grand_total.text = f"{totals['grand_total_minor'] / 100.0:.2f}"

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
