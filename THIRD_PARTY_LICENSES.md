# ZONATA UNIVERSAL AI CO-WORKER FABRIC — THIRD-PARTY LICENSES
## Software Bill of Materials (SBOM) & Open-Source License Governance

**Version**: 1.0.0  
**Classification**: SUPPLY CHAIN & LEGAL GOVERNANCE  

---

## 1. Third-Party Integration Inventory

All external open-source technologies integrated into the Co-worker Fabric are maintained as replaceable capability adapters. Source code is never copied or forked unnecessarily.

| Project / Component | Repository | Version / Tag | License | License Compatibility | Adapter Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenAdapt** | `github.com/OpenAdaptAI/OpenAdapt` | `v0.12.0` | MIT License | Permissive (Compatible) | `core/coworker/providers/openadapt_provider.py` |
| **Playwright** | `github.com/microsoft/playwright-python`| `v1.46.0` | Apache-2.0 | Permissive (Compatible) | `core/coworker/providers/playwright_provider.py` |
| **Robocorp RPA** | `github.com/robocorp/rpaframework` | `v28.5.1` | Apache-2.0 | Permissive (Compatible) | `core/coworker/providers/rpa_providers.py` |
| **OpenRPA** | `github.com/open-rpa/openrpa` | `v1.4.54` | MPL-2.0 | Permissive / File-Scoped | `core/coworker/providers/rpa_providers.py` |
| **Agent S / UI-TARS**| `github.com/bytedance/ui-tars` | `v0.1.2` | Apache-2.0 | Permissive (Compatible) | `core/coworker/providers/visual_cua_provider.py` |
| **Model Context Protocol**| `github.com/modelcontextprotocol/python-sdk`| `v0.1.0` | MIT License | Permissive (Compatible) | `core/coworker/providers/computer_use_mcp_provider.py` |
| **Cryptography** | `github.com/pyca/cryptography` | `v43.0.0` | Apache-2.0 / BSD | Permissive (Compatible) | Sovereign Vault Subsystem |

---

## 2. Supply-Chain Governance Invariants

1. **No GPL Contamination**: No viral copyleft (GPLv3 / AGPLv3) software is bundled into the core sovereign runtime.
2. **Pinned Versions**: All production adapter dependencies are pinned to specific semantic versions with cryptographic hashes.
3. **Sovereign Admission**: Third-party adapters are subjected to automated dependency vulnerability scanning (`pip audit`, `bandit`) before release promotion.
