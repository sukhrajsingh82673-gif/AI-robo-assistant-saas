# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Object Storage & Artifact Lifecycle Architecture

---

### 1. Multi-Tenant S3 Partitioning Topology
To prevent database bloat and manage large unstructured binaries, ZONATA employs `ObjectStorageService` (`core/object_storage.py`) with tenant-isolated S3/MinIO compliant bucket partitioning:
```
{storage_root}/{tenant_id}/{lifecycle_state}/{sha256[:2]}/{sha256}_{filename}
```
* **Screenshots & Browser Traces**: `s3://zonata-artifacts/{tenant_id}/TEMPORARY/`
* **OpenHands Workspace Dumps**: `s3://zonata-artifacts/{tenant_id}/ACTIVE/`
* **Exported Financial Reports & SBOMs**: `s3://zonata-artifacts/{tenant_id}/ARCHIVED/`
* **Audit Evidences Under Subpoena**: `s3://zonata-artifacts/{tenant_id}/LEGAL_HOLD/`

---

### 2. Artifact Lifecycle State Machine

```
   [UPLOAD]
      |
      +---> TEMPORARY (Default TTL: 7 days, auto-pruned during disk pressure)
      |
      +---> ACTIVE (Live mission working files, preserved during mission)
      |
      +---> ARCHIVED (Immutable completed deliverables, retained 7 years)
      |
      +---> LEGAL_HOLD (STRICT RETENTION: Deletion physically blocked)
      |
      v
   [EXPIRED / DELETED] (Only permitted for non-held TEMPORARY items)
```

> [!IMPORTANT]
> **Legal Hold Guarantee**: Under no circumstances can any cleanup script, storage governor, or administrator command delete an object tagged `LEGAL_HOLD` or `ARCHIVED`.
