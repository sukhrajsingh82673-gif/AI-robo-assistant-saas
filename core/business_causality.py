"""
RoboAssistant Company OS 2.0 — Business Causality & Outcome Attribution Engine
Traces the lineage from Strategy -> Mission -> Task -> Action -> Event -> Transaction ->
Revenue -> Cost -> Contribution -> Verified Business Outcome.
Invariant: TASK_SUCCESS != BUSINESS_OUTCOME.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
from .db import db

class OutcomeStatus:
    PENDING_EVIDENCE = "PENDING_EVIDENCE"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    FAILED_HYPOTHESIS = "FAILED_HYPOTHESIS"
    UNPROVEN = "UNPROVEN"

class BusinessCausalityEngine:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"

    def _ensure_scope(self) -> None:
        """Guarantee the FK targets (tenant, company) exist before attribution.

        The chain rows reference tenants/companies; a runtime that is asked to
        attribute an outcome to a scope must not fail on a missing parent row.
        Existing rows are never modified.
        """
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at)
                VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)
                """,
                (self.tenant_id, f"Tenant {self.tenant_id}", time.time()),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO companies (
                    company_id, tenant_id, name, country, industry,
                    company_type, status, created_at
                ) VALUES (?, ?, ?, 'IN', 'TECHNOLOGY', 'EXISTING', 'OPERATIONAL', ?)
                """,
                (self.company_id, self.tenant_id, f"Company {self.company_id}", time.time()),
            )
            conn.commit()

    def record_causal_link(
        self,
        strategy_goal: str,
        mission_id: str,
        task_id: str,
        action_id: str,
        transaction_id: Optional[str] = None,
        revenue_attributed: float = 0.0,
        cost_attributed: float = 0.0,
        verified_outcome: str = OutcomeStatus.PENDING_EVIDENCE
    ) -> str:
        """
        Records an explicit causal chain.
        """
        chain_id = f"csl_{uuid.uuid4().hex[:8]}"
        now = time.time()
        self._ensure_scope()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO business_causality_chains (
                    chain_id, tenant_id, company_id, strategy_goal, mission_id,
                    task_id, action_id, transaction_id, revenue_attributed,
                    cost_attributed, verified_outcome, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chain_id, self.tenant_id, self.company_id, strategy_goal,
                    mission_id, task_id, action_id, transaction_id,
                    revenue_attributed, cost_attributed, verified_outcome, now
                )
            )
            conn.commit()

        return chain_id

    def verify_outcome_with_transaction(
        self,
        chain_id: str,
        verified_transaction_id: str,
        verified_revenue: float
    ) -> Dict[str, Any]:
        """
        Elevates a causal link from PENDING_EVIDENCE to VERIFIED_SUCCESS
        only when hard transaction evidence is presented.
        """
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM business_causality_chains WHERE chain_id = ?",
                (chain_id,)
            ).fetchone()

            if not row:
                return {"success": False, "error": f"Causal chain '{chain_id}' not found"}

            net_contribution = verified_revenue - row["cost_attributed"]
            status = OutcomeStatus.VERIFIED_SUCCESS if net_contribution >= 0 else OutcomeStatus.FAILED_HYPOTHESIS

            conn.execute(
                """
                UPDATE business_causality_chains SET
                    transaction_id = ?,
                    revenue_attributed = ?,
                    verified_outcome = ?
                WHERE chain_id = ?
                """,
                (verified_transaction_id, verified_revenue, status, chain_id)
            )
            conn.commit()

        return {
            "success": True,
            "chain_id": chain_id,
            "verified_outcome": status,
            "revenue": verified_revenue,
            "cost": row["cost_attributed"],
            "net_contribution": net_contribution,
            "business_impact_verified": True
        }

    def get_causality_summary(self, mission_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Provides evidence-backed outcome attribution.
        Distinguishes between mere task completion and actual business outcome.
        """
        with db.get_connection() as conn:
            if mission_id:
                rows = conn.execute(
                    "SELECT * FROM business_causality_chains WHERE mission_id = ?",
                    (mission_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM business_causality_chains WHERE company_id = ?",
                    (self.company_id,)
                ).fetchall()

            chains = [dict(r) for r in rows]

        total_rev = sum(c["revenue_attributed"] for c in chains if c["verified_outcome"] == OutcomeStatus.VERIFIED_SUCCESS)
        total_cost = sum(c["cost_attributed"] for c in chains)
        verified_count = sum(1 for c in chains if c["verified_outcome"] == OutcomeStatus.VERIFIED_SUCCESS)
        pending_count = sum(1 for c in chains if c["verified_outcome"] == OutcomeStatus.PENDING_EVIDENCE)

        return {
            "company_id": self.company_id,
            "total_chains_tracked": len(chains),
            "verified_outcomes_count": verified_count,
            "pending_evidence_count": pending_count,
            "verified_attributed_revenue": total_rev,
            "total_incurred_cost": total_cost,
            "net_verified_contribution": total_rev - total_cost,
            "invariant_respected": "TASK_SUCCESS != BUSINESS_OUTCOME (Zero revenue credited without verified transaction)"
        }
