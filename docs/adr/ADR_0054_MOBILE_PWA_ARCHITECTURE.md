# ADR 0054: Mobile PWA Architecture (Rule 84)

## Status
Accepted

## Context
Enterprise executives, operations managers, and department heads require mobile access to review urgent approvals (e.g., invoices, supply chain purchase orders, access grants), inspect dashboards, and receive push notifications on iOS and Android devices without the development and maintenance overhead of separate native apps.

## Decision
1. **Progressive Web App (PWA) Standard:**
   - Implement a responsive PWA conforming to W3C Web App Manifest specifications (`manifest.json`) and Service Worker standards.
   - Support "Add to Home Screen" installation on iOS (Safari) and Android (Chrome).
2. **Offline Read-Only Capability:**
   - Service worker caches core UI shell, theme assets, and recent approval tickets in IndexedDB/CacheStorage for offline inspection.
   - State-changing actions are disabled when offline, with clear UI indicators preventing stale mutation errors.
3. **Security & Passkey Authentication:**
   - Support FIDO2 / WebAuthn passkey authentication for biometric verification (Face ID / Touch ID / fingerprint) when approving high-risk workflows.
   - Outbound notifications dispatched via Web Push (VAPID standard).

## Consequences
- **Positive:** Single unified web codebase; instant updates without app store review delays; native-like mobile experience.
- **Negative:** iOS Web Push requires user to have installed PWA to home screen (iOS 16.4+).
