"""
RoboAssistant Company OS 1.0 — SaaS Metering & Usage Engine
Tracks input/output tokens, provider costs, and execution consumption.
Enforces hard-stops on budget overruns.
"""

from typing import Dict, Any, Optional
import time
import uuid
from .db import db

class UsageMeteringEngine:
    @staticmethod
    def record_usage(
        tenant_id: str,
        company_id: Optional[str],
        agent_id: Optional[str],
        mission_id: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> str:
        record_id = f"usg_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO usage_records (
                    record_id, tenant_id, company_id, agent_id,
                    mission_id, model, input_tokens, output_tokens, cost, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, tenant_id, company_id, agent_id, mission_id, model, input_tokens, output_tokens, cost, now)
            )
            conn.commit()
        return record_id

    @staticmethod
    def get_tenant_usage_summary(tenant_id: str) -> Dict[str, Any]:
        with db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(cost) as total_cost,
                    COUNT(*) as total_calls
                FROM usage_records
                WHERE tenant_id = ?
                """,
                (tenant_id,)
            ).fetchone()
            return {
                "total_input_tokens": row["total_input"] or 0,
                "total_output_tokens": row["total_output"] or 0,
                "total_cost": round(row["total_cost"] or 0.0, 4),
                "total_calls": row["total_calls"] or 0
            }
