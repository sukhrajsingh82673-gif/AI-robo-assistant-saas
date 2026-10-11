# ZONATA / URA — Sovereign AI Security Threat Model & Attack Matrix

**Comprehensive Security Risk & Attack Surface Evaluation**  
**Document Classification:** RESTRICTED — SECURITY AUDIT  
**Framework Alignment:** MITRE ATT&CK for Enterprise / OWASP Top 10 for LLM Applications (2025/2026)  
**Baseline Commit:** `53bd2ef` (Lineage verified from `45cf91f`)  
**Status:** PRODUCTION QUALIFIED — VERIFIED SCOPE  

---

## 1. Protected Enterprise Assets & Trust Boundaries

### 1.1 Core Assets
- **Corporate Secrets & Credentials**: API keys, Vault root tokens, JWT signing secrets, SSH keys, TLS certificates, canary secrets.
- **Customer & Financial Data**: PII (SSN, names, emails, phone numbers), India financial/tax identifiers (PAN, Aadhaar, GSTIN, IFSC), bank account/routing numbers, ledger records.
- **Intellectual Property & Business Strategy**: M&A targets, project codenames (Project Falcon), proprietary prompts, KG embeddings.
- **Operational Authority**: AI CEO voting quorum, approval receipts, budget allocations, process supervision.

### 1.2 Trust Boundaries
- **Boundary $\alpha$ (External Egress & LLM Providers)**: Internal agent runtimes $\leftrightarrow$ Third-party cloud LLMs, LiteLLM gateway, and SaaS APIs.
- **Boundary $\beta$ (Inter-Agent / Inter-Tenant)**: Agent A $\leftrightarrow$ Agent B (A2A gateway) and Tenant isolation boundaries.
- **Boundary $\gamma$ (Tool & Connectors Execution)**: Co-worker runtime $\leftrightarrow$ MCP servers, Shell sandbox, Docker, Browser nodes, and Enterprise Automation Connectors.
- **Boundary $\delta$ (Data Storage & Memory)**: Working memory $\leftrightarrow$ SQLite databases, Letta episodic/operational memory pools, audit ledgers.

---

## 2. Comprehensive 14-Vector Threat Matrix

