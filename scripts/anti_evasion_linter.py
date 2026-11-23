#!/usr/bin/env python3
"""
ZONATA Sovereign Core — Anti-Evasion & Anti-Captcha Rule 25 Linter.

Audits repository dependencies and source code for banned stealth plugins,
automated CAPTCHA solving libraries, and fingerprint spoofing patterns.
Fails with exit code 1 if violations are discovered.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.security.anti_evasion import scan_repository_anti_evasion


def main() -> int:
    print("=" * 70)
    print("ZONATA Rule 25 Audit — Anti-Evasion & Anti-Captcha Dependency Check")
    print(f"Scanning repository root: {REPO_ROOT}")
    print("=" * 70)

    violations = scan_repository_anti_evasion(REPO_ROOT)

    if not violations:
        print("[PASS] Zero Rule 25 anti-evasion or captcha solver violations found.")
        print("=" * 70)
        return 0

    print(f"\n[FAIL] Found {len(violations)} Rule 25 anti-evasion violation(s):\n")
    for v in violations:
        loc = f"{v.file_path}:{v.line_number}" if v.line_number else v.file_path
        print(f"  - [{v.violation_type}] {loc}")
        print(f"    Symbol: {v.offending_symbol}")
        print(f"    Reason: {v.description}\n")

    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
