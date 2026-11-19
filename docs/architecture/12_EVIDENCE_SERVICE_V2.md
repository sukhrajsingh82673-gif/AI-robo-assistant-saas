# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Production Evidence Service V2 (Transactional Merkle Ledger)

---

### 1. Authoritative Storage Architecture
The `EvidenceServiceV2` (`core/evidence_service.py`) replaces node-local file locking with transactional database persistence in the relational table `merkle_evidence_events`:

```sql
CREATE TABLE merkle_evidence_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_index BIGSERIAL NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    company_id VARCHAR(64) NOT NULL,
    mission_id VARCHAR(64),
    workflow_id VARCHAR(64),
    agent_id VARCHAR(64),
    action_id VARCHAR(64),
    event_type VARCHAR(64) NOT NULL,
    canonical_payload_hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    current_hash VARCHAR(64) NOT NULL,
    causality_id VARCHAR(64),
    verification_state VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    artifact_storage_ref TEXT,
    timestamp DOUBLE PRECISION NOT NULL
);
CREATE UNIQUE INDEX idx_ev_v2_seq ON merkle_evidence_events(event_index);
CREATE INDEX idx_ev_v2_tenant ON merkle_evidence_events(tenant_id);
CREATE INDEX idx_ev_v2_cur_hash ON merkle_evidence_events(current_hash);
```

---

### 2. Cryptographic Hash Chaining Specification

Each event is bound to its immediate predecessor using SHA-256:
```python
chain_str = f"{event_id}|{event_index}|{tenant_id}|{event_type}|{payload_hash}|{previous_hash}|{timestamp}"
current_hash = hashlib.sha256(chain_str.encode("utf-8")).hexdigest()
```
* **Genesis State**: The initial block for any tenant begins with `previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"`.
* **Sequential Integrity**: Sequences are guaranteed monotonically increasing via database serial generation.
* **Continuous Verification**: `evidence_service.verify_chain_integrity(tenant_id)` walks every record from Genesis to tip, proving 0 forks, 0 tampered payloads, and 100% hash continuity.
