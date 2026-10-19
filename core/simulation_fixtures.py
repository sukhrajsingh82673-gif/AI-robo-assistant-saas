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
    os.environ["STRICT_ISOLATION_REQUIRED"] = "1"
    os.environ["ZONATA_ALLOW_HOST_SHELL"] = "0"

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
        "strict_isolation": True,
        "allow_host_shell": False,
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
            INSERT INTO tenants (tenant_id, name, plan, status, created_at, metadata)
            VALUES (?, ?, 'ENTERPRISE_QUALIFIED', 'ACTIVE', ?, ?)
            ON CONFLICT (tenant_id) DO UPDATE SET
                name = EXCLUDED.name,
                plan = EXCLUDED.plan,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata
            """,
            (SIM_TENANT_ID, "Nova Enterprise Tenant (Simulation)", now, json.dumps({"simulation": True, "sandbox_mode": "ISOLATED"}))
        )

        # 2. Company
        conn.execute(
            """
            INSERT INTO companies (
                company_id, tenant_id, name, country, industry, company_type,
                status, currency, timezone, revenue, cost, contribution,
                understanding_pct, operating_rules, baseline_summary, created_at
            ) VALUES (?, ?, ?, 'IN', 'ENTERPRISE_AI', 'SYNTHETIC_SIMULATION', 'OPERATIONAL', '₹', 'Asia/Kolkata',
                      12500000.0, 4200000.0, 8300000.0, 95.0, ?, ?, ?)
            ON CONFLICT (company_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                name = EXCLUDED.name,
                country = EXCLUDED.country,
                industry = EXCLUDED.industry,
                company_type = EXCLUDED.company_type,
                status = EXCLUDED.status,
                currency = EXCLUDED.currency,
                timezone = EXCLUDED.timezone,
                revenue = EXCLUDED.revenue,
                cost = EXCLUDED.cost,
                contribution = EXCLUDED.contribution,
                understanding_pct = EXCLUDED.understanding_pct,
                operating_rules = EXCLUDED.operating_rules,
                baseline_summary = EXCLUDED.baseline_summary
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

        # 3. 9 Enterprise Departments
        departments = [
            ("dept_exec", "Executive Council & AI CEO", "agt_ceo_sim"),
            ("dept_fin", "Finance & Corporate Treasury", "agt_fin_lead"),
            ("dept_sales", "Sales & Client Operations", "agt_sales_lead"),
            ("dept_support", "Customer Support & Success", "agt_support_lead"),
            ("dept_mktg", "Marketing & Brand Growth", "agt_mktg_lead"),
            ("dept_ops", "Operations & Infrastructure Logistics", "agt_ops_lead"),
            ("dept_eng", "AI Systems & Autonomous Engineering", "agt_eng_lead"),
            ("dept_hr", "Human Resources & Talent Governance", "agt_hr_lead"),
            ("dept_procure", "Procurement & Vendor Governance", "agt_procure_lead"),
        ]
        for d_id, d_name, mgr_agent in departments:
            conn.execute(
                """
                INSERT INTO departments (department_id, company_id, tenant_id, name, manager_agent_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (department_id) DO UPDATE SET
                    company_id = EXCLUDED.company_id,
                    tenant_id = EXCLUDED.tenant_id,
                    name = EXCLUDED.name,
                    manager_agent_id = EXCLUDED.manager_agent_id
                """,
                (d_id, SIM_COMPANY_ID, SIM_TENANT_ID, d_name, mgr_agent, now)
            )

            # Seed Manager Employee for each department
            conn.execute(
                """
                INSERT INTO employees (
                    agent_id, company_id, department_id, tenant_id, role,
                    department, manager, responsibilities, objectives,
                    allowed_tools, allowed_hosts, data_access, budget_limit,
                    spending_limit, authority_ceiling, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'AI CEO', ?, ?, ?, ?, ?, 100000.0, 25000.0, 'SUPERVISED_AUTONOMOUS', ?)
                ON CONFLICT (agent_id) DO UPDATE SET
                    company_id = EXCLUDED.company_id,
                    department_id = EXCLUDED.department_id,
                    role = EXCLUDED.role,
                    department = EXCLUDED.department
                """,
                (
                    mgr_agent, SIM_COMPANY_ID, d_id, SIM_TENANT_ID,
                    f"{d_name} Department Lead", d_name,
                    json.dumps([f"Lead operations for {d_name}"]),
                    json.dumps(["Maintain operational KPIs", "Ensure budget compliance"]),
                    json.dumps(["*"]), json.dumps(["*"]), json.dumps(["*"]), now
                )
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
                INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
                ON CONFLICT (user_id) DO UPDATE SET
                    tenant_id = EXCLUDED.tenant_id,
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    role = EXCLUDED.role,
                    status = EXCLUDED.status
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

        # 5. Multi-Tier Budgets (Company, Departments, Agents)
        conn.execute(
            """
            INSERT INTO enterprise_budgets (
                entity_id, entity_type, tenant_id, company_id, allocated_usd,
                spent_usd, soft_limit_pct, hard_limit_pct, is_frozen, created_at, updated_at
            ) VALUES (?, 'COMPANY', ?, ?, 10000000.0, 150000.0, 80.0, 100.0, 0, ?, ?)
            ON CONFLICT (entity_id) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                tenant_id = EXCLUDED.tenant_id,
                company_id = EXCLUDED.company_id,
                allocated_usd = EXCLUDED.allocated_usd,
                spent_usd = EXCLUDED.spent_usd,
                soft_limit_pct = EXCLUDED.soft_limit_pct,
                hard_limit_pct = EXCLUDED.hard_limit_pct,
                is_frozen = EXCLUDED.is_frozen,
                updated_at = EXCLUDED.updated_at
            """,
            (f"bdg_master_{SIM_COMPANY_ID}", SIM_TENANT_ID, SIM_COMPANY_ID, now, now)
        )

        for d_id, _, _ in departments:
            conn.execute(
                """
                INSERT INTO enterprise_budgets (
                    entity_id, entity_type, tenant_id, company_id, allocated_usd,
                    spent_usd, soft_limit_pct, hard_limit_pct, is_frozen, created_at, updated_at
                ) VALUES (?, 'DEPARTMENT', ?, ?, 500000.0, 15000.0, 80.0, 100.0, 0, ?, ?)
                ON CONFLICT (entity_id) DO UPDATE SET
                    allocated_usd = EXCLUDED.allocated_usd,
                    spent_usd = EXCLUDED.spent_usd,
                    updated_at = EXCLUDED.updated_at
                """,
                (d_id, SIM_TENANT_ID, SIM_COMPANY_ID, now, now)
            )

        # 6. CRM Customers & Deals (Sales Department)
        customers = [
            ("cust_sim_01", "Vertex Health AI", "ENTERPRISE", "Healthcare AI", 240000.0, 720000.0),
            ("cust_sim_02", "Apex FinTech Global", "ENTERPRISE", "Financial Services", 480000.0, 1440000.0),
            ("cust_sim_03", "Nexus Logistics Group", "GROWTH", "Logistics & Supply", 120000.0, 360000.0),
        ]
        for c_id, c_name, tier, ind, arr, ltv in customers:
            conn.execute(
                """
                INSERT INTO crm_customers (
                    customer_id, tenant_id, company_id, name, tier, industry,
                    status, health_score, arr, ltv, sla_level, renewal_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', 96.5, ?, ?, 'Standard 99.9%', '2027-12-31', ?, ?)
                ON CONFLICT (customer_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    tier = EXCLUDED.tier,
                    arr = EXCLUDED.arr,
                    ltv = EXCLUDED.ltv
                """,
                (c_id, SIM_TENANT_ID, SIM_COMPANY_ID, c_name, tier, ind, arr, ltv, now, now)
            )

        deals = [
            ("deal_sim_01", "cust_sim_01", "Enterprise AI Diagnostics Suite", "proposal", 120000.0, 0.7),
            ("deal_sim_02", "cust_sim_02", "Realtime Fraud Detection Fabric", "negotiation", 240000.0, 0.85),
            ("deal_sim_03", "cust_sim_03", "Autonomous Fleet Dispatch Pilot", "discovery", 60000.0, 0.4),
        ]
        for d_id, c_id, title, stage, val, prob in deals:
            conn.execute(
                """
                INSERT INTO crm_deals (
                    deal_id, tenant_id, company_id, customer_id, title,
                    stage, value, probability, closing_date, owner, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '2026-11-30', 'agt_sales_lead', ?, ?)
                ON CONFLICT (deal_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    stage = EXCLUDED.stage,
                    value = EXCLUDED.value,
                    probability = EXCLUDED.probability
                """,
                (d_id, SIM_TENANT_ID, SIM_COMPANY_ID, c_id, title, stage, val, prob, now, now)
            )

        # 7. Missions & Causality Chains
        missions = [
            ("mis_sim_01", "dept_exec", "Autonomous Operations Optimization Q4", "agt_ceo_sim", "EXECUTE", 85),
            ("mis_sim_02", "dept_sales", "Accelerate Enterprise AI Deal Velocity", "agt_sales_lead", "EXECUTE", 60),
            ("mis_sim_03", "dept_eng", "Zero-Downtime Multi-Region Database Hardening", "agt_eng_lead", "COMPLETED", 100),
        ]
        for m_id, d_id, m_title, owner, status, prog in missions:
            conn.execute(
                """
                INSERT INTO missions (
                    mission_id, company_id, department_id, tenant_id, title,
                    owner_agent, department, target_outcome, status, progress,
                    started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Verified Autonomous Outcome', ?, ?, ?)
                ON CONFLICT (mission_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    progress = EXCLUDED.progress
                """,
                (m_id, SIM_COMPANY_ID, d_id, SIM_TENANT_ID, m_title, owner, d_id, status, prog, now)
            )

        conn.execute(
            """
            INSERT INTO business_causality_chains (
                chain_id, tenant_id, company_id, strategy_goal, mission_id,
                revenue_attributed, cost_attributed, verified_outcome, created_at
            ) VALUES (?, ?, ?, 'Accelerate Enterprise AI Deal Velocity', 'mis_sim_02', 360000.0, 24000.0, 'VERIFIED_SUCCESS', ?)
            ON CONFLICT (chain_id) DO NOTHING
            """,
            ("chain_sim_01", SIM_TENANT_ID, SIM_COMPANY_ID, now)
        )

        conn.commit()

        return {
            "departments_count": len(departments),
            "users_count": len(users),
            "users": user_tokens,
            "master_budget_usd": 10000000.0,
            "crm_customers_count": len(customers),
            "crm_deals_count": len(deals),
            "missions_count": len(missions)
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
