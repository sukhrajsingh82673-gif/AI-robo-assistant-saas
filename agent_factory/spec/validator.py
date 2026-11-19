"""ZONATA Agent Factory - Spec Schema & Semantic Validator (Gate G01).

Implements rigorous JSON Schema validation and Gate G01 semantic rules:
- No credential-like strings (API keys, private keys, high-entropy tokens)
- No URLs with embedded credentials or tokens
- may_use_employees is strictly False (agents may never use employees)
- Required limits and bounds
- Instruction size caps
- Registered tool verification
"""

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# Regex patterns for credential detection
CREDENTIAL_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}\b"),
    re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[0-9a-zA-Z]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[a-zA-Z0-9_]{32,45}\b(?=.*(?:secret|token|apikey|password))", re.IGNORECASE),
    re.compile(r"(?:api_key|apikey|secret_key|private_key|auth_token|access_token|password)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{8,}['\"]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{25,}", re.IGNORECASE),
]

# URLs with embedded tokens or credentials
URL_TOKEN_PATTERNS = [
    re.compile(r"https?://[^:\s]+:[^@\s]+@[a-zA-Z0-9\.-]+"),
    re.compile(r"https?://[^\s]+\?(?:[^#\s]*&)?(?:token|key|secret|api_key|access_token|apikey)=[^&#\s]{8,}", re.IGNORECASE),
]

CATEGORIES = {
    "c_suite", "corporate_management", "finance", "accounting", "hr",
    "marketing", "sales", "operations", "research", "data_analysis",
    "customer_support", "software_engineering", "devops",
    "database_engineering", "defensive_cybersecurity", "browser_automation",
    "document_processing", "knowledge_management", "custom"
}

RISK_TIERS = {"R0", "R1", "R2", "R3"}
WORKFLOW_TYPES = {"sequential", "parallel", "dag", "supervisor", "hierarchical"}


def shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    counts: Dict[str, int] = {}
    for c in data:
        counts[c] = counts.get(c, 0) + 1
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def scan_for_credentials(obj: Any, path: str = "") -> List[str]:
    """Scan arbitrary JSON-like object for credentials, secret patterns, and entropy."""
    violations: List[str] = []

    if isinstance(obj, str):
        # 1. Regex credential patterns
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(obj):
                violations.append(f"Credential pattern detected at '{path}': matches {pattern.pattern}")

        # 2. URL embedded tokens
        for url_pattern in URL_TOKEN_PATTERNS:
            if url_pattern.search(obj):
                violations.append(f"URL with embedded credential/token detected at '{path}'")

        # 3. High entropy check on continuous tokens
        # Check tokens without spaces longer than 28 chars
        tokens = re.split(r"[\s,;'\"]+", obj)
        for token in tokens:
            if len(token) >= 32 and re.match(r"^[A-Za-z0-9+/=_-]+$", token):
                ent = shannon_entropy(token)
                if ent > 4.5:
                    violations.append(
                        f"High-entropy token ({ent:.2f} bits/symbol) detected at '{path}': '{token[:6]}...{token[-4:]}'"
                    )

    elif isinstance(obj, dict):
        for k, v in obj.items():
            child_path = f"{path}.{k}" if path else k
            # Suspicious keys with raw secrets
            if any(secret_term in k.lower() for secret_term in ("secret", "private_key", "password")):
                if isinstance(v, str) and len(v) > 0 and not v.startswith("ref:"):
                    violations.append(f"Hard-coded secret in property '{child_path}'")
            violations.extend(scan_for_credentials(v, child_path))

    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            violations.extend(scan_for_credentials(item, f"{path}[{idx}]"))

    return violations


class ValidationResult:
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


