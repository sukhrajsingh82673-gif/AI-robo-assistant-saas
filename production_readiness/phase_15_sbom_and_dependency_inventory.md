# Phase 15 Software Bill of Materials (SBOM) & Dependency Inventory Report

**Evaluation Date:** October 19, 2026  
**Artifact Directory:** `storage/evidence/sbom/`  
**Standard Specifications Generated:**
1. **CycloneDX JSON v1.5**: `storage/evidence/sbom/cyclonedx_sbom.json`
2. **SPDX JSON v2.3**: `storage/evidence/sbom/spdx_sbom.json`  
**Total Identified Components:** 41 components (8 Python libraries + 33 Node.js packages)  
**Supply-Chain Standard Compliance:** NIST SP 800-218 (SSDF), Executive Order 14028, NTIA Minimum Elements for SBOM  

---

## 1. Supply-Chain Architecture Overview

To provide enterprise-grade supply-chain assurance and eliminate unverified third-party dependencies, ZONATA generated machine-readable SBOM manifests conforming to the two globally recognized open standards:

```
storage/evidence/sbom/
├── cyclonedx_sbom.json   # CycloneDX v1.5 JSON (OWASP Foundation standard)
└── spdx_sbom.json         # SPDX v2.3 JSON (ISO/IEC 5962:2021 international standard)
```

Both files are persisted in the version-controlled repository, cryptographically verifiable, and suitable for automated ingestion by enterprise vulnerability scanners (Snyk, Grype, Dependency-Check, Trivy, Mend, Black Duck).

---

## 2. Direct Dependencies Inventory

### A. Python Production Runtime (`requirements.txt`)
| Component | Direct / Transitive | Version | License | Package URL (`purl`) | Primary Purpose |
|:---|:---:|:---:|:---:|:---|:---|
| `psycopg2-binary` | Direct | `2.9.9` | `LGPL-3.0-or-later WITH OpenSSL-Exception` | `pkg:pypi/psycopg2-binary@2.9.9` | High-performance C-extension PostgreSQL DB-API driver |
| `pg8000` | Direct | `1.31.5` | `BSD-3-Clause` | `pkg:pypi/pg8000@1.31.5` | Pure-Python PostgreSQL DB-API 2.0 driver (zero C-extension fallback) |
| `PyYAML` | Direct | `6.0.1` | `MIT` | `pkg:pypi/pyyaml@6.0.1` | Secure parsing of configuration templates & DAG specs |
| `numpy` | Direct | `1.26.4` | `BSD-3-Clause` | `pkg:pypi/numpy@1.26.4` | High-dimensional array computations & economic budget matrices |
| `pandas` | Direct | `2.2.2` | `BSD-3-Clause` | `pkg:pypi/pandas@2.2.2` | Relational analytics, financial timeseries, & cohort retention |
| `python-dateutil`| Direct | `2.9.0.post0`| `Apache-2.0` | `pkg:pypi/python-dateutil@2.9.0.post0`| ISO 8601 parsing & timezone-aware timestamp arithmetic |
| `cryptography` | Direct | `46.0.5` | `Apache-2.0` | `pkg:pypi/cryptography@46.0.5` | HMAC-SHA256, PBKDF2, AES-GCM, & digital signatures |
| `bcrypt` | Transitive | `5.0.0` | `Apache-2.0` | `pkg:pypi/bcrypt@5.0.0` | Modern password hashing & key derivation fallback |

