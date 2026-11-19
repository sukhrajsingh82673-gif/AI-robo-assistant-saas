"""Enterprise operating skills + multi-judge decision arena regressions."""

import json

import pytest

from core.db import db
from core.evidence_ledger import EvidenceLedger
from core.operating_skills import OperatingSkillRegistry
from core.skill_arena import SkillArena, role_to_authority


REQUIRED_SKILLS = {
    "task-planning",
    "issue-triage",
    "board-reporting",
    "code-review-gate",
    "incident-recovery",
    "verified-delivery",
    "scope-discipline",
    "finance-control",
    "risk-adjudication",
    "workforce-delegation",
    "incident-reporting",
    "infrastructure-readiness",
}


@pytest.fixture()
def arena():
    return SkillArena("tnt_primary", "comp_primary", ledger=EvidenceLedger())


def _requester(role="OWNER", user_id="usr_test"):
    return {"user_id": user_id, "role": role, "departments": ["Operations"]}


def _strong_option(option_id="opt_a", title="Evidence-backed option"):
    return {
        "id": option_id,
        "title": title,
        "description": "Backed by retained evidence and reversible.",
        "risk_level": "LOW",
        "reversibility": "REVERSIBLE",
        "estimated_cost_usd": 100.0,
        "evidence_refs": ["EV-1", "EV-2"],
        "confidence": 0.9,
        "policy_compliant": True,
    }


def _weak_option(option_id="opt_b", title="Speculative option"):
    return {
        "id": option_id,
        "title": title,
        "description": "No evidence and costly to reverse.",
        "risk_level": "MEDIUM",
        "reversibility": "PARTIAL",
        "estimated_cost_usd": 5000.0,
        "evidence_refs": [],
        "confidence": 0.4,
        "policy_compliant": True,
    }


