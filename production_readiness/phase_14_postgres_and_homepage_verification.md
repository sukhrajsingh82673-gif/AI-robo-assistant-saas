# Phase 14 PostgreSQL Compatibility & Homepage Verification Report

**Evaluation Date:** October 19, 2026  
**Branch:** `engineering/production-readiness-gap-closure`  
**Host Environment:** Linux aarch64, Python 3.14.6, pytest-9.1.1  
**Scope:** SQL Parameter Tokenization Parity, Error Response Boundaries & Live Staging Probing  
**Verdict:** **LOCAL VERIFICATION PASSED / LIVE STAGING MERGE BLOCKED**

---

## 1. SQL Parameter Translation Hardening (Workstream B)

### Defect Identified in Baseline Analysis
In Phase 13, `normalize_sql_for_postgres` in `core/db.py` utilized global naive substitution:
```python
normalized = sql.replace("?", "%s")
```
This naive substitution mutated question marks inside:
- Single-quoted string literals: e.g., `'Why?'` became `'Why%s'`
- Double-quoted identifiers: e.g., `"column?1"` became `"column%s1"`
- Single-line SQL comments: e.g., `-- Is this ok?` became `-- Is this ok%s`
- Multi-line block comments: e.g., `/* Has ? */` became `/* Has %s */`
- Dollar-quoted constants: `$$question?$$`

In PostgreSQL drivers (such as `psycopg2` or `psycopg3`), mutating string literals causes parameter count mismatches (`TypeError: not all arguments converted during string formatting`) or corrupts search text.

### Architectural Remediation
Implemented a robust tokenizer/lexer `_tokenize_and_replace_placeholders(sql: str) -> str` in `core/db.py`:
- Tracks lexical state (`in_single_quote`, `in_double_quote`, `in_line_comment`, `in_block_comment`, `in_dollar_quote`).
- Correctly handles escaped quotes (`''` and `\"`).
- Converts `?` to `%s` strictly when outside string constants, identifiers, and comments.

### Automated Test Qualification
Added `test_03b_sql_normalizer_preserves_question_marks_in_literals_and_comments` in `tests/test_postgresql_dialect_compatibility.py`.

```bash
$ PYTHONPATH=. pytest tests/test_postgresql_dialect_compatibility.py
============================== 10 passed in 4.78s ==============================
```
All 10 dialect compatibility tests passed with 100% compliance.

---

## 2. Overview Service & API Error Boundary Hardening

In `api_server.py`, the `/api/overview` and `/api/overview/snapshot` endpoints were wrapped with strict `try...except Exception as e:` error handlers:
- Any backend database timeout or query error logs full context via `logger.error(...)`.
- The handler returns an explicit HTTP 500 JSON response with headers `Content-Type: application/json` and body `{"error": "Internal Server Error", "detail": "..."}`.
- This guarantees the connection is not dropped abruptly at the socket level, preventing Cloudflare/Render reverse proxies from converting uncaught exceptions into opaque `502 Bad Gateway` responses that break frontend JSON parsing (`Unexpected end of JSON input`).

---

## 3. Public HTTPS Live Staging Probing (`https://zonata-staging.onrender.com`)

Probing was conducted directly against the live deployment over public HTTPS using standard curl and Python HTTP clients:

| Target Endpoint | HTTP Method | Auth State | Observed HTTP Status | Content-Type | Observed Response Body / Behavior | Classification |
|:---|:---:|:---:|:---:|:---:|:---|:---:|
| `/healthz` | GET | Public | **200 OK** | `application/json` | `{"status": "HEALTHY", "uptime_seconds": 34.66, "version": "1.0.0-GA", "database": "CONNECTED", ...}` | **PASS** |
| `/readyz` | GET | Public | **200 OK** | `application/json` | `{"status": "HEALTHY", "database": "CONNECTED", "merkle_ledger": "INTEGRITY_VERIFIED", ...}` | **PASS** |
| `/api/auth/register` | POST | Synthetic Disposable | **201 Created** | `application/json` | Successfully created user `OWNER`, tenant `tnt_f5d51c32`, returned valid Bearer JWT | **PASS** |
| `/api/overview/snapshot` | GET | Unauthenticated | **401 Unauthorized** | `application/json` | `{"error": "Unauthorized", "detail": "Authentication Required: Missing, invalid, or expired Bearer token"}` | **PASS** |
| `/api/overview/snapshot` | GET | Authenticated (JWT) | **502 Bad Gateway** | `text/html` (Cloudflare) | Cloudflare 502 Bad Gateway response from Render origin | **BLOCKED (DEPLOYMENT BRANCH DIVERGENCE)** |

### Root Cause Analysis of Live Staging 502
Inspection of git remote references revealed:
```bash
$ git ls-remote --heads origin
13be43e... refs/heads/engineering/production-readiness-gap-closure
1020d0e... refs/heads/main
```
1. Render staging is configured to continuously deploy from branch `refs/heads/main`.
2. Branch `main` is currently pinned to commit `1020d0e` (dating from Phase 10).
3. The Phase 13 (`a19e7c3`) and Phase 14 (`db.py` / `api_server.py`) fixes reside on `engineering/production-readiness-gap-closure` and have not yet been merged into `main`.
4. As a result, the live Render service is executing the old Phase 10 binary which still attempts SQLite `?` placeholder execution on Neon PostgreSQL, precipitating the origin error.

### Required Manual Action
To update the live staging deployment, merge `engineering/production-readiness-gap-closure` into `main` or configure Render's deploy branch to `engineering/production-readiness-gap-closure`.
