"""
ZONATA Sovereign Core — Anti-Evasion & Dependency Deny-List Policy (Rule 25).

Enforces Rule 25:
"No circumvention of verification challenges. The system never solves,
bypasses or evades CAPTCHAs, bot checks, paywalls, rate limits or site blocks.
No solver services, no ML solvers, no stealth or fingerprint-spoofing plugins,
no proxy rotation to evade blocks. A challenge means: stop, hand off to a human,
or take an official route (API, export, allow-listing, the site owner's own settings).
CI enforces a dependency and code deny-list (3F)."
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Set


class AntiEvasionViolationError(Exception):
    """Raised when anti-evasion or captcha bypass code/dependency is detected."""
    pass


@dataclass(frozen=True)
class AntiEvasionViolation:
    file_path: str
    line_number: Optional[int]
    violation_type: str
    description: str
    offending_symbol: str


# Banned package names across Python (PyPI) and Node.js (npm)
BANNED_PACKAGES: Set[str] = {
    # Stealth plugins & fingerprint evasion
    "playwright-stealth",
    "puppeteer-extra-plugin-stealth",
    "undetected-chromedriver",
    "selenium-stealth",
    "curl-impersonate",
    "fake-useragent",
    "fingerprintjs-bypass",
    "puppeteer-extra",
    # Captcha solving SDKs and services
    "2captcha",
    "2captcha-python",
    "twocaptcha",
    "anticaptcha",
    "anti-captcha",
    "anticaptchaofficial",
    "deathbycaptcha",
    "capmonster",
    "capmonstercloud-client",
    "capsolver",
    "yescaptcha",
    "hcaptcha-solver",
    "recaptcha-solver",
    "recaptcha-v2-solver",
    "recaptcha-v3-solver",
    "turnstile-solver",
    "solver-captcha",
    "bypass-captcha",
}

# Banned API endpoints / URLs
BANNED_URL_PATTERNS: List[re.Pattern] = [
    re.compile(r"2captcha\.com/(in|res)\.php", re.IGNORECASE),
    re.compile(r"api\.anti-captcha\.com/(createTask|getTaskResult)", re.IGNORECASE),
    re.compile(r"api\.capmonster\.cloud/(createTask|getTaskResult)", re.IGNORECASE),
    re.compile(r"api\.capsolver\.com/(createTask|getTaskResult)", re.IGNORECASE),
]

# Banned AST code patterns (fingerprint spoofing / evasion)
BANNED_AST_SUBSTRINGS: List[str] = [
    "navigator.webdriver",
    "cdc_adoqpwpcnm",
    "--disable-blink-features=AutomationControlled",
]


class AntiEvasionASTVisitor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[AntiEvasionViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0].lower().replace("_", "-")
            if base_module in BANNED_PACKAGES or alias.name.lower() in BANNED_PACKAGES:
                self.violations.append(
                    AntiEvasionViolation(
                        file_path=self.filename,
                        line_number=node.lineno,
                        violation_type="BANNED_IMPORT",
                        description=f"Import of banned stealth/solver package '{alias.name}' is prohibited by Rule 25.",
                        offending_symbol=alias.name,
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split(".")[0].lower().replace("_", "-")
            if base_module in BANNED_PACKAGES or node.module.lower() in BANNED_PACKAGES:
                self.violations.append(
                    AntiEvasionViolation(
                        file_path=self.filename,
                        line_number=node.lineno,
                        violation_type="BANNED_IMPORT",
                        description=f"Import from banned stealth/solver package '{node.module}' is prohibited by Rule 25.",
                        offending_symbol=node.module,
                    )
                )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            val = node.value
            for pat in BANNED_URL_PATTERNS:
                if pat.search(val):
                    self.violations.append(
                        AntiEvasionViolation(
                            file_path=self.filename,
                            line_number=node.lineno,
                            violation_type="BANNED_SOLVER_ENDPOINT",
                            description=f"Hardcoded automated CAPTCHA solver endpoint detected: {val}",
                            offending_symbol=val,
                        )
                    )
            for sub in BANNED_AST_SUBSTRINGS:
                # Disallow scripts attempting to spoof webdriver or stealth flags
                if sub in val and "test" not in self.filename.lower() and "anti_evasion" not in self.filename.lower():
                    self.violations.append(
                        AntiEvasionViolation(
                            file_path=self.filename,
                            line_number=node.lineno,
                            violation_type="BANNED_STEALTH_PATTERN",
                            description=f"Stealth evasion script substring detected: {sub}",
                            offending_symbol=sub,
                        )
                    )
        self.generic_visit(node)


def scan_python_code(code: str, filename: str = "<string>") -> List[AntiEvasionViolation]:
    """Parse and AST-scan Python code for Rule 25 violations."""
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError:
        return []
    visitor = AntiEvasionASTVisitor(filename=filename)
    visitor.visit(tree)
    return visitor.violations


def scan_dependency_file(file_path: str) -> List[AntiEvasionViolation]:
    """Scan requirements.txt, pyproject.toml, or package.json for banned dependencies."""
    violations: List[AntiEvasionViolation] = []
    if not os.path.exists(file_path):
        return violations

    basename = os.path.basename(file_path)

    if basename in ("requirements.txt", "requirements-dev.txt") or basename.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                clean_line = line.strip().split("#")[0].strip()
                if not clean_line:
                    continue
                pkg_name = re.split(r"[><=~!;]", clean_line)[0].strip().lower().replace("_", "-")
                if pkg_name in BANNED_PACKAGES:
                    violations.append(
                        AntiEvasionViolation(
                            file_path=file_path,
                            line_number=idx,
                            violation_type="BANNED_DEPENDENCY",
                            description=f"Banned package '{pkg_name}' found in requirements.",
                            offending_symbol=pkg_name,
                        )
                    )

    elif basename == "pyproject.toml":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                for pkg in BANNED_PACKAGES:
                    # check for "pkg" or 'pkg'
                    pattern = rf"[\"']{re.escape(pkg)}[\"']"
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append(
                            AntiEvasionViolation(
                                file_path=file_path,
                                line_number=idx,
                                violation_type="BANNED_DEPENDENCY",
                                description=f"Banned package '{pkg}' found in pyproject.toml.",
                                offending_symbol=pkg,
                            )
                        )

    elif basename == "package.json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            deps = {}
            deps.update(data.get("dependencies", {}))
            deps.update(data.get("devDependencies", {}))
            for dep in deps:
                norm_dep = dep.lower().replace("_", "-")
                if norm_dep in BANNED_PACKAGES:
                    violations.append(
                        AntiEvasionViolation(
                            file_path=file_path,
                            line_number=None,
                            violation_type="BANNED_NPM_DEPENDENCY",
                            description=f"Banned npm package '{dep}' found in package.json.",
                            offending_symbol=dep,
                        )
                    )
        except Exception:
            pass

    return violations


def scan_repository_anti_evasion(root_dir: str) -> List[AntiEvasionViolation]:
    """Recursively scan codebase and manifests for Rule 25 violations."""
    all_violations: List[AntiEvasionViolation] = []
    exclude_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, root_dir)

            # Check dependency manifests
            if fname in ("requirements.txt", "pyproject.toml", "package.json"):
                all_violations.extend(scan_dependency_file(fpath))

            # Check Python source files (skip anti_evasion definition itself and tests checking it)
            elif fname.endswith(".py"):
                if "core/security/anti_evasion.py" in rel_path or "test_step3_anti_evasion.py" in rel_path:
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    all_violations.extend(scan_python_code(content, filename=rel_path))
                except Exception:
                    pass

    return all_violations
