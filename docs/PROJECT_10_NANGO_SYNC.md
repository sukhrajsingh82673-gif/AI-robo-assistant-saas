# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Project 10: Nango — Data Synchronization & Provenance Architecture

### 1. Governed Data Synchronization Modes

ZONATA integrates Nango's synchronization engine across five operational modes:

1. **`INITIAL`**: Complete initial ingest of provider entities into ZONATA storage upon connection activation.
2. **`INCREMENTAL`**: Delta-based synchronization using high-watermark cursors or timestamp checkpoints.
3. **`WEBHOOK_TRIGGERED`**: Event-driven delta refresh triggered by verified inbound webhooks.
4. **`SCHEDULED`**: Cron-driven background jobs (e.g., nightly financial reconciliation).
5. **`MANUAL`**: Operator-initiated synchronization from the ZONATA Cockpit.

---

### 2. Data Minimization & Privacy Protection

ZONATA does not blindly copy entire third-party databases:
* **Selective Field Ingestion**: Only fields required for active AI workforce tasks are retained.
* **Sensitive Token Redaction**: Access tokens, internal session cookies, and private encryption keys are scrubbed before storage in `nango_sync_records`.

---

### 3. Immutable Provenance Metadata

Every synchronized record stored in SQLite includes immutable provenance tracking:

```json
{
  "SOURCE_SYSTEM": "NANGO_GOVERNED_ADAPTER",
  "SOURCE_PROVIDER": "salesforce",
  "SOURCE_OBJECT": "contacts",
  "SOURCE_ID": "rec_salesforce_contacts_1",
  "SOURCE_CONNECTION": "conn_salesforce_1e54443b",
  "SYNC_TIME": 1727863294.12,
  "SYNC_RUN": "sync_3d09a1bf",
  "TENANT": "tnt_primary",
  "COMPANY": "comp_primary"
}
```

This guarantees complete traceability from external enterprise database rows to AI workforce decisions and verified business outcomes.
