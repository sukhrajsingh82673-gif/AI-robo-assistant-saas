"""
Poland KSeF (Krajowy System e-Faktur) FA_VAT XML Export Adapter (Rule 70 & Rule 73)
Maps CanonicalInvoice (EN 16931) to Polish Ministry of Finance FA(2) schema.
Adheres to mandatory clearance portal submission requirements under Polish VAT Law.
"""

from typing import Dict, Any
import xml.etree.ElementTree as ET
from core.invoicing.canonical import CanonicalInvoice


class PolandKSeFAdapter:
    """Exports EN 16931 canonical invoice to Poland KSeF FA(2) XML."""

    ADAPTER_ID = "adapter_pl_ksef_v2"
    MODEL_TYPE = "CENTRAL_PORTAL"

    def __init__(self, is_configured: bool = False):
        self.is_configured = is_configured

    def generate_ksef_xml(self, invoice: CanonicalInvoice) -> str:
        """Constructs canonical KSeF FA(2) XML string."""
        totals = invoice.calculate_totals()

        # Root element
        root = ET.Element("Faktura", {
            "xmlns": "http://crd.gov.pl/wzor/2023/06/29/12648/",
            "xmlns:etd": "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        })

        # Naglowek
        naglowek = ET.SubElement(root, "Naglowek")
        kod_form = ET.SubElement(naglowek, "KodFormularza", {"kodSystemowy": "FA (2)", "wersjaSchemy": "1-0E"})
        kod_form.text = "FA"
        wariant = ET.SubElement(naglowek, "WariantFormularza")
        wariant.text = "2"
        data_wytw = ET.SubElement(naglowek, "DataWytworzeniaFa")
        data_wytw.text = f"{invoice.issue_date}T10:00:00Z"
        system_info = ET.SubElement(naglowek, "SystemInfo")
        system_info.text = "Zonata E-Invoicing Engine"

        # Podmiot1 (Sprzedawca - Supplier)
        podmiot1 = ET.SubElement(root, "Podmiot1")
        dane_id1 = ET.SubElement(podmiot1, "DaneIdentyfikacyjne")
        nip1 = ET.SubElement(dane_id1, "NIP")
        nip1.text = invoice.supplier.tax_identifier.replace("PL", "")
        nazwa1 = ET.SubElement(dane_id1, "Nazwa")
        nazwa1.text = invoice.supplier.legal_name

        adres1 = ET.SubElement(podmiot1, "Adres")
        kod_kraju1 = ET.SubElement(adres1, "KodKraju")
        kod_kraju1.text = invoice.supplier.country_code
        adres_pol1 = ET.SubElement(adres1, "AdresPol")
        ulica1 = ET.SubElement(adres_pol1, "Ulica")
        ulica1.text = invoice.supplier.street_address
        miejscowosc1 = ET.SubElement(adres_pol1, "Miejscowosc")
        miejscowosc1.text = invoice.supplier.city
        kod_pocztowy1 = ET.SubElement(adres_pol1, "KodPocztowy")
        kod_pocztowy1.text = invoice.supplier.postal_code

        # Podmiot2 (Nabywca - Customer)
        podmiot2 = ET.SubElement(root, "Podmiot2")
        dane_id2 = ET.SubElement(podmiot2, "DaneIdentyfikacyjne")
        nip2 = ET.SubElement(dane_id2, "NIP")
        nip2.text = invoice.customer.tax_identifier.replace("PL", "")
        nazwa2 = ET.SubElement(dane_id2, "Nazwa")
        nazwa2.text = invoice.customer.legal_name

        adres2 = ET.SubElement(podmiot2, "Adres")
        kod_kraju2 = ET.SubElement(adres2, "KodKraju")
        kod_kraju2.text = invoice.customer.country_code
        adres_pol2 = ET.SubElement(adres2, "AdresPol")
        ulica2 = ET.SubElement(adres_pol2, "Ulica")
        ulica2.text = invoice.customer.street_address
        miejscowosc2 = ET.SubElement(adres_pol2, "Miejscowosc")
        miejscowosc2.text = invoice.customer.city
        kod_pocztowy2 = ET.SubElement(adres_pol2, "KodPocztowy")
        kod_pocztowy2.text = invoice.customer.postal_code

        # Fa (Document details)
        fa = ET.SubElement(root, "Fa")
        kod_waluty = ET.SubElement(fa, "KodWaluty")
        kod_waluty.text = invoice.currency
        p_1 = ET.SubElement(fa, "P_1")  # Data wystawienia
        p_1.text = invoice.issue_date
        p_2 = ET.SubElement(fa, "P_2")  # Numer faktury
        p_2.text = invoice.invoice_number

        # Line items FaWiersz
        for i, line in enumerate(invoice.lines, 1):
            wiersz = ET.SubElement(fa, "FaWiersz")
            nr_wiersza = ET.SubElement(wiersz, "NrWierszaFa")
            nr_wiersza.text = str(i)
            p_7 = ET.SubElement(wiersz, "P_7")  # Nazwa towaru/uslugi
            p_7.text = line.item_name
            p_8a = ET.SubElement(wiersz, "P_8A") # Jednostka miary
            p_8a.text = "szt"
            p_8b = ET.SubElement(wiersz, "P_8B") # Ilosc
            p_8b.text = f"{line.quantity:.2f}"
            p_9a = ET.SubElement(wiersz, "P_9A") # Cena jednostkowa netto
            p_9a.text = f"{line.unit_price_minor / 100:.2f}"
            p_11 = ET.SubElement(wiersz, "P_11") # Wartosc netto
            p_11.text = f"{line.line_total_minor / 100:.2f}"
            p_12 = ET.SubElement(wiersz, "P_12") # Stawka podatku
            p_12.text = str(int(line.tax_rate_percent))

        # Totals in Fa
        p_13_1 = ET.SubElement(fa, "P_13_1")  # Suma netto stawki podstawowej
        p_13_1.text = f"{totals['total_net_minor'] / 100:.2f}"
        p_14_1 = ET.SubElement(fa, "P_14_1")  # Podatek stawki podstawowej
        p_14_1.text = f"{totals['total_tax_minor'] / 100:.2f}"
        p_15 = ET.SubElement(fa, "P_15")      # Naleznosc ogolem
        p_15.text = f"{totals['grand_total_minor'] / 100:.2f}"

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
