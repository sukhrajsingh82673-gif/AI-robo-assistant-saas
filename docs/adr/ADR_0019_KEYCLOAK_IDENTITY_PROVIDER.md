# ADR 0019: Keycloak as Authoritative B2B Identity Provider & Dual-Run Migration Plan

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 42 (Least privilege and default deny), Rule 44 (Owner principal cannot be minted)

---

## 1. Context and Problem Statement
ZONATA currently uses in-code HMAC-SHA256 token issuance and verification in `core/auth.py`. While effective for early prototypes, enterprise B2B customers require:
- Single Sign-On (SAML 2.0 / OIDC) and enterprise IdP federation (Okta, Azure AD, Google Workspace).
- Phishing-resistant FIDO2/WebAuthn passkeys.
- SCIM 2.0 user lifecycle provisioning and deprovisioning.
- Multi-tenant organization scoping where each company manages its own directory and policy.
- Step-up authentication for high-risk actions.

## 2. Alternatives Considered

| IdP Solution | License | Evaluation & Characteristics | Decision |
| :--- | :--- | :--- | :--- |
| **Keycloak 26.x** | **Apache-2.0** | Enterprise grade, native B2B Organizations feature, WebAuthn/Passkeys, SCIM API (in 26.8), step-up auth, MCP auth server support. | **ADOPTED (Lead):** Permissive Apache-2.0 license, full sovereignty, self-hostable, zero external subscription dependencies. |
| **Zitadel** | **Apache-2.0** | Cloud-native multi-tenant IdP written in Go. Excellent B2B org model. | **STRONG RUNNER-UP:** Excellent architecture, but smaller ecosystem and plugin catalog compared to Keycloak. |
| **Ory (Kratos/Hydra)** | **Apache-2.0 / BSL** | Modular architecture, but Ory Network has BSL/commercial boundaries on management tooling. | **REJECTED:** Fragmented components and licensing boundaries. |
| **Authentik** | **GPL-3.0** | Feature-rich Python/Go IdP. | **REJECTED:** GPL-3.0 presents boundary and legal review obstacles for core platform integration. |

## 3. Decision
1. **Adopt Keycloak 26.x (Apache-2.0)** as the authoritative Identity Provider.
2. **Organization Isolation:** Keycloak's Organizations feature maps directly to ZONATA tenants (`tenant_id`).
3. **Owner Principal Protection (Rule 44):**
   - The `OWNER` role is explicitly blocked from SCIM sync, IdP group mapping, and API provisioning.
   - Any attempt to mint or elevate an identity to `OWNER` via SAML/OIDC claim or SCIM payload is caught by the ingress validator and rejected with HTTP 403 `UNAUTHORIZED_OWNER_PROMOTION`.
4. **Dual-Run Migration Strategy (Zero-Downtime):**
   - **Phase 1 (Dual-Run):** `core/auth.py` accepts both Keycloak-issued OIDC JWTs (verified via JWKS) and legacy HMAC tokens.
   - **Phase 2 (Shadow Verification):** User sign-ins authenticate against Keycloak; successful authentication issues Keycloak JWTs while syncing user records.
   - **Phase 3 (Cutover & Deprecation):** HMAC token issuance disabled. Legacy token acceptance restricted to a 24-hour expiration window.
   - **Rollback Mechanism:** Setting `ZONATA_AUTH_FALLBACK_HMAC=1` instantly re-enables HMAC signing and verification without database schema changes.

## 4. Consequences
- **Positive:** Enterprise SSO readiness, WebAuthn passkey support, centralized user lifecycle and credential revocation.
- **Negative:** Adds a Java/Quarkus container to deployment topology; local development requires Keycloak test container or mock OIDC provider.
