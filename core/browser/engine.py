"""
ZONATA Governed Browser Automation Engine (OpenCode Step 3E)
Coordinates:
- BrowserPort (Playwright lead + Sandbox fallback)
- Origin-Bound Credential Vault (Rule 24 late-binding injection)
- Challenge Detection & Human Handoff (Rule 25 zero solver invariant)
- Untrusted Page Content Delimiters (Rule 26)
- Download Scanning & Malware Defense (Rule 32)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.db import db
from core.ports.browser import browser_port, BrowserExecutionResult, BrowserPageSnapshot
from core.vault import OriginBoundSecretVault, CredentialInjector, OriginValidator, OriginMismatchError
from core.evidence_service import evidence_service
from .types import ChallengeType, ChallengeDetectionResult, BrowserDownloadResult
from .challenge_detector import ChallengeDetector
from .downloads import BrowserDownloadPipeline

logger = logging.getLogger("zonata.browser.engine")


class GovernedBrowserEngine:
    """
    Autonomous browser hand governed by strict safety, anti-evasion, and zero-leakage rules.
    """

    def __init__(
        self,
        vault: Optional[OriginBoundSecretVault] = None,
        injector: Optional[CredentialInjector] = None,
        download_pipeline: Optional[BrowserDownloadPipeline] = None,
        port: Optional[Any] = None,
    ):
        self.vault = vault or OriginBoundSecretVault()
        self.injector = injector or CredentialInjector(vault=self.vault)
        self.download_pipeline = download_pipeline or BrowserDownloadPipeline()
        self.port = port or browser_port
        self._current_url: str = "about:blank"
        self._current_page_snapshot: Optional[BrowserPageSnapshot] = None

    @property
    def current_url(self) -> str:
        return self._current_url

    def navigate(
        self,
        url: str,
        tenant_id: str,
        company_id: str,
        task_id: Optional[str] = None,
    ) -> BrowserExecutionResult:
        """
        Navigates to URL and enforces:
        1. Challenge detection (Cloudflare, reCAPTCHA, etc.) -> BLOCKED + human handoff.
        2. Untrusted content delimiting (Rule 26).
        3. Audit recording in Merkle evidence ledger.
        """
        provider = browser_port.resolve_provider()
        exec_res: BrowserExecutionResult = provider.navigate(url, tenant_id, company_id)

        self._current_url = url
        self._current_page_snapshot = exec_res.page_snapshot

        if not exec_res.page_snapshot:
            return exec_res

        # 1. Challenge Check (Rule 25)
        raw_html = exec_res.page_snapshot.raw_content
        challenge: ChallengeDetectionResult = ChallengeDetector.detect(raw_html, current_url=url)

        if challenge.has_challenge:
            exec_res.challenge_detected = True
            exec_res.blocked_reason = "VERIFICATION_CHALLENGE"

            # Create item in human inbox for human handoff (Rule 25)
            self._create_challenge_handoff_item(
                tenant_id=tenant_id,
                company_id=company_id,
                url=url,
                challenge_type=challenge.challenge_type.value,
                task_id=task_id,
            )

            # Record event in evidence ledger with masked widget pointer
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="BROWSER_CHALLENGE_BLOCKED_HUMAN_HANDOFF",
                payload={
                    "url": url,
                    "challenge_type": challenge.challenge_type.value,
                    "signatures": challenge.signatures_detected,
                    "status": "BLOCKED",
                    "reason": "VERIFICATION_CHALLENGE",
                    "solver_invoked": False,  # Strict Rule 25 invariant
                    "masked_widget_bounds": challenge.masked_widget_bounds,
                },
            )

        return exec_res

    def fill_credential(
        self,
        selector: str,
        placeholder_or_value: str,
        tenant_id: str,
        company_id: str,
        actor_id: str = "agent_browser",
        is_human_approved: bool = False,
    ) -> Tuple[BrowserExecutionResult, str]:
        """
        Injects a credential placeholder into the active page form.
        Refuses if the current page URL does not match the bound origin.
        """
        if not self._current_url or self._current_url == "about:blank":
            raise ValueError("Browser has no active page loaded.")

        # Substitute placeholder with origin-bound secret
        injected_value, secrets_to_mask = self.injector.substitute_placeholders(
            command_or_script=placeholder_or_value,
            target_url=self._current_url,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
            is_human_approved=is_human_approved,
        )

        provider = browser_port.resolve_provider()
        res = provider.fill(selector, injected_value)

        # Audit injection (never plaintext)
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="BROWSER_CREDENTIAL_INJECTED",
            payload={
                "selector": selector,
                "url": self._current_url,
                "placeholder": placeholder_or_value,
                "actor_id": actor_id,
            },
        )

        return res, injected_value

    def extract_page_content_delimited(self) -> str:
        """
        Rule 26: Returns page content safely wrapped in data delimiters.
        """
        if self._current_page_snapshot:
            return f"<<<PAGE_CONTENT>>>\n{self._current_page_snapshot.raw_content}\n<<<END_PAGE_CONTENT>>>"
        return "<<<PAGE_CONTENT>>>\nabout:blank\n<<<END_PAGE_CONTENT>>>"

    def download(
        self,
        filename: str,
        payload: bytes,
        tenant_id: str,
        company_id: str,
    ) -> BrowserDownloadResult:
        """
        Downloads a file and enforces ClamAV scanning and Rule 32 executable refusal.
        """
        return self.download_pipeline.process_download(
            filename=filename,
            payload=payload,
            tenant_id=tenant_id,
            company_id=company_id,
        )

    def _create_challenge_handoff_item(
        self,
        tenant_id: str,
        company_id: str,
        url: str,
        challenge_type: str,
        task_id: Optional[str] = None,
    ) -> str:
        inbox_id = f"inb_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with db.get_connection() as conn:
            # Insert into human_inbox table if exists
            try:
                conn.execute(
                    """
                    INSERT INTO human_inbox (
                        id, tenant_id, company_id, task_id, title,
                        description, priority, target_principal_type,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'HIGH', 'HUMAN', 'PENDING', ?)
                    """,
                    (
                        inbox_id, tenant_id, company_id, task_id,
                        f"Verification Challenge Encountered: {challenge_type}",
                        f"Page at '{url}' presented a {challenge_type} bot verification challenge. "
                        "Automated completion is prohibited by Rule 25. Please complete verification manually.",
                        now,
                    ),
                )
                if hasattr(conn, "commit"):
                    conn.commit()
            except Exception:
                pass
        return inbox_id
