# Google Gemma 4 Rollback & Sovereign Safety Runbook
## ZONATA / URA Universal AI Company Operating System

---

## 1. Emergency Containment Procedure (Section 24)

### Purpose
When unexpected behavioral deviations, security alerts, or anomalous expenditures occur, the Sovereign Human Owner can immediately freeze all active automated operations across all departments without relying on Gemma 4 availability.

### Triggering Emergency STOP via UI
1. Navigate to `http://localhost:8080/`.
2. Click the red **🛑 Emergency STOP** button in the header bar.
3. Confirm containment prompt. All active missions immediately transition to `PAUSED` and an immutable Merkle audit record is sealed.

### Triggering Emergency STOP via API
```bash
curl -s -X POST http://localhost:8080/api/v8/emergency-stop \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tnt_primary" \
  -H "X-Company-ID: comp_primary" \
  -d '{"reason": "Immediate containment ordered by Sovereign Owner"}'
```

### Response
```json
{
  "success": true,
  "command_type": "EMERGENCY_STOP",
  "emergency_halted": true,
  "paused_missions_count": 4,
  "evidence_digest": "sha256:0c610069...",
  "ceo_response": "EMERGENCY CONTAINMENT ACTIVATED: Paused 4 active missions. Audit state preserved."
}
```

---

## 2. Resuming Operations

### Via UI
Click the green **▶️ Resume** button in the console header.

### Via API
```bash
curl -s -X POST http://localhost:8080/api/v8/emergency-resume \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tnt_primary" \
  -H "X-Company-ID: comp_primary" \
  -d '{"reason": "Operations verified and resumed by Owner"}'
```

---

## 3. Rollback Procedure

Every operational mission executed by the planning engine specifies an idempotent rollback handler:
- `rollback_revenue_management`: Reverts dynamic room ADR pricing corridors to the pre-dispatch baseline.
- `pause_ad_campaign`: Immediately pauses digital campaign ad spend across marketing connectors.
- `kill_sandbox_process`: Terminates sandboxed subprocesses in the Universal Terminal.

Rollback records are immutably appended to the Evidence Ledger with SHA-256 cryptographic proofs.
