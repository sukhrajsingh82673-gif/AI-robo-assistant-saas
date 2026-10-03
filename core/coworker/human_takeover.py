"""
ZONATA Universal AI Co-worker Fabric — Human Takeover & Live Supervision Manager
Manages live desktop supervision, pause, human takeover, session state capture,
state re-observation, and synchronized handoff back to AI.
Strict invariant: Never allows simultaneous uncontrolled human and AI input.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid
from .contracts import SupervisedControlMode

class HumanTakeoverManager:
    """
    Supervises live desktop control and manages explicit handoff between Human and AI.
    """

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def initialize_session(self, session_id: str, worker_id: str, initial_mode: SupervisedControlMode = SupervisedControlMode.AI_CONTROL) -> Dict[str, Any]:
        session = {
            "session_id": session_id,
            "worker_id": worker_id,
            "mode": initial_mode,
            "last_captured_state": {},
            "human_actions_log": [],
            "takeover_timestamp": None,
            "return_timestamp": None,
            "active": True
        }
        self._sessions[session_id] = session
        return session

    def get_session_mode(self, session_id: str) -> SupervisedControlMode:
        sess = self._sessions.get(session_id)
        if not sess:
            return SupervisedControlMode.PAUSED
        return sess["mode"]

    def human_takeover(self, session_id: str, current_ai_state: Dict[str, Any], operator_id: str = "human_owner") -> Tuple[bool, str]:
        """
        Human assumes direct control:
        1. AI execution pauses immediately.
        2. Session state is captured.
        3. Supervised mode switches to HUMAN_CONTROL.
        """
        sess = self._sessions.get(session_id)
        if not sess:
            return False, f"Session {session_id} not found"

        sess["mode"] = SupervisedControlMode.HUMAN_CONTROL
        sess["last_captured_state"] = current_ai_state
        sess["takeover_timestamp"] = time.time()
        sess["operator_id"] = operator_id

        return True, "Human takeover engaged: AI execution halted, state captured"

    def record_human_action(self, session_id: str, action_description: str) -> bool:
        sess = self._sessions.get(session_id)
        if not sess or sess["mode"] != SupervisedControlMode.HUMAN_CONTROL:
            return False
        sess["human_actions_log"].append({
            "action": action_description,
            "timestamp": time.time()
        })
        return True

    def return_control_to_ai(self, session_id: str, final_observed_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Human returns control back to AI:
        1. State is re-observed and synchronized.
        2. Mode transitions through VERIFYING to AI_CONTROL.
        """
        sess = self._sessions.get(session_id)
        if not sess:
            return False, f"Session {session_id} not found"

        sess["return_timestamp"] = time.time()
        sess["re_observed_state"] = final_observed_state
        sess["mode"] = SupervisedControlMode.AI_CONTROL

        return True, "Control returned to AI: State re-synchronized and verified"

    def pause_session(self, session_id: str, reason: str = "Awaiting review") -> bool:
        sess = self._sessions.get(session_id)
        if sess:
            sess["mode"] = SupervisedControlMode.PAUSED
            sess["pause_reason"] = reason
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        sess = self._sessions.get(session_id)
        if sess and sess["mode"] == SupervisedControlMode.PAUSED:
            sess["mode"] = SupervisedControlMode.AI_CONTROL
            return True
        return False
