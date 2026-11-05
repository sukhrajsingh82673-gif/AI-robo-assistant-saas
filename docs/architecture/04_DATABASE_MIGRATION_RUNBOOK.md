# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Database Migration & Schema Versioning Runbook

---

### 1. Overview & Tooling
ZONATA provides an automated, transactionally safe database migration framework managed by `migrations/migration_manager.py`. It guarantees forward progress, SHA-256 migration checksum validation, and atomic rollbacks.

* **Tracking Table**: `schema_migrations`
* **Supported Dialects**: PostgreSQL (Production) and SQLite (Development/Test)
* **Directory Structure**:
  - `migrations/common/`: Universal schema changes applicable to all dialects.
  - `migrations/pg/`: PostgreSQL-specific DDL (UUID extensions, JSONB indexes, BigSerial sequences).
  - `migrations/sqlite/`: SQLite-specific DDL optimizations.

---

### 2. Standard Migration Execution Procedure

#### Step 1: Pre-Migration Backup Drill
Before executing schema changes on production database:
```bash
# 1. Trigger automated online backup drill
python3 -c "from core.disaster_recovery import dr_manager; print(dr_manager.create_full_backup())"

# 2. Verify SHA-256 manifest integrity
python3 -c "from core.disaster_recovery import dr_manager; print(dr_manager.verify_backup_integrity())"
```

#### Step 2: Check Migration Status
```bash
python3 -c "from migrations.migration_manager import MigrationManager; print(MigrationManager().get_status())"
```

#### Step 3: Apply Pending Migrations
```bash
python3 -c "from migrations.migration_manager import MigrationManager; print(MigrationManager().apply_pending_migrations())"
```

---

### 3. SQLite to PostgreSQL Live Migration Procedure

When migrating production data from an existing SQLite store to a managed PostgreSQL cluster:

1. **Provision Managed PostgreSQL 15+ Cluster**:
   - Enable SSL (`sslmode=require`).
   - Configure PgBouncer pooler (`pool_mode = transaction`, `max_client_conn = 1000`, `default_pool_size = 25`).
2. **Execute PostgreSQL Schema DDL**:
   ```bash
   export DATABASE_URL="postgresql://zonata_admin:PASSWORD@pg-primary.prod.internal:5432/zonata_production?sslmode=require"
   python3 -c "from migrations.migration_manager import MigrationManager; MigrationManager().apply_pending_migrations()"
   ```
3. **Run ETL Migration Pipeline**:
   - Extract data per tenant in dependency order: `tenants` → `companies` → `departments` → `employees` → `missions` → `governed_agents` → `merkle_evidence_events`.
   - Validate row counts and foreign key integrity.
4. **Verification & Cutover**:
   - Run `python3 -c "from core.database_engine import engine; print(engine.health_check())"`
   - Direct API pods to `DATABASE_URL`.
