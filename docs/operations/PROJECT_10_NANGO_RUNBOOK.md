# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Operational Runbook & Administrator Guide

### 1. Provisioning a New Connection

1. Navigate to **Integrations & SaaS** in the ZONATA Cockpit (`/web/index.html`).
2. Click **Integration Catalog**.
3. Select the desired enterprise provider (e.g. Salesforce, Stripe, QuickBooks) and click **Connect**.
4. In production environments, complete the OAuth consent screen.
5. In development/testing environments, an isolated sandbox connection is automatically provisioned and validated.

---

### 2. Testing Connection Health

```bash
# Via REST API
curl -s -X POST http://localhost:8080/api/nango/connections/{connection_id}/test
```
* Response `{"success": true, "message": "Provider endpoint reachable and credentials valid."}` indicates operational health (`HEALTHY`).
* If `AUTH_REQUIRED`, trigger re-authorization.

---

### 3. Triggering Data Synchronization

```bash
# Sync contacts model
curl -s -X POST http://localhost:8080/api/nango/connections/{connection_id}/sync \
  -H "Content-Type: application/json" \
  -d '{"model": "contacts", "limit": 50}'
```

---

### 4. Engaging Emergency Multi-Scope KillSwitch

```bash
# Halt all interactions with Salesforce
curl -s -X POST http://localhost:8080/api/nango/killswitch \
  -H "Content-Type: application/json" \
  -d '{"scope": "PROVIDER", "target_id": "salesforce", "action": "halt", "reason": "Security audit"}'

# Resume Salesforce interactions
curl -s -X POST http://localhost:8080/api/nango/killswitch \
  -H "Content-Type: application/json" \
  -d '{"scope": "PROVIDER", "target_id": "salesforce", "action": "resume"}'
```

---

### 5. Running Canonical Scenario Verification

```bash
# Run Section 95 Grand Acceptance Test
curl -s -X POST http://localhost:8080/api/nango/demo/scenarios \
  -H "Content-Type: application/json" \
  -d '{"scenario": "SECTION_95"}'
```
