# ZONATA / URA — AI Security Integration Inventory & Capability Assessment

**Security Component Baseline, Integration Status & License Evidence**  
**Document Classification:** RESTRICTED — AUDIT REPORT  
**Baseline Commit:** `53bd2ef` (ancestry from `45cf91f` verified)  
**Evaluation Date:** October 11, 2026  

---

## 1. Capability Classification Taxonomy

All enterprise security capabilities in the repository are audited and classified into one of six normative categories:
1. `IMPLEMENTED_AND_CONNECTED`: Implemented in source code, wired directly to execution paths, and enforced at runtime.
2. `IMPLEMENTED_BUT_NOT_ENFORCED`: Module exists in repository but lacks an active interceptor or gate in real execution paths.
3. `REGISTERED_ONLY`: Metadata or schema registered in catalog/database without active local code mediation.
4. `TEST_ONLY_OR_MOCKED`: Capability exists only within test fixtures or simulated harnesses.
5. `MISSING`: Capability is not present in the codebase.
6. `BLOCKED_BY_ENVIRONMENT`: Capability requires external daemon or native build toolchain unavailable in current container.

---

## 2. Comprehensive Security Component Inventory

| Component Name | Source Path | Role & Function | License / SPDX | Integration Status | Justification / Notes |
|---|---|---|:---:|:---:|---|
| **ZONATA Company Kernel & AI CEO** | `core/aic_ceo_engine.py` | Sovereign authority root, executive oversight | Proprietary / ZONATA | `IMPLEMENTED_AND_CONNECTED` | Primary authority root; cannot be bypassed. |
| **PolicyEngineV2** | `core/policy_engine_v2.py` | Multi-dimensional ABAC corporate policy engine | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for spend limits, destructive actions, and clearances. |
| **KillSwitchMatrix** | `core/killswitch_matrix.py` | 9-level execution barrier (Global to Tool) | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for Class 4 automated worker isolation. |
| **DataClassificationEngine** | `core/data_classification_engine.py` | Content sensitivity grading & compliance rules | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for data grading across all channels. |
| **ModelDataFirewall** | `core/model_data_firewall.py` | Pre-dispatch prompt inspection & PII redaction | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Upgraded to bridge Presidio and bounded base64 deobfuscation. |
| **ModelGatewayV4** | `core/model_gateway_v4.py` | Central LLM dispatcher & token budget ledger | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for model dispatch and sovereign local failover. |
| **CognitiveModelProvider** | `core/cognitive_model_provider.py` | Multi-provider cognitive execution engine | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with fail-closed DLP across all chat message inputs. |
| **SecurityCenter** | `core/security_center.py` | Threat event collection & incident tracking | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for logging prompt injections and exfiltration attempts. |
| **EvidenceService** | `core/evidence_service.py` | SHA-256 Merkle audit ledger event sealing | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for tamper-evident security records. |
| **EdgeSecurityGateway** | `core/edge_security_gateway.py` | Ingress WAF & IP/tenant rate limiter | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Reused for outer perimeter protection. |
| **GovernedMCPController** | `core/coworker/controllers/mcp_controller.py` | MCP tool invocation mediation | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with outbound argument DLP & inbound injection defense. |
| **GovernedA2AController** | `core/coworker/controllers/a2a_controller.py` | Agent-to-Agent communication gateway | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with cross-tenant isolation and payload sanitization. |
| **GovernedBrowserController** | `core/coworker/controllers/browser_controller.py` | SSRF-guarded browser runtime | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with IPv4/IPv6, integer IPs, port constraints, and redirect revalidation. |
| **GovernedTerminalController** | `core/coworker/controllers/terminal_controller.py` | Sandbox shell & filesystem supervisor | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with realpath confinement and restricted prefix protection. |
| **GovernedMemoryManager** | `core/coworker/memory_tier.py` | Multi-tiered memory architecture | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with pre-persistence credential scrubbing. |
| **GovernedConnectorRegistry** | `core/automation_fabric/connector_registry.py` | External connector mediation & discovery | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | Hardened with outbound DLP parameter checks on external mutations. |
| **SecretManager & VaultClient** | `core/secret_manager.py`, `core/vault_client.py` | Secrets mediation & JIT injection | Apache-2.0 / MPL-2.0 | `IMPLEMENTED_AND_CONNECTED` | In-memory fallback active locally; remote Vault is `BLOCKED_ENVIRONMENT`. |
| **Presidio Compatible Engine** | `core/presidio_dlp_engine.py` | Sensitive entity detection & anonymization | MIT | `IMPLEMENTED_AND_CONNECTED` | **SOVEREIGN INTEGRATION (Integration A)**. Pure-Python local engine with India tax recognizers. |
| **Autonomous AI DLP Gateway**| `core/ai_dlp_gateway.py` | Outbound egress mediation & containment | Apache-2.0 | `IMPLEMENTED_AND_CONNECTED` | **SOVEREIGN INTEGRATION (Integration B)**. Central DLP plane with immediate first-attempt denial. |
| **CI/CD Secret Scanner** | `.github/workflows/ci_cd.yml` | Repo & commit credential screening | ZONATA CI/CD | `IMPLEMENTED_AND_CONNECTED` | **HARDENED INTEGRATION (Integration C)**. High-entropy scanner with scrubbed build logs. |
| **Falco Security Daemon** | `core/observability_stack.py` | Linux kernel runtime security | Apache-2.0 | `BLOCKED_BY_ENVIRONMENT` | Requires Linux eBPF/kmod privileges unavailable in non-root container. |
| **Wazuh Agent** | `core/production_observability.py` | Host intrusion detection system | GPL-2.0 | `BLOCKED_BY_ENVIRONMENT` | Requires external Wazuh Manager daemon. |
| **Gitleaks Binary** | System PATH | Git history secret scanner | MIT | `BLOCKED_BY_ENVIRONMENT` | External binary absent; fulfilled natively via Stage 1 CI/CD scanner. |

---

## 3. Justification of External Integrations (Zero Unnecessary Bloat)

1. **Integration A — Microsoft Presidio Compatible Engine (`core/presidio_dlp_engine.py`)**:
   - *Audit Finding*: Needed extensible recognition of PII, Luhn-valid payment cards, credentials, synthetic canaries, Indian identifiers (PAN, Aadhaar, GSTIN, IFSC), and custom corporate tokens without external dependencies.
   - *Implementation*: Native pure-Python Presidio-compatible engine implementing `RecognizerResult`, `PatternRecognizer`, `PresidioAnalyzerEngine`, and `PresidioAnonymizerEngine`. Accurately recorded as Component 24 in CycloneDX SBOM under MIT license.
2. **Integration B — Autonomous AI DLP Gateway (`core/ai_dlp_gateway.py`)**:
   - *Audit Finding*: Outbound data leaves through 10 distinct routes (LLM, SDK, MCP, A2A, Memory, Browser, Terminal, Connectors, Logs, CI/CD) requiring uniform mediation.
   - *Implementation*: Central egress gateway mediating all channels under 5 Progressive Response Classes, immediate denial on first unauthorized attempt, and automated Class 4 worker containment.
3. **Integration C — CI/CD Pipeline Secret Scanner (`.github/workflows/ci_cd.yml`)**:
   - *Audit Finding*: Must prevent commit of unencrypted production secrets while ensuring CI logs never leak the secret strings.
   - *Implementation*: Integrated multi-pattern high-entropy secret scanner in Stage 1 CI/CD pipeline, screening private keys, tokens, and canary secrets with safe scrubbed logging.
