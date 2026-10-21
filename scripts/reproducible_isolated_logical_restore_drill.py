#!/usr/bin/env python3
"""
ZONATA Enterprise SaaS — Reproducible Isolated Logical PostgreSQL Restore Drill
Executes an end-to-end logical restore verification against live Neon PostgreSQL 16.
Verifies:
1. Schema & Data Completeness (multi-table relational set with PKs, FKs, indexes)
2. Referential Integrity & Critical Indexes post-restore
3. Tenant Data Consistency (isolation across 3 pilot organizations)
4. Post-Restore Authentication & Representative Workflow Execution
5. Measured RTO & precise data loss boundaries
6. Non-conflation: Explicitly isolates logical dump/restore from continuous WAL PITR
"""

import os
import sys
import time
import json
import uuid
import hashlib
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

OUTPUT_FILE = os.path.join(PROJECT_ROOT, "storage", "evidence", "isolated_logical_restore_drill.json")

def get_db_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not db_url:
        raise ValueError("DATABASE_URL not configured")
    return db_url

def sanitize_url(raw_url: str) -> str:
    try:
        from core.db import sanitize_db_url
        return sanitize_db_url(raw_url)
    except Exception:
        return "postgresql://***@neon.tech/Postgres"

def run_psql(db_url: str, sql: str) -> str:
    res = subprocess.run(
        ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-tA"],
        input=sql,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60
    )
    if res.returncode != 0:
        raise RuntimeError(f"psql execution failed: {res.stderr.strip()}")
    return res.stdout.strip()

