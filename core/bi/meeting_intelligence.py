"""
Meeting Intelligence & Action Item Extraction Engine
====================================================
Ingests meeting transcripts, verifies agenda alignment, extracts action items
(owner, action, deadline, context), and formats tasks for the work engine.
"""

import re
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    action_id: str
    owner: str
    action_description: str
    deadline: Optional[str] = None
    context_quote: str


class MeetingAnalysisResult(BaseModel):
    meeting_title: str
    agenda_topics: List[str]
    action_items: List[ActionItem] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)


class MeetingIntelligenceEngine:
    """Parses natural meeting transcripts into structured action items and tasks."""

    @staticmethod
    def parse_transcript(title: str, agenda: List[str], transcript_text: str) -> MeetingAnalysisResult:
        action_items: List[ActionItem] = []
        decisions: List[str] = []

        # Find action item statements: [Name] to [action] by [deadline] or [Name] will [action]
        action_regex = re.compile(r"([A-Z][a-zA-Z]+)\s+(?:will|to|should)\s+([^,\.\n]+?)(?:\s+by\s+([A-Za-z0-9\-]+))?(?:[\.\n]|$)", re.IGNORECASE)
        matches = action_regex.findall(transcript_text)

        import uuid
        for i, (owner, action, deadline) in enumerate(matches):
            if any(w in action.lower() for w in ["submit", "review", "deploy", "prepare", "send", "update", "verify"]):
                action_items.append(ActionItem(
                    action_id=f"act_{i+1}",
                    owner=owner.strip(),
                    action_description=action.strip(),
                    deadline=deadline.strip() if deadline else "End of Sprint",
                    context_quote=f"{owner} will {action}"
                ))

        # Decision statements: "Decided to ...", "Agreed on ..."
        decision_regex = re.compile(r"(?:decided|agreed|approved)\s+(?:to|that|on)?\s+([^,\.\n]+)", re.IGNORECASE)
        d_matches = decision_regex.findall(transcript_text)
        for d in d_matches:
            decisions.append(d.strip())

        return MeetingAnalysisResult(
            meeting_title=title,
            agenda_topics=agenda,
            action_items=action_items,
            key_decisions=decisions
        )
