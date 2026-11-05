# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Reality & Business Outcome Verification Specification

---

### 1. Constitutional Requirement: TASK_SUCCESS != BUSINESS_OUTCOME
In ZONATA, internal execution success (HTTP 200, tool exit code 0, LLM completion) NEVER automatically implies business reality. Every mutating action must define:
1. `EXPECTED_STATE`: The specific factual condition that constitutes success.
2. `OBSERVATION_METHOD`: The authoritative read path to check physical or external reality.
3. `VERIFICATION_RESULT`: The evaluation outcome (`VERIFIED`, `UNKNOWN_OUTCOME`, `FAILED`).
4. `CONFIDENCE`: The numeric certainty score (0.0 to 1.0).

---

### 2. Universal Verification Matrix

| Subsystem / Action Type | Internal Execution | Reality Observation Method | Verification Criteria |
| :--- | :--- | :--- | :--- |
| **Nango / HubSpot CRM** | `POST /contacts` returns 200 | `GET /contacts/{id}` via separate read replica | Contact exists with matching email and properties |
| **Stripe / Financial Mutation**| `POST /charges` returns 200 | Query provider transaction balance / settlement record | Transaction status is `succeeded` and funds settled |
| **Cloudbeds PMS / Hotel Booking**| `POST /reservations` returns 200 | Inspect PMS reservation ledger via read query | Reservation code exists and dates are locked |
| **OpenHands / File Creation** | Bash script exits 0 | Inspect filesystem sha256 checksum and file mode | File exists on disk with expected cryptographic hash |
| **Browser Use / Form Submit** | Playwright click returns 0 | Query post-submission confirmation banner / URL path | Confirmation URL loaded and confirmation DOM element visible |
| **Temporal Durable Saga** | Activity completed | Query workflow event history & saga compensation state | Saga steps verified in order without compensation rollback |
