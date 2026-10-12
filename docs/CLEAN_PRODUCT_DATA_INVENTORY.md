# URA / ZONATA SaaS — Clean Product Data & Mock Inventory

**Audit Date**: 12 October 2026  
**Baseline Commit**: `198bd6734b93f15182c3e3e95ae2c7d307470814`  
**Target Branch**: `remediation/audit-hardening-simulation-gate`  
**Scope**: Repository-wide inspection of all hardcoded mock records, synthetic seeders, simulated telemetry, placeholder metrics, and developer conveniences.

---

## 1. Executive Summary

This inventory documents every synthetic, mock, sample, and placeholder data structure across the URA / ZONATA Enterprise SaaS codebase. Following the controlled production-readiness guidelines, each item has been identified, classified into one of seven mandatory categories, and remediated to guarantee **zero fake metrics, zero fabricated business records, and honest operational empty states** across all user-facing interfaces.

### Inventory Summary by Classification Category

| Category | Description | Count of Items | Remediation Status |
|---|---|---|---|
| **Cat 1** | User-Facing Fake Data (to remove or empty) | 18 | Remediated (Gated / Replaced with Empty States) |
| **Cat 2** | Production Startup Seeders (disable or clean defaults) | 4 | Remediated (Gated behind `APP_ENV` & `ZONATA_DISABLE_DEMO_SEED`) |
| **Cat 3** | Synthetic Simulation Fixtures (retain strictly in test/sim) | 12 | Isolated strictly within `core/simulation_fixtures.py` & `scratch/` |
| **Cat 4** | Genuine Schema Defaults (statutory enterprise defaults) | 8 | Preserved (Zero-balance COA, system roles, invariant tables) |
| **Cat 5** | Unconfigured Feature States (honest empty/setup states) | 14 | Remediated (Honest modal disclosures & setup prompts) |
| **Cat 6** | Mock Connector Responses (replace with credential checks) | 6 | Remediated (Real credential validation & unconfigured disclosures) |
| **Cat 7** | Dev-Only Conveniences (gate behind environment flags) | 5 | Remediated (Removed implicit auto-login; opt-in flag required) |

---

## 2. Category 1: User-Facing Fake Data (Removed / Dynamicized)

The following items previously displayed fabricated metrics, sample deals, or hardcoded activities on user screens.

| ID | Location | Original Artifact / Value | Classification | Remediation Applied |
|---|---|---|---|---|
| **C1-01** | `web/index.html:315` | `onclick="showToast('2 pending owner approvals...', 'warning')"` | Cat 1 | Replaced with dynamic navigation to `/approvals` and reactive badge |
| **C1-02** | `web/crm_sales_workspace.js:22-201` | `CUSTOMERS_DATA` (Taj Hospitality, Apex Industrial, NovaTech) | Cat 1 | Encapsulated as `DEMO_CUSTOMERS_DATA`; `getCustomersData()` returns `[]` in production |
| **C1-03** | `web/crm_sales_workspace.js:258` | Hardcoded Weighted Forecast `₹5,420,000` | Cat 1 | Dynamically computed from active deal store or displays ₹0.00 |
| **C1-04** | `web/crm_sales_workspace.js:276` | Static `3 Key Accounts` count | Cat 1 | Replaced with `getCustomersData().length Accounts` |
| **C1-05** | `web/crm_sales_workspace.js:380` | Pre-rendered customer rows without empty fallback | Cat 1 | Added responsive empty state with `+ Add Customer Account` action |
| **C1-06** | `web/finance_workspace.js:42` | Pre-populated bank balances (`₹46,20,000`) | Cat 1 | Standard Chart of Accounts starts at `0.00` in clean/production mode |
| **C1-07** | `web/records_workspace.js:55` | Hardcoded sample invoices and POs | Cat 1 | Gated seeder; clean mode returns 0 records with ingestion prompt |
| **C1-08** | `web/files_workspace.js:38` | Hardcoded Certificate of Incorporation and Q3 PnL | Cat 1 | Gated seeder; clean mode displays empty document repository |
| **C1-09** | `web/reports_workspace.js:45` | Hardcoded Q3 Profit & Loss statement | Cat 1 | Gated seeder; clean mode displays "No reports generated" |
| **C1-10** | `web/agent_network_workspace.js:82` | Sample topology nodes with mock throughput | Cat 1 | Connected to real kernel agent registry via `/api/agent-engine/status` |
| **C1-11** | `web/overview_workspace.js:140` | Hardcoded trailing 30-day revenue placeholder | Cat 1 | Replaced with live backend aggregation via `/api/overview` |
| **C1-12** | `web/workforce_workspace.js:64` | Hardcoded sample contractor list | Cat 1 | Dynamic query to `employees` database table with empty state |
| **C1-13** | `web/floating_assistant.js:112` | Mock canned citations | Cat 1 | Grounded strictly in active tenant context and ledger records |
| **C1-14** | `web/meeting_room_workspace.js:88` | Sample pre-recorded meeting minutes | Cat 1 | Only renders meetings stored in `ai_ceo_meetings` database table |
| **C1-15** | `web/plugins_workspace.js:72` | Hardcoded "Connected" indicators for unconfigured tools | Cat 1 | Evaluates true credential validity; shows "Unconfigured" if keys missing |
| **C1-16** | `web/browser_workspace.js:50` | Mock browser execution traces | Cat 1 | Evaluates true Playwright/Chrome headless session or reports offline |
| **C1-17** | `web/openhands_workspace.js:60` | Mock workspace container files | Cat 1 | Evaluates actual workspace sandbox filesystem |
| **C1-18** | `web/temporal_workspace.js:70` | Mock workflow run history | Cat 1 | Queries live Temporal gRPC gateway or displays unconfigured state |

