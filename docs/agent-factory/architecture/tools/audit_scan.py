#!/usr/bin/env python3
"""ZONATA repository audit scanner (read-only, stdlib only, no network).

Produces a *map of evidence* for EXISTING_SYSTEM_AUDIT Phase 1. It does NOT classify anything as
"implemented and verified" — that requires executing tests and reading the code. It tells the auditor
exactly where to look, and flags likely stubs/mocks so nothing is mistaken for working functionality.

Usage:  python3 -I audit_scan.py /path/to/repo --out audit_scan.json --md audit_scan.md
"""
from __future__ import annotations
import argparse, collections, json, os, re, sys

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".turbo", "coverage", ".mypy_cache", ".pytest_cache", "target"}
TEXT_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".go", ".rs", ".java", ".sql", ".yaml", ".yml", ".json", ".toml", ".md", ".prisma", ".tf", ".sh", ".env", ".cfg", ".ini"}
MAX_BYTES = 1_500_000

COMPONENTS = {  # key -> regex (case-insensitive). Evidence of *mention*, not of function.
    "company_kernel": r"company[_ -]?kernel", "constitution": r"constitution", "policy_engine": r"policy[_ -]?engine|PolicyEngine",
    "authority_gateway": r"authority[_ -]?gateway|AuthorityGateway", "approval_engine": r"approval[_ -]?engine|ApprovalEngine|consent",
    "evidence_ledger": r"evidence[_ -]?ledger|EvidenceLedger|merkle", "kill_switch": r"kill[_ -]?switch|KillSwitchMatrix",
    "ai_ceo": r"ai[_ -]?ceo|\bAICU\b", "agency_swarm": r"agency[_ -]?swarm", "langgraph": r"langgraph", "letta": r"\bletta\b", "hal": r"\bHAL\b",
    "mcp": r"\bmcp\b|model[_ -]?context[_ -]?protocol", "a2a": r"\ba2a\b|agent2agent|agent[_ -]?card", "openhands": r"openhands", "browser_use": r"browser[_ -]?use",
    "terminal": r"universal[_ -]?(linux[_ -]?)?terminal|\bpty\b|xterm", "automation_fabric": r"automation[_ -]?fabric", "temporal": r"temporalio|\btemporal\b",
    "vault": r"\bvault\b|hvac|openbao", "keycloak": r"keycloak", "openfga": r"openfga", "nats": r"\bnats\b|jetstream", "s3_minio": r"minio|boto3|s3[_-]client|aioboto",
    "otel": r"opentelemetry|\botel\b", "langfuse": r"langfuse", "posthog": r"posthog", "model_gateway": r"model[_ -]?gateway|litellm|inference",
    "rls_tenant": r"row level security|ENABLE ROW LEVEL|set_config\(.zonata|current_setting\(|tenant_id",
    "agent_factory_existing": r"agent[_ -]?factory|AgentFactory|agent[_ -]?template|AgentTemplate|agent[_ -]?registry|AgentRegistry|spawn_agent|create_agent|build_agent|agent[_ -]?builder",
    "workforce": r"ai[_ -]?employee|synthetic[_ -]?employee|workforce|department|chro",
    "dlp": r"\bdlp\b|data[_ -]?loss|redact",
}
STUB_MARKERS = {
    "not_implemented": r"NotImplementedError|raise NotImplemented", "todo": r"\bTODO\b|\bFIXME\b|\bXXX\b", "stub_word": r"\bstub(bed)?\b|\bplaceholder\b|\bmock(ed)?[_ -]?(data|response|provider)\b|lorem ipsum",
    "canned_ok": r"return\s*\{\s*[\"']status[\"']\s*:\s*[\"'](ok|success)[\"']\s*\}", "pass_body": r"^\s*pass\s*(#.*)?$", "scripted": r"scripted|hard[- ]?coded sample|sample data|fake[_ -]?data",
}
ROUTE_PATTERNS = [r"@(?:\w+)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)", r"\b(?:router|app)\.(get|post|put|patch|delete)\(\s*[\"'`]([^\"'`]+)", r"path\(\s*[\"']([^\"']+)[\"']"]
VERSION_RE = re.compile(r"/api/(v\d+)\b")
CREATE_TABLE_RE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:\"?[\w]+\"?\.)?\"?(\w+)\"?", re.I)
PY_MODEL_RE = re.compile(r"__tablename__\s*=\s*[\"'](\w+)[\"']")
PRISMA_RE = re.compile(r"^model\s+(\w+)\s*\{", re.M)
FW = {"fastapi": "FastAPI", "flask": "Flask", "django": "Django", "express": "Express", "next": "Next.js", "nestjs": "NestJS", "react": "React", "vite": "Vite",
      "sqlalchemy": "SQLAlchemy", "alembic": "Alembic", "prisma": "Prisma", "drizzle-orm": "Drizzle", "pydantic": "Pydantic", "langgraph": "LangGraph", "temporalio": "Temporal SDK",
      "celery": "Celery", "pytest": "pytest", "vitest": "Vitest", "jest": "Jest", "playwright": "Playwright"}


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = os.path.join(d, f)
            if os.path.splitext(f)[1].lower() in TEXT_EXT or f in ("Dockerfile", "Makefile", "requirements.txt"):
                try:
                    if os.path.getsize(p) <= MAX_BYTES:
                        yield p
                except OSError:
                    pass


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("repo"); ap.add_argument("--out", default="audit_scan.json"); ap.add_argument("--md", default="audit_scan.md")
    ap.add_argument("--max-hits", type=int, default=12); a = ap.parse_args()
    root = os.path.abspath(a.repo)
    comp_rx = {k: re.compile(v, re.I) for k, v in COMPONENTS.items()}
    stub_rx = {k: re.compile(v, re.I | re.M) for k, v in STUB_MARKERS.items()}
    ext_count, hits, stubs = collections.Counter(), {k: [] for k in COMPONENTS}, collections.defaultdict(collections.Counter)
    comp_files = {k: collections.Counter() for k in COMPONENTS}
    routes, versions, tables, tests, manifests, migrations, frameworks = [], collections.Counter(), set(), [], [], [], set()
    for p in walk(root):
        rel = os.path.relpath(p, root); ext = os.path.splitext(p)[1].lower(); ext_count[ext] += 1
        base = os.path.basename(p)
        if base in ("package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml", "docker-compose.yml", "docker-compose.yaml", "render.yaml", "Dockerfile"):
            manifests.append(rel)
        if re.search(r"(^|/)(tests?|__tests__|spec)(/|$)|test_.*\.py$|\.(test|spec)\.[tj]sx?$", rel):
            tests.append(rel)
        if re.search(r"(^|/)(migrations?|alembic|versions|prisma/migrations)(/|$)", rel):
            migrations.append(rel)
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if base in ("package.json", "pyproject.toml", "requirements.txt"):
            low = txt.lower()
            for k, v in FW.items():
                if re.search(r'(^|[\s"\'])' + re.escape(k) + r'([\s"\'=<>~!,\]:^]|$)', low):
                    frameworks.add(v)
        is_code = ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".mjs")
        lines = txt.splitlines()
        for k, rx in comp_rx.items():
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    comp_files[k][rel] += 1
                    if len(hits[k]) < a.max_hits and (is_code or ext in (".sql", ".yaml", ".yml", ".toml", ".json")):
                        hits[k].append(f"{rel}:{i}: {line.strip()[:140]}")
        if is_code:
            for k, rx in stub_rx.items():
                n = len(rx.findall(txt))
                if n:
                    stubs[rel][k] += n
            for rx in ROUTE_PATTERNS:
                for m in re.finditer(rx, txt):
                    g = m.groups(); routes.append(dict(file=rel, method=(g[0].upper() if len(g) == 2 else "ANY"), path=g[-1]))
            for m in VERSION_RE.finditer(txt):
                versions[m.group(1)] += 1
        if ext == ".sql" or "migration" in rel.lower() or "alembic" in rel.lower():
            for m in CREATE_TABLE_RE.finditer(txt):
                tables.add(m.group(1))
        if ext == ".py":
            tables.update(PY_MODEL_RE.findall(txt))
        if ext == ".prisma":
            tables.update(PRISMA_RE.findall(txt))
    stub_rank = sorted(((sum(c.values()), f, dict(c)) for f, c in stubs.items()), reverse=True)[:40]
    result = dict(root=root, extension_counts=dict(ext_count.most_common(20)), manifests=sorted(manifests), frameworks_detected=sorted(frameworks),
                  api_version_prefixes=dict(versions.most_common()), route_count=len(routes), routes_sample=routes[:200], tables=sorted(tables),
                  migration_files=sorted(migrations)[:80], test_file_count=len(tests), test_files_sample=sorted(tests)[:80],
                  component_mentions={k: dict(files=len(comp_files[k]), occurrences=sum(comp_files[k].values()), top_files=comp_files[k].most_common(5), sample_hits=hits[k]) for k in COMPONENTS},
                  stub_or_mock_markers_top_files=[dict(score=s, file=f, markers=m) for s, f, m in stub_rank])
    json.dump(result, open(a.out, "w"), indent=1)
    md = [f"# audit_scan — {root}\n", "**This is a map of where to look, not a verdict.** Mentions are not implementations; stub markers are not proof of stubs.\n",
          f"- Files by extension: {result['extension_counts']}", f"- Frameworks detected in manifests: {result['frameworks_detected']}",
          f"- API version prefixes seen in code: {result['api_version_prefixes']}  (use the **highest in active use** for the factory namespace)",
          f"- Routes found: {result['route_count']} · tables found: {len(tables)} · test files: {result['test_file_count']} · migration files: {len(migrations)}\n",
          "## Component mentions (files / occurrences)\n", "| component | files | occurrences | top file |", "|---|---|---|---|"]
    for k, v in result["component_mentions"].items():
        top = v["top_files"][0][0] if v["top_files"] else "—"
        md.append(f"| {k} | {v['files']} | {v['occurrences']} | {top} |")
    md += ["\n## Likely stubs / mocks / placeholders (highest density first)\n", "| score | file | markers |", "|---|---|---|"] + [f"| {x['score']} | {x['file']} | {x['markers']} |" for x in result["stub_or_mock_markers_top_files"][:25]]
    md += ["\n## Tables detected\n", ", ".join(sorted(tables)) or "none", "\n## Manifests\n", "\n".join(f"- {m}" for m in sorted(manifests))]
    open(a.md, "w").write("\n".join(md) + "\n")
    print(f"wrote {a.out} and {a.md}: {result['route_count']} routes, {len(tables)} tables, {result['test_file_count']} test files, frameworks={result['frameworks_detected']}")


if __name__ == "__main__":
    sys.exit(main())
