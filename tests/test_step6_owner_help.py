"""
Unit and Integration Tests for Antigravity Sub-Step 6D:
Owner Help Protocol (3-Step Rule, Deduplication, Rate Limiting, Step-Up Auth, Ask Once / Learn Forever).
"""

import time
import pytest
from core.evolution.owner_help import (
    OwnerHelpEngine,
    HelpTicket,
    HelpValidationError,
    StepUpAuthRequiredError,
)


class TestStep6OwnerHelpProtocol:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = OwnerHelpEngine()

    def test_01_three_step_rule_enforcement_rejects_greater_than_three(self):
        """Rule 1: Help request must provide 1 to 3 action steps; >3 is strictly rejected."""
        # >3 steps rejected
        with pytest.raises(HelpValidationError) as exc:
            self.engine.submit_help_request(
                tenant_id="t1",
                company_id="c1",
                task_id="task_1",
                question="How do I configure Stripe webhooks?",
                action_steps=[
                    "1. Log in to Stripe Dashboard",
                    "2. Navigate to Developers > Webhooks",
                    "3. Click Add endpoint",
                    "4. Enter URL https://example.com/webhook",
                ],
            )
        assert "3-Step Rule Violated" in str(exc.value)

        # 0 steps rejected
        with pytest.raises(HelpValidationError) as exc:
            self.engine.submit_help_request(
                tenant_id="t1",
                company_id="c1",
                task_id="task_2",
                question="No steps provided",
                action_steps=[],
            )
        assert "at least 1 action step" in str(exc.value)

        # 1 to 3 steps accepted
        ticket = self.engine.submit_help_request(
            tenant_id="t1",
            company_id="c1",
            task_id="task_3",
            question="Configure Stripe webhooks",
            action_steps=[
                "1. Log in to Stripe Dashboard",
                "2. Click Add endpoint and copy signing secret",
                "3. Paste secret here",
            ],
        )
        assert ticket.status == "OPEN"
        assert len(ticket.action_steps) == 3

    def test_02_duplicate_question_within_24h_returns_existing_ticket(self):
        """Rule 2: An agent may never ask the owner the same question twice in 24 hours."""
        t1 = self.engine.submit_help_request(
            tenant_id="t_dedup",
            company_id="c1",
            task_id="task_a",
            question="Where is the company tax ID stored?",
            action_steps=["1. Check IRS letter in safe", "2. Provide EIN"],
        )

        # Immediate duplicate
        t2 = self.engine.submit_help_request(
            tenant_id="t_dedup",
            company_id="c1",
            task_id="task_b",
            question="Where is the company tax ID stored?",
            action_steps=["1. Check IRS letter", "2. Provide EIN"],
        )

        assert t1.ticket_id == t2.ticket_id
        assert len(self.engine.get_open_tickets("t_dedup")) == 1

    def test_03_hourly_rate_limit_enforces_queuing_after_5_requests(self):
        """Rule 2: Max 5 requests/hour per tenant; excess queued without bothering owner."""
        tenant = "t_rate_limit"
        tickets = []
        for i in range(5):
            t = self.engine.submit_help_request(
                tenant_id=tenant,
                company_id="c1",
                task_id=f"task_{i}",
                question=f"Unique question {i} regarding fiscal compliance?",
                action_steps=["1. Review policy", "2. Approve"],
            )
            assert t.status == "OPEN"
            tickets.append(t)

        # 6th request within the hour is queued
        t6 = self.engine.submit_help_request(
            tenant_id=tenant,
            company_id="c1",
            task_id="task_5",
            question="Sixth question exceeding rate cap?",
            action_steps=["1. Review doc"],
        )
        assert t6.status == "QUEUED"
        assert len(self.engine.get_open_tickets(tenant)) == 5
        assert len(self.engine.get_queued_tickets(tenant)) == 1

    def test_04_sensitive_action_requires_step_up_token(self):
        """Rule 3: Sensitive actions require step-up cryptographic auth confirmation."""
        ticket = self.engine.submit_help_request(
            tenant_id="t_sensitive",
            company_id="c1",
            task_id="task_wire",
            question="Approve $50,000 vendor wire transfer to Acme Corp?",
            action_steps=[
                "1. Open corporate banking portal",
                "2. Confirm beneficiary IBAN matches invoice",
                "3. Authorize via hardware token",
            ],
            is_sensitive=True,
        )

        # Attempt to resolve without step-up token
        with pytest.raises(StepUpAuthRequiredError) as exc:
            self.engine.resolve_help_request(
                ticket_id=ticket.ticket_id,
                human_response="Approved, go ahead and send wire.",
            )
        assert "Sensitive action requires verified cryptographic step-up" in str(exc.value)

        # Resolve with valid step-up token
        resolved_ticket = self.engine.resolve_help_request(
            ticket_id=ticket.ticket_id,
            human_response="Approved, wire reference 998822.",
            step_up_token="stepup_d8f7a6e5b4c3a210fedcba98",
        )
        assert resolved_ticket.status == "RESOLVED"
        assert resolved_ticket.resolution is not None

    def test_05_ask_once_learn_forever_auto_resolves_future_queries(self):
        """Rule 4: Resolved request indexes into knowledge store; next query auto-resolves."""
        tenant = "t_learn"
        q = "What is our standard vendor payment terms?"

        # First request: human resolves
        t1 = self.engine.submit_help_request(
            tenant_id=tenant,
            company_id="c1",
            task_id="task_initial",
            question=q,
            action_steps=["1. Review standard master services agreement", "2. State default terms"],
        )
        self.engine.resolve_help_request(
            ticket_id=t1.ticket_id,
            human_response="Net 30 days upon invoice receipt.",
        )

        # Second request: identical question submitted by another agent
        t2 = self.engine.submit_help_request(
            tenant_id=tenant,
            company_id="c1",
            task_id="task_future",
            question=q,
            action_steps=["1. Review MSA", "2. State terms"],
        )

        assert t2.status == "RESOLVED"
        assert t2.auto_resolved is True
        assert t2.resolution == "Net 30 days upon invoice receipt."

    def test_06_mutation_check_raw_secret_in_answer_routed_to_vault(self):
        """Mutation test: human answer containing raw credentials routed to Vault, never plaintext."""
        tenant = "t_vault"
        ticket = self.engine.submit_help_request(
            tenant_id=tenant,
            company_id="c1",
            task_id="task_key",
            question="Please provide the API key for weather data feed?",
            action_steps=["1. Generate key in WeatherAPI", "2. Paste key"],
        )

        human_reply = "Here is the key: api_key=zonata_sec_mock_weather_feed_key_12345678 and password: MySecretDbPassword!"
        resolved = self.engine.resolve_help_request(
            ticket_id=ticket.ticket_id,
            human_response=human_reply,
        )

        # Verify plaintext secrets are NOT in ticket resolution
        assert "zonata_sec_mock_weather_feed_key_12345678" not in resolved.resolution
        assert "MySecretDbPassword!" not in resolved.resolution
        assert "vault://t_vault/secrets/sec_" in resolved.resolution
        assert len(resolved.vault_secret_keys) == 2

        # Verify secrets exist inside the secure vault
        for v_uri in resolved.vault_secret_keys:
            assert v_uri in self.engine.vault
            assert self.engine.vault[v_uri] in ("zonata_sec_mock_weather_feed_key_12345678", "MySecretDbPassword!")