---

## 3. Category 2: Production Startup Seeders (Controlled / Gated)

Automatic seeders running in `core/` modules previously seeded mock records whenever a table was empty.

| ID | File & Method | Seeded Records / Entities | Production Remediation |
|---|---|---|---|
| **C2-01** | `core/enterprise_finance.py`  
`_seed_default_finance_if_empty()` | 12 Chart of Accounts with balances, 4 transactions (`tx_101-104`), 3 expenses (`exp_101-103`) | **Remediated**: When `APP_ENV=production` or `ZONATA_DISABLE_DEMO_SEED=1`, seeds canonical Chart of Accounts with **0.00 balances**; completely suppresses fake transactions and expenses. |
| **C2-02** | `core/enterprise_records.py`  
`_seed_default_records_if_empty()` | `rec_inv_1001` (Taj Hospitality ₹1,45,000), `rec_exp_2004` (Apex PO-9021 ₹78,500), `rec_cust_taj` | **Remediated**: Immediately returns in clean/production mode. Table remains empty until real user ingestion occurs. |
| **C2-03** | `core/enterprise_files.py`  
`_seed_default_files_if_empty()` | `file_corp_incorp`, `file_fin_audited_pnl`, `file_legal_msa_taj`, `file_ops_sop_nightaudit` | **Remediated**: Immediately returns in clean/production mode. Repository remains empty until authentic uploads occur. |
| **C2-04** | `core/enterprise_reports.py`  
`_seed_default_reports_if_empty()` | `rep_exec_pl_q3` (EBITDA ₹44,90,000), `rep_cash_flow_daily` (Daily cash flow ₹67,20,000) | **Remediated**: Immediately returns in clean/production mode. Reports screen displays honest empty state. |

---

## 4. Category 3: Synthetic Simulation Fixtures (Retained in Test/Sim Only)

The following fixtures are required to test complex multi-tenant policies, sandboxes, and verification gates. They are strictly quarantined from production execution paths.

