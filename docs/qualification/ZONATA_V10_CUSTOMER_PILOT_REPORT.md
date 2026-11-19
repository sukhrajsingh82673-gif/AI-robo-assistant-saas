# ZONATA V10 CUSTOMER PILOT REPORT
## Enterprise Pilot Readiness, Customer Onboarding Protocol & Blocked Items

**Document Version**: 1.0.0  
**Target Pilot Customer**: Enterprise Hospitality Partner (Resort & Spa Operations)  
**Classification**: COMMERCIAL ENGAGEMENT & DEPLOYMENT RUNBOOK  

---

## 1. Pilot Status & Claim Discipline

| Dimension | Status | Evidence Classification | Operational Readiness |
| :--- | :--- | :--- | :--- |
| **Sovereign Software Engine** | `READY` | `LOCAL_REAL_EXECUTION` | Deployed and verified on sovereign host. |
| **Connector Integration Contract**| `READY` | `LOCAL_REAL_EXECUTION` | Verified with 100x idempotency & HMAC checks. |
| **Live Third-Party Credentials** | `BLOCKED` | `BLOCKED (CREDENTIALS_REQUIRED)` | Awaiting customer production OAuth2 keys. |
| **Commercial Pilot Execution** | `PENDING` | `PENDING_PILOT_AUTHORIZATION` | Scheduled post-credential onboarding. |

> [!IMPORTANT]
> ZONATA will **never claim** that a live hotel pilot is active until real customer production credentials have been onboarded and authenticated via live TLS handshakes.

---

## 2. Five-Phase Customer Pilot Protocol

```
Phase 1: Security & Credential Onboarding (Customer delivers OAuth2 Client ID/Secret)
   ↓
Phase 2: Passive Shadow Telemetry (Read-only observation of ADR, Occupancy, RevPAR)
   ↓
Phase 3: Bounded Autonomous Mutations (Rate adjustments restricted to ±5% and <₹10,000/day)
   ↓
Phase 4: Closed-Loop Night Audit (Automated folio settlement & zero-variance ledger check)
   ↓
Phase 5: Executive P&L Review (Human Owner reviews verified business outcomes)
```

---

## 3. Required Customer Pre-Flight Checklist
- [ ] Sign Enterprise Data Processing Agreement (DPA).
- [ ] Provision OAuth2 Client ID and Client Secret in Oracle Opera Cloud / Cloudbeds.
- [ ] Configure outbound webhook to ZONATA `/api/webhooks/pms` with HMAC secret.
- [ ] Define designated Human Owner YubiKey / SecP256k1 public key for dual authorization.