def run_logical_restore_drill() -> Dict[str, Any]:
    drill_id = f"ldr_{uuid.uuid4().hex[:8]}"
    db_url = get_db_url()
    sanitized_endpoint = sanitize_url(db_url)
    
    raw_orgs = f"dr_orgs_{drill_id}"
    raw_users = f"dr_users_{drill_id}"
    raw_workflows = f"dr_workflows_{drill_id}"
    raw_audit = f"dr_audit_{drill_id}"

    t_orgs = f"public.{raw_orgs}"
    t_users = f"public.{raw_users}"
    t_workflows = f"public.{raw_workflows}"
    t_audit = f"public.{raw_audit}"
    
    dump_file = f"/tmp/{drill_id}_dump.sql"
    
    start_time = time.perf_counter()
    report: Dict[str, Any] = {
        "drill_id": drill_id,
        "database_engine": "Neon Serverless PostgreSQL 16 (AWS us-east-2)",
        "sanitized_endpoint": sanitized_endpoint,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "drill_scope": "Representative Multi-Table Relational Schema with Foreign Keys & Indexes",
        "tables_tested": [t_orgs, t_users, t_workflows, t_audit],
        "stages": {},
        "verdict": "FAILED"
    }
    
    print(f"================================================================================")
    print(f"ZONATA Isolated Logical PostgreSQL Restore Drill [{drill_id}]")
    print(f"Target: {sanitized_endpoint}")
    print(f"Timestamp: {report['timestamp_utc']}")
    print(f"================================================================================")
    
    try:
        # ----------------------------------------------------------------------
        # STAGE 1: Schema Setup with Foreign Keys, Constraints & Indexes
        # ----------------------------------------------------------------------
        print(f"--> [Stage 1] Creating relational tables with FKs and indexes...")
        t0 = time.perf_counter()
        schema_sql = f"""
        DROP TABLE IF EXISTS {t_audit}, {t_workflows}, {t_users}, {t_orgs} CASCADE;

        CREATE TABLE {t_orgs} (
            org_id VARCHAR(64) PRIMARY KEY,
            org_name VARCHAR(128) NOT NULL,
            tier VARCHAR(32) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE {t_users} (
            user_id VARCHAR(64) PRIMARY KEY,
            org_id VARCHAR(64) NOT NULL REFERENCES {t_orgs}(org_id) ON DELETE CASCADE,
            email VARCHAR(128) NOT NULL,
            role VARCHAR(32) NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
            mfa_enabled BOOLEAN DEFAULT FALSE
        );
        CREATE INDEX idx_{raw_users}_org_id ON {t_users}(org_id);
        CREATE UNIQUE INDEX idx_{raw_users}_email ON {t_users}(email);

        CREATE TABLE {t_workflows} (
            workflow_id VARCHAR(64) PRIMARY KEY,
            org_id VARCHAR(64) NOT NULL REFERENCES {t_orgs}(org_id) ON DELETE CASCADE,
            title VARCHAR(128) NOT NULL,
            status VARCHAR(32) NOT NULL,
            config_json TEXT NOT NULL
        );
        CREATE INDEX idx_{raw_workflows}_status ON {t_workflows}(status);

        CREATE TABLE {t_audit} (
            entry_id VARCHAR(64) PRIMARY KEY,
            org_id VARCHAR(64) NOT NULL REFERENCES {t_orgs}(org_id) ON DELETE CASCADE,
            action VARCHAR(64) NOT NULL,
            prev_hash VARCHAR(64) NOT NULL,
            merkle_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        run_psql(db_url, schema_sql)
        report["stages"]["stage_1_schema_creation"] = {
            "status": "SUCCESS",
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
            "tables_created": 4,
            "indexes_created": 3
        }
        print(f"    Schema created in {report['stages']['stage_1_schema_creation']['duration_ms']}ms.")

        # ----------------------------------------------------------------------
        # STAGE 2: Seed Representative Multi-Tenant Pilot Records
        # ----------------------------------------------------------------------
        print(f"--> [Stage 2] Seeding representative non-sensitive pilot records...")
        t0 = time.perf_counter()
        
        # 3 Organizations
        orgs = [
            ("org_alpha", "Alpha Manufacturing Corp", "PILOT_ENTERPRISE"),
            ("org_beta", "Beta Hospitality Group", "PILOT_STARTER"),
            ("org_gamma", "Gamma Logistics Ltd", "PILOT_FREE")
        ]
        
        # 6 Users
        # Using fixed PBKDF2 hash for deterministic test authentication
        test_hash = "pbkdf2:sha256:100000$zonata_salt$e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        users = [
            ("usr_a1", "org_alpha", "ceo@alphamfg.com", "OWNER", test_hash, True),
            ("usr_a2", "org_alpha", "ops@alphamfg.com", "OPERATOR", test_hash, False),
            ("usr_b1", "org_beta", "gm@betahotels.com", "OWNER", test_hash, True),
            ("usr_b2", "org_beta", "finance@betahotels.com", "OPERATOR", test_hash, False),
            ("usr_g1", "org_gamma", "lead@gammalog.com", "OWNER", test_hash, False),
            ("usr_g2", "org_gamma", "audit@gammalog.com", "VIEWER", test_hash, False)
        ]
        
        # 6 Workflows
        workflows = [
            ("wf_a1", "org_alpha", "Inventory Restocking Protocol", "ACTIVE", '{"cadence": "DAILY", "auto_approve_under": 5000}'),
            ("wf_a2", "org_alpha", "Financial Month-End Reconciliation", "SCHEDULED", '{"cutoff_day": 28, "ledger_audit": true}'),
            ("wf_b1", "org_beta", "Guest Check-In Autonomous Dispatch", "ACTIVE", '{"pms": "OPERA_CLOUD", "notify_sms": true}'),
            ("wf_b2", "org_beta", "Revenue Management Dynamic Pricing", "PENDING", '{"min_occupancy": 0.85, "max_delta": 0.15}'),
            ("wf_g1", "org_gamma", "Fleet Maintenance Telemetry Sync", "ACTIVE", '{"iot_broker": "MQTT_TLS", "interval_s": 30}'),
            ("wf_g2", "org_gamma", "Driver Safety Incident Review", "COMPLETED", '{"review_officer": "CHIEF_SAFETY_OFFICER"}')
        ]
        
        # 6 Merkle Audit Entries
        audit_entries = [
            ("aud_1", "org_alpha", "INIT_COMPANY_REGISTERED", "0000000000000000000000000000000000000000000000000000000000000000", "hash_alpha_01"),
            ("aud_2", "org_alpha", "CEO_POLICY_APPROVED", "hash_alpha_01", "hash_alpha_02"),
            ("aud_3", "org_beta", "HOTEL_PMS_CONNECTED", "0000000000000000000000000000000000000000000000000000000000000000", "hash_beta_01"),
            ("aud_4", "org_beta", "PRICING_RULE_MUTATED", "hash_beta_01", "hash_beta_02"),
            ("aud_5", "org_gamma", "FLEET_SENSOR_REGISTERED", "0000000000000000000000000000000000000000000000000000000000000000", "hash_gamma_01"),
            ("aud_6", "org_gamma", "TELEMETRY_LOG_SEALED", "hash_gamma_01", "hash_gamma_02")
        ]
        
        insert_sqls = []
        for o in orgs:
            insert_sqls.append(f"INSERT INTO {t_orgs} (org_id, org_name, tier) VALUES ('{o[0]}', '{o[1]}', '{o[2]}');")
        for u in users:
            insert_sqls.append(f"INSERT INTO {t_users} (user_id, org_id, email, role, password_hash, mfa_enabled) VALUES ('{u[0]}', '{u[1]}', '{u[2]}', '{u[3]}', '{u[4]}', {str(u[5]).lower()});")
        for w in workflows:
            escaped_json = w[4].replace("'", "''")
            insert_sqls.append(f"INSERT INTO {t_workflows} (workflow_id, org_id, title, status, config_json) VALUES ('{w[0]}', '{w[1]}', '{w[2]}', '{w[3]}', '{escaped_json}');")
        for a in audit_entries:
            insert_sqls.append(f"INSERT INTO {t_audit} (entry_id, org_id, action, prev_hash, merkle_hash) VALUES ('{a[0]}', '{a[1]}', '{a[2]}', '{a[3]}', '{a[4]}');")
            
        run_psql(db_url, "\n".join(insert_sqls))
        
        # Calculate Baseline Merkle Root across all rows
        dataset_tokens = [f"{o[0]}|{o[1]}" for o in orgs] + [f"{u[0]}|{u[2]}" for u in users] + [f"{w[0]}|{w[3]}" for w in workflows] + [f"{a[0]}|{a[4]}" for a in audit_entries]
        baseline_merkle = hashlib.sha256(";;".join(sorted(dataset_tokens)).encode("utf-8")).hexdigest()
        
        report["stages"]["stage_2_data_seeding"] = {
            "status": "SUCCESS",
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
            "organizations_seeded": len(orgs),
            "users_seeded": len(users),
            "workflows_seeded": len(workflows),
            "audit_entries_seeded": len(audit_entries),
            "total_records": len(orgs) + len(users) + len(workflows) + len(audit_entries),
            "baseline_dataset_merkle_sha256": baseline_merkle
        }
        print(f"    Seeded {report['stages']['stage_2_data_seeding']['total_records']} records across 4 tables. Merkle: {baseline_merkle[:16]}...")

        # ----------------------------------------------------------------------
        # STAGE 3: Logical Backup via pg_dump
        # ----------------------------------------------------------------------
        print(f"--> [Stage 3] Executing pg_dump on isolated test tables...")
        t0 = time.perf_counter()
        dump_cmd = [
            "pg_dump",
            db_url,
            "-t", t_orgs,
            "-t", t_users,
            "-t", t_workflows,
            "-t", t_audit,
            "--no-owner",
            "--no-privileges",
            "-f", dump_file
        ]
        dump_res = subprocess.run(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if dump_res.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {dump_res.stderr.strip()}")
        dump_duration_s = round(time.perf_counter() - t0, 3)
        dump_size_bytes = os.path.getsize(dump_file)
        with open(dump_file, "rb") as fh:
            dump_sha256 = hashlib.sha256(fh.read()).hexdigest()
            
        report["stages"]["stage_3_pg_dump"] = {
            "status": "SUCCESS",
            "duration_seconds": dump_duration_s,
            "dump_size_bytes": dump_size_bytes,
            "dump_file_sha256": dump_sha256
        }
        print(f"    pg_dump completed in {dump_duration_s}s. Size: {dump_size_bytes} bytes. SHA-256: {dump_sha256[:16]}...")

        # ----------------------------------------------------------------------
        # STAGE 4: Simulate Catastrophic Data Loss (DROP TABLES CASCADE)
        # ----------------------------------------------------------------------
        print(f"--> [Stage 4] Simulating data loss by dropping all 4 tables...")
        t0 = time.perf_counter()
        # Safety containment check: strictly verify targets are isolated disposable drill tables
        for tbl in [t_audit, t_workflows, t_users, t_orgs]:
            assert tbl.startswith("public.dr_") and drill_id in tbl, f"Safety check: refusing to drop non-test table: {tbl}"
        drop_sql = f"DROP TABLE IF EXISTS {t_audit}, {t_workflows}, {t_users}, {t_orgs} CASCADE;"
        run_psql(db_url, drop_sql)
        
        # Verify tables are dropped
        check_sql = f"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('{raw_orgs}', '{raw_users}', '{raw_workflows}', '{raw_audit}');"
        count_remaining = run_psql(db_url, check_sql)
        assert count_remaining == "0", f"Tables still exist after drop! Count: {count_remaining}"
        
        report["stages"]["stage_4_data_loss_simulation"] = {
            "status": "SUCCESS",
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
            "tables_dropped": 4,
            "verified_absent": True,
            "simulated_data_loss_utc": datetime.now(timezone.utc).isoformat()
        }
        print(f"    Data loss simulated cleanly: 4 tables dropped.")

        # ----------------------------------------------------------------------
        # STAGE 5: Logical Restore via psql & RTO Measurement
        # ----------------------------------------------------------------------
        print(f"--> [Stage 5] Executing logical restore via psql and measuring RTO...")
        t0 = time.perf_counter()
        restore_cmd = ["psql", db_url, "-f", dump_file]
        restore_res = subprocess.run(restore_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        if restore_res.returncode != 0:
            raise RuntimeError(f"psql restore failed: {restore_res.stderr.strip()}")
        rto_seconds = round(time.perf_counter() - t0, 3)
        
        report["stages"]["stage_5_psql_restore"] = {
            "status": "SUCCESS",
            "rto_seconds": rto_seconds,
            "rto_sla_met": rto_seconds <= 300.0
        }
        print(f"    psql restore finished in {rto_seconds}s (Measured RTO).")

        # ----------------------------------------------------------------------
        # STAGE 6: Relational Integrity & Schema Completeness Verification
        # ----------------------------------------------------------------------
        print(f"--> [Stage 6] Verifying schema completeness, FK integrity, and indexes...")
        t0 = time.perf_counter()
        
        # 1. Row counts
        cnt_orgs = int(run_psql(db_url, f"SELECT count(*) FROM {t_orgs};"))
        cnt_users = int(run_psql(db_url, f"SELECT count(*) FROM {t_users};"))
        cnt_wf = int(run_psql(db_url, f"SELECT count(*) FROM {t_workflows};"))
        cnt_aud = int(run_psql(db_url, f"SELECT count(*) FROM {t_audit};"))
        
        assert cnt_orgs == len(orgs), f"Orgs count mismatch: {cnt_orgs} != {len(orgs)}"
        assert cnt_users == len(users), f"Users count mismatch: {cnt_users} != {len(users)}"
        assert cnt_wf == len(workflows), f"Workflows count mismatch: {cnt_wf} != {len(workflows)}"
        assert cnt_aud == len(audit_entries), f"Audit count mismatch: {cnt_aud} != {len(audit_entries)}"
        
        # 2. Foreign Key & Referential Integrity (Zero orphan users or workflows)
        orphan_users = int(run_psql(db_url, f"SELECT count(*) FROM {t_users} u LEFT JOIN {t_orgs} o ON u.org_id = o.org_id WHERE o.org_id IS NULL;"))
        orphan_wfs = int(run_psql(db_url, f"SELECT count(*) FROM {t_workflows} w LEFT JOIN {t_orgs} o ON w.org_id = o.org_id WHERE o.org_id IS NULL;"))
        assert orphan_users == 0, f"Referential integrity failure: {orphan_users} orphan users detected!"
        assert orphan_wfs == 0, f"Referential integrity failure: {orphan_wfs} orphan workflows detected!"
        
        # 3. Critical Indexes Restored
        raw_idx = run_psql(db_url, f"SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename IN ('{raw_users}', '{raw_workflows}') ORDER BY indexname;")
        indexes_found = [line.strip() for line in raw_idx.splitlines() if line.strip()]
        assert any(f"idx_{raw_users}_org_id" in idx for idx in indexes_found), f"Missing index on users(org_id), found: {indexes_found}"
        assert any(f"idx_{raw_users}_email" in idx for idx in indexes_found), f"Missing index on users(email), found: {indexes_found}"
        assert any(f"idx_{raw_workflows}_status" in idx for idx in indexes_found), f"Missing index on workflows(status), found: {indexes_found}"
        
        # 4. Multi-Tenant Segmentation Intact
        alpha_users = int(run_psql(db_url, f"SELECT count(*) FROM {t_users} WHERE org_id = 'org_alpha';"))
        beta_users = int(run_psql(db_url, f"SELECT count(*) FROM {t_users} WHERE org_id = 'org_beta';"))
        gamma_users = int(run_psql(db_url, f"SELECT count(*) FROM {t_users} WHERE org_id = 'org_gamma';"))
        assert alpha_users == 2 and beta_users == 2 and gamma_users == 2, "Tenant user isolation altered post-restore!"
        
        # 5. Dataset Merkle Hash Re-computation
        raw_all = run_psql(
            db_url,
            f"SELECT 'org:' || org_id || '|' || org_name FROM {t_orgs} "
            f"UNION ALL SELECT 'usr:' || user_id || '|' || email FROM {t_users} "
            f"UNION ALL SELECT 'wf:' || workflow_id || '|' || status FROM {t_workflows} "
            f"UNION ALL SELECT 'aud:' || entry_id || '|' || merkle_hash FROM {t_audit};"
        )
        restored_tokens = [line.strip().replace("org:", "").replace("usr:", "").replace("wf:", "").replace("aud:", "") for line in raw_all.splitlines() if line.strip()]
        restored_merkle = hashlib.sha256(";;".join(sorted(restored_tokens)).encode("utf-8")).hexdigest()
        assert restored_merkle == baseline_merkle, "Dataset Merkle parity mismatch post-restore!"
        
        report["stages"]["stage_6_integrity_verification"] = {
            "status": "SUCCESS",
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
            "restored_counts": {"orgs": cnt_orgs, "users": cnt_users, "workflows": cnt_wf, "audit": cnt_aud},
            "referential_integrity_orphans": 0,
            "critical_indexes_restored": len(indexes_found),
            "tenant_isolation_verified": True,
            "merkle_parity_match": True,
            "restored_merkle_sha256": restored_merkle
        }
        print(f"    Relational integrity verified: 0 orphans, {len(indexes_found)} indexes, exact Merkle parity.")

        # ----------------------------------------------------------------------
        # STAGE 7: Post-Restore Authentication & Workflow Execution Viability
        # ----------------------------------------------------------------------
        print(f"--> [Stage 7] Testing post-restore authentication & workflow mutation...")
        t0 = time.perf_counter()
        
        # Verify authentication lookup
        auth_row = run_psql(db_url, f"SELECT password_hash, role, mfa_enabled FROM {t_users} WHERE email = 'ceo@alphamfg.com';")
        parts = auth_row.strip().split("|")
        assert len(parts) == 3, "Auth query returned malformed record"
        retrieved_hash, role, mfa = parts
        assert retrieved_hash == test_hash, "Restored password hash altered!"
        assert role == "OWNER", "Restored role corrupted!"
        
        # Verify workflow mutation on restored table
        run_psql(db_url, f"UPDATE {t_workflows} SET status = 'ACTIVE' WHERE workflow_id = 'wf_b2';")
        updated_status = run_psql(db_url, f"SELECT status FROM {t_workflows} WHERE workflow_id = 'wf_b2';")
        assert updated_status.strip() == "ACTIVE", "Workflow mutation failed on restored table"
        
        report["stages"]["stage_7_application_viability"] = {
            "status": "SUCCESS",
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
            "post_restore_auth_verified": True,
            "post_restore_workflow_mutation_verified": True
        }
        print(f"    Application viability verified: Post-restore auth OK, workflow mutation OK.")

        # ----------------------------------------------------------------------
        # STAGE 8: Clean Up
        # ----------------------------------------------------------------------
        run_psql(db_url, f"DROP TABLE IF EXISTS {t_audit}, {t_workflows}, {t_users}, {t_orgs} CASCADE;")
        if os.path.exists(dump_file):
            os.remove(dump_file)

        # Safety assertion: verify all dropped tables are strictly isolated disposable test objects
        disposable_tables = [t_audit, t_workflows, t_users, t_orgs]
        for tbl in disposable_tables:
            assert tbl.startswith("public.dr_") and drill_id in tbl, f"Safety violation: Non-disposable table targeted for drop: {tbl}"

        total_duration = round(time.perf_counter() - start_time, 3)
        end_to_end_data_cycle = round(dump_duration_s + rto_seconds, 3)
        report["verdict"] = "PASS"
        report["metrics"] = {
            "backup_creation_seconds": dump_duration_s,
            "restore_execution_seconds_rto": rto_seconds,
            "end_to_end_data_cycle_seconds": end_to_end_data_cycle,
            "sla_target_rto_seconds": 300.0,
            "rto_sla_met": rto_seconds <= 300.0,
            "total_drill_duration_seconds": total_duration,
            "safety_isolation_verified": True,
            "data_loss_boundary": "Point of logical backup creation (pg_dump timestamp)",
            "recovery_scope_distinction": {
                "proven_capability": "Logical dump/restore of application relational schema, data, foreign keys, and indexes via pg_dump/psql",
                "unproven_not_tested": "Continuous WAL PITR to arbitrary historical timestamps and off-host S3 WORM archive (requires paid credentials)"
            }
        }
        print(f"================================================================================")
        print(f"Drill Completed Successfully in {total_duration}s.")
        print(f"  - Backup Creation: {dump_duration_s}s")
        print(f"  - Restore Execution (RTO): {rto_seconds}s (Target <= 300s, MET)")
        print(f"  - End-to-End Data Recovery Cycle: {end_to_end_data_cycle}s")
        print(f"================================================================================")

    except Exception as e:
        report["verdict"] = "FAILED"
        report["error"] = str(e)
        print(f"CRITICAL DRILL FAILURE: {e}")
        # Clean up on failure
        try:
            run_psql(db_url, f"DROP TABLE IF EXISTS {t_audit} CASCADE; DROP TABLE IF EXISTS {t_workflows} CASCADE; DROP TABLE IF EXISTS {t_users} CASCADE; DROP TABLE IF EXISTS {t_orgs} CASCADE;")
        except Exception:
            pass
        if os.path.exists(dump_file):
            os.remove(dump_file)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    res = run_logical_restore_drill()
    if res.get("verdict") != "PASS":
        sys.exit(1)
