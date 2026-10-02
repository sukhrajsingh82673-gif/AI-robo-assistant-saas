# ZONATA V4 — ENTERPRISE IDENTITY INTEGRATION GUIDE
**SSO, SAML 2.0, OIDC, SCIM 2.0 Provisioning, & Key Management**

## 1. Enterprise SSO Integration
ZONATA V4 integrates natively with corporate identity providers via OpenID Connect (OIDC) and SAML 2.0:
- **Supported IdPs**: Okta, Microsoft Entra ID (Azure AD), Ping Identity, Google Workspace, OneLogin.
- **Protocol Support**: OIDC Authorization Code Flow with PKCE, SAML 2.0 Web Browser SSO Profile.
- **Attribute Mapping**: IdP claims (`email`, `groups`, `department`, `roles`) map directly into `EnterpriseIdentity` attributes in `core/identity_gateway.py`.

---

## 2. Automated Lifecycle via SCIM 2.0
- When an employee joins, changes departments, or leaves the customer organization, the IdP sends SCIM 2.0 events (`/scim/v2/Users`).
- Deprovisioning triggers immediate distributed session revocation across all ZONATA cluster nodes within 50ms, revoking all active agent sessions and delegations.