| ID | Location | Purpose | Quarantined Mechanism |
|---|---|---|---|
| **C3-01** | `core/simulation_fixtures.py` | Disposable database creation and test isolation | Gated behind ephemeral temp paths; never writes to production database |
| **C3-02** | `scratch/run_synthetic_company_simulation.py` | 10 Synthetic business workflows & 9 security negative tests | Standalone scratch script; executed only during formal qualification runs |
| **C3-03** | `tests/test_audit_remediation_security.py` | Regression negative authentication and spoofing suites | Uses in-memory / temporary test database fixtures |
| **C3-04** | `tests/test_overview_production.py` | 42-criteria overview snapshot validation | Uses dedicated test tenant isolation |
| **C3-05** | `tests/test_prompt03_features.py` | Schedule, meeting, assistant, and plugins unit tests | Uses `configure_isolated_test_db()` in temporary directory |
| **C3-06** | `tests/test_settings_enterprise_qualification.py` | 32 categories of enterprise settings tests | Uses temporary isolated test database and isolated HTTP server |
| **C3-07** | `core/automation_fabric/synthetic_data_generator.py` | Anonymized test profile generator | Available only when invoked with explicit test fixture seed |
| **C3-08** | `storage/evidence/audit_ledger.jsonl` | Baseline cryptographic invariant audit log | Immutable read-only reference baseline (SHA-256 preserved) |
| **C3-09** | `storage/roboassistant.db` | Baseline cryptographic invariant SQLite state | Immutable read-only reference baseline (SHA-256 preserved) |
| **C3-10** | `web/workflow_workspace.js` | Visual canvas DAG editor | Immutable client asset (Git Blob SHA preserved) |
| **C3-11** | `core/universal_terminal/reversibility_engine.py` | Undo/rollback simulation fixtures | Active only during reversible command pipeline testing |
| **C3-12** | `core/coworker/background_dispatcher.py` | Synthetic mission execution benchmarks | Gated behind isolated test queue |

---

## 5. Category 4: Genuine Schema Defaults (Preserved)

Legitimate enterprise structures that represent structural schema or regulatory baselines rather than demo content:

| ID | Schema Entity | Purpose | Justification |
|---|---|---|---|
| **C4-01** | Chart of Accounts Structure (COA) | Codes 1010, 1020, 1100, 2010, 3010, 4010, 5010, 6010 | Statutory GAAP/IFRS accounting categories required for double-entry bookkeeping (balances start at ₹0.00) |
| **C4-02** | User Roles (`core/auth.py`) | `OWNER`, `EXECUTIVE`, `MANAGER`, `OPERATOR`, `AUDITOR` | RBAC constitutional role definitions |
| **C4-03** | Agent Blueprints | `agt_bp_cfo_controller`, `agt_bp_procurement_lead`, etc. | Canonical role templates available for deployment |
| **C4-04** | Setting Key Definitions | 32 categories of system configuration keys | System registry defaults for operational parameters |
| **C4-05** | Table Schemas (`core/db.py`) | Relational table creation statements | Normalized database schema |
| **C4-06** | Audit Ledger Header | Genesis block format | Merkle-tree cryptographic specification |
| **C4-07** | Timezone / Currency Defaults | `UTC` / `USD` / `INR` currency tokens | Standard internationalization tokens |
| **C4-08** | Supported File Types | `PDF`, `XLSX`, `DOCX`, `CSV`, `JSON` | MIME-type routing rules |

---

## 6. Category 5: Unconfigured Feature States (Honest Disclosures)

When third-party services or physical infrastructure are absent, the application displays honest disclosures rather than fabricated success.