### B. Node.js Production Runtime (`package.json` & `package-lock.json`)
| Component | Direct / Transitive | Version | License | Package URL (`purl`) | Primary Purpose |
|:---|:---:|:---:|:---:|:---|:---|
| `@neon/config` | Direct | `1.9.2` | `Apache-2.0` | `pkg:npm/@neon/config@1.9.2` | Neon Lakebase configuration loader & connection manager |
| `@neon/env` | Direct | `1.6.3` | `Apache-2.0` | `pkg:npm/@neon/env@1.6.3` | Neon environment variable discovery & credential injector |
| `@neon/sdk` | Transitive | `7.3.0` | `Apache-2.0` | `pkg:npm/@neon/sdk@7.3.0` | Neon Cloud API client for branch & auth management |
| `zod` | Transitive | `4.6.7` | `MIT` | `pkg:npm/zod@4.6.7` | Type-safe schema validation for configuration payloads |
| `yargs` | Transitive | `18.2.0` | `MIT` | `pkg:npm/yargs@18.2.0` | CLI argument parsing for helper utilities |
| `yargs-parser` | Transitive | `22.0.0` | `ISC` | `pkg:npm/yargs-parser@22.0.0` | Low-level tokenization engine for CLI arguments |
| `jiti` | Transitive | `2.7.0` | `MIT` | `pkg:npm/jiti@2.7.0` | Runtime TypeScript and ESM compilation bridge |
| `cliui` | Transitive | `9.0.1` | `ISC` | `pkg:npm/cliui@9.0.1` | Formatted console table rendering for diagnostics |
| `strip-ansi` | Transitive | `7.2.0` | `MIT` | `pkg:npm/strip-ansi@7.2.0` | ANSI escape code sanitization for secure log persistence |
| `wrap-ansi` | Transitive | `9.0.2` | `MIT` | `pkg:npm/wrap-ansi@9.0.2` | Terminal line wrapping for structured operational alerts |
| `ansi-styles` | Transitive | `6.2.3` | `MIT` | `pkg:npm/ansi-styles@6.2.3` | Terminal styling primitives |
| `ansi-regex` | Transitive | `6.4.0` | `MIT` | `pkg:npm/ansi-regex@6.4.0` | Regular expressions for ANSI control code detection |
| `string-width` | Transitive | `8.3.0` | `MIT` | `pkg:npm/string-width@8.3.0` | Visual width calculation for multi-byte Unicode strings |
| `emoji-regex` | Transitive | `10.6.0` | `MIT` | `pkg:npm/emoji-regex@10.6.0` | Regex for detecting emoji sequences in logs |
| `escalade` | Transitive | `3.2.0` | `MIT` | `pkg:npm/escalade@3.2.0` | Fast directory traversal for module configuration resolution |
| `get-caller-file`| Transitive | `2.0.5` | `ISC` | `pkg:npm/get-caller-file@2.0.5` | Stack inspection for error diagnostics |
| `get-east-asian-width`| Transitive| `1.7.0` | `MIT`| `pkg:npm/get-east-asian-width@1.7.0`| Character width inspection for internationalization |
| `y18n` | Transitive | `5.0.8` | `ISC` | `pkg:npm/y18n@5.0.8` | Internationalization string translation utility |
| `@napi-rs/keyring`| Transitive | `1.3.0` | `MIT` | `pkg:npm/@napi-rs/keyring@1.3.0` | Native OS secure keyring adapter (macOS, Linux, Win32) |
| `@napi-rs/keyring-*` (12 archs) | Transitive | `1.3.0` | `MIT` | `pkg:npm/@napi-rs/keyring-*@1.3.0` | Pre-compiled native bindings across target architectures |

---

## 3. NTIA Minimum Elements Compliance Matrix

| NTIA Minimum Requirement | CycloneDX v1.5 Manifest | SPDX v2.3 Manifest | Status |
|:---|:---|:---|:---:|
| **Supplier Name** | Present (`metadata.component.supplier` and component attributes) | Present (`packages[].originator` / `supplier`) | **COMPLIANT** |
| **Component Name** | Present in all 41 components | Present (`packages[].name`) | **COMPLIANT** |
| **Version of the Component** | Exact semantic version recorded | Present (`packages[].versionInfo`) | **COMPLIANT** |
| **Other Unique Identifiers** | Package URL (`purl`) and `bom-ref` specified | `purl` recorded in `externalRefs` | **COMPLIANT** |
| **Dependency Relationship** | Directed dependency tree in `dependencies` array | Relationships declared (`DEPENDS_ON`) | **COMPLIANT** |
| **Author of SBOM Data** | Recorded (`ZONATA SecOps`, `ZONATA Supply-Chain Auditor`) | Recorded in `creationInfo.creators` | **COMPLIANT** |
| **Timestamp** | ISO 8601 UTC timestamp recorded | ISO 8601 UTC timestamp recorded | **COMPLIANT** |
