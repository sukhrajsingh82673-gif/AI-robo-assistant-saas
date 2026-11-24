"""
Bounded Negotiation Engine
===========================
Executes structured price negotiations adhering to strict mathematical boundaries:
- Initial starting price
- Maximum concession limit (e.g. 15% discount)
- Concession step schedule (e.g. 5% per counter-offer round)
- Fallback floor price (absolute non-negotiable floor)
"""

from typing import Optional, Tuple
from pydantic import BaseModel, Field


class NegotiationState(BaseModel):
    deal_id: str
    list_price: float
    floor_price: float  # Absolute minimum price allowed
    max_concession_pct: float = Field(0.15, le=0.50)
    concession_step_pct: float = Field(0.05, gt=0.0)
    current_round: int = 0
    current_offered_price: float
    is_concluded: bool = False
    outcome: Optional[str] = None  # 'ACCEPTED', 'WALK_AWAY', 'IN_PROGRESS'


class BoundedNegotiationEngine:
    """Manages multi-round deal negotiations within governed concession bounds."""

    def initialize_negotiation(self, deal_id: str, list_price: float, floor_price: float, max_concession_pct: float = 0.15, step_pct: float = 0.05) -> NegotiationState:
        if floor_price > list_price:
            raise ValueError("Floor price cannot exceed list price")
        return NegotiationState(
            deal_id=deal_id,
            list_price=list_price,
            floor_price=floor_price,
            max_concession_pct=max_concession_pct,
            concession_step_pct=step_pct,
            current_round=0,
            current_offered_price=list_price,
            outcome="IN_PROGRESS"
        )

    def evaluate_counter_offer(self, state: NegotiationState, buyer_counter_offer: float) -> Tuple[NegotiationState, str]:
        """Evaluates a buyer's counter-offer and returns (updated_state, response_message)."""
        if state.is_concluded:
            return state, f"Negotiation already concluded with outcome: {state.outcome}"

        state.current_round += 1

        # 1. Buyer accepts current offer or offers above current offer
        if buyer_counter_offer >= state.current_offered_price:
            state.is_concluded = True
            state.outcome = "ACCEPTED"
            state.current_offered_price = buyer_counter_offer
            return state, f"Accepted buyer offer of {buyer_counter_offer:.2f}"

        # 2. Buyer counter is acceptable (above floor and within max concession)
        max_allowed_concession_amount = state.list_price * state.max_concession_pct
        calculated_floor = max(state.floor_price, state.list_price - max_allowed_concession_amount)

        if buyer_counter_offer >= calculated_floor:
            # Check if we accept or make a next bounded concession step
            next_step_price = state.list_price * (1.0 - (state.current_round * state.concession_step_pct))
            counter_proposal = max(calculated_floor, next_step_price)

            if buyer_counter_offer >= counter_proposal:
                state.is_concluded = True
                state.outcome = "ACCEPTED"
                state.current_offered_price = buyer_counter_offer
                return state, f"Deal accepted at buyer offer of {buyer_counter_offer:.2f}"
            else:
                state.current_offered_price = counter_proposal
                return state, f"Counter-offering with revised price: {counter_proposal:.2f}"

        # 3. Buyer counter is below acceptable floor: make final counter at floor, or walk away if final round
        if state.current_round >= 3 or buyer_counter_offer < (state.floor_price * 0.8):
            state.is_concluded = True
            state.outcome = "WALK_AWAY"
            return state, f"Buyer offer {buyer_counter_offer:.2f} is below our non-negotiable floor {calculated_floor:.2f}. Walking away."

        state.current_offered_price = calculated_floor
        return state, f"Cannot meet offer. Presenting our best and final floor price: {calculated_floor:.2f}"
