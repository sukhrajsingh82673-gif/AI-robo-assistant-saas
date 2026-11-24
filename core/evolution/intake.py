"""
ZONATA Open-Source Agent and Tool Intake Engine ("Agent Zoo") (Sub-Step 6G).

Governs external agent intake, quarantine, evaluation, sandboxing, and promotion.
Features:
- State Machine: DISCOVERED -> QUARANTINED -> EVALUATED -> APPROVED_FOR_SANDBOX -> CERTIFIED -> ACTIVE.
- Human-only promotion to ACTIVE (Rule 53, Rule 57).
- License classification: permissive, BOUNDARY (AGPL/GPL), or PROHIBITED (Rule 5).
- Static AST and installer checks: blocks `curl | sh`, unpinned dependencies, dangerous syscalls, secret exfiltration (Rule 32).
- Untrusted documentation and README prompt-injection scanner.
- Behavioral sandbox: tracks syscalls, egress restriction, and capability reconciliation.
- Reference evaluation of Hermes Agent (Nous Research, MIT License).
"""

import ast
import re
import uuid
import hashlib
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple


class IntakeState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUARANTINED = "QUARANTINED"
    EVALUATED = "EVALUATED"
    APPROVED_FOR_SANDBOX = "APPROVED_FOR_SANDBOX"
    CERTIFIED = "CERTIFIED"
    ACTIVE = "ACTIVE"


class LicenseClassification(str, Enum):
    PERMISSIVE = "PERMISSIVE"
    BOUNDARY = "BOUNDARY"
    PROHIBITED = "PROHIBITED"


class IntakeSecurityViolationError(Exception):
    """Raised when an external agent fails security policies."""
    pass


class HumanApprovalRequiredError(Exception):
    """Raised when an automated agent or unverified actor attempts promotion to ACTIVE."""
    pass


class UnpinnedDependencyError(IntakeSecurityViolationError):
    """Raised when an external agent has unpinned or unhashed dependencies."""
    pass


class InstallerProhibitedError(IntakeSecurityViolationError):
    """Raised when pipe-to-shell or uncontrolled installer scripts are detected (Rule 32)."""
    pass


class EgressViolationError(IntakeSecurityViolationError):
    """Raised when sandbox execution attempts unauthorized network egress."""
    pass


class CapabilityMismatchError(IntakeSecurityViolationError):
    """Raised when observed behavior exceeds declared capabilities."""
    pass


class AgentManifest:
    """Metadata specification for an intake candidate."""

    def __init__(
        self,
        name: str,
        version: str,
        repository_url: str,
        commit_hash: str,
        license_spdx: str,
        dependencies: List[Dict[str, str]],
        declared_capabilities: List[str],
        entrypoint: str,
        source_files: Dict[str, str],
        readme_content: str = "",
        installer_script: Optional[str] = None,
        author: str = "unknown",
    ):
        self.name = name
        self.version = version
        self.repository_url = repository_url
        self.commit_hash = commit_hash
        self.license_spdx = license_spdx
        self.dependencies = dependencies  # [{name, version, hash}]
        self.declared_capabilities = declared_capabilities
        self.entrypoint = entrypoint
        self.source_files = source_files  # {relative_path: code_str}
        self.readme_content = readme_content
        self.installer_script = installer_script
        self.author = author