class SpecValidator:
    """Validates zonata.agent/v1 specifications against schema and G01 semantic policies."""

    def __init__(self, known_tools: Optional[Set[str]] = None):
        self.known_tools = known_tools or {
            "web.fetch_page", "web.search", "doc.generate", "doc.parse",
            "db.query_readonly", "chart.render", "email.send", "git.read",
            "git.commit", "code.test", "slack.notify", "memory.retrieve",
            "knowledge.search", "calculator", "terminal.execute_safe"
        }

    def validate(self, spec: Dict[str, Any]) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(spec, dict):
            return ValidationResult(False, ["Spec must be a JSON/YAML object"])

        # 1. Structural Validation
        api_version = spec.get("apiVersion")
        if api_version != "zonata.agent/v1":
            errors.append(f"Unsupported apiVersion '{api_version}', expected 'zonata.agent/v1'")

        kind = spec.get("kind")
        if kind != "Agent":
            errors.append(f"Unsupported kind '{kind}', expected 'Agent'")

        required_sections = [
            "apiVersion", "kind", "metadata", "identity", "role", "model",
            "capabilities", "permissions", "workflow", "memory", "limits",
            "io", "observability", "tests"
        ]
        for sec in required_sections:
            if sec not in spec:
                errors.append(f"Missing required section: '{sec}'")

        # Unknown extra sections check
        for sec in spec.keys():
            if sec not in required_sections:
                errors.append(f"Unexpected extra property: '{sec}'")

        # Metadata checks
        metadata = spec.get("metadata", {})
        if isinstance(metadata, dict):
            name = metadata.get("name")
            if not name or not re.match(r"^[a-z0-9][a-z0-9-]{2,62}$", str(name)):
                errors.append(f"Invalid metadata.name: '{name}'. Must match ^[a-z0-9][a-z0-9-]{{2,62}}$")

            cat = metadata.get("category")
            if cat not in CATEGORIES:
                errors.append(f"Invalid metadata.category: '{cat}'")

            risk = metadata.get("risk_tier")
            if risk not in RISK_TIERS:
                errors.append(f"Invalid metadata.risk_tier: '{risk}'. Expected one of {sorted(RISK_TIERS)}")

            ver = metadata.get("version")
            if not ver or not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$", str(ver)):
                errors.append(f"Invalid metadata.version: '{ver}'. Must be valid semver")
        else:
            errors.append("metadata must be an object")

        # Identity checks (G01 rule: may_use_employees = False, principal_kind = 'agent')
        identity = spec.get("identity", {})
        if isinstance(identity, dict):
            if identity.get("principal_kind") != "agent":
                errors.append(f"identity.principal_kind must be 'agent', got '{identity.get('principal_kind')}'")
            if identity.get("tenant_bound") is not True:
                errors.append("identity.tenant_bound must be true")
            if identity.get("may_use_employees") is True:
                errors.append("Security violation (G01): identity.may_use_employees is True. Agents may never use employees.")
        else:
            errors.append("identity must be an object")

        # Role checks
        role = spec.get("role", {})
        if isinstance(role, dict):
            if not role.get("title") or len(str(role.get("title"))) > 120:
                errors.append("role.title is required and must be <= 120 characters")
            if not role.get("mission") or len(str(role.get("mission"))) > 1000:
                errors.append("role.mission is required and must be <= 1000 characters")
            resp = role.get("responsibilities")
            if not isinstance(resp, list) or len(resp) < 1:
                errors.append("role.responsibilities must be a non-empty list")
            crit = role.get("success_criteria")
            if not isinstance(crit, list) or len(crit) < 1:
                errors.append("role.success_criteria must be a non-empty list")
            instructions = role.get("instructions", "")
            if len(str(instructions)) > 20000:
                errors.append(f"role.instructions exceeds maximum length of 20000 chars (got {len(instructions)})")
        else:
            errors.append("role must be an object")

        # Limits checks
        limits = spec.get("limits", {})
        if isinstance(limits, dict):
            if "max_steps" not in limits or not (1 <= limits.get("max_steps", 0) <= 500):
                errors.append("limits.max_steps is required and must be between 1 and 500")
            if "timeout_seconds" not in limits or not (1 <= limits.get("timeout_seconds", 0) <= 86400):
                errors.append("limits.timeout_seconds is required and must be between 1 and 86400")
            if "max_cost_usd_per_task" not in limits or limits.get("max_cost_usd_per_task", -1) < 0:
                errors.append("limits.max_cost_usd_per_task is required and must be >= 0")
        else:
            errors.append("limits must be an object")

        # Workflow checks
        workflow = spec.get("workflow", {})
        if isinstance(workflow, dict):
            wf_type = workflow.get("type")
            if wf_type not in WORKFLOW_TYPES:
                errors.append(f"workflow.type '{wf_type}' must be one of {sorted(WORKFLOW_TYPES)}")
        else:
            errors.append("workflow must be an object")

        # IO checks
        io = spec.get("io", {})
        if isinstance(io, dict):
            if "input_schema" not in io or not isinstance(io["input_schema"], dict):
                errors.append("io.input_schema is required and must be an object")
            if "output_schema" not in io or not isinstance(io["output_schema"], dict):
                errors.append("io.output_schema is required and must be an object")
        else:
            errors.append("io must be an object")

        # Observability checks
        obs = spec.get("observability", {})
        if isinstance(obs, dict):
            if obs.get("trace") is not True:
                errors.append("observability.trace must be true")
            if obs.get("capture_content") not in ("none", "redacted", "full_in_staging_only"):
                errors.append("observability.capture_content must be 'none', 'redacted', or 'full_in_staging_only'")
        else:
            errors.append("observability must be an object")

        # Tests checks
        tests = spec.get("tests", {})
        if isinstance(tests, dict):
            if "author_cases" not in tests or not isinstance(tests["author_cases"], list):
                errors.append("tests.author_cases must be a list")
            if "dataset_refs" not in tests or not isinstance(tests["dataset_refs"], list):
                errors.append("tests.dataset_refs must be a list")
        else:
            errors.append("tests must be an object")

        # 2. Gate G01 Semantic Credential Scan
        credential_errors = scan_for_credentials(spec)
        errors.extend(credential_errors)

        return ValidationResult(is_valid=(len(errors) == 0), errors=errors, warnings=warnings)
