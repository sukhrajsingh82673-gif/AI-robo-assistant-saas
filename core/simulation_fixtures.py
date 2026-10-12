"""
ZONATA Universal AI Company Operating System
Deterministic Simulation Fixtures & Database Isolation Engine
=============================================================
Provides clean, reproducible synthetic enterprise data seeding
inside strictly isolated test/simulation database and evidence environments.
Guarantees zero mutation or contamination of developer and production databases.
"""

import os
import time
import json
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional, Tuple

from core.db import db, Database, get_default_db_path
from core.auth import UserManager, UserRole, TenantManager
from core.models import EvidenceStatus, ExecutionClassification

SIM_TENANT_ID = "tnt_sim_enterprise"
SIM_COMPANY_ID = "comp_sim_nova"
SIM_COMPANY_NAME = "Nova Dynamics Simulation Corp"

def get_simulation_storage_dir() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sim_dir = os.path.join(base_dir, "storage", "simulation")
    os.makedirs(sim_dir, exist_ok=True, mode=0o750)
    return sim_dir

def init_simulation_environment(
    db_path: Optional[str] = None,
    evidence_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initializes a completely isolated SQLite database and evidence ledger
    with deterministic synthetic enterprise fixtures for safe simulation qualification.
    """
    sim_dir = get_simulation_storage_dir()
    target_db = db_path or os.path.join(sim_dir, "simulation_company.db")
    target_ev = evidence_path or os.path.join(sim_dir, "simulation_audit_ledger.jsonl")

    # Set environment variables for child processes/threads
    os.environ["ZONATA_DB_PATH"] = os.path.abspath(target_db)
    os.environ["ZONATA_EVIDENCE_PATH"] = os.path.abspath(target_ev)

    # Point global singleton database to the isolated simulation path
    db.set_db_path(target_db)

    # Seed deterministic enterprise fixtures
    fixtures_summary = seed_synthetic_enterprise(target_db)

    return {
        "status": "INITIALIZED",
        "simulation_db": target_db,
        "simulation_evidence": target_ev,
        "tenant_id": SIM_TENANT_ID,
        "company_id": SIM_COMPANY_ID,
        "fixtures": fixtures_summary
    }

def seed_synthetic_enterprise(db_path: str) -> Dict[str, Any]:
    """
    Seeds a full synthetic enterprise into the target database:
    Tenants, Companies, Departments, Users, Roles, Budgets, Policies, and Tokens.
    """
    now = time.time()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # 1. Tenant
        conn.execute(
            """
            INSERT OR REPLACE INTO tenants (tenant_id, name, plan, status, created_at, metadata)
            VALUES (?, ?, 'ENTERPRISE_QUALIFIED', 'ACTIVE', ?, ?)
            """,
            (SIM_TENANT_ID, "Nova Enterprise Tenant (Simulation)", now, json.dumps({"simulation": True, "sandbox_mode": "ISOLATED"}))
        )

        # 2. Company
        conn.execute(
            """
            INSERT OR REPLACE INTO companies (
                company_id, tenant_id, name, country, industry, company_type,
                status, currency, timezone, revenue, cost, contribution,
                understanding_pct, operating_rules, baseline_summary, created_at
            ) VALUES (?, ?, ?, 'IN', 'ENTERPRISE_AI', 'SYNTHETIC_SIMULATION', 'OPERATIONAL', '₹', 'Asia/Kolkata',
                      12500000.0, 4200000.0, 8300000.0, 95.0, ?, ?, ?)
            """,
            (
                SIM_COMPANY_ID,
                SIM_TENANT_ID,
                SIM_COMPANY_NAME,
                json.dumps({"max_single_spend": 250000.0, "require_approval_above": 50000.0}),
                json.dumps({"employees": 24, "annual_run_rate": 50000000.0}),
                now
            )
        )

        # 3. Departments
        departments = [
            ("dept_exec", "Executive Council & Governance", "agt_ceo_sim"),
            ("dept_eng", "AI Systems & Autonomous Engineering", "agt_eng_lead"),
            ("dept_sales", "Client Acquisition & Revenue Operations", "agt_sales_lead"),
            ("dept_ops", "Infrastructure & Automation Logistics", "agt_ops_lead"),
            ("dept_fin", "Corporate Treasury & Risk Compliance", "agt_fin_lead"),
        ]
        for d_id, d_name, mgr_agent in departments:
            conn.execute(
                """
                INSERT OR REPLACE INTO departments (department_id, company_id, tenant_id, name, manager_agent_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (d_id, SIM_COMPANY_ID, SIM_TENANT_ID, d_name, mgr_agent, now)
            )

        # 4. Users with Granular Roles
        users = [
            ("usr_sim_owner", "owner@novadynamics.sim", "Sovereign Host", UserRole.OWNER),
            ("usr_sim_exec", "exec@novadynamics.sim", "Executive Director", UserRole.EXECUTIVE),
            ("usr_sim_mgr", "manager@novadynamics.sim", "Operations Manager", UserRole.MANAGER),
            ("usr_sim_op", "operator@novadynamics.sim", "Autonomous Operator", UserRole.OPERATOR),
            ("usr_sim_audit", "auditor@novadynamics.sim", "Independent Auditor", UserRole.AUDITOR),
        ]
        user_tokens = {}
        for u_id, email, name, role in users:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, tenant_id, email, name, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (u_id, SIM_TENANT_ID, email, name, role, now)
            )
            # Pre-generate valid tokens
            user_obj = {
                "user_id": u_id,
                "tenant_id": SIM_TENANT_ID,
                "company_id": SIM_COMPANY_ID,
                "email": email,
                "role": role,
                "permissions": ["*"] if role == UserRole.OWNER else ["read", "execute"]
            }
            tok = UserManager.generate_token(user_obj, expires_in_seconds=86400 * 30)
            user_tokens[u_id] = {
                "token": tok,
                "role": role,
                "email": email
            }

        # 5. Corporate Budgets
        conn.execute(
            """
            INSERT OR REPLACE INTO enterprise_budgets (
                entity_id, entity_type, tenant_id, company_id, allocated_usd,
                spent_usd, soft_limit_pct, hard_limit_pct, is_frozen, created_at, updated_at
            ) VALUES (?, 'COMPANY', ?, ?, 10000000.0, 150000.0, 80.0, 100.0, 0, ?, ?)
            """,
            (f"bdg_master_{SIM_COMPANY_ID}", SIM_TENANT_ID, SIM_COMPANY_ID, now, now)
        )

        conn.commit()

        return {
            "departments_count": len(departments),
            "users_count": len(users),
            "users": user_tokens,
            "master_budget_inr": 10000000.0
        }

    finally:
        conn.close()

def verify_baseline_integrity(baseline_db_hash: str, baseline_ledger_hash: str) -> Dict[str, Any]:
    """
    Verifies that the original baseline database and evidence ledger have not been modified.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    prod_db = os.path.join(base_dir, "storage", "roboassistant.db")
    prod_ledger = os.path.join(base_dir, "storage", "evidence", "audit_ledger.jsonl")

    current_db_hash = ""
    if os.path.exists(prod_db):
        with open(prod_db, "rb") as f:
            current_db_hash = hashlib.sha256(f.read()).hexdigest()

    current_ledger_hash = ""
    if os.path.exists(prod_ledger):
        with open(prod_ledger, "rb") as f:
            current_ledger_hash = hashlib.sha256(f.read()).hexdigest()

    db_intact = (current_db_hash == baseline_db_hash)
    ledger_intact = (current_ledger_hash == baseline_ledger_hash)

    return {
        "db_intact": db_intact,
        "ledger_intact": ledger_intact,
        "current_db_hash": current_db_hash,
        "baseline_db_hash": baseline_db_hash,
        "current_ledger_hash": current_ledger_hash,
        "baseline_ledger_hash": baseline_ledger_hash,
        "all_preserved": db_intact and ledger_intact
    }
