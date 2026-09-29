"""
RoboAssistant Company OS — Operational Skills & SOPs Catalog
Provides deterministic, standard operating procedures (SOPs) for autonomous agents.
"""

from typing import Dict, List, Any, Optional

SKILLS_CATALOG: Dict[str, Dict[str, Any]] = {
    "task-planning": {
        "id": "task-planning",
        "name": "Autonomous Task Planning & Decomposition",
        "category": "Orchestration",
        "description": "Standard procedure for decomposing high-level company goals into unambiguous, actionable child tasks with clear acceptance criteria.",
        "author": "Enterprise Core",
        "version": "2.4.0",
        "sop_rules": [
            "Never create child tasks with descriptions that say 'see parent' — every task must be self-contained and independently executable.",
            "Identify and declare all DAG dependencies explicitly before assigning tasks to prevent execution deadlocks.",
            "Formulate specific, testable acceptance criteria for each subtask so verification can be 100% automated.",
            "If an execution path requires external capital spend or destructive mutation, insert an explicit 'pending_approval' gate."
        ],
        "applicable_roles": ["Chief Executive Officer (CEO)", "Chief Technology Officer (CTO)", "Lead Product Manager"]
    },
    "issue-triage": {
        "id": "issue-triage",
        "name": "Deterministic Issue Triage & Prioritization",
        "category": "Operations",
        "description": "Lifecycle contract for processing incoming tasks, assigning priority buckets, and ensuring single-worker task locks.",
        "author": "Enterprise Core",
        "version": "1.8.0",
        "sop_rules": [
            "Process tasks strictly in order: in_progress tasks first, then in_review, then todo.",
            "Skip 'blocked' tasks until upstream dependencies are satisfied.",
            "Always acquire an atomic lease (checkout) with run ID before commencing work; halt immediately on 409 Conflict.",
            "Update issue status incrementally with evidence deltas to preserve an immutable timeline."
        ],
        "applicable_roles": ["All Autonomous Agents"]
    },
    "board-reporting": {
        "id": "board-reporting",
        "name": "Executive Board Reporting & Approval Escalation",
        "category": "Governance",
        "description": "SOP for compiling high-signal briefings, unblocking stalled initiatives, and presenting structured proposals for owner sign-off.",
        "author": "Enterprise Core",
        "version": "2.1.0",
        "sop_rules": [
            "Synthesize outcomes into three core metrics: Capital efficiency, SLA completion rate, and verified truth delta.",
            "Present decisions in actionable multiple-choice format with clear risk/benefit analysis.",
            "Highlight budget ceilings and notify the board immediately when spending reaches 80% of threshold."
        ],
        "applicable_roles": ["Chief Executive Officer (CEO)", "Chief Operating Officer (COO)"]
    },
    "code-review-gate": {
        "id": "code-review-gate",
        "name": "Automated Code Review & Integrity Gate",
        "category": "Engineering",
        "description": "Enforces strict static verification, security scanning, and test pass requirements before accepting software changes.",
        "author": "Enterprise Core",
        "version": "3.0.0",
        "sop_rules": [
            "Verify all files match formatting and lint standards with zero warnings.",
            "Execute end-to-end regression suites and verify 100% passing results.",
            "Scan diffs for hardcoded credentials, bearer tokens, or private keys; reject immediately on detection."
        ],
        "applicable_roles": ["Chief Technology Officer (CTO)", "Senior Fullstack Engineer", "QA & Reliability Engineer"]
    },
    "incident-recovery": {
        "id": "incident-recovery",
        "name": "Autonomous Incident Recovery & Exponential Backoff",
        "category": "Resilience",
        "description": "Resilience protocol handling agent timeouts, API exhaustion (e.g. 429 errors), and state restoration.",
        "author": "Enterprise Core",
        "version": "2.2.0",
        "sop_rules": [
            "Apply exponential backoff (base * 2^failures) with randomized symmetric jitter on API rate limit encounters.",
            "On 5 consecutive unhandled failures, gracefully pause the agent and submit a diagnostic alert to the owner.",
            "Replay recent session events from checkpoint to recover intermediate progress without data loss."
        ],
        "applicable_roles": ["All Autonomous Agents", "DevOps & Platform Engineer"]
    }
}


class OperatingSkillRegistry:
    """Registry providing access to enterprise operational skills."""

    @staticmethod
    def list_skills() -> List[Dict[str, Any]]:
        return list(SKILLS_CATALOG.values())

    @staticmethod
    def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
        return SKILLS_CATALOG.get(skill_id)

# Aliases for backwards compatibility
ExecutiveSkillRegistry = OperatingSkillRegistry
SkillRegistry = OperatingSkillRegistry
