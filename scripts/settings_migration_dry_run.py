#!/usr/bin/env python3
"""Settings V2 migration dry-run.

This tool is deliberately read-only.  It reads the legacy
``enterprise_settings`` table and the legacy JSON mirror, classifies every row
against the typed registry, and writes a report.  It never prints or stores a
setting value: secret rows are reduced to a classification, and non-secret rows
are reported by key and scope only.

Usage::

    python3 scripts/settings_migration_dry_run.py
    python3 scripts/settings_migration_dry_run.py --db storage/roboassistant.db

Exit codes:
    0  report generated
    2  input missing or unreadable
    3  registry invalid (should not happen in a committed tree)
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sqlite3
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.settings.registry import settings_registry  # noqa: E402
from core.settings.models import SettingStatus  # noqa: E402

DEFAULT_DB = os.path.join("storage", "roboassistant.db")
DEFAULT_MIRROR = os.path.join("storage", "enterprise_settings.json")
DEFAULT_JSON_OUT = os.path.join("docs", "reports", "SETTINGS_MIGRATION_DRY_RUN.json")
DEFAULT_MD_OUT = os.path.join("docs", "reports", "SETTINGS_MIGRATION_DRY_RUN.md")

PLACEHOLDER_MARKERS = (
    "change_me",
    "changeme",
    "your_",
    "your-",
    "placeholder",
    "example",
    "dummy",
    "demo",
    "test_",
    "xxxx",
    "secrettoken",
    "secret_token",
    "secretkey",
    "secret_key",
    "mcp_sec_live_",
    "whsec_live_",
    "zapi_live_",
    "\u2022",  # bullet characters used by the seeded look-alike defaults
)
REVOKED_MARKERS = ("revoked", "revoked_by_host")


def _read_only_connection(path: str) -> sqlite3.Connection:
    uri = "file:" + os.path.abspath(path).replace("?", "%3f") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def classify_secret(raw_json: Optional[str]) -> str:
    """Classify a secret without returning the value itself."""
    if raw_json is None:
        return "missing"
    try:
        value = json.loads(raw_json)
    except Exception:
        return "unreadable"
    if value is None:
        return "empty"
    text = str(value)
    if not text:
        return "empty"
    lowered = text.lower()
    if any(marker in lowered for marker in REVOKED_MARKERS):
        return "revoked_or_placeholder"
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return "placeholder"
    # The seeded look-alike defaults are short, prefixed demo credentials.
    if len(text) < 16:
        return "too_short_for_real_credential"
    return "configured"


def _rows(conn: sqlite3.Connection, table: str) -> List[sqlite3.Row]:
    return list(
        conn.execute(
            f"""
            SELECT tenant_id, company_id, scope, category, setting_key,
                   setting_value_json, version, updated_at, updated_by
            FROM {table}
            ORDER BY tenant_id, company_id, setting_key
            """
        ).fetchall()
    )


def _company_ids(conn: sqlite3.Connection, rows: Iterable[sqlite3.Row]) -> Dict[str, List[str]]:
    """Companies that actually have a stored setting, per tenant."""
    by_tenant: Dict[str, set] = collections.defaultdict(set)
    for row in rows:
        by_tenant[str(row["tenant_id"])].add(str(row["company_id"]))
    return {tenant: sorted(companies) for tenant, companies in by_tenant.items()}


def _registered_company_ids(conn: sqlite3.Connection, rows: Iterable[sqlite3.Row]) -> Dict[str, List[str]]:
    """Companies registered in the companies table, limited to settings tenants."""
    tenants = {str(row["tenant_id"]) for row in rows}
    by_tenant: Dict[str, set] = {tenant: set() for tenant in tenants}
    if _table_exists(conn, "companies"):
        try:
            for row in conn.execute("SELECT tenant_id, company_id FROM companies").fetchall():
                tenant = str(row[0])
                if tenant in by_tenant:
                    by_tenant[tenant].add(str(row[1]))
        except Exception:
            pass
    return {tenant: sorted(companies) for tenant, companies in by_tenant.items()}


def _normalize_value(raw_json: str) -> str:
    """Stable comparison key for a stored JSON value.

    Values are hashed only for equality grouping; the digest is not reported.
    """
    import hashlib

    try:
        value = json.loads(raw_json)
    except Exception:
        value = raw_json
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_report(db_path: str, mirror_path: str) -> Dict[str, Any]:
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    registry_counts = settings_registry.counts()
    registry_sections = []
    for section in settings_registry.public_catalog()["sections"]:
        registry_sections.append(
            {
                "id": section["id"],
                "num": section["num"],
                "name": section["name"],
                "setting_count": section["setting_count"],
                "live_count": section["live_count"],
                "coming_soon_count": section["coming_soon_count"],
                "hidden_count": section["hidden_count"],
                "action_count": section["action_count"],
            }
        )

    report: Dict[str, Any] = {
        "report": "settings_migration_dry_run",
        "generated_at": generated_at,
        "read_only": True,
        "database": db_path,
        "mirror": mirror_path,
        "registry": {
            "counts": registry_counts,
            "live_keys": settings_registry.live_keys(),
            "sections": registry_sections,
        },
        "source": {
            "table_exists": False,
            "row_count": 0,
            "tenant_count": 0,
            "companies": {},
            "registered_companies": {},
            "stored_scopes": {},
            "stored_categories": {},
        },
        "organization_default_candidates": [],
        "proposed_moves": {
            "keep_company_scope": 0,
            "move_to_secrets": 0,
            "seed_organization_default": 0,
            "action_rows": 0,
            "unknown_registry_rows": 0,
        },
        "secrets_review": [],
        "conflicts": [],
        "json_mirror": {
            "exists": False,
            "key_count": 0,
            "non_setting_key_count": 0,
            "keys_only_in_mirror": [],
            "keys_only_in_db": [],
        },
        "warnings": [],
    }

    if not os.path.exists(db_path):
        report["warnings"].append("Database not found; nothing to classify.")
        return report

    try:
        conn = _read_only_connection(db_path)
    except Exception as exc:
        report["warnings"].append(f"Database could not be opened read-only: {type(exc).__name__}.")
        return report

    try:
        if not _table_exists(conn, "enterprise_settings"):
            report["warnings"].append("Table enterprise_settings does not exist; nothing to classify.")
            return report

        rows = _rows(conn, "enterprise_settings")
        report["source"]["table_exists"] = True
        report["source"]["row_count"] = len(rows)

        companies = _company_ids(conn, rows)
        registered_companies = _registered_company_ids(conn, rows)
        report["source"]["companies"] = companies
        report["source"]["registered_companies"] = registered_companies
        report["source"]["tenant_count"] = len(companies)

        scope_counter: collections.Counter = collections.Counter()
        category_counter: collections.Counter = collections.Counter()
        db_keys = set()
        for row in rows:
            key = str(row["setting_key"])
            scope = str(row["scope"] or "")
            category = str(row["category"] or "")
            db_keys.add(key)
            scope_counter[scope] += 1
            category_counter[category] += 1

            definition = settings_registry.get(key)
            if definition is None:
                report["proposed_moves"]["unknown_registry_rows"] += 1
                report["conflicts"].append(
                    {
                        "kind": "unknown_registry_key",
                        "key": key,
                        "tenant_id": str(row["tenant_id"]),
                        "company_id": str(row["company_id"]),
                        "action": "hide until a definition exists",
                    }
                )
                continue

            if definition.status is SettingStatus.ACTION:
                report["proposed_moves"]["action_rows"] += 1
                continue

            if definition.secret:
                classification = classify_secret(row["setting_value_json"])
                report["secrets_review"].append(
                    {
                        "key": key,
                        "tenant_id": str(row["tenant_id"]),
                        "company_id": str(row["company_id"]),
                        "classification": classification,
                        "proposed_action": (
                            "move_to_secrets" if classification == "configured" else "mark_unconfigured"
                        ),
                    }
                )
                if classification == "configured":
                    report["proposed_moves"]["move_to_secrets"] += 1
                else:
                    report["conflicts"].append(
                        {
                            "kind": "secret_not_configured",
                            "key": key,
                            "tenant_id": str(row["tenant_id"]),
                            "company_id": str(row["company_id"]),
                            "classification": classification,
                            "action": "require re-entry; do not migrate the value",
                        }
                    )
            else:
                report["proposed_moves"]["keep_company_scope"] += 1

        report["source"]["stored_scopes"] = dict(sorted(scope_counter.items()))
        report["source"]["stored_categories"] = dict(sorted(category_counter.items()))

        # Organisation defaults are seeded only where every company in the
        # tenant has the same value for a key.  Anything else stays at Company
        # scope.  Secrets are never promoted; they stay write-only and scoped.
        rows_by_tenant_key: Dict[Tuple[str, str], List[sqlite3.Row]] = collections.defaultdict(list)
        for row in rows:
            rows_by_tenant_key[(str(row["tenant_id"]), str(row["setting_key"]))].append(row)

        for (tenant_id, key), group in sorted(rows_by_tenant_key.items()):
            definition = settings_registry.get(key)
            if definition is None or definition.sensitive or definition.status is SettingStatus.ACTION:
                continue
            tenant_companies = registered_companies.get(tenant_id) or companies.get(tenant_id, [])
            if len(tenant_companies) < 2:
                continue
            values_by_company: Dict[str, str] = {}
            for row in group:
                values_by_company[str(row["company_id"])] = _normalize_value(str(row["setting_value_json"]))
            if set(values_by_company) != set(tenant_companies):
                continue
            if len(set(values_by_company.values())) != 1:
                continue
            report["organization_default_candidates"].append(
                {
                    "tenant_id": tenant_id,
                    "key": key,
                    "company_count": len(tenant_companies),
                    "proposed_scope": "organization",
                    "action": "seed organization default; keep company rows unchanged",
                }
            )
            report["proposed_moves"]["seed_organization_default"] += 1

        # Host-labelled rows are stored per company.  Divergent values under the
        # same Host key are the migration's real conflict: one of them cannot
        # become the platform default without changing another company.
        for (tenant_id, key), group in sorted(rows_by_tenant_key.items()):
            definition = settings_registry.get(key)
            if definition is None:
                continue
            if not any(str(row["scope"]) == "Host" for row in group):
                continue
            if len({_normalize_value(str(row["setting_value_json"])) for row in group}) > 1:
                report["conflicts"].append(
                    {
                        "kind": "host_scope_divergence",
                        "key": key,
                        "tenant_id": tenant_id,
                        "companies": sorted({str(row["company_id"]) for row in group}),
                        "action": "choose one organization default or keep per-company values",
                    }
                )

        # Unknown stored scopes are reported once per scope label.
        known_scopes = {"Host", "Company", "User"}
        for scope_label in sorted(scope_counter):
            if scope_label not in known_scopes:
                report["conflicts"].append(
                    {
                        "kind": "unknown_stored_scope",
                        "scope": scope_label,
                        "row_count": scope_counter[scope_label],
                        "action": "map to company scope during migration review",
                    }
                )

        # Compare the legacy JSON mirror by key name only.
        if os.path.exists(mirror_path):
            try:
                with open(mirror_path, "r", encoding="utf-8") as handle:
                    mirror = json.load(handle)
                if isinstance(mirror, dict):
                    registry_keys = {definition.key for definition in settings_registry.all()}
                    mirror_keys = {str(key) for key in mirror if str(key) in registry_keys}
                    non_setting_keys = {str(key) for key in mirror if str(key) not in registry_keys}
                    report["json_mirror"] = {
                        "exists": True,
                        "key_count": len(mirror_keys),
                        "non_setting_key_count": len(non_setting_keys),
                        "keys_only_in_mirror": sorted(mirror_keys - db_keys),
                        "keys_only_in_db": sorted(db_keys - mirror_keys),
                    }
                else:
                    report["json_mirror"] = {
                        "exists": True,
                        "key_count": 0,
                        "non_setting_key_count": 0,
                        "keys_only_in_mirror": [],
                        "keys_only_in_db": [],
                    }
                    report["warnings"].append("Legacy mirror is not a JSON object.")
            except Exception as exc:
                report["warnings"].append(f"Legacy mirror could not be parsed: {type(exc).__name__}.")
        else:
            report["warnings"].append("Legacy JSON mirror not found.")

        if report["source"]["tenant_count"] > 1:
            report["warnings"].append(
                "More than one tenant is present. Organisation-default seeding is evaluated per tenant."
            )
        if not report["organization_default_candidates"]:
            report["warnings"].append(
                "No key has an identical value across every company, so no Organization default will be seeded automatically."
            )
    finally:
        conn.close()

    return report


def render_markdown(report: Dict[str, Any]) -> str:
    counts = report["registry"]["counts"]
    source = report["source"]
    lines: List[str] = []
    lines.append("# Settings Migration Dry-Run Report")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at']}`")
    lines.append("")
    lines.append(
        "> **Read-only.** This report was produced without writing to the database, "
        "the JSON mirror, or any settings table. Secret values are never printed; "
        "they are reduced to a classification."
    )
    lines.append("")
    lines.append("## 1. Registry readiness")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|---|---:|")
    for status in ("live", "coming_soon", "hidden", "action"):
        lines.append(f"| `{status}` | {counts.get(status, 0)} |")
    lines.append(f"| **total** | **{counts.get('total', 0)}** |")
    lines.append(f"| categories | {counts.get('categories', 0)} |")
    lines.append(f"| sections | {counts.get('sections', 0)} |")
    lines.append("")
    lines.append("## 2. Stored data")
    lines.append("")
    lines.append(f"- Source database: `{report['database']}`")
    lines.append(f"- Legacy table present: `{source['table_exists']}`")
    lines.append(f"- Rows: **{source['row_count']}**")
    lines.append(f"- Tenants: **{source['tenant_count']}**")
    registered_counts = {
        tenant: len(companies)
        for tenant, companies in source.get("registered_companies", {}).items()
    }
    if registered_counts:
        lines.append(
            "- Registered companies: "
            + ", ".join(f"`{tenant}`={count}" for tenant, count in registered_counts.items())
        )
    lines.append("")
    if source["companies"]:
        lines.append("| Tenant | Companies |")
        lines.append("|---|---|")
        for tenant, companies in source["companies"].items():
            lines.append(f"| `{tenant}` | {', '.join(f'`{company}`' for company in companies)} |")
        lines.append("")
    lines.append("| Stored scope label | Rows |")
    lines.append("|---|---:|")
    for scope, count in source["stored_scopes"].items():
        lines.append(f"| `{scope}` | {count} |")
    lines.append("")
    lines.append("## 3. Proposed scope handling")
    lines.append("")
    moves = report["proposed_moves"]
    lines.append("| Action | Rows / keys |")
    lines.append("|---|---:|")
    lines.append(f"| Keep at Company scope | {moves['keep_company_scope']} |")
    lines.append(f"| Move configured secret to vault | {moves['move_to_secrets']} |")
    lines.append(f"| Seed Organization default | {moves['seed_organization_default']} |")
    lines.append(f"| Danger-zone action rows | {moves['action_rows']} |")
    lines.append(f"| Unknown registry keys | {moves['unknown_registry_rows']} |")
    lines.append("")
    lines.append(
        "Host-labelled rows are kept at Company scope. An Organization default is seeded "
        "only when every company in the tenant stores the same value. No locks are created."
    )
    lines.append("")
    lines.append("### Organization default candidates")
    lines.append("")
    if report["organization_default_candidates"]:
        lines.append("| Tenant | Key | Companies agreeing |")
        lines.append("|---|---|---:|")
        for candidate in report["organization_default_candidates"]:
            lines.append(
                f"| `{candidate['tenant_id']}` | `{candidate['key']}` | {candidate['company_count']} |"
            )
    else:
        lines.append("_None. Organization defaults will be seeded from the registry instead._")
    lines.append("")
    lines.append("## 4. Secret review")
    lines.append("")
    lines.append("No secret value, prefix, suffix, or length is included below.")
    lines.append("")
    if report["secrets_review"]:
        lines.append("| Key | Tenant | Company | Classification | Proposed action |")
        lines.append("|---|---|---|---|---|")
        for item in report["secrets_review"]:
            lines.append(
                f"| `{item['key']}` | `{item['tenant_id']}` | `{item['company_id']}` | "
                f"`{item['classification']}` | `{item['proposed_action']}` |"
            )
    else:
        lines.append("_No secret-classified rows were found._")
    lines.append("")
    lines.append("## 5. Conflicts and review items")
    lines.append("")
    if report["conflicts"]:
        lines.append("| Kind | Key / scope | Tenant | Action |")
        lines.append("|---|---|---|---|")
        for conflict in report["conflicts"]:
            target = conflict.get("key") or conflict.get("scope") or ""
            companies = conflict.get("companies")
            if companies and "company_id" not in conflict:
                target = f"{target} ({len(companies)} companies)"
            lines.append(
                f"| `{conflict['kind']}` | `{target}` | `{conflict.get('tenant_id', '')}` | "
                f"{conflict.get('action', '')} |"
            )
    else:
        lines.append("_No conflicts found._")
    lines.append("")
    lines.append("## 6. Legacy JSON mirror")
    lines.append("")
    mirror = report["json_mirror"]
    lines.append(f"- Present: `{mirror['exists']}`")
    lines.append(f"- Registry setting keys: **{mirror['key_count']}**")
    if mirror.get("non_setting_key_count"):
        lines.append(f"- Non-setting keys (category/domain aliases): {mirror['non_setting_key_count']}")
    if mirror["keys_only_in_mirror"]:
        lines.append(
            "- Keys only in mirror: " + ", ".join(f"`{key}`" for key in mirror["keys_only_in_mirror"])
        )
    if mirror["keys_only_in_db"]:
        preview = mirror["keys_only_in_db"][:20]
        suffix = "" if len(preview) == len(mirror["keys_only_in_db"]) else " …"
        lines.append(
            f"- Keys only in DB ({len(mirror['keys_only_in_db'])}): "
            + ", ".join(f"`{key}`" for key in preview)
            + suffix
        )
        lines.append("  The JSON mirror is a legacy compatibility cache; it is not the source of truth.")
    lines.append("")
    lines.append("## 7. Warnings")
    lines.append("")
    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("_None._")
    lines.append("")
    lines.append("## 8. Next gate")
    lines.append("")
    lines.append(
        "Phase 1 ends here. No migration has been applied. Phase 2 (resolver, RBAC, "
        "secrets vault, audit chain, approvals, API v2) requires checkpoint 2 approval."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Settings V2 migration dry-run.")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database to inspect (read-only).")
    parser.add_argument("--mirror", default=DEFAULT_MIRROR, help="Legacy JSON mirror to compare.")
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT, help="JSON report path.")
    parser.add_argument("--md-out", default=DEFAULT_MD_OUT, help="Markdown report path.")
    parser.add_argument("--stdout", action="store_true", help="Print the JSON report to stdout.")
    args = parser.parse_args(argv)

    try:
        report = build_report(args.db, args.mirror)
    except ValueError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return 3

    for path in (args.json_out, args.md_out):
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

    with open(args.json_out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with open(args.md_out, "w", encoding="utf-8") as handle:
        handle.write(render_markdown(report))

    if args.stdout:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"wrote {args.json_out} and {args.md_out} "
            f"({report['source']['row_count']} rows, {len(report['conflicts'])} review items)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
