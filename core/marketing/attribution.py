"""
First-Party Multi-Touch Attribution Engine
==========================================
Calculates marketing campaign attribution without third-party cookies:
- First-Touch Attribution
- Last-Touch Attribution
- Linear Attribution
- Time-Decay Attribution
- U-Shaped (Position-Based) Attribution: 40% First, 40% Last, 20% Middle
"""

import math
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Touchpoint(BaseModel):
    touchpoint_id: str
    user_id: str
    campaign_id: str
    channel: str
    timestamp: str  # ISO-8601


class AttributionResult(BaseModel):
    model_name: str
    total_conversion_value: float
    campaign_credits: Dict[str, float]  # campaign_id -> attributed value


class MultiTouchAttributionEngine:
    """Computes deterministic revenue attribution across customer touchpoints."""

    @staticmethod
    def _parse_time(ts: str) -> datetime:
        return datetime.fromisoformat(ts)

    def calculate_attribution(
        self,
        touchpoints: List[Touchpoint],
        conversion_value: float,
        model: str = "LINEAR",
        half_life_days: float = 7.0
    ) -> AttributionResult:
        if not touchpoints:
            return AttributionResult(model_name=model, total_conversion_value=conversion_value, campaign_credits={})

        # Sort touchpoints chronologically
        sorted_touch = sorted(touchpoints, key=lambda t: self._parse_time(t.timestamp))
        credits: Dict[str, float] = {}

        n = len(sorted_touch)
        model = model.upper()

        if model == "FIRST_TOUCH":
            c_id = sorted_touch[0].campaign_id
            credits[c_id] = round(conversion_value, 2)

        elif model == "LAST_TOUCH":
            c_id = sorted_touch[-1].campaign_id
            credits[c_id] = round(conversion_value, 2)

        elif model == "LINEAR":
            share = conversion_value / float(n)
            for t in sorted_touch:
                credits[t.campaign_id] = round(credits.get(t.campaign_id, 0.0) + share, 2)

        elif model == "U_SHAPED":
            if n == 1:
                credits[sorted_touch[0].campaign_id] = round(conversion_value, 2)
            elif n == 2:
                half = conversion_value / 2.0
                credits[sorted_touch[0].campaign_id] = round(credits.get(sorted_touch[0].campaign_id, 0.0) + half, 2)
                credits[sorted_touch[1].campaign_id] = round(credits.get(sorted_touch[1].campaign_id, 0.0) + half, 2)
            else:
                first_share = conversion_value * 0.40
                last_share = conversion_value * 0.40
                middle_total = conversion_value * 0.20
                middle_each = middle_total / float(n - 2)

                # First
                c_first = sorted_touch[0].campaign_id
                credits[c_first] = round(credits.get(c_first, 0.0) + first_share, 2)

                # Middle
                for t in sorted_touch[1:-1]:
                    credits[t.campaign_id] = round(credits.get(t.campaign_id, 0.0) + middle_each, 2)

                # Last
                c_last = sorted_touch[-1].campaign_id
                credits[c_last] = round(credits.get(c_last, 0.0) + last_share, 2)

        elif model == "TIME_DECAY":
            # Weights = 2^(-delta_days / half_life)
            conv_time = self._parse_time(sorted_touch[-1].timestamp)
            weights = []
            for t in sorted_touch:
                delta_days = max(0.0, (conv_time - self._parse_time(t.timestamp)).total_seconds() / 86400.0)
                w = math.pow(2.0, -delta_days / half_life_days)
                weights.append(w)

            total_weight = sum(weights)
            for i, t in enumerate(sorted_touch):
                frac = (weights[i] / total_weight) if total_weight > 0 else (1.0 / n)
                val = round(conversion_value * frac, 2)
                credits[t.campaign_id] = round(credits.get(t.campaign_id, 0.0) + val, 2)

        else:
            raise ValueError(f"Unsupported attribution model: {model}")

        return AttributionResult(
            model_name=model,
            total_conversion_value=conversion_value,
            campaign_credits=credits
        )
