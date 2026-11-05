# ZONATA V10 IDENTITY AND SECRET REPORT
## Enterprise Identity Boundaries, Secret Vault Reference URIs & Sovereign Key Governance

**Document Version**: 1.0.0  
**Modules**: `core/secret_vault.py` & `core/sovereign_key_manager.py`  
**Classification**: SECURITY & CRYPTOGRAPHIC GOVERNANCE  

---

## 1. Identity Trust Taxonomy

To prevent privilege confusion, ZONATA strictly separates identities into non-interchangeable tiers:

| Identity Class | Trust Authority | Creation Right | Execution Ceiling |
| :--- | :--- | :--- | :--- |
| **Human Owner** | Sovereign Root / OIDC / MFA | Sovereign Bootstrap | Unlimited (Subject to dual-key for root) |
| **Enterprise User**| Enterprise IdP (SAML / SCIM) | HR Directory Sync | Scoped by assigned RBAC role |
| **Service Identity**| mTLS / API Gateway Token | Platform Deployer | Scoped by microservice policy |
| **AI Employee** | Employee Factory V7 Contract | AI CEO / Owner Approved | Bounded by Employment Contract & Policy Matrix |
| **Agent Tool** | Tool Factory V2 Hash | Tool Registry | Sandboxed POSIX execution |

> [!CAUTION]
> **Constitutional Invariant**: AI-generated identities can **NEVER** become trusted Human Owner identities. AI employees cannot elevate their own authority or modify sovereign credentials.

---

## 2. Secret Vault Reference URIs

Plaintext credentials are eliminated from application configurations, database rows, and logs. Secrets are referenced exclusively through the `secret://` URI scheme:

```
secret://<tenant_id>/<secret_id>
```

### Vault Capabilities:
- **Encrypted Storage**: Payloads encrypted using authenticated symmetric envelopes.
- **Audit Logging**: Every access attempt logged to `enterprise_secret_access_audit` with actor ID and timestamp.
- **Rotation & Expiry**: Native support for automatic version incrementation and time-to-live expiration.
- **Leakage Scanning**: Automated pattern matcher scans logs and prompts for accidental plaintext exposure.

---

## 3. Sovereign Root Key Governance
- **Access Control**: Root sovereign keys are accessible **exclusively** to the Human Owner.
- **Dual-Key Authorization**: Rotation or replacement of root keys requires independent cryptographic signatures from two authorized human keys.
- **AI Exclusion Barrier**: Any attempt by an AI agent (`AI_CEO`, `DEPT_HEAD`, `SPECIALIST`) to access, inspect, or rotate sovereign root keys raises a `SovereignAuthorityViolation` and halts the agent.
