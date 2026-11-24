"""
Bank Reconciliation Engine (Multi-Format Statement Parsing & Intelligent Matching)
==================================================================================
Supports:
- CAMT.053 (ISO 20022 XML)
- MT940 (SWIFT Flat File)
- Standard Bank CSV
Matching:
- Exact match (amount + date + reference)
- Fuzzy match (amount + date +/- 3 days + payee similarity >= 0.85)
- Exceptions routed to bank rec exception queue (Rule 59: Never auto-correct)
"""

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field


class BankTransaction(BaseModel):
    transaction_id: str
    date: str  # YYYY-MM-DD
    amount: float  # Positive for credit (inbound), negative for debit (outbound)
    currency: str
    payee_or_narrative: str
    reference: Optional[str] = None


class LedgerTransaction(BaseModel):
    entry_id: str
    date: str
    amount: float
    currency: str
    payee: str
    reference: Optional[str] = None


class ReconciliationMatch(BaseModel):
    bank_tx_id: str
    ledger_entry_id: str
    match_type: str  # 'EXACT' or 'FUZZY'
    confidence: float
    details: Dict[str, str] = Field(default_factory=dict)


class BankRecResult(BaseModel):
    total_bank_transactions: int
    matched_count: int
    unmatched_bank_txs: List[BankTransaction] = Field(default_factory=list)
    unmatched_ledger_entries: List[LedgerTransaction] = Field(default_factory=list)
    matches: List[ReconciliationMatch] = Field(default_factory=list)
    match_rate: float


class BankStatementParser:
    """Parses CAMT.053, MT940, and CSV into canonical BankTransaction list."""

    @staticmethod
    def parse_csv(csv_content: str, currency: str = "INR") -> List[BankTransaction]:
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        txs: List[BankTransaction] = []
        for i, row in enumerate(reader):
            date_str = row.get("date") or row.get("Date") or ""
            amt_str = row.get("amount") or row.get("Amount") or "0"
            payee = row.get("payee") or row.get("description") or row.get("Narrative") or "Unknown"
            ref = row.get("reference") or row.get("Reference") or None
            txs.append(BankTransaction(
                transaction_id=f"tx_csv_{i+1}",
                date=date_str.strip(),
                amount=float(amt_str),
                currency=currency,
                payee_or_narrative=payee.strip(),
                reference=ref.strip() if ref else None
            ))
        return txs

    @staticmethod
    def parse_mt940(mt940_content: str, currency: str = "INR") -> List[BankTransaction]:
        txs: List[BankTransaction] = []
        # Regex matching tag 61: :61:YYMMDD[C|D]amount[N]...
        pattern_61 = re.compile(r":61:(\d{6})([CD])([0-9,.]+)(?:[A-Z0-9]+)?(?:\n:86:([^\n]+))?")
        matches = pattern_61.findall(mt940_content)

        for i, m in enumerate(matches):
            raw_date, cd_mark, raw_amt, narrative = m
            # YYMMDD -> 20YY-MM-DD
            dt = datetime.strptime(f"20{raw_date}", "%Y%m%d").strftime("%Y-%m-%d")
            amt = float(raw_amt.replace(",", "."))
            if cd_mark == "D":
                amt = -amt
            txs.append(BankTransaction(
                transaction_id=f"tx_mt940_{i+1}",
                date=dt,
                amount=amt,
                currency=currency,
                payee_or_narrative=narrative.strip() if narrative else "MT940 Statement Entry",
                reference=None
            ))
        return txs

    @staticmethod
    def parse_camt053(xml_content: str) -> List[BankTransaction]:
        txs: List[BankTransaction] = []
        # Strip namespaces for simple parsing
        xml_clean = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
        root = ET.fromstring(xml_clean)

        for i, ntry in enumerate(root.findall(".//Ntry")):
            amt_elem = ntry.find("Amt")
            amt = float(amt_elem.text) if amt_elem is not None and amt_elem.text else 0.0
            currency = amt_elem.attrib.get("Ccy", "INR") if amt_elem is not None else "INR"

            # Check credit/debit indicator
            cdt_dbt = ntry.find("CdtDbtInd")
            if cdt_dbt is not None and cdt_dbt.text == "DBIT":
                amt = -amt

            date_elem = ntry.find(".//BookgDt/Dt")
            date_str = date_elem.text if date_elem is not None and date_elem.text else datetime.now().strftime("%Y-%m-%d")

            narrative_elem = ntry.find(".//AddtlNtryInf")
            narrative = narrative_elem.text if narrative_elem is not None and narrative_elem.text else "CAMT.053 Entry"

            ref_elem = ntry.find(".//AcctSvcrRef")
            ref = ref_elem.text if ref_elem is not None and ref_elem.text else None

            txs.append(BankTransaction(
                transaction_id=f"tx_camt_{i+1}",
                date=date_str.strip(),
                amount=amt,
                currency=currency,
                payee_or_narrative=narrative.strip(),
                reference=ref
            ))
        return txs


