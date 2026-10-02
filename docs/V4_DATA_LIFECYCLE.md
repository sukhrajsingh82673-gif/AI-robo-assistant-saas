# ZONATA V4 — ENTERPRISE DATA LIFECYCLE & DELETION VERIFICATION
**Retention Management, Legal Holds, & Zero-Remnant Cryptographic Shredding**

## 1. Lifecycle Overview
Enterprise compliance (GDPR Article 17, CCPA, HIPAA, SOC 2) requires strict controls over data retention and permanent deletion. The `DataLifecycleManager` (`core/data_lifecycle_manager.py`) coordinates retention sweeps, legal holds, and cryptographic deletion.

---

## 2. Legal Holds
- Any authorized legal officer can place a `legal_hold` on specific documents, customer accounts, or employee audit logs.
- **Constitutional Invariant**: `LEGAL_HOLD_PREVENTS_DELETION`.
- Attempting to delete or purge an object under an active legal hold throws `LegalHoldViolationError`.
- Legal holds must be explicitly released by an authorized identity before any deletion can proceed.

---

## 3. Cryptographic Purge & Zero-Remnant Verification
When an object is permanently purged:
1. **Index Deletion**: All chunks and vector embeddings associated with `object_id` are removed from `knowledge_index_chunks`.
2. **Relational Shredding**: Content in `corporate_data_objects` is overwritten with `[PURGED]` and status transitioned to `PURGED`.
3. **Evidence Certificate**: A cryptographic event (`DATA_OBJECT_PURGED`) is recorded in the Merkle Evidence Ledger.
4. **Certificate Returned**: The caller receives a `DeletionVerificationCertificate` proving storage and index removal.
