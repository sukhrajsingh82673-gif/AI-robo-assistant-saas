"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Security Gateway
Enforces 12-tier risk classification, PolicyEngine / ApprovalEngine barriers,
Vault credential scrubbing, prompt injection neutralization, and data loss prevention.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import os
import time
import logging
from enum import Enum

from .models import TerminalCommandRisk, IsolationLevel, NetworkMode

logger = logging.getLogger("zonata.terminal.security")

class TerminalSecurityGateway:
    """
    Sovereign security gateway for the Universal Terminal.
    Subordinate to ZONATA Sovereign Authority. Cannot be modified or bypassed by terminal agents.
    """

    FORBIDDEN_COMMAND_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        ":(){ :|:& };:", # Fork bomb
        "mkfs",
        "dd if=/dev/zero",
        "> /dev/sda",
        "chmod -R 777 /",
        "chown -R",
        "curl -s http://* | bash",
        "curl -s https://* | bash",
        "wget -O- * | bash"
    ]

    SECRET_PATTERNS = [
        re.compile(r'(?i)(api[_-]?key|secret|token|password|auth[_-]?token)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?'),
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        re.compile(r'github_pat_[a-zA-Z0-9_]{82}'),
        re.compile(r'sk-[a-zA-Z0-9]{32,}'),
        re.compile(r'Bearer\s+[a-zA-Z0-9\-_\.]{20,}'),
        re.compile(r'(?i)(postgres(ql)?|mysql|mongodb(\+srv)?|redis)://[^\s:@/]+:[^\s@/]+@'),
        re.compile(r'(?i)\b(DATABASE_URL|DIRECT_URL|API_KEY|ACCESS_KEY|PRIVATE_KEY|CLIENT_SECRET)\b\s*=\s*\S+'),
    ]


    # Credential-bearing paths that a general-purpose agent must never read or copy.
    SENSITIVE_PATH_PATTERNS = [
        re.compile(r'(^|[\s/\'"=:(])\.env(\.[\w.-]+)?\b'),
        re.compile(r'(?i)(^|[\s/])id_(rsa|dsa|ecdsa|ed25519)\b'),
        re.compile(r'(?i)\.(pem|p12|pfx|key)\b'),
        re.compile(r'(?i)\.git-credentials\b'),
        re.compile(r'(?i)\.netrc\b'),
        re.compile(r'(?i)\.aws/credentials\b'),
        re.compile(r'(?i)\.npmrc\b'),
        re.compile(r'(?i)(credentials|secrets?|service[_-]account)[\w.-]*\.json\b'),
        re.compile(r'(?i)enterprise_settings\.json\b'),
        re.compile(r'(?i)/etc/(shadow|gshadow|sudoers)\b'),
        re.compile(r'(?i)vault[_-]?token\b'),
    ]

    SENSITIVE_PATH_MESSAGE = (
        "Credential access blocked: the command references a secret-bearing path. "
        "Secrets are never exposed to agents or terminals; use the credential broker instead."
    )

    @classmethod
    def check_sensitive_paths(cls, command: str) -> Tuple[bool, Optional[str]]:
        for pat in cls.SENSITIVE_PATH_PATTERNS:
            if pat.search(command):
                return False, cls.SENSITIVE_PATH_MESSAGE
        return True, None

    # Prompt injection patterns in external command output / untrusted README data
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r'(?i)ignore\s+(all\s+)?previous\s+instructions'),
        re.compile(r'(?i)disregard\s+(all\s+)?prior\s+instructions'),
        re.compile(r'(?i)system\s*:\s*you\s+are\s+now'),
        re.compile(r'(?i)new\s+system\s+directive'),
        re.compile(r'(?i)you\s+must\s+execute\s+this\s+command\s+as\s+root'),
        re.compile(r'(?i)bypass\s+governance'),
        re.compile(r'(?i)override\s+policy')
    ]

    @classmethod
    def classify_risk(cls, command: str, capability: str = "terminal.run_command") -> TerminalCommandRisk:
        """12-Tier granular risk classification."""
        cmd_l = command.strip().lower()

        if any(w in cmd_l for w in ["stripe", "paypal", "payout", "transfer_funds", "bank", "charge_card"]):
            return TerminalCommandRisk.FINANCIAL_ACTION

        if any(w in cmd_l for w in ["production.db", "production.env", "drop table", "drop database", "alter table"]):
            return TerminalCommandRisk.PRODUCTION_MUTATION

        if any(w in cmd_l for w in ["/etc/", "/boot/", "/sys/", "iptables", "sysctl", "chmod 777", "visudo"]):
            return TerminalCommandRisk.SYSTEM_MUTATION

        if any(w in cmd_l.split() for w in ["rm", "unlink", "shred"]) or "rm -" in cmd_l or "rmdir" in cmd_l:
            return TerminalCommandRisk.DATA_DELETION

        if any(w in cmd_l.split() for w in ["useradd", "usermod", "userdel", "passwd", "groupadd"]):
            return TerminalCommandRisk.ACCOUNT_OPERATION

        if any(w in cmd_l for w in [".env", "id_rsa", "id_ed25519", "/etc/shadow", "/etc/passwd", "credentials.json", "vault"]):
            return TerminalCommandRisk.CREDENTIAL_ACCESS

        if any(w in cmd_l for w in ["pip install", "npm install", "apt install", "apt-get install", "yarn add", "cargo install"]):
            return TerminalCommandRisk.PACKAGE_INSTALL

        if any(w in cmd_l.split() for w in ["kill", "pkill", "killall", "systemctl", "service", "nohup"]):
            return TerminalCommandRisk.PROCESS_CONTROL

        if any(w in cmd_l for w in ["mail", "sendmail", "slack.com/api", "discord.com/api/webhooks"]):
            return TerminalCommandRisk.EXTERNAL_COMMUNICATION

        if any(w in cmd_l.split() for w in ["curl", "wget", "ssh", "scp", "nc", "netcat", "ping", "nmap"]):
            return TerminalCommandRisk.NETWORK_ACCESS

        if any(w in cmd_l.split() for w in ["touch", "mkdir", "cp", "mv", "sed", "tee"]) or ">" in cmd_l or ">>" in cmd_l:
            return TerminalCommandRisk.LOCAL_MUTATION

        if any(w in cmd_l.split() for w in ["ls", "cat", "grep", "find", "head", "tail", "pwd", "uname", "whoami", "echo", "wc", "git"]):
            return TerminalCommandRisk.READ_ONLY

        return TerminalCommandRisk.LOCAL_MUTATION

    @classmethod
    def check_forbidden(cls, command: str) -> Tuple[bool, Optional[str]]:
        sensitive_ok, sensitive_err = cls.check_sensitive_paths(command)
        if not sensitive_ok:
            return False, sensitive_err
        norm = " ".join(command.lower().split())
        for pat in cls.FORBIDDEN_COMMAND_PATTERNS:
            pat_norm = " ".join(pat.lower().split())
            if "*" in pat_norm:
                regex_pat = "^.*" + re.escape(pat_norm).replace(r"\*", ".*") + ".*$"
                if re.match(regex_pat, norm):
                    return False, f"Forbidden dangerous pattern detected: '{pat}'"
            elif pat_norm in norm:
                return False, f"Forbidden dangerous pattern detected: '{pat}'"
        return True, None

    @classmethod
    def sanitize_untrusted_output(cls, text: str) -> Tuple[str, bool]:
        """
        Scans command output / downloaded data for prompt injection payloads.
        Treats output as untrusted DATA and neutralizes instructions.
        """
        detected_injection = False
        sanitized = text
        for pat in cls.PROMPT_INJECTION_PATTERNS:
            if pat.search(sanitized):
                detected_injection = True
                sanitized = pat.sub("[PROMPT_INJECTION_ATTEMPT_NEUTRALIZED]", sanitized)
        return sanitized, detected_injection

    @classmethod
    def scrub_credentials(cls, text: str) -> str:
        """Redacts all credentials, tokens, and keys from commands, logs, and outputs."""
        scrubbed = text
        for pat in cls.SECRET_PATTERNS:
            scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
        return scrubbed

    @classmethod
    def verify_workspace_boundary(cls, target_path: str, allowed_workspace: str) -> Tuple[bool, str]:
        """Prevents path traversal attacks outside the permitted workspace root."""
        norm_target = os.path.abspath(target_path)
        norm_ws = os.path.abspath(allowed_workspace)
        norm_tmp = os.path.abspath("/tmp")

        is_allowed = norm_target.startswith(norm_ws) or norm_target.startswith(norm_tmp)
        return is_allowed, norm_target

    @classmethod
    def check_authorization(
        cls,
        risk_level: TerminalCommandRisk,
        human_approved: bool = False,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary"
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates whether an operation requires explicit human or policy approval.
        Consequential mutations cannot execute autonomously without authorization.
        """
        approval_required_tiers = {
            TerminalCommandRisk.DATA_DELETION,
            TerminalCommandRisk.PACKAGE_INSTALL,
            TerminalCommandRisk.SYSTEM_MUTATION,
            TerminalCommandRisk.PRODUCTION_MUTATION,
            TerminalCommandRisk.FINANCIAL_ACTION,
            TerminalCommandRisk.CREDENTIAL_ACCESS
        }

        if risk_level in approval_required_tiers and not human_approved:
            return False, f"Operation classified as high-consequence {risk_level.value}. Explicit human authorization required."
        return True, None
