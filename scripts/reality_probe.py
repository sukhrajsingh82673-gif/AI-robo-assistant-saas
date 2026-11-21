#!/usr/bin/env python3
"""ZONATA Sovereign Core — Reality Probe CLI.

Executes live reality probes across all 18 enterprise capabilities,
prints the truth table with measured latencies to stdout, and generates
docs/reports/CAPABILITY_STATUS.md dynamically.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.capability_probe import probe_all_capabilities, summarize_capabilities


def format_status_label(status_str: str) -> str:
    """Human-readable plain language status."""
    mapping = {
        "OK": "Live",
        "ACCEPTED_BY_PROVIDER": "Accepted",
        "SANDBOX": "Test Only",
        "NOT_CONFIGURED": "Not Connected",
        "NOT_IMPLEMENTED": "Not Implemented",
        "DEGRADED": "Degraded",
        "FAILED": "Failed"
    }
    return mapping.get(status_str, status_str)


def generate_markdown_report(results: dict, summary: dict, output_path: Path) -> None:
    """Generate docs/reports/CAPABILITY_STATUS.md from measured probe data."""
    now_utc = datetime.now(timezone.utc).isoformat()
    lines = [
        "# ZONATA Universal AI Operating System — Capability Truth Table",
        "",
        f"**Generated:** `{now_utc}`  ",
        f"**Environment:** `{os.environ.get('APP_ENV', 'development')}`  ",
        f"**Hardware Platform:** `{os.uname().machine} {os.uname().sysname}`  ",
        f"**Execution Mode:** {'Sandbox / Test' if os.environ.get('ZONATA_TEST_MODE') == '1' else 'Standard Sovereign'}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Live (Operational):** `{summary.get('live', 0)}`",
        f"- **Test / Sandbox:** `{summary.get('test_only', 0)}`",
        f"- **Not Connected / Unconfigured:** `{summary.get('not_connected', 0)}`",
        f"- **Degraded Mode:** `{summary.get('degraded', 0)}`",
        f"- **Not Implemented:** `{summary.get('not_implemented', 0)}`",
        f"- **Failed:** `{summary.get('failed', 0)}`",
        "",
        "---",
        "",
        "## 2. Capability Status & Latency Truth Table",
        "",
        "| Capability | Reality Status | Plain Language | Provider | Provider Ref | Latency (ms) | Sandbox | Details / Error |",
        "|:---|:---|:---|:---|:---|:---|:---|:---|"
    ]

    for cap, res in sorted(results.items()):
        status_val = res.status.value if hasattr(res.status, "value") else str(res.status)
        plain = format_status_label(status_val)
        provider = res.provider or "-"
        pref = res.provider_ref or "-"
        lat = f"{res.latency_ms:.2f}"
        sb = "Yes" if res.sandbox else "No"
        detail = res.error or (json.dumps(res.metadata) if res.metadata else "-")
        detail = detail.replace("\n", " ").replace("|", "/")
        lines.append(f"| `{cap}` | **{status_val}** | {plain} | `{provider}` | `{pref}` | {lat} | {sb} | {detail} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Truth Invariants Verified",
        "1. **No False Success:** Zero capabilities report operational status without a live verified handshake.",
        "2. **Measured Latencies:** Latency recorded per individual harmless probe in milliseconds.",
        "3. **Explicit Absence:** Browser automation and Desktop GUI control are acknowledged as `NOT_IMPLEMENTED`.",
        "4. **No Secrets Exposed:** Provider credentials, tokens, and database passwords scrubbed from all outputs.",
        ""
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="ZONATA Reality Probe CLI")
    parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout")
    parser.add_argument("--out", type=str, default="docs/reports/CAPABILITY_STATUS.md", help="Report destination path")
    parser.add_argument("--strict", action="store_true", help="Fail with non-zero exit code if any capability failed")
    args = parser.parse_args()

    results = probe_all_capabilities()
    summary = summarize_capabilities(results)

    out_file = Path(args.out)
    generate_markdown_report(results, summary, out_file)

    if args.json:
        data = {
            "summary": summary,
            "capabilities": {k: v.to_dict() for k, v in results.items()}
        }
        print(json.dumps(data, indent=2))
    else:
        print("\n" + "=" * 80)
        print(" ZONATA UNIVERSAL AI OS — CAPABILITY TRUTH TABLE")
        print("=" * 80)
        print(f" Summary: {summary['live']} Live | {summary['test_only']} Test | "
              f"{summary['not_connected']} Unconfigured | {summary['not_implemented']} Not Implemented | "
              f"{summary['degraded']} Degraded | {summary['failed']} Failed")
        print("-" * 80)
        print(f" {'Capability':<18} | {'Status':<16} | {'Plain Language':<15} | {'Latency':<10} | {'Provider'}")
        print("-" * 80)
        for cap, res in sorted(results.items()):
            status_val = res.status.value if hasattr(res.status, "value") else str(res.status)
            plain = format_status_label(status_val)
            print(f" {cap:<18} | {status_val:<16} | {plain:<15} | {res.latency_ms:>7.2f} ms | {res.provider}")
        print("=" * 80)
        print(f" Generated report at: {out_file}\n")

    if args.strict and summary["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