| ID | Feature / Module | Previous Presentation | Honest Production State |
|---|---|---|---|
| **C5-01** | Social OAuth (Google, Apple, Microsoft) | Instant mock sign-in with dummy user | Modal displaying *"Enterprise Identity Provider Not Configured"* with instructions to supply OAuth client keys |
| **C5-02** | Stripe / Razorpay Payment Gateway | Mock "Settled" status badges | *"Unconfigured Gateway"* badge; setup guide displayed |
| **C5-03** | QuickBooks / NetSuite Accounting Sync | Simulated ledger synchronization | *"Connector Offline: Missing API Token"* disclosure |
| **C5-04** | AWS / GCP S3 Storage Backend | Simulated bucket upload | Falls back to local disk storage with persistent warning |
| **C5-05** | SendGrid / SMTP Mail Gateway | Simulated email dispatched toast | Reports *"SMTP Server Not Configured"* with setup prompt |
| **C5-06** | Twilio SMS / WhatsApp Connector | Simulated notification delivered | Displays *"SMS Gateway Inactive"* |
| **C5-07** | OpenHands Sandbox Execution | Simulated container spin-up | Fails closed with *"Container Sandbox Daemon Unavailable"* |
| **C5-08** | Browser Automation (Playwright) | Simulated browser screenshot | Displays *"Headless Browser Cluster Offline"* |
| **C5-09** | Temporal Durable Workflow Gateway | Simulated workflow step completed | Reports *"Temporal Server Connection Refused"* |
| **C5-10** | Nango Universal Unified Integrations | Simulated 3rd-party auth | Displays *"Nango Secret Key Missing"* |
| **C5-11** | SCIM / Okta Directory Sync | Simulated employee roster sync | Reports *"IdP SCIM Endpoint Unreachable"* |
| **C5-12** | Model Inference (OpenAI / Anthropic) | Simulated agent reasoning | Displays *"LLM API Key Not Provisioned"* |
| **C5-13** | Datadog / OTEL Collector | Simulated metrics export | Logs local telemetry with *"Collector Unreachable"* |
| **C5-14** | KMS Vault Secret Key Storage | Simulated encryption key rotation | Falls back to local environment secrets with warning |

---

## 7. Category 6: Mock Connector Responses (Real Credential Checks)

Connectors in `core/automation_fabric/enterprise_connectors.py` have been audited to verify that live credentials are checkable:

| ID | Connector | Original Behavior | Remediated Behavior |
|---|---|---|---|
| **C6-01** | `HospitalityPMSConnector` | Returned synthetic Opera/Fidelio reservations | Verifies API endpoint and bearer token; returns 401/503 if unconfigured |
| **C6-02** | `AccountingConnector` | Returned simulated ledger balances | Tests live connection to QuickBooks/Xero; returns empty or connection error |
| **C6-03** | `PaymentGatewayConnector` | Returned simulated Stripe charge responses | Validates secret key format against gateway API; reports honest status |
| **C6-04** | `ERPConnector` | Returned fake SAP/Oracle purchase orders | Requires valid base URL and mutual TLS credentials |
| **C6-05** | `NangoConnector` | Returned mock connector tokens | Checks `NANGO_SECRET_KEY` presence before attempting token exchange |
| **C6-06** | `McpConnector` | Presumed remote MCP servers always available | Pings stdio/SSE socket; marks server `OFFLINE` if unresponsive |

---

## 8. Category 7: Dev-Only Conveniences (Gated Behind Flags)

| ID | Convenience Feature | Original State | Hardened Production State |
|---|---|---|---|
| **C7-01** | Auto Sovereign Host Login | Automatically set `state.host` in development | **Disabled by default**: Requires explicit opt-in via `localStorage.getItem('zonata_dev_autologin') === 'true'` and non-production environment |
| **C7-02** | Dev Auth Secret Fallback | `ROBOASSISTANT_INTERNAL_TENANT_HMAC_SECRET_2026` | Refused in production mode; raises `RuntimeError` if `ZONATA_AUTH_SECRET` is unset |
| **C7-03** | Local SQLite File Engine | `storage/roboassistant.db` used everywhere | Production Docker Compose configures dedicated PostgreSQL 16 service with connection pooling |
| **C7-04** | Unrestricted Host Shell Command Fallback | Permitted local host execution in dev | Strict production check refuses any host execution (`ZONATA_ALLOW_HOST_FALLBACK=0`) |
| **C7-05** | Unchecked User Registration | Absent `/api/auth/register` endpoint | Fully implemented `POST /api/auth/register` with cryptographic token issuance and tenant scoping |

---

## 9. Verification & Invariant Proof

All modifications have been verified against the 3 protected reference assets:
- `storage/roboassistant.db`: SHA-256 `ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4` **(PASS)**
- `storage/evidence/audit_ledger.jsonl`: SHA-256 `ca8181ec9314f281acad3512a34d32323fc195e6eed9f6412d7262e1e6dd0996` **(PASS)**
- `web/workflow_workspace.js`: Git Blob SHA `198d57ec6bda875cd2a6825fe2ef8929b7ba30bd` **(PASS)**
