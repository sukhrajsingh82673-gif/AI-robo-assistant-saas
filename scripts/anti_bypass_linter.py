#!/usr/bin/env python3
"""
ZONATA Sovereign Core — Anti-Bypass Rule 34 Linter.

Audits repository source code ensuring no framework reaches models, tools,
or OS commands except through ZONATA ports (LLMGateway, ToolRegistry, TerminalPort).
Fails with exit code 1 if violations are discovered.
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.security.anti_bypass import scan_repository_anti_bypass, scan_python_code


def main() -> int:
    parser = argparse.ArgumentParser(description="ZONATA Rule 34 Anti-Bypass AST Linter")
    parser.add_argument("--scan-path", default=REPO_ROOT, help="Root path to audit")
    parser.add_argument("--verbose", action="store_true", help="Verbose log output")
    args = parser.parse_args()

    print("=" * 70)
    print("ZONATA Rule 34 Audit — Port Egress & Framework Anti-Bypass Linter")
    print(f"Scanning directory: {args.scan_path}")
    print("=" * 70)

    violations = scan_repository_anti_bypass(args.scan_path)

    if not violations:
        print("[PASS] Zero Rule 34 port bypass violations found across all frameworks.")
        print("=" * 70)
        return 0

    print(f"\n[FAIL] Found {len(violations)} Rule 34 anti-bypass violation(s):\n")
    for v in violations:
        loc = f"{v.file_path}:{v.line_number}" if v.line_number else v.file_path
        print(f"  - [{v.violation_type}] {loc}")
        print(f"    Symbol: {v.offending_symbol}")
        print(f"    Reason: {v.description}\n")

    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
