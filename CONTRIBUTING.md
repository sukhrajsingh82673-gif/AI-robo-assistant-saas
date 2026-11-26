# Contributing to ZONATA

Thank you for contributing to ZONATA / RoboAssistant. All contributions must uphold the platform's governance, security, and verification standards.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Verification Checklist (Required Before Opening a PR)

Run these checks locally before submitting any pull request:

```bash
# 1. Bytecode & AST Security Linters
python3 -m compileall -q .
python3 scripts/anti_evasion_linter.py
python3 scripts/anti_bypass_linter.py

# 2. Frontend JS Syntax (requires Node.js 20+)
node --check web/*.js web/pwa/*.js

# 3. Pytest Suite & Preservation Contracts (isolated SQLite test mode)
env -u DATABASE_URL -u DATABASE_URL_UNPOOLED ZONATA_DB_DIALECT=sqlite ZONATA_TEST_MODE=1 \
  python3 -m pytest -q

# 4. Release Readiness & End-to-End Scenario
python3 scripts/release_readiness.py
python3 scripts/step9_scenario.py
```

## Engineering Rules

1. **Truth Rule:** Never report simulated behavior as live execution. Unconfigured credentials must raise or return `NOT_CONFIGURED`; unbuilt paths must report `NOT_IMPLEMENTED`.
2. **Test Side-Effects:** Tests must operate exclusively in temporary paths (`tmp_path`, `tempfile`, `ZONATA_DB_PATH`, `ZONATA_SBOM_PATH`, `ZONATA_EVIDENCE_PATH`) and must never mutate tracked documentation or database files in place.
3. **Preservation Contract:** Changes touching protected files tracked under `security/protected_paths*.yaml` require explicit security review and baseline re-sealing across `docs/baselines/`.
4. **No Hardcoded Industry Branches (Rule 68):** Industry behavior must remain declarative inside `packs/` and data registries — never `if industry == ...`.
5. **Secret Hygiene:** Never commit plaintext credentials, private keys, or real tenant data. All templates use non-sensitive placeholders.

## Pull Request Process

1. Branch from `main` using descriptive branch names (e.g. `feat/<topic>`, `fix/<issue>`, `security/<hardening>`).
2. Keep commits focused and atomic.
3. Complete the pull request checklist in `.github/PULL_REQUEST_TEMPLATE.md`.
4. Ensure all GitHub Actions CI checks pass before requesting human owner merge approval.
