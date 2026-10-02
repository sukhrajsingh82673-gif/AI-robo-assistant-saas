# ZONATA V3 — Production Rollback & Downgrade Runbook

## 1. When to Initiate Rollback
A production rollback should be immediately executed if any of the following occur:
- `/readyz` fails for > 60 seconds across > 33% of API pods.
- Cryptographic Merkle chain audit detects `TAMPER_DETECTED` or a broken previous-hash link.
- Split-brain detected with multiple active leader leases.
- Unknown outcome rate exceeds 1.0% in a 15-minute window.

---

## 2. Kubernetes Rolling Rollback
1. **Rollback API Deployment:**
   ```bash
   kubectl rollout undo deployment/zonata-api -n zonata-system
   ```
2. **Rollback Worker Deployment:**
   ```bash
   kubectl rollout undo deployment/zonata-worker -n zonata-system
   ```
3. **Verify Rollout Status:**
   ```bash
   kubectl rollout status deployment/zonata-api -n zonata-system
   ```

---

## 3. Database State Rollback
If a schema migration or bad mutation must be reverted:
1. Stop API and Worker deployments:
   ```bash
   kubectl scale deployment zonata-api --replicas=0 -n zonata-system
   kubectl scale deployment zonata-worker --replicas=0 -n zonata-system
   ```
2. Restore the pre-deployment snapshot:
   ```bash
   python3 -c "from core.disaster_recovery import DisasterRecoveryEngine; DisasterRecoveryEngine().restore_from_snapshot('<snapshot_id>')"
   ```
3. Verify Merkle chain integrity:
   ```bash
   python3 -c "from core.evidence_service import evidence_service; print(evidence_service.verify_chain_integrity('tnt_primary'))"
   ```
4. Restore replicas:
   ```bash
   kubectl scale deployment zonata-api --replicas=3 -n zonata-system
   kubectl scale deployment zonata-worker --replicas=4 -n zonata-system
   ```
