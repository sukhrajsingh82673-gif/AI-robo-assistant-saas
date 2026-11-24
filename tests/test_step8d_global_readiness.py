"""
Tests for Sub-Step 8D: Global Corporate Readiness (Rule 67, 68, 70, 71, 73)
Validates group consolidation, e-invoicing adapters, tax escalation, CLDR/RTL/pseudo-localization,
cellular residency routing, Wave 1 enterprise connectors, and procurement pack generator.
"""

import pytest
import xml.etree.ElementTree as ET
from decimal import Decimal

# Consolidation
from core.consolidation.engine import (
    ConsolidationEngine,
    LegalEntity,
    IntercompanyTransaction,
    ConsolidationMethod,
)

# Invoicing
from core.invoicing.canonical import CanonicalInvoice, InvoiceParty, InvoiceLineItem
from core.invoicing.tax_escalation import TaxEscalationEngine, TaxDeterminationEscalationRequired
from core.invoicing.adapters.india_irp import IndiaIRPAdapter
from core.invoicing.adapters.germany_zugferd import GermanyZUGFeRDAdapter
from core.invoicing.adapters.peppol_bis3 import PeppolBIS3Adapter
from core.invoicing.adapters.italy_sdi import ItalySdIAdapter
from core.invoicing.adapters.poland_ksef import PolandKSeFAdapter

# I18n / Localization
from core.i18n.cldr import CLDREngine
from core.i18n.rtl import RTLEngine
from core.i18n.pseudo import PseudoLocalizer
from core.i18n.translation_guard import (
    TranslationGuard,
    UnreviewedLegalTranslationBlockedError,
)

# Data Residency / Cellular Routing
from core.residency.cell_router import (
    CellRouter,
    CrossRegionOperationRefusedError,
)

# Wave 1 Connectors
from core.connectors.wave1.sap_s4hana import SAPS4HANAConnector
from core.connectors.wave1.quickbooks import QuickBooksConnector
from core.connectors.wave1.salesforce import SalesforceConnector
from core.connectors.wave1.workday import WorkdayConnector
from core.connectors.wave1.servicenow import ServiceNowConnector
from core.connectors.wave1.slack import SlackConnector
from core.connectors.wave1.snowflake import SnowflakeConnector
from core.connectors.wave1.edi_iso20022 import ISO20022Connector

# Procurement Pack
from core.procurement.buyer_pack import (
    BuyerPackGenerator,
    ProcurementEvidenceMissingError,
    REQUIRED_EVIDENCE_KEYS,
)