class TestOperatingSkillContracts:
    def test_catalog_exposes_executable_contracts(self):
        catalog = {s["id"]: s for s in OperatingSkillRegistry.list_skills()}
        assert REQUIRED_SKILLS.issubset(catalog)
        for skill_id in REQUIRED_SKILLS:
            skill = catalog[skill_id]
            assert skill["authority_floor"] in ("EMPLOYEE", "OPERATOR", "MANAGER", "EXECUTIVE", "OWNER")
            assert skill["risk_class"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            assert isinstance(skill["checks"], list) and skill["checks"]

    def test_role_mapping_is_conservative(self):
        assert role_to_authority("OBSERVER") == "EMPLOYEE"
        assert role_to_authority("MANAGER") == "MANAGER"
        assert role_to_authority("EXECUTIVE") == "EXECUTIVE"
        assert role_to_authority("GLOBAL_ADMIN") == "OWNER"
        assert role_to_authority("unknown-role") == "EMPLOYEE"

    def test_employee_cannot_execute_executive_skill(self, arena):
        result = arena.run_skill(
            "board-reporting",
            {"topic": "Q4 capital allocation"},
            _requester(role="OPERATOR", user_id="usr_employee"),
        )
        assert result["success"] is True
        assert result["status"] == "ESCALATED"
        assert result["authority"]["required"] == "EXECUTIVE"
        assert result["authority"]["granted"] is False
        assert result["evidence"]["evidence_id"].startswith("EV-")

    def test_evidence_contract_fails_without_evidence(self, arena):
        result = arena.run_skill(
            "verified-delivery",
            {"claim": "Migration finished successfully"},
            _requester(role="OPERATOR"),
        )
        assert result["status"] == "CONTRACT_FAILED"
        assert result["success"] is False
        checks = {c["check"]: c for c in result["checks"]}
        assert checks["evidence_reference_present"]["passed"] is False

    def test_skill_run_satisfied_and_persisted(self, arena):
        result = arena.run_skill(
            "verified-delivery",
            {
                "claim": "Expense workflow posted to GL",
                "evidence_refs": ["EV-547A66A5"],
            },
            _requester(role="OPERATOR"),
        )
        assert result["status"] == "SATISFIED"
        assert result["success"] is True
        runs = arena.list_skill_runs()
        assert any(r["run_id"] == result["run_id"] for r in runs)


class TestDecisionArena:
    def test_skill_runs_are_company_scoped(self, arena):
        result = arena.run_skill(
            "verified-delivery",
            {"claim": "Scoped run", "evidence_refs": ["EV-SCOPED"]},
            _requester(role="OPERATOR"),
        )
        runs = arena.list_skill_runs()
        assert any(r["run_id"] == result["run_id"] for r in runs)
        assert runs[0]["run_id"] == result["run_id"]
        assert runs[0]["company_id"] == "comp_primary"

        other_company = SkillArena("tnt_primary", "comp_other", ledger=EvidenceLedger())
        assert other_company.list_skill_runs() == []
        other_tenant = SkillArena("tnt_other", "comp_primary", ledger=EvidenceLedger())
        assert other_tenant.list_skill_runs() == []

    def test_consensus_decision_is_deterministic_and_sealed(self, arena):
        result = arena.evaluate(
            {
                "question": "Which vendor should we pilot?",
                "risk_level": "LOW",
                "options": [_strong_option(), _weak_option()],
            },
            _requester(),
        )
        assert result["status"] == "DECIDED"
        assert result["consensus"]["outcome"] == "CONSENSUS"
        assert result["winner"]["option_id"] == "opt_a"
        assert result["authority"]["granted"] is True
        assert result["approval_id"] is None
        assert len(result["judges"]) == 4
        assert result["evidence"]["evidence_id"].startswith("EV-")

        stored = arena.get_decision(result["decision_id"])
        assert stored is not None
        assert stored["winner_option_id"] == "opt_a"
        assert stored["status"] == "DECIDED"

    def test_single_option_is_rejected(self, arena):
        with pytest.raises(ValueError):
            arena.evaluate(
                {"question": "Approve this?", "options": [_strong_option()]},
                _requester(),
            )

    def test_missing_evidence_needs_evidence_instead_of_guessing(self, arena):
        result = arena.evaluate(
            {
                "question": "Which market should we enter?",
                "options": [
                    {"id": "a", "title": "Market A", "evidence_refs": [], "confidence": 0.1},
                    {"id": "b", "title": "Market B", "evidence_refs": [], "confidence": 0.1},
                ],
            },
            _requester(),
        )
        assert result["consensus"]["outcome"] == "INSUFFICIENT_EVIDENCE"
        assert result["status"] == "NEEDS_EVIDENCE"
        assert result["approval_id"] is None

    def test_high_risk_escalates_and_creates_approval(self, arena):
        result = arena.evaluate(
            {
                "question": "Should we acquire the supplier?",
                "risk_level": "HIGH",
                "options": [
                    _strong_option("buy", "Acquire supplier"),
                    _strong_option("build", "Build in-house"),
                ],
            },
            _requester(role="MANAGER", user_id="usr_manager"),
        )
        assert result["status"] == "ESCALATED"
        assert result["authority"]["required"] == "EXECUTIVE"
        assert result["authority"]["granted"] is False
        assert result["approval_id"] is not None

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT status, company_id, risk_level FROM approvals WHERE request_id = ?",
                (result["approval_id"],),
            ).fetchone()
        assert row is not None
        assert row["status"] == "PENDING"
        assert row["company_id"] == "comp_primary"
        assert row["risk_level"] == "HIGH"

    def test_restricted_data_is_denied_by_policy(self, arena):
        result = arena.evaluate(
            {
                "question": "Expose restricted customer records?",
                "data_classification": "HIGHLY_RESTRICTED",
                "options": [_strong_option(), _weak_option()],
            },
            _requester(role="OPERATOR", user_id="usr_employee"),
        )
        assert result["policy"]["decision"] == "DENY"
        assert result["status"] == "DENIED"
        assert result["approval_id"] is None

    def test_budget_overrun_is_denied(self, arena):
        result = arena.evaluate(
            {
                "question": "Spend beyond the employee budget?",
                "requested_spend_usd": 5000,
                "remaining_budget_usd": 100,
                "options": [_strong_option(), _weak_option()],
            },
            _requester(role="OPERATOR", user_id="usr_employee"),
        )
        assert result["policy"]["decision"] == "DENY"
        assert result["status"] == "DENIED"

    def test_decisions_are_company_scoped(self, arena):
        result = arena.evaluate(
            {
                "question": "Which support tier?",
                "options": [_strong_option(), _weak_option()],
            },
            _requester(),
        )
        other_company = SkillArena("tnt_primary", "comp_other", ledger=EvidenceLedger())
        assert other_company.get_decision(result["decision_id"]) is None
        assert other_company.list_decisions() == []

    def test_judge_scores_are_reproducible(self, arena):
        request = {
            "question": "Which plan?",
            "options": [_strong_option(), _weak_option()],
        }
        first = arena.evaluate(request, _requester())
        second = arena.evaluate(request, _requester())
        assert first["aggregate_scores"] == second["aggregate_scores"]
        assert first["winner"]["option_id"] == second["winner"]["option_id"]
        assert first["consensus"]["outcome"] == second["consensus"]["outcome"]
