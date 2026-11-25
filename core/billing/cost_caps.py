"""
AI Spend Safeguards and Cost Caps (Rule 78).
Prevents runaway spend, alerts at soft cap (80%), and halts discretionary workflows at hard cap (100%).
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class SpendAlert:
    tenant_id: str
    level: str  # SOFT_CAP, HARD_CAP
    current_spend_cents: int
    cap_cents: int
    message: str


class CostCapManager:
    """
    Tracks tenant spend in minor integer cents and enforces cost caps.
    """

    def __init__(self):
        # tenant_id -> (soft_cap_cents, hard_cap_cents, current_spend_cents, auto_halt_active)
        self._caps: Dict[str, Dict[str, Any]] = {}

    def set_caps(
        self,
        tenant_id: str,
        hard_cap_cents: int,
        soft_cap_cents: Optional[int] = None,
        auto_halt_active: bool = True,
    ):
        if hard_cap_cents <= 0:
            raise ValueError("Hard cap must be strictly greater than 0 cents")
        effective_soft = soft_cap_cents if soft_cap_cents is not None else int(hard_cap_cents * 0.8)

        if effective_soft > hard_cap_cents:
            raise ValueError("Soft cap cannot exceed hard cap")

        self._caps[tenant_id] = {
            "hard_cap_cents": hard_cap_cents,
            "soft_cap_cents": effective_soft,
            "current_spend_cents": 0,
            "auto_halt_active": auto_halt_active,
            "soft_alert_fired": False,
            "hard_alert_fired": False,
        }

    def record_spend(self, tenant_id: str, amount_cents: int) -> Optional[SpendAlert]:
        """
        Records incremental spend in cents. Returns SpendAlert if a cap threshold was crossed.
        """
        if amount_cents < 0:
            raise ValueError("Spend amount cannot be negative")

        cap_info = self._caps.get(tenant_id)
        if not cap_info:
            return None

        cap_info["current_spend_cents"] += amount_cents
        spend = cap_info["current_spend_cents"]
        hard = cap_info["hard_cap_cents"]
        soft = cap_info["soft_cap_cents"]

        if spend >= hard and not cap_info["hard_alert_fired"]:
            cap_info["hard_alert_fired"] = True
            return SpendAlert(
                tenant_id=tenant_id,
                level="HARD_CAP",
                current_spend_cents=spend,
                cap_cents=hard,
                message=f"Hard cap reached: spend {spend} cents exceeds cap {hard} cents. Discretionary workflows halted.",
            )
        elif spend >= soft and not cap_info["soft_alert_fired"]:
            cap_info["soft_alert_fired"] = True
            return SpendAlert(
                tenant_id=tenant_id,
                level="SOFT_CAP",
                current_spend_cents=spend,
                cap_cents=soft,
                message=f"Soft cap reached: spend {spend} cents has crossed 80% threshold of {soft} cents.",
            )

        return None

    def is_spend_allowed(self, tenant_id: str, estimated_cents: int = 0) -> Tuple[bool, str]:
        """
        Verifies if an operation with estimated_cents is permitted under active hard cap.
        """
        cap_info = self._caps.get(tenant_id)
        if not cap_info:
            return True, "No caps configured."

        if not cap_info["auto_halt_active"]:
            return True, "Auto-halt disabled."

        projected = cap_info["current_spend_cents"] + estimated_cents
        if projected > cap_info["hard_cap_cents"]:
            return False, f"Projected spend {projected} cents exceeds hard cap {cap_info['hard_cap_cents']} cents."

        return True, "Spend approved."

    def reset_period(self, tenant_id: str):
        if tenant_id in self._caps:
            self._caps[tenant_id]["current_spend_cents"] = 0
            self._caps[tenant_id]["soft_alert_fired"] = False
            self._caps[tenant_id]["hard_alert_fired"] = False