| # | Threat Vector | Protected Asset | Trust Boundary | Attacker Capability | Preventive Control | Detection Method | Response & Recovery | Test Verification |
|:---:|---|---|---|---|---|---|---|---|
| **1** | **Prompt Injection (Direct & Indirect)** | Agent instruction integrity & authority | LLM prompt & tool output | Attacker embeds `ignore previous instructions` in scraped web page or retrieved document | `ExternalContentFirewall`, `inspect_tool_output()`, and `BrowserController` scan extracted DOM | Regex signature analysis in `presidio_dlp_engine` & MCP firewall | Rejection with `PROMPT_INJECTION_BLOCKED`; incident recorded in `security_center` | `test_09`, `test_12` |
| **2** | **Sensitive Data Leakage in LLM Prompts** | Customer PII & financial records | Outbound LLM gateway | Agent incorporates unredacted customer SSN, PAN card, or financial forecast in cloud prompt | `AutonomousAIDLPGateway` & `ModelDataFirewall` intercept prompts | Presidio entity recognizers (`US_SSN`, `CREDIT_CARD`, `EMAIL_ADDRESS`, `INDIA_PAN`, `INDIA_AADHAAR`, `INDIA_GSTIN`) | Class 2 Transform: Redacts or tokenizes PII; mission continues seamlessly | `test_01`, `test_06` |
| **3** | **API Key & Credential Exfiltration** | Cloud provider keys, private keys | Outbound model / tool boundary | Compromised agent attempts to send AWS/OpenAI key to external destination | Outbound DLP denies raw credentials to non-sovereign destinations | `ApiKeyAndSecretRecognizer`, `CryptoKeyRecognizer`, `SecurityCanaryRecognizer` | Class 3 Restrict (Strike 1 immediate block) escalating to Class 4 KillSwitch containment (Strike 3) | `test_05`, `test_18`, `test_20` |
| **4** | **Unauthorized & Malicious MCP Servers** | Local filesystem, DB, host commands | MCP controller boundary | Malicious actor registers rogue MCP server or requests unadmitted tool | Strict MCP admission registry; rejects unadmitted servers | Registry lookup in `GovernedMCPController.execute_tool()` | Request rejected with `MCP server not found or not admitted` | `test_08` |
| **5** | **Cross-Tenant Information Disclosure** | Tenant-segregated database & memory | Multi-tenant control plane | Tenant A agent crafts semantic query or message targeting Tenant B data | SQL WHERE-clause tenant isolation & A2A tenant verification | `GovernedA2AController` cross-tenant check | Outbound transmission blocked with HTTP 403; critical incident logged | `test_10` |
| **6** | **A2A Identity Spoofing & Escalation** | Sovereign agent authorization | A2A gateway | External agent claims to have sovereign authority or forged identity | Server-side cryptographic signing (`sig_a2a_...`) and role verification | A2A message signature & HMAC digest verification | Unverified messages dropped as `UNTRUSTED_EXTERNAL_ADVISORY` | `test_10`, `test_12` |
| **7** | **SSRF & Metadata Bypass (IPv4/IPv6, Decimal, Userinfo)** | Cloud instance credentials (`169.254.169.254`), internal services | Browser & HTTP egress | Malicious prompt directs browser to navigate to internal IPs via decimal (`2130706433`), hex (`0x7f...`), IPv6 (`::1`), userinfo (`user@169.254.169.254`), or open redirect | Multi-format IP filtering, port allowlisting (80, 443, 8080, 8443), & `SSRFSafeRedirectHandler` | Multi-family `socket.getaddrinfo` & `ipaddress.ip_address` evaluation | Navigation aborted with `SSRF Block`; request terminated | `test_15` |
| **8** | **Data Exfiltration via Connectors & SDKs** | Proprietary code, customer database, keys | Automation Connectors & SDK Clients | Script attempts data exfiltration via external connector parameters or raw SDK client calls | Connector pre-execution parameter DLP screening (`ConnectorRegistry.execute`) & fail-closed `CognitiveModelProvider` | `AutonomousAIDLPGateway.inspect_and_enforce()` | Exfiltration blocked immediately with `ConnectorSecurityError` or `[DLP_BLOCKED]` | `test_19`, connector qualification |
| **9** | **Path Traversal & Restricted Filesystem Access** | System configuration (`/etc/passwd`, `/root/.vault`, SSH keys) | Terminal & workspace | Agent attempts `../../etc/passwd` or symlink escape from outside sandbox | `GovernedTerminalController.file_operation()` path confinement | Path normalization and `os.path.realpath` evaluation against `/etc`, `/root/.vault`, `/proc`, `/sys`, `/root/.ssh`, `/root/.gnupg`, `/dev` | Operation blocked with `FAILED_SECURITY_POLICY` | `test_16` |
| **10** | **Dependency & Supply-Chain Compromise** | Runtime code integrity | Python runtime & build | Vulnerable or hostile dependency introduced via package installation | CycloneDX v1.5 SBOM audit & OSI license compliance validation | `AutomationLicenseValidator.validate_dependency()` | Unapproved licenses or unpinned packages blocked at build time | CI/CD Stage 1, `test_24` |
| **11** | **Secret Leakage in Git & CI/CD Logs** | Development & production secrets | GitHub repository & logs | Engineer or agent accidentally commits API key, DB connection string, or canary token | Stage 1 CI/CD secret scanner with refined high-entropy patterns and scrubbed log output | CI/CD secret detection step scanning repo working tree | Commit/PR blocked with exit code 1; zero secret emission | CI/CD Pipeline Stage 1 |
| **12** | **Replay & Approval Tampering (TOCTOU)** | Financial authorization & approvals | Workflow execution runtime | Adversary re-submits expired approval or tampers with approved parameters | Canonical HMAC-SHA256 receipts binding action and `parameters_hash` | `UniversalAutomationFabric.verify_approval_receipt()` | Tampered approval halts execution with `AutomationSecurityException` | `test_10`, `test_12` (AI CEO suite) |
| **13** | **Denial of Service & Security Disablement** | Continuous OS availability | Edge proxy & WAF | Attacker floods API or attempts to disable security middleware | Token-bucket rate limiting and immutable security interceptors | `EdgeSecurityGateway._check_rate_limit()` | Offending IP throttled with HTTP 429; security remains active | Edge Gateway qualification |
| **14** | **Compromised Worker / Insider Threat** | Enterprise operational continuity | Autonomous workforce pool | Compromised agent begins rogue behavior or exfiltration | Multi-level `KillSwitchMatrix` (AGENT, EMPLOYEE, TOOL levels) | Automated violation tracking in `AutonomousAIDLPGateway` | Class 4 automated isolation: Strike 1 denied immediately; Strike 3 engages KillSwitch; other agents continue | `test_18` |

---

## 3. Residual Risks & Scoped Deployment Boundaries

1. **Detection Heuristics**: Presidio pattern recognition and regex inspection detect known patterns and structured formats. Sophisticated steganography or novel encrypted ciphertexts in prompts cannot be detected by regex alone; they are mitigated by destination allowlisting and sovereign local routing.
2. **Local Container Boundary**: Scoped qualification covers single-node containerized deployments. Multi-node distributed clusters require external encrypted mesh (WireGuard / mTLS) and remote secrets managers.
3. **Third-Party Model Retention**: Cloud LLM providers maintain their own logging policies; ZONATA mitigates this by redacting sensitive identifiers before payloads leave the container perimeter.

---

## 4. Final Threat Model Verdict

```
================================================================================
FINAL THREAT MODEL VERDICT: PRODUCTION QUALIFIED — VERIFIED SCOPE
================================================================================
```
