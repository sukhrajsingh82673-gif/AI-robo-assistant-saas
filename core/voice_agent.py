"""
RoboAssistant Company OS 2.0 — Governed Voice AI Platform
Handles inbound/outbound telephony dialogue states with explicit epistemic boundaries:
CUSTOMER_SAID, SYSTEM_FACT, AI_INFERENCE, PROPOSED_RESPONSE.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
from .db import db

class VoiceUtteranceType:
    CUSTOMER_SAID = "CUSTOMER_SAID"
    SYSTEM_FACT = "SYSTEM_FACT"
    AI_INFERENCE = "AI_INFERENCE"
    PROPOSED_RESPONSE = "PROPOSED_RESPONSE"

class GovernedVoiceAgent:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"

    def initiate_call_session(
        self,
        caller_id: str,
        direction: str = "INBOUND",
        consent_given: bool = True
    ) -> Dict[str, Any]:
        session_id = f"vcall_{uuid.uuid4().hex[:8]}"
        now = time.time()
        initial_transcript = [
            {
                "type": VoiceUtteranceType.PROPOSED_RESPONSE,
                "text": "Thank you for calling. This call may be recorded for quality assurance. How can I assist you today?",
                "timestamp": now
            }
        ]

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO voice_sessions (
                    session_id, tenant_id, company_id, caller_id, direction,
                    call_state, consent_given, recording_authorized, outcome, transcript, timestamp
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?, 'IN_PROGRESS', ?, ?)
                """,
                (
                    session_id, self.tenant_id, self.company_id, caller_id, direction,
                    1 if consent_given else 0, 1 if consent_given else 0,
                    json.dumps(initial_transcript), now
                )
            )
            conn.commit()

        return {
            "session_id": session_id,
            "direction": direction,
            "caller_id": caller_id,
            "consent_given": consent_given,
            "call_state": "ACTIVE"
        }

    def process_utterance(self, session_id: str, spoken_text: str) -> Dict[str, Any]:
        """
        Processes incoming speech transcript, separates factual ground from inferences,
        and constructs compliant response.
        """
        now = time.time()
        customer_item = {
            "type": VoiceUtteranceType.CUSTOMER_SAID,
            "text": spoken_text,
            "timestamp": now
        }

        # Knowledge Grounding
        spoken_lower = spoken_text.lower()
        if "rate" in spoken_lower or "price" in spoken_lower:
            fact = "Deluxe Heritage Suites are ₹8,500/night with complimentary breakfast."
            response_text = f"Our current direct rate for the Deluxe Heritage Suite is ₹8,500 per night. Would you like me to hold this room for you?"
        elif "cancel" in spoken_lower:
            fact = "Cancellations permitted up to 48 hours before check-in with 100% refund."
            response_text = "Our policy allows full cancellation up to 48 hours prior to arrival with zero fees."
        else:
            fact = "Standard operations active."
            response_text = "I have noted that. Let me connect you directly to our reservation desk or send confirmation via WhatsApp."

        fact_item = {
            "type": VoiceUtteranceType.SYSTEM_FACT,
            "text": fact,
            "timestamp": now
        }
        agent_item = {
            "type": VoiceUtteranceType.PROPOSED_RESPONSE,
            "text": response_text,
            "timestamp": now
        }

        # Update session transcript in DB
        with db.get_connection() as conn:
            row = conn.execute("SELECT transcript FROM voice_sessions WHERE session_id = ?", (session_id,)).fetchone()
            existing_transcript = json.loads(row["transcript"]) if row and row["transcript"] else []
            existing_transcript.extend([customer_item, fact_item, agent_item])

            conn.execute(
                "UPDATE voice_sessions SET transcript = ? WHERE session_id = ?",
                (json.dumps(existing_transcript), session_id)
            )
            conn.commit()

        return {
            "session_id": session_id,
            "system_fact": fact,
            "spoken_response": response_text,
            "transcript_turn": [customer_item, fact_item, agent_item]
        }

    def complete_call(self, session_id: str, outcome: str = "COMPLETED_SATISFIED") -> bool:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE voice_sessions SET call_state = 'COMPLETED', outcome = ? WHERE session_id = ?",
                (outcome, session_id)
            )
            conn.commit()
            return True
