# ZONATA / URA — Backup, Restore & Rollback Procedures

This document outlines procedures for database backups, disaster recovery, workflow version rollback, and GitOps release rollback.

---

## 1. Hot Database Backup & Recovery

### Automated Online SQLite Backup
ZONATA utilizes SQLite's native online backup API, implemented in [`core/remote_disaster_recovery.py`](../../core/remote_disaster_recovery.py):

```python
import sqlite3
import hashlib

def perform_hot_backup(source_db_path: str, backup_dest_path: str) -> str:
    src_conn = sqlite3.connect(source_db_path)
    dst_conn = sqlite3.connect(backup_dest_path)
    with dst_conn:
        src_conn.backup(dst_conn, pages=100)
    dst_conn.close()
    src_conn.close()

    # Compute checksum of backup artifact
    hasher = hashlib.sha256()
    with open(backup_dest_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
```

### Backup Verification & Restoring
1. **Verification:**
   `sqlite3 storage/roboassistant_backup.db "PRAGMA integrity_check;"` -> Must return `ok`.
2. **Restoration:**
   ```bash
   # 1. Stop active worker and API processes
   kill -15 $(pgrep -f api_server.py)
   # 2. Swap restored file into place
   cp storage/roboassistant_backup.db storage/roboassistant.db
   # 3. Restart daemon
   python3 api_server.py 8080 &
   ```

---

## 2. Workflow Version Rollback

ZONATA maintains immutable versions of all published workflows:
- When a workflow is published, its version increments.
- If a regression occurs in version `N`, roll back to version `N-1`:

```bash
curl -X POST http://127.0.0.1:8080/api/automation/workflows/<workflow_id>/rollback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <valid_token>" \
  -d '{"target_version": 1}'
```
**Invariants:**
- Rolling back a workflow invalidates all stale pending approvals for version `N`.
- New execution leases will strictly bind to target version `N-1`.

---

## 3. GitOps Container Release Rollback

Argo CD controlled delivery allows instant release rollback:
```bash
python3 -c "
from core.automation_fabric.connector_registry import connector_registry
res = connector_registry.execute_connector_operation(
    connector_id='conn_argocd_gitops',
    operation='rollback_release',
    parameters={'app_name': 'zonata-production'},
    tenant_id='tnt_primary'
)
print('GitOps rollback result:', res['data']['rollback_status'])
"
```

---

## 4. Feature Flag Emergency Rollback

Using OpenFeature, an offending capability can be disabled instantly without restarting processes:
```bash
python3 -c "
from core.automation_fabric.connector_registry import connector_registry
connector_registry.execute_connector_operation(
    connector_id='conn_openfeature_flags',
    operation='rollback_flag',
    parameters={'flag_key': 'enable_experimental_feature'},
    tenant_id='tnt_primary'
)
"
```
