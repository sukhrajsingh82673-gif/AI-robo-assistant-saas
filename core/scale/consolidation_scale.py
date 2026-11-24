"""
50-Entity Multi-National Group Consolidation Scale Benchmark (Rule 67, 73, ADR 0043)
Evaluates ConsolidationEngine scalability across 50 international corporate subsidiaries,
10 functional currencies, and 500 paired intercompany transactions.
Verifies sub-500ms execution SLA and zero net elimination drift.
"""

from typing import Dict, Any, List, Tuple
import time
from decimal import Decimal
from core.consolidation.engine import (
    ConsolidationEngine,
    LegalEntity,
    IntercompanyTransaction,
    ConsolidationMethod,
)

CURRENCIES = ["EUR", "USD", "GBP", "INR", "JPY", "CHF", "SGD", "AUD", "CAD", "BRL"]

# Reference FX rates to presentation currency (EUR)
FX_SPOT_RATES = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.17,
    "INR": 0.011,
    "JPY": 0.0062,
    "CHF": 1.06,
    "SGD": 0.69,
    "AUD": 0.61,
    "CAD": 0.68,
    "BRL": 0.16,
}

FX_AVG_RATES = {
    "EUR": 1.0,
    "USD": 0.91,
    "GBP": 1.16,
    "INR": 0.011,
    "JPY": 0.0061,
    "CHF": 1.05,
    "SGD": 0.68,
    "AUD": 0.60,
    "CAD": 0.67,
    "BRL": 0.15,
}


class ConsolidationScaleBenchmark:
    """Benchmarks multi-company consolidation at global enterprise scale."""

    @classmethod
    def run_50_entity_scale_test(cls) -> Dict[str, Any]:
        """Runs 50-entity, 10-currency, 500-transaction group consolidation."""
        t_start = time.perf_counter()

        # 1. Instantiate 50 legal entities
        entities = []
        parent_id = "ENT-000"
        parent = LegalEntity(
            company_id=parent_id,
            legal_name="Zonata Global Parent Holding SE",
            jurisdiction_code="DE",
            functional_currency="EUR",
            ownership_percentage=100.0,
        )
        entities.append(parent)

        for i in range(1, 50):
            cid = f"ENT-{i:03d}"
            curr = CURRENCIES[i % len(CURRENCIES)]
            entities.append(
                LegalEntity(
                    company_id=cid,
                    legal_name=f"Zonata Global Subsidiary {i} Corp",
                    jurisdiction_code="US" if curr == "USD" else ("IN" if curr == "INR" else "DE"),
                    functional_currency=curr,
                    ownership_percentage=100.0,
                )
            )

        engine = ConsolidationEngine(
            group_id="GRP-SCALE-50",
            group_name="Zonata Scale Test Enterprise Group",
            presentation_currency="EUR",
            parent_company_id=parent_id,
            entities=entities,
        )

        # 2. Populate account balances for each entity
        entity_balances = {}
        account_types = {
            "1000_CASH": "ASSET",
            "1100_INTERCOMPANY_AR": "ASSET",
            "2100_INTERCOMPANY_AP": "LIABILITY",
            "3000_COMMON_STOCK": "EQUITY",
            "4000_REVENUE": "REVENUE",
            "5000_EXPENSES": "EXPENSE",
        }

        for ent in entities:
            entity_balances[ent.company_id] = {
                "1000_CASH": 5000000,
                "1100_INTERCOMPANY_AR": 1000000,
                "2100_INTERCOMPANY_AP": 1000000,
                "3000_COMMON_STOCK": 4000000,
                "4000_REVENUE": 2000000,
                "5000_EXPENSES": 1000000,
            }

        # 3. Generate 500 intercompany transactions
        ic_txs = []
        for j in range(500):
            from_idx = j % 50
            to_idx = (j + 1) % 50
            from_ent = entities[from_idx]
            to_ent = entities[to_idx]

            ic_txs.append(
                IntercompanyTransaction(
                    transaction_id=f"IC-TX-{j:04d}",
                    from_company_id=from_ent.company_id,
                    to_company_id=to_ent.company_id,
                    amount_minor=50000 + (j * 100),
                    currency="EUR",  # Settled in group presentation currency
                    transaction_type="MANAGEMENT_FEE",
                    matched_reference=f"REF-MGMT-{j}",
                )
            )

        # 4. Measure Translation
        t_trans_start = time.perf_counter()
        translated = engine.translate_balances(entity_balances, account_types, FX_SPOT_RATES, FX_AVG_RATES)
        t_trans_ms = (time.perf_counter() - t_trans_start) * 1000.0

        # 5. Measure Eliminations
        t_elim_start = time.perf_counter()
        elim_journals, net_balance = engine.compute_intercompany_eliminations(ic_txs, FX_SPOT_RATES)
        t_elim_ms = (time.perf_counter() - t_elim_start) * 1000.0

        # 6. Measure Financials Generation
        t_fin_start = time.perf_counter()
        consolidated = engine.generate_consolidated_financials(translated, elim_journals)
        t_fin_ms = (time.perf_counter() - t_fin_start) * 1000.0

        total_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "entities_count": len(entities),
            "currencies_count": len(set(e.functional_currency for e in entities)),
            "intercompany_txs_count": len(ic_txs),
            "elimination_entries_count": len(elim_journals),
            "net_elimination_balance": net_balance,  # MUST BE EXACTLY 0
            "translation_latency_ms": round(t_trans_ms, 2),
            "elimination_latency_ms": round(t_elim_ms, 2),
            "financials_latency_ms": round(t_fin_ms, 2),
            "total_latency_ms": round(total_elapsed_ms, 2),
            "sub_500ms_sla_passed": total_elapsed_ms < 500.0,
            "consolidation_seal": consolidated["consolidation_seal"],
        }
