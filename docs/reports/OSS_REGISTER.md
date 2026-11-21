# OpenCode Step 1 — Open Source Software (OSS) Register

Generated directly from installed package metadata (`importlib.metadata`).
Governed by Standing Rule 5 (Licence Boundary).

| Package | Version | SPDX License | Compliance Status |
| :--- | :--- | :--- | :--- |
| **asn1crypto** | `1.5.1` | `MIT` | APPROVED (Allowlist) |
| **boolean.py** | `5.0` | `BSD-2-Clause` | APPROVED (Allowlist) |
| **CacheControl** | `0.15.0` | `Apache-2.0` | APPROVED (Allowlist) |
| **certifi** | `2026.10.23` | `MPL-2.0` | APPROVED (Allowlist) |
| **cffi** | `2.1.1` | `MIT-0` | APPROVED (Allowlist) |
| **charset-normalizer** | `3.5.2` | `MIT` | APPROVED (Allowlist) |
| **cryptography** | `50.0.2` | `Apache-2.0` | APPROVED (Allowlist) |
| **cyclonedx-python-lib** | `11.12.0` | `Apache-2.0` | APPROVED (Allowlist) |
| **defusedxml** | `0.7.1` | `PSFL` | APPROVED (Allowlist) |
| **filelock** | `4.2.12` | `MIT` | APPROVED (Allowlist) |
| **idna** | `3.20` | `BSD-3-Clause` | APPROVED (Allowlist) |
| **iniconfig** | `2.3.1` | `MIT` | APPROVED (Allowlist) |
| **license-expression** | `30.4.4` | `Apache-2.0` | APPROVED (Allowlist) |
| **markdown-it-py** | `4.3.0` | `MIT` | APPROVED (Allowlist) |
| **mdurl** | `0.1.2` | `MIT` | APPROVED (Allowlist) |
| **msgpack** | `1.2.4` | `Apache-2.0` | APPROVED (Allowlist) |
| **numpy** | `2.5.5` | `UNKNOWN` | APPROVED (Allowlist) |
| **packageurl-python** | `0.17.6` | `MIT` | APPROVED (Allowlist) |
| **packaging** | `26.3` | `Apache-2.0` | APPROVED (Allowlist) |
| **pandas** | `3.1.1` | `BSD-3-Clause` | APPROVED (Allowlist) |
| **pg8000** | `1.31.6` | `BSD-3-Clause` | APPROVED (Allowlist) |
| **pip** | `26.3` | `MIT` | APPROVED (Allowlist) |
| **pip-requirements-parser** | `32.0.1` | `MIT` | APPROVED (Allowlist) |
| **pip_api** | `0.0.35` | `Apache-2.0` | APPROVED (Allowlist) |
| **pip_audit** | `2.10.1` | `Apache-2.0` | APPROVED (Allowlist) |
| **platformdirs** | `4.14.7` | `MIT` | APPROVED (Allowlist) |
| **pluggy** | `1.7.0` | `MIT` | APPROVED (Allowlist) |
| **proot-distro** | `5.10.3` | `GPL-3.0-only` | BOUNDARY — legal review before commercial use |
| **py-serializable** | `2.2.0` | `Apache-2.0` | APPROVED (Allowlist) |
| **pycparser** | `3.12` | `BSD-3-Clause` | APPROVED (Allowlist) |
| **Pygments** | `2.21.0` | `BSD-2-Clause` | APPROVED (Allowlist) |
| **pyparsing** | `3.3.3` | `MIT` | APPROVED (Allowlist) |
| **pytest** | `9.2.0` | `MIT` | APPROVED (Allowlist) |
| **python-dateutil** | `4.0.0` | `BSD-3-Clause` | APPROVED (Allowlist) |
| **python-dotenv** | `1.2.4` | `BSD-3-Clause` | APPROVED (Allowlist) |
| **PyYAML** | `6.0.3` | `MIT` | APPROVED (Allowlist) |
| **requests** | `2.34.2` | `Apache-2.0` | APPROVED (Allowlist) |
| **rich** | `15.0.0` | `MIT` | APPROVED (Allowlist) |
| **scramp** | `1.5.0` | `MIT-0` | APPROVED (Allowlist) |
| **sortedcontainers** | `2.4.0` | `Apache-2.0` | APPROVED (Allowlist) |
| **tomli** | `2.5.0` | `MIT` | APPROVED (Allowlist) |
| **tomli_w** | `1.2.0` | `MIT` | APPROVED (Allowlist) |
| **tzdata** | `2026.6` | `Apache-2.0` | APPROVED (Allowlist) |
| **urllib3** | `2.8.0` | `MIT` | APPROVED (Allowlist) |

## Network Service Boundaries (External Containers)

| Service | Pinned Image | License (SPDX) | Architecture Boundary | Status |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL 16** | `postgres:16.4-alpine` | PostgreSQL (MIT-style) | TCP Port 5432 network service | APPROVED |
| **SeaweedFS** | `chrislusf/seaweedfs:3.79` | Apache-2.0 | TCP Port 8333 S3 HTTP API | APPROVED |
| **Mailpit** | `axllent/mailpit:v1.21.8` | Apache-2.0 / MIT | TCP Port 1025 / 8025 API | APPROVED |
| **Apache Tika** | `apache/tika:2.9.2.1` | Apache-2.0 | TCP Port 9998 REST API | APPROVED |
| **ClamAV** | `clamav/clamav:1.4.1` | GPL-2.0-only (daemon) | TCP Port 3310 socket | BOUNDARY — legal review before commercial use |