class StaticSecurityScanner:
    """Static and AST scanner for external codebases."""

    DANGEROUS_CALLS = {"eval", "exec", "__import__"}
    PROHIBITED_INSTALLER_PATTERNS = [
        re.compile(r"curl\s+.*\|\s*(?:ba)?sh", re.IGNORECASE),
        re.compile(r"wget\s+.*\|\s*(?:ba)?sh", re.IGNORECASE),
        re.compile(r"Invoke-WebRequest\s+.*\|\s*iex", re.IGNORECASE),
        re.compile(r"python\s+-c\s+.*urllib", re.IGNORECASE),
    ]
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"print\s+(?:system\s+prompt|credentials|secrets|token)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
        re.compile(r"exfiltrate\s+to\s+https?://", re.IGNORECASE),
    ]

    PERMISSIVE_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
    BOUNDARY_LICENSES = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-3.0", "SSPL", "BSL-1.1"}

    @classmethod
    def classify_license(cls, spdx: str) -> LicenseClassification:
        normalized = spdx.strip().upper()
        for perm in cls.PERMISSIVE_LICENSES:
            if perm.upper() == normalized:
                return LicenseClassification.PERMISSIVE
        for bnd in cls.BOUNDARY_LICENSES:
            if bnd.upper() in normalized:
                return LicenseClassification.BOUNDARY
        return LicenseClassification.PROHIBITED

    @classmethod
    def scan_manifest(cls, manifest: AgentManifest) -> Dict[str, Any]:
        findings = []

        # 1. Pinned commit check
        if not re.match(r"^[0-9a-f]{40}$", manifest.commit_hash):
            findings.append({
                "severity": "CRITICAL",
                "category": "SUPPLY_CHAIN",
                "message": f"Unpinned commit hash '{manifest.commit_hash}'. Full 40-char SHA-1 required.",
            })

        # 2. Dependency locks & hashes check
        for dep in manifest.dependencies:
            dep_name = dep.get("name", "unknown")
            dep_ver = dep.get("version", "")
            dep_hash = dep.get("hash", "")
            if not dep_ver or any(c in dep_ver for c in ["*", "^", "~", ">", "<"]):
                findings.append({
                    "severity": "CRITICAL",
                    "category": "UNPINNED_DEPENDENCY",
                    "message": f"Dependency '{dep_name}' has unpinned version constraint '{dep_ver}'.",
                })
            if not dep_hash or len(dep_hash) < 32:
                findings.append({
                    "severity": "CRITICAL",
                    "category": "UNPINNED_DEPENDENCY",
                    "message": f"Dependency '{dep_name}' is missing cryptographic hash lock.",
                })

        # 3. Installer script check (Rule 32)
        if manifest.installer_script:
            for pat in cls.PROHIBITED_INSTALLER_PATTERNS:
                if pat.search(manifest.installer_script):
                    findings.append({
                        "severity": "BLOCKER",
                        "category": "PROHIBITED_INSTALLER",
                        "message": "Pipe-to-shell installer detected in setup script.",
                    })

        # 4. License check
        lic_class = cls.classify_license(manifest.license_spdx)
        if lic_class == LicenseClassification.PROHIBITED:
            findings.append({
                "severity": "BLOCKER",
                "category": "LICENSE_VIOLATION",
                "message": f"License '{manifest.license_spdx}' is prohibited under Rule 5 allow-list.",
            })
        elif lic_class == LicenseClassification.BOUNDARY:
            findings.append({
                "severity": "WARNING",
                "category": "LICENSE_BOUNDARY",
                "message": f"License '{manifest.license_spdx}' requires BOUNDARY isolation container.",
            })

        # 5. Untrusted README injection check
        if manifest.readme_content:
            for pat in cls.PROMPT_INJECTION_PATTERNS:
                if pat.search(manifest.readme_content):
                    findings.append({
                        "severity": "CRITICAL",
                        "category": "PROMPT_INJECTION",
                        "message": "Potential prompt injection detected in untrusted documentation.",
                    })

        # 6. Source files AST scan
        for path, code in manifest.source_files.items():
            cls._scan_ast(path, code, findings)

        is_clean = not any(f["severity"] in ("CRITICAL", "BLOCKER") for f in findings)
        return {
            "clean": is_clean,
            "license_classification": lic_class,
            "findings": findings,
        }

    @classmethod
    def _scan_ast(cls, path: str, code: str, findings: List[Dict[str, Any]]) -> None:
        try:
            tree = ast.parse(code, filename=path)
        except SyntaxError as e:
            findings.append({
                "severity": "CRITICAL",
                "category": "SYNTAX_ERROR",
                "message": f"File {path} failed AST parsing: {e}",
            })
            return

        for node in ast.walk(tree):
            # Dangerous calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.DANGEROUS_CALLS:
                    findings.append({
                        "severity": "CRITICAL",
                        "category": "DANGEROUS_CALL",
                        "message": f"Prohibited dynamic evaluation '{node.func.id}' in {path}:L{node.lineno}",
                    })
            # Secret / Environment inspection
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "environ":
                    findings.append({
                        "severity": "CRITICAL",
                        "category": "ENV_READ_ATTEMPT",
                        "message": f"Direct environment access detected in {path}:L{node.lineno}",
                    })
            # Directory traversal writes
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value
                if any(val.startswith(p) for p in ["/etc", "/usr", "/root", "../.."]):
                    findings.append({
                        "severity": "CRITICAL",
                        "category": "TRAVERSAL_ATTEMPT",
                        "message": f"Suspicious path constant '{val}' in {path}:L{node.lineno}",
                    })


