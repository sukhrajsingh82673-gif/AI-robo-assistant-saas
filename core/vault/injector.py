"""
ZONATA Credential Injector (OpenCode Step 3D)
Performs late-binding placeholder substitution inside execution engines (browser/host).
Applies Rule 24 zero-plaintext masking post-injection.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple, Any

from .vault import OriginBoundSecretVault
from .types import OriginMismatchError, HighPrivilegeApprovalRequiredError

logger = logging.getLogger("zonata.vault.injector")

# Regular expression matching credential placeholders
PLACEHOLDER_REGEX = re.compile(r"\{\{(?:CREDENTIAL|SECRET):([a-zA-Z0-9_\-\.]+)\}\}")


class CredentialInjector:
    """
    Substitutes symbolic placeholders with plaintext credentials at the exact moment of injection.
    """

    def __init__(self, vault: Optional[OriginBoundSecretVault] = None):
        self.vault = vault or OriginBoundSecretVault()

    def substitute_placeholders(
        self,
        command_or_script: str,
        target_url: str,
        tenant_id: str,
        company_id: str,
        actor_id: str = "agent_executor",
        actor_role: str = "WORKER",
        is_human_approved: bool = False,
    ) -> Tuple[str, List[str]]:
        """
        Scans string for {{CREDENTIAL:name}} or {{SECRET:name}}.
        Injects credentials if target_url matches registered origin.
        Returns:
            (injected_string, list_of_injected_secrets_to_mask)
        """
        matches = PLACEHOLDER_REGEX.findall(command_or_script)
        if not matches:
            return (command_or_script, [])

        injected_str = command_or_script
        secrets_to_mask: List[str] = []

        for name in matches:
            # Query vault for secret bound to target_url
            username, secret_val = self.vault.inject_credential(
                tenant_id=tenant_id,
                company_id=company_id,
                name=name,
                target_url=target_url,
                actor_id=actor_id,
                actor_role=actor_role,
                is_human_approved=is_human_approved,
            )

            # Substitute placeholder with real secret
            placeholder_1 = f"{{{{CREDENTIAL:{name}}}}}"
            placeholder_2 = f"{{{{SECRET:{name}}}}}"
            injected_str = injected_str.replace(placeholder_1, secret_val)
            injected_str = injected_str.replace(placeholder_2, secret_val)

            secrets_to_mask.append(secret_val)
            if username:
                secrets_to_mask.append(username)

        return (injected_str, secrets_to_mask)

    @classmethod
    def mask_secrets(cls, text: str, secrets_to_mask: List[str]) -> str:
        """
        Masks all known secret strings from text, DOM dumps, or logs with [MASKED_INPUT].
        """
        if not text or not secrets_to_mask:
            return text

        masked_text = text
        for s in secrets_to_mask:
            if s and len(s) >= 3:
                masked_text = masked_text.replace(s, "[MASKED_INPUT]")

        return masked_text
