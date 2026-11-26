"""
Italy SdI (Sistema di Interscambio) FatturaPA XML Export Adapter (Rule 70 & Rule 73)
Maps CanonicalInvoice (EN 16931) to FatturaPA v1.2.1 format.
Adheres to Agenzia delle Entrate specifications for mandatory clearance CTC.
"""

from typing import Dict, Any
import xml.etree.ElementTree as ET
from core.invoicing.canonical import CanonicalInvoice


class ItalySdIAdapter:
    """Exports EN 16931 canonical invoice to Italy FatturaPA XML."""

    ADAPTER_ID = "adapter_it_sdi_v12"
    MODEL_TYPE = "CLEARANCE_CTC"

    def __init__(self, is_configured: bool = False):
        self.is_configured = is_configured

    def generate_fatturapa_xml(self, invoice: CanonicalInvoice, trasmissione_id: str = "IT01234567890") -> str:
        """Constructs canonical FatturaPA XML string."""
        totals = invoice.calculate_totals()

        # Root element
        root = ET.Element("p:FatturaElettronica", {
            "versione": "FPR12",
            "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
            "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_v1.2.xsd",
        })

        # Header
        header = ET.SubElement(root, "FatturaElettronicaHeader")

        # DatiTrasmissione
        dati_trasm = ET.SubElement(header, "DatiTrasmissione")
        id_trasm = ET.SubElement(dati_trasm, "IdTrasmittente")
        id_paese = ET.SubElement(id_trasm, "IdPaese")
        id_paese.text = invoice.supplier.country_code
        id_codice = ET.SubElement(id_trasm, "IdCodice")
        id_codice.text = invoice.supplier.tax_identifier.replace(invoice.supplier.country_code, "")
        prog_invio = ET.SubElement(dati_trasm, "ProgressivoInvio")
        prog_invio.text = invoice.invoice_number.replace("-", "")[:10]
        formato_trasm = ET.SubElement(dati_trasm, "FormatoTrasmissione")
        formato_trasm.text = "FPR12"  # B2B
        codice_dest = ET.SubElement(dati_trasm, "CodiceDestinatario")
        codice_dest.text = "0000000"  # Standard B2B default

        # CedentePrestatore (Supplier)
        cedente = ET.SubElement(header, "CedentePrestatore")
        dati_anag_ced = ET.SubElement(cedente, "DatiAnagrafici")
        id_fisc_ced = ET.SubElement(dati_anag_ced, "IdFiscaleIVA")
        id_fisc_ced_paese = ET.SubElement(id_fisc_ced, "IdPaese")
        id_fisc_ced_paese.text = invoice.supplier.country_code
        id_fisc_ced_cod = ET.SubElement(id_fisc_ced, "IdCodice")
        id_fisc_ced_cod.text = invoice.supplier.tax_identifier.replace(invoice.supplier.country_code, "")
        anag_ced = ET.SubElement(dati_anag_ced, "Anagrafica")
        denominazione_ced = ET.SubElement(anag_ced, "Denominazione")
        denominazione_ced.text = invoice.supplier.legal_name
        regime_fisc = ET.SubElement(dati_anag_ced, "RegimeFiscale")
        regime_fisc.text = "RF01"  # Ordinario

        sede_ced = ET.SubElement(cedente, "Sede")
        indirizzo_ced = ET.SubElement(sede_ced, "Indirizzo")
        indirizzo_ced.text = invoice.supplier.street_address
        cap_ced = ET.SubElement(sede_ced, "CAP")
        cap_ced.text = invoice.supplier.postal_code
        comune_ced = ET.SubElement(sede_ced, "Comune")
        comune_ced.text = invoice.supplier.city
        nazione_ced = ET.SubElement(sede_ced, "Nazione")
        nazione_ced.text = invoice.supplier.country_code

        # CessionarioCommittente (Customer)
        cessionario = ET.SubElement(header, "CessionarioCommittente")
        dati_anag_cess = ET.SubElement(cessionario, "DatiAnagrafici")
        id_fisc_cess = ET.SubElement(dati_anag_cess, "IdFiscaleIVA")
        id_fisc_cess_paese = ET.SubElement(id_fisc_cess, "IdPaese")
        id_fisc_cess_paese.text = invoice.customer.country_code
        id_fisc_cess_cod = ET.SubElement(id_fisc_cess, "IdCodice")
        id_fisc_cess_cod.text = invoice.customer.tax_identifier.replace(invoice.customer.country_code, "")
        anag_cess = ET.SubElement(dati_anag_cess, "Anagrafica")
        denominazione_cess = ET.SubElement(anag_cess, "Denominazione")
        denominazione_cess.text = invoice.customer.legal_name

        sede_cess = ET.SubElement(cessionario, "Sede")
        indirizzo_cess = ET.SubElement(sede_cess, "Indirizzo")
        indirizzo_cess.text = invoice.customer.street_address
        cap_cess = ET.SubElement(sede_cess, "CAP")
        cap_cess.text = invoice.customer.postal_code
        comune_cess = ET.SubElement(sede_cess, "Comune")
        comune_cess.text = invoice.customer.city
        nazione_cess = ET.SubElement(sede_cess, "Nazione")
        nazione_cess.text = invoice.customer.country_code

        # Body
        body = ET.SubElement(root, "FatturaElettronicaBody")

        # DatiGenerali
        dati_gen = ET.SubElement(body, "DatiGenerali")
        dati_gen_doc = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
        tipo_doc = ET.SubElement(dati_gen_doc, "TipoDocumento")
        tipo_doc.text = "TD01"  # Fattura ordinaria
        divisa = ET.SubElement(dati_gen_doc, "Divisa")
        divisa.text = invoice.currency
        data_doc = ET.SubElement(dati_gen_doc, "Data")
        data_doc.text = invoice.issue_date
        num_doc = ET.SubElement(dati_gen_doc, "Numero")
        num_doc.text = invoice.invoice_number
        imp_tot = ET.SubElement(dati_gen_doc, "ImportoTotaleDocumento")
        imp_tot.text = f"{totals['grand_total_minor'] / 100:.2f}"

        # DatiBeniServizi
        dati_beni = ET.SubElement(body, "DatiBeniServizi")
        for i, line in enumerate(invoice.lines, 1):
            dett_line = ET.SubElement(dati_beni, "DettaglioLinee")
            num_line = ET.SubElement(dett_line, "NumeroLinea")
            num_line.text = str(i)
            desc_line = ET.SubElement(dett_line, "Descrizione")
            desc_line.text = line.item_name
            qta_line = ET.SubElement(dett_line, "Quantita")
            qta_line.text = f"{line.quantity:.2f}"
            pr_unit = ET.SubElement(dett_line, "PrezzoUnitario")
            pr_unit.text = f"{line.unit_price_minor / 100:.2f}"
            pr_tot = ET.SubElement(dett_line, "PrezzoTotale")
            pr_tot.text = f"{line.line_total_minor / 100:.2f}"
            aliquota = ET.SubElement(dett_line, "AliquotaIVA")
            aliquota.text = f"{line.tax_rate_percent:.2f}"

        dati_riepilogo = ET.SubElement(dati_beni, "DatiRiepilogo")
        aliquota_riep = ET.SubElement(dati_riepilogo, "AliquotaIVA")
        aliquota_riep.text = f"{invoice.lines[0].tax_rate_percent:.2f}" if invoice.lines else "0.00"
        imp_riep = ET.SubElement(dati_riepilogo, "ImponibileImporto")
        imp_riep.text = f"{totals['total_net_minor'] / 100:.2f}"
        imposta_riep = ET.SubElement(dati_riepilogo, "Imposta")
        imposta_riep.text = f"{totals['total_tax_minor'] / 100:.2f}"
        esigibilita = ET.SubElement(dati_riepilogo, "EsigibilitaIVA")
        esigibilita.text = "I"  # Immediata

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