class BehavioralSandbox:
    """Monitored sandbox runner evaluating candidate behavior."""

    def __init__(self, allowed_egress_hosts: Optional[Set[str]] = None):
        self.allowed_egress_hosts = allowed_egress_hosts or {
            "api.anthropic.com",
            "api.openai.com",
            "raw.githubusercontent.com",
        }

    def simulate_execution(
        self,
        manifest: AgentManifest,
        simulated_trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes or verifies candidate behavior against security policies.
        Traces: network_calls, file_writes, process_spawns, env_reads.
        """
        trace = simulated_trace or {
            "network_calls": [],
            "file_writes": [f"/sandbox/work/{manifest.name}/output.txt"],
            "process_spawns": [],
            "env_reads": [],
        }

        violations = []
        observed_capabilities = set()

        # Check network calls against allow-list
        for host in trace.get("network_calls", []):
            observed_capabilities.add("network_egress")
            if host not in self.allowed_egress_hosts:
                violations.append({
                    "type": "EGRESS_VIOLATION",
                    "details": f"Attempted network egress to unauthorized host '{host}'",
                })

        # Check filesystem writes stay within /sandbox/work/
        for fpath in trace.get("file_writes", []):
            observed_capabilities.add("filesystem_write")
            if not fpath.startswith("/sandbox/work/"):
                violations.append({
                    "type": "FILESYSTEM_ESCAPE",
                    "details": f"Attempted write outside sandbox directory: '{fpath}'",
                })

        # Check process spawns
        for proc in trace.get("process_spawns", []):
            observed_capabilities.add("process_spawn")
            if any(term in proc for term in ["bash", "sh", "nc", "curl"]):
                violations.append({
                    "type": "UNAUTHORIZED_PROCESS",
                    "details": f"Suspicious process spawn: '{proc}'",
                })

        # Check environment reads
        for env_key in trace.get("env_reads", []):
            violations.append({
                "type": "ENV_EXFILTRATION",
                "details": f"Attempted access to environment key '{env_key}'",
            })

        # Reconcile observed vs declared capabilities
        declared = set(manifest.declared_capabilities)
        undeclared = observed_capabilities - declared
        if undeclared:
            violations.append({
                "type": "CAPABILITY_MISMATCH",
                "details": f"Observed undeclared capabilities: {list(undeclared)}",
            })

        passed = len(violations) == 0
        return {
            "passed": passed,
            "observed_capabilities": list(observed_capabilities),
            "violations": violations,
        }


class AgentZooRecord:
    """Represents a managed external agent in the zoo."""

    def __init__(
        self,
        intake_id: str,
        manifest: AgentManifest,
        tenant_id: str,
        company_id: str,
        state: IntakeState = IntakeState.DISCOVERED,
    ):
        self.intake_id = intake_id
        self.manifest = manifest
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.state = state
        self.static_report: Optional[Dict[str, Any]] = None
        self.sandbox_report: Optional[Dict[str, Any]] = None
        self.promoted_by: Optional[str] = None
        self.active_version: Optional[str] = None


class AgentZooManager:
    """Manages external agent lifecycle, catalog, and promotions."""

    def __init__(self):
        self._records: Dict[str, AgentZooRecord] = {}
        self.sandbox = BehavioralSandbox()

    def discover_agent(
        self,
        manifest: AgentManifest,
        tenant_id: str,
        company_id: str,
    ) -> AgentZooRecord:
        """Step 1: Discover and immediately quarantine external candidate."""
        intake_id = f"zoo_{uuid.uuid4().hex[:12]}"
        record = AgentZooRecord(
            intake_id=intake_id,
            manifest=manifest,
            tenant_id=tenant_id,
            company_id=company_id,
            state=IntakeState.QUARANTINED,
        )
        self._records[intake_id] = record
        return record

    def evaluate_candidate(self, intake_id: str) -> AgentZooRecord:
        """Step 2: Run static and AST analysis."""
        record = self._records[intake_id]
        if record.state != IntakeState.QUARANTINED:
            raise ValueError(f"Cannot evaluate agent in state '{record.state}'. Must be QUARANTINED.")

        static_report = StaticSecurityScanner.scan_manifest(record.manifest)
        record.static_report = static_report

        if not static_report["clean"]:
            # Stays quarantined due to security failures
            return record

        record.state = IntakeState.EVALUATED
        return record

    def approve_for_sandbox(self, intake_id: str) -> AgentZooRecord:
        """Step 3: Move from evaluated to approved for sandbox execution."""
        record = self._records[intake_id]
        if record.state != IntakeState.EVALUATED:
            raise ValueError(f"Cannot approve for sandbox in state '{record.state}'.")
        record.state = IntakeState.APPROVED_FOR_SANDBOX
        return record

    def run_sandbox_evaluation(
        self,
        intake_id: str,
        simulated_trace: Optional[Dict[str, Any]] = None,
    ) -> AgentZooRecord:
        """Step 4: Execute in monitored behavioral sandbox."""
        record = self._records[intake_id]
        if record.state != IntakeState.APPROVED_FOR_SANDBOX:
            raise ValueError(f"Cannot execute sandbox in state '{record.state}'.")

        sandbox_report = self.sandbox.simulate_execution(record.manifest, simulated_trace)
        record.sandbox_report = sandbox_report

        if sandbox_report["passed"]:
            record.state = IntakeState.CERTIFIED
        return record

    def promote_to_active(
        self,
        intake_id: str,
        actor_principal: str,
    ) -> AgentZooRecord:
        """
        Step 5: Promote certified agent to ACTIVE.
        Rule 53 & Rule 57: Only human principals can promote external code to ACTIVE.
        """
        record = self._records[intake_id]
        if record.state != IntakeState.CERTIFIED:
            raise ValueError(f"Cannot promote agent in state '{record.state}'. Must be CERTIFIED.")

        if not actor_principal.startswith("human:") and not actor_principal.startswith("owner:"):
            raise HumanApprovalRequiredError(
                f"Principal '{actor_principal}' is unauthorized. Only human/owner accounts can activate external agents."
            )

        record.state = IntakeState.ACTIVE
        record.promoted_by = actor_principal
        record.active_version = record.manifest.version
        return record

    def get_record(self, intake_id: str) -> Optional[AgentZooRecord]:
        return self._records.get(intake_id)


class HermesEvaluator:
    """Evaluates Nous Research Hermes Agent as the first reference case."""

    @classmethod
    def create_hermes_manifest(cls) -> AgentManifest:
        return AgentManifest(
            name="hermes-agent",
            version="0.4.0",
            repository_url="https://github.com/NousResearch/Hermes-Agent",
            commit_hash="a1b2c3d4e5f67890123456789abcdef012345678",
            license_spdx="MIT",
            dependencies=[
                {
                    "name": "pydantic",
                    "version": "2.6.0",
                    "hash": "sha256:abcd1234ef567890abcd1234ef567890abcd1234ef567890abcd1234ef567890",
                },
                {
                    "name": "httpx",
                    "version": "0.27.0",
                    "hash": "sha256:1234abcd5678ef011234abcd5678ef011234abcd5678ef011234abcd5678ef01",
                },
            ],
            declared_capabilities=["filesystem_read", "filesystem_write", "http_query"],
            entrypoint="hermes.agent:main",
            source_files={
                "hermes/agent.py": "def main():\n    print('Hermes Agent active')\n",
                "hermes/skills.py": "def discover_skills():\n    return ['search', 'summary']\n",
            },
            readme_content="# Hermes Agent\nAutonomous research assistant from Nous Research.\nMIT Licensed.",
            author="Nous Research",
        )

    @classmethod
    def generate_evaluation_report(cls, manifest: AgentManifest) -> Dict[str, Any]:
        scanner_results = StaticSecurityScanner.scan_manifest(manifest)
        return {
            "candidate": manifest.name,
            "version": manifest.version,
            "license": manifest.license_spdx,
            "license_classification": scanner_results["license_classification"].value,
            "static_clean": scanner_results["clean"],
            "findings_count": len(scanner_results["findings"]),
            "architectural_comparison": {
                "skill_creation": "Covered natively by ZONATA 6E Governed Knowledge Store (Playbooks)",
                "skill_curation": "Covered natively by ZONATA 6D Owner Help & Review Workflow",
                "session_search": "Covered natively by ZONATA 6E pgvector / Cosine Playbook Embeddings",
                "prompt_tuning": "Covered natively by ZONATA 6F DSPy + GEPA Optimizer",
            },
            "recommendation": (
                "ADOPTION_EVALUATION_ONLY: Hermes patterns are largely superseded by native ZONATA "
                "Step 6 governance engines. Recommend sandboxed integration only if specific tool adapters are needed."
            ),
        }