class BankReconciliationMatcher:
    """Matches bank transactions to ledger entries via Exact and Fuzzy logic."""

    def __init__(self, date_window_days: int = 3, min_similarity: float = 0.85):
        self.date_window_days = date_window_days
        self.min_similarity = min_similarity

    def _similarity(self, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1.lower().strip(), s2.lower().strip()).ratio()

    def reconcile(self, bank_txs: List[BankTransaction], ledger_entries: List[LedgerTransaction]) -> BankRecResult:
        matches: List[ReconciliationMatch] = []
        matched_ledger_ids = set()
        matched_bank_tx_ids = set()

        # Phase 1: Exact Match (Amount + Date + Reference)
        for b_tx in bank_txs:
            for l_tx in ledger_entries:
                if l_tx.entry_id in matched_ledger_ids:
                    continue
                if (
                    b_tx.amount == l_tx.amount and
                    b_tx.currency == l_tx.currency and
                    b_tx.date == l_tx.date and
                    b_tx.reference and l_tx.reference and
                    b_tx.reference == l_tx.reference
                ):
                    matches.append(ReconciliationMatch(
                        bank_tx_id=b_tx.transaction_id,
                        ledger_entry_id=l_tx.entry_id,
                        match_type="EXACT",
                        confidence=1.0,
                        details={"rule": "Exact amount, date and reference"}
                    ))
                    matched_bank_tx_ids.add(b_tx.transaction_id)
                    matched_ledger_ids.add(l_tx.entry_id)
                    break

        # Phase 2: Fuzzy Match (Amount identical + Date within +/- window + Payee similarity >= threshold)
        for b_tx in bank_txs:
            if b_tx.transaction_id in matched_bank_tx_ids:
                continue
            b_dt = datetime.strptime(b_tx.date, "%Y-%m-%d")

            for l_tx in ledger_entries:
                if l_tx.entry_id in matched_ledger_ids:
                    continue
                if b_tx.amount == l_tx.amount and b_tx.currency == l_tx.currency:
                    l_dt = datetime.strptime(l_tx.date, "%Y-%m-%d")
                    day_diff = abs((b_dt - l_dt).days)
                    if day_diff <= self.date_window_days:
                        sim = self._similarity(b_tx.payee_or_narrative, l_tx.payee)
                        if sim >= self.min_similarity:
                            matches.append(ReconciliationMatch(
                                bank_tx_id=b_tx.transaction_id,
                                ledger_entry_id=l_tx.entry_id,
                                match_type="FUZZY",
                                confidence=round(sim, 3),
                                details={"rule": f"Date window {day_diff}d, payee similarity {sim:.2f}"}
                            ))
                            matched_bank_tx_ids.add(b_tx.transaction_id)
                            matched_ledger_ids.add(l_tx.entry_id)
                            break

        unmatched_bank = [b for b in bank_txs if b.transaction_id not in matched_bank_tx_ids]
        unmatched_ledger = [l for l in ledger_entries if l.entry_id not in matched_ledger_ids]

        rate = (len(matches) / len(bank_txs)) if bank_txs else 1.0
        return BankRecResult(
            total_bank_transactions=len(bank_txs),
            matched_count=len(matches),
            unmatched_bank_txs=unmatched_bank,
            unmatched_ledger_entries=unmatched_ledger,
            matches=matches,
            match_rate=round(rate, 4)
        )