class TestStep8DGlobalReadiness:

    # 1. Group Consolidation & Zero-Net Eliminations
    def test_01_three_entity_group_consolidation_and_eliminations(self):
        # Parent (DE)
        parent = LegalEntity(company_id="E001", legal_name="Zonata Holding GmbH", jurisdiction_code="DE", functional_currency="EUR", ownership_percentage=100.0)
        # Sub 1 (US)
        sub_us = LegalEntity(company_id="E002", legal_name="Zonata US Inc", jurisdiction_code="US", functional_currency="USD", ownership_percentage=100.0)
        # Sub 2 (IN)
        sub_in = LegalEntity(company_id="E003", legal_name="Zonata India Pvt Ltd", jurisdiction_code="IN", functional_currency="INR", ownership_percentage=100.0)

        engine = ConsolidationEngine(
            group_id="GRP-001",
            group_name="Zonata Global Group",
            presentation_currency="EUR",
            parent_company_id="E001",
            entities=[parent, sub_us, sub_in],
        )

        # Exchange rates to EUR
        fx_spot = {"EUR": 1.0, "USD": 0.92, "INR": 0.011}
        fx_avg = {"EUR": 1.0, "USD": 0.90, "INR": 0.011}

        # Balances
        entity_balances = {
            "E001": {"1000_CASH": 1000000, "1100_INTERCOMPANY_AR": 200000, "3000_EQUITY": 1200000},
            "E002": {"1000_CASH": 500000, "2100_INTERCOMPANY_AP": 217391, "3000_EQUITY": 282609},
            "E003": {"1000_CASH": 50000000, "3000_EQUITY": 50000000},
        }
        account_types = {
            "1000_CASH": "ASSET",
            "1100_INTERCOMPANY_AR": "ASSET",
            "2100_INTERCOMPANY_AP": "LIABILITY",
            "3000_EQUITY": "EQUITY",
        }

        # 1. Translate
        trans_res = engine.translate_balances(entity_balances, account_types, fx_spot, fx_avg)
        assert "E001" in trans_res
        assert "E002" in trans_res
        assert "E003" in trans_res

        # 2. Intercompany loan elimination: E001 lent EUR 200,000 to E002
        ic_tx = IntercompanyTransaction(
            transaction_id="IC-001",
            from_company_id="E001",
            to_company_id="E002",
            amount_minor=200000,
            currency="EUR",
            transaction_type="LOAN",
            matched_reference="REF-LOAN-2026-001"
        )
        elim_journals, net_balance = engine.compute_intercompany_eliminations([ic_tx], fx_spot)
        assert len(elim_journals) == 1
        assert net_balance == 0  # Debits == credits, nets to exactly zero

        # 3. Consolidated financials
        report = engine.generate_consolidated_financials(trans_res, elim_journals)
        assert report["presentation_currency"] == "EUR"
        assert len(report["entities_consolidated"]) == 3
        assert report["elimination_entries_count"] == 1
        assert "consolidation_seal" in report

    # 2. EN 16931 Canonical Invoicing to Deep Jurisdiction Formats
    def test_02_canonical_invoicing_adapters(self):
        supplier = InvoiceParty(
            party_id="P-001",
            legal_name="Zonata Europe GmbH",
            tax_identifier="DE123456789",
            country_code="DE",
            street_address="Taunusanlage 8",
            city="Frankfurt",
            postal_code="60329"
        )
        customer = InvoiceParty(
            party_id="P-002",
            legal_name="Client International Corp",
            tax_identifier="US987654321",
            country_code="US",
            street_address="100 Wall St",
            city="New York",
            postal_code="10005"
        )
        line1 = InvoiceLineItem(
            line_id="L1",
            item_name="Autonomous Orchestration Enterprise Subscription",
            quantity=1.0,
            unit_price_minor=1000000, # 10,000.00
            tax_category="S",
            tax_rate_percent=19.0
        )
        invoice = CanonicalInvoice(
            invoice_number="INV-2026-EU-001",
            issue_date="2026-11-24",
            due_date="2026-12-24",
            currency="EUR",
            supplier=supplier,
            customer=customer,
            lines=[line1]
        )

        totals = invoice.calculate_totals()
        assert totals["total_net_minor"] == 1000000
        assert totals["total_tax_minor"] == 190000
        assert totals["grand_total_minor"] == 1190000

        # Germany ZUGFeRD / XRechnung (CII XML)
        de_adapter = GermanyZUGFeRDAdapter()
        de_xml = de_adapter.generate_cii_xml(invoice)
        assert "CrossIndustryInvoice" in de_xml
        assert "INV-2026-EU-001" in de_xml

        # India IRP JSON
        in_adapter = IndiaIRPAdapter()
        irp_doc = in_adapter.generate_irp_payload(invoice)
        assert irp_doc["DocDtls"]["No"] == "INV-2026-EU-001"
        assert "Irn" in irp_doc

        # Peppol BIS 3.0 UBL XML
        peppol_adapter = PeppolBIS3Adapter()
        peppol_xml = peppol_adapter.generate_peppol_ubl(invoice)
        assert "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" in peppol_xml

        # Italy SdI FatturaPA XML
        it_adapter = ItalySdIAdapter()
        it_xml = it_adapter.generate_fatturapa_xml(invoice)
        assert "FatturaElettronica" in it_xml
        assert "FPR12" in it_xml

        # Poland KSeF XML
        pl_adapter = PolandKSeFAdapter()
        pl_xml = pl_adapter.generate_ksef_xml(invoice)
        assert "Faktura" in pl_xml
        assert "FA (2)" in pl_xml

    # 3. Tax Escalation Gate
    def test_03_statutory_tax_escalation_gate(self):
        engine = TaxEscalationEngine()

        # Verified rule for standard Germany VAT
        rate = engine.determine_tax_rate(
            jurisdiction_code="DE",
            tax_category="S",
            is_rule_verified=True
        )
        assert rate == 19.0

        # Unverified cross-border complexity raises TaxDeterminationEscalationRequired
        with pytest.raises(TaxDeterminationEscalationRequired) as exc:
            engine.determine_tax_rate(
                jurisdiction_code="BR",
                tax_category="SPECIAL",
                is_rule_verified=False
            )
        assert "Tax determination escalated" in str(exc.value)

    # 4. CLDR Number, Currency, and Date Formatting
    def test_04_cldr_formatting(self):
        # 1234567.89 formatting in US vs DE vs HI (Indian system)
        val = 1234567.89
        us_num = CLDREngine.format_number(val, locale="en_US")
        assert us_num == "1,234,567.89"

        de_num = CLDREngine.format_number(val, locale="de_DE")
        assert de_num == "1.234.567,89"

        hi_num = CLDREngine.format_number(val, locale="hi_IN")
        assert hi_num == "12,34,567.89"

        # Currency formatting with minor integer units
        # 1,500.50 EUR in de_DE -> '1.500,50 €'
        eur_str = CLDREngine.format_currency(150050, currency="EUR", locale="de_DE")
        assert eur_str == "1.500,50 €"

        # 10,000 USD in en_US -> '$10,000.00'
        usd_str = CLDREngine.format_currency(1000000, currency="USD", locale="en_US")
        assert usd_str == "$10,000.00"

        # Date formatting
        date_str = CLDREngine.format_date("2026-11-24", locale="de_DE")
        assert date_str == "24.11.2026"

    # 5. RTL Layout and Bi-directional Text
    def test_05_rtl_detection_and_bidi(self):
        assert RTLEngine.is_rtl("ar_SA") is True
        assert RTLEngine.is_rtl("he_IL") is True
        assert RTLEngine.is_rtl("en_US") is False

        ar_meta = RTLEngine.get_layout_metadata("ar_SA")
        assert ar_meta["direction"] == "rtl"
        assert ar_meta["start_align"] == "right"
        assert ar_meta["mirror_icons"] is True

        en_meta = RTLEngine.get_layout_metadata("en_US")
        assert en_meta["direction"] == "ltr"
        assert en_meta["start_align"] == "left"
        assert en_meta["mirror_icons"] is False

    # 6. Pseudo-Localization String Expansion
    def test_06_pseudo_localization(self):
        original = "Account Settings"
        pseudo = PseudoLocalizer.transform(original, expand=True)
        assert pseudo.startswith("[!!!")
        assert pseudo.endswith("!!!]")
        assert len(pseudo) > len(original) * 1.2

    # 7. Translation Guard for Statutory/Legal Texts
    def test_07_unreviewed_legal_translation_blocked(self):
        # Uncertified legal translation attempt raises UnreviewedLegalTranslationBlockedError
        with pytest.raises(UnreviewedLegalTranslationBlockedError) as exc:
            TranslationGuard.verify_translation_eligibility(
                document_type="STATUTORY_TAX_FILING",
                source_lang="de",
                target_lang="en",
                is_human_certified=False
            )
        assert "UNREVIEWED_LEGAL_TRANSLATION_BLOCKED" in str(exc.value)

        # Certified legal translation passes
        assert TranslationGuard.verify_translation_eligibility(
            document_type="STATUTORY_TAX_FILING",
            source_lang="de",
            target_lang="en",
            is_human_certified=True,
            certified_reviewer_id="CERT-LEGAL-REV-09"
        ) is True

    # 8. Sovereign Data Residency & Cellular Routing
    def test_08_cellular_routing_and_cross_region_refusal(self):
        assert CellRouter.get_cell_for_jurisdiction("DE") == "cell-eu-frankfurt"
        assert CellRouter.get_cell_for_jurisdiction("US") == "cell-us-east"
        assert CellRouter.get_cell_for_jurisdiction("IN") == "cell-in-mumbai"

        # Intra-cell passes
        assert CellRouter.validate_cross_cell_access("cell-eu-frankfurt", "cell-eu-frankfurt", "QUERY") is True

        # Cross-cell without lawful basis raises CrossRegionOperationRefusedError
        with pytest.raises(CrossRegionOperationRefusedError) as exc:
            CellRouter.validate_cross_cell_access(
                source_cell_id="cell-eu-frankfurt",
                target_cell_id="cell-us-east",
                operation_type="REPLICATION",
                has_lawful_transfer_mechanism=False
            )
        assert "CROSS_REGION_OPERATION_REFUSED" in str(exc.value)

    # 9. Wave 1 Enterprise Connectors Replay Contracts
    def test_09_wave1_connectors_contracts(self):
        # 1. SAP S/4HANA
        sap = SAPS4HANAConnector(replay_mode=True)
        gl = sap.get_gl_account("1000", "100100")
        assert gl["d"]["results"][0]["GLAccount"] == "100100"

        # 2. QuickBooks
        qb = QuickBooksConnector(replay_mode=True)
        info = qb.get_company_info()
        assert "CompanyName" in info["CompanyInfo"]

        # 3. Salesforce
        sf = SalesforceConnector(replay_mode=True)
        acc = sf.query_account("Acme")
        assert acc["records"][0]["Name"] == "Acme Global Industries"

        # 4. Workday
        wd = WorkdayConnector(replay_mode=True)
        worker = wd.get_worker("W009841")
        assert worker["Worker_Data"]["Worker_ID"] == "W009841"

        # 5. ServiceNow
        sn = ServiceNowConnector(replay_mode=True)
        inc = sn.get_incident("INC0010023")
        assert inc["result"]["number"] == "INC0010023"

        # 6. Slack
        slack = SlackConnector(replay_mode=True)
        msg = slack.post_message("C0123456789", "Test alert")
        assert msg["ok"] is True

        # 7. Snowflake
        sf_wh = SnowflakeConnector(replay_mode=True)
        rows = sf_wh.execute_query("SELECT * FROM balances")
        assert len(rows["data"]) == 2

        # 8. ISO 20022
        iso = ISO20022Connector(replay_mode=True)
        pacs_xml = iso.generate_pacs_008_xml(
            msg_id="MSG-001",
            debtor_name="Zonata GmbH",
            debtor_iban="DE89370400440532013000",
            creditor_name="Supplier B.V.",
            creditor_iban="NL91ABNA0417164300",
            amount=50000.00
        )
        assert "FIToFICstmrCdtTrf" in pacs_xml
        assert "MSG-001" in pacs_xml

    # 10. Enterprise Procurement Pack Generator
    def test_10_procurement_pack_generator(self):
        citations = {
            "soc2_type2_attestation": "SOC 2 Type II Report dated 2026-10-15 by Ernst & Young",
            "iso27001_certification": "ISO/IEC 27001:2022 Certificate #CERT-99281-BSI",
            "gdpr_dpa_standard_clauses": "Zonata Standard DPA v2026.2 incorporating EU SCC 2021/914",
            "last_pentest_attestation": "Third-party Gray-box Pentest by Cure53 dated 2026-09-30",
            "dr_rpo_rto_sla": "SLA Addendum Schedule C: RPO <= 1h, RTO <= 4h across AWS/GCP regions",
        }

        # Full citations pass
        pack = BuyerPackGenerator.generate_dossier(
            company_name="MegaCorp Global",
            target_industry_code="C28",
            target_jurisdiction="DE",
            evidence_citations=citations,
            author_id="CORP-SALES-ARCHITECT-01"
        )
        assert "dossier_seal_sha256" in pack
        assert pack["security_certifications"]["soc2"] == citations["soc2_type2_attestation"]

        # Missing citation raises ProcurementEvidenceMissingError
        incomplete = citations.copy()
        del incomplete["soc2_type2_attestation"]
        with pytest.raises(ProcurementEvidenceMissingError) as exc:
            BuyerPackGenerator.generate_dossier(
                company_name="MegaCorp Global",
                target_industry_code="C28",
                target_jurisdiction="DE",
                evidence_citations=incomplete,
                author_id="CORP-SALES-ARCHITECT-01"
            )
        assert "PROCUREMENT_EVIDENCE_MISSING" in str(exc.value)
